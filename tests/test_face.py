import os
from pathlib import Path

import numpy as np
import pytest
from django.conf import settings

from acesso.face import ReconhecedorFacial, identificar, similaridade_cosseno


def test_similaridade_cosseno():
    a = np.array([1.0, 0.0])
    assert similaridade_cosseno(a, a) == pytest.approx(1.0)
    assert similaridade_cosseno(a, np.array([0.0, 1.0])) == pytest.approx(0.0)


def test_identifica_o_mais_parecido_acima_do_limiar():
    candidatos = [("0001", np.array([1.0, 0.0, 0.0])), ("0002", np.array([0.0, 1.0, 0.0]))]
    chave, s = identificar(np.array([0.9, 0.1, 0.0]), candidatos, limiar=0.8)
    assert chave == "0001" and s > 0.8


def test_abaixo_do_limiar_vai_para_conferencia():
    """RD-04: sem confirmação, não há chave; o operador decide."""
    candidatos = [("0001", np.array([1.0, 0.0]))]
    chave, s = identificar(np.array([0.0, 1.0]), candidatos, limiar=0.363)
    assert chave is None and s < 0.363


# Teste com os modelos reais: roda quando os .onnx estão em modelos/ e
# FACE_IMAGEM_TESTE aponta para uma foto com um rosto.
_imagem = os.environ.get("FACE_IMAGEM_TESTE", "")
_modelos = Path(settings.FACE_MODELO_DETECTOR).exists() and Path(settings.FACE_MODELO_RECONHECEDOR).exists()


@pytest.mark.skipif(not (_modelos and _imagem), reason="modelos ou FACE_IMAGEM_TESTE ausentes")
def test_mesma_foto_confere():
    rec = ReconhecedorFacial(settings.FACE_MODELO_DETECTOR, settings.FACE_MODELO_RECONHECEDOR, settings.FACE_LIMIAR)
    foto = Path(_imagem).read_bytes()
    modelo = rec.extrair_modelo(foto)
    confirmou, s = rec.confere(modelo, rec.extrair_modelo(foto))
    assert modelo.shape == (1, 128)
    assert confirmou and s > 0.99
