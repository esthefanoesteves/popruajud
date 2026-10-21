"""Reconhecimento facial com OpenCV: YuNet detecta o rosto e SFace gera o modelo.

RF-05 (gerar o modelo), RF-08 (reconhecer no posto), RF-14 (conferência), RNF-09 (limiar).

RD-03: este módulo só compara um rosto com modelos de pessoas credenciadas que
consentiram. Não guarda imagens, não classifica emoções nem comportamento.
RD-04: abaixo do limiar o resultado é "conferir", nunca "negar".
"""

from __future__ import annotations

import threading
from collections.abc import Hashable, Iterable
from pathlib import Path

import numpy as np

LARGURA_MAXIMA = 640  # fotos de celular são reduzidas antes da detecção


class ModelosAusentes(RuntimeError):
    pass


class FaceNaoEncontrada(ValueError):
    pass


def similaridade_cosseno(a: np.ndarray, b: np.ndarray) -> float:
    """Mesma medida do FaceRecognizerSF com FR_COSINE."""
    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def identificar(
    modelo: np.ndarray, candidatos: Iterable[tuple[Hashable, np.ndarray]], limiar: float
) -> tuple[Hashable | None, float]:
    """Compara o rosto capturado com os credenciados e devolve o mais parecido.

    Devolve (chave, similaridade) se passar do limiar, ou (None, melhor similaridade)
    para o operador conferir (RF-14 / RD-04).
    """
    melhor_chave, melhor = None, -1.0
    for chave, referencia in candidatos:
        s = similaridade_cosseno(modelo, referencia)
        if s > melhor:
            melhor_chave, melhor = chave, s
    if melhor >= limiar:
        return melhor_chave, melhor
    return None, melhor


class ReconhecedorFacial:
    def __init__(self, caminho_detector: Path, caminho_reconhecedor: Path, limiar: float):
        import cv2  # import tardio: o resto do sistema roda sem OpenCV carregado

        for caminho in (caminho_detector, caminho_reconhecedor):
            if not Path(caminho).exists():
                raise ModelosAusentes(
                    f"Modelo não encontrado: {caminho}. Rode: python scripts/baixar_modelos.py"
                )
        self._cv2 = cv2
        self._detector = cv2.FaceDetectorYN.create(str(caminho_detector), "", (320, 320))
        self._reconhecedor = cv2.FaceRecognizerSF.create(str(caminho_reconhecedor), "")
        self.limiar = limiar
        self._trava = threading.Lock()  # o detector guarda o tamanho da última imagem

    def extrair_modelo(self, imagem: bytes) -> np.ndarray:
        """Recebe a foto (JPEG/PNG) e devolve o modelo facial do maior rosto."""
        cv2 = self._cv2
        img = cv2.imdecode(np.frombuffer(imagem, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise FaceNaoEncontrada("Imagem inválida.")
        altura, largura = img.shape[:2]
        if largura > LARGURA_MAXIMA:
            escala = LARGURA_MAXIMA / largura
            img = cv2.resize(img, (LARGURA_MAXIMA, round(altura * escala)))
            altura, largura = img.shape[:2]
        with self._trava:
            self._detector.setInputSize((largura, altura))
            _, rostos = self._detector.detect(img)
            if rostos is None or len(rostos) == 0:
                raise FaceNaoEncontrada("Nenhum rosto encontrado. Peça para olhar para a câmera.")
            maior = max(rostos, key=lambda r: r[2] * r[3])
            alinhado = self._reconhecedor.alignCrop(img, maior)
            return self._reconhecedor.feature(alinhado).copy()

    def confere(self, modelo: np.ndarray, referencia: np.ndarray) -> tuple[bool, float]:
        """Comparação 1:1 com a referência de uma pessoa específica."""
        s = similaridade_cosseno(modelo, referencia)
        return s >= self.limiar, s


_instancia: ReconhecedorFacial | None = None
_trava_instancia = threading.Lock()


def obter_reconhecedor() -> ReconhecedorFacial:
    """Carrega os modelos uma vez por processo."""
    global _instancia
    if _instancia is None:
        with _trava_instancia:
            if _instancia is None:
                from django.conf import settings

                _instancia = ReconhecedorFacial(
                    settings.FACE_MODELO_DETECTOR,
                    settings.FACE_MODELO_RECONHECEDOR,
                    settings.FACE_LIMIAR,
                )
    return _instancia
