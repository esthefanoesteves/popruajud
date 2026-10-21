"""Cifragem em repouso das fotos e modelos faciais (RNF-08: AES-256)."""

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

_TAM_NONCE = 12


def cifrar(dados: bytes) -> bytes:
    """AES-256-GCM. O nonce aleatório vai nos 12 primeiros bytes."""
    nonce = os.urandom(_TAM_NONCE)
    return nonce + AESGCM(settings.CHAVE_DADOS_FACIAIS).encrypt(nonce, dados, None)


def decifrar(blob: bytes) -> bytes:
    nonce, cifrado = blob[:_TAM_NONCE], blob[_TAM_NONCE:]
    return AESGCM(settings.CHAVE_DADOS_FACIAIS).decrypt(nonce, cifrado, None)
