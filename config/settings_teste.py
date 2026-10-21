"""Configurações dos testes automatizados (pytest)."""

import base64
import os

os.environ.setdefault("DJANGO_SECRET_KEY", "chave-somente-para-testes")
os.environ.setdefault("CHAVE_DADOS_FACIAIS", base64.b64encode(b"t" * 32).decode())
os.environ.setdefault("DJANGO_SSL_REDIRECT", "0")

from .settings import *  # noqa: E402,F401,F403

# Hash rápido nos testes; o bcrypt continua valendo fora deles.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
