"""Baixa os modelos abertos do OpenCV Zoo usados no reconhecimento facial.

YuNet (detecção, licença MIT) e SFace (reconhecimento, licença Apache 2.0).
Uso: python scripts/baixar_modelos.py
"""

import sys
import urllib.request
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent / "modelos"
BASE = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models"
MODELOS = {
    "face_detection_yunet_2023mar.onnx": f"{BASE}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx": f"{BASE}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}


def main() -> int:
    PASTA.mkdir(exist_ok=True)
    for nome, url in MODELOS.items():
        destino = PASTA / nome
        if destino.exists() and destino.stat().st_size > 100_000:
            print(f"ok  {nome} (já existe)")
            continue
        print(f"... {nome}")
        urllib.request.urlretrieve(url, destino)
        if destino.stat().st_size < 100_000:
            destino.unlink()
            print(f"Falhou: {nome} veio vazio. Baixe manualmente de {url}")
            return 1
        print(f"ok  {nome} ({destino.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
