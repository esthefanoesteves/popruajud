"""Configurações do PopRuaJud.

Os requisitos citados (RNF-xx) estão no projeto do Notion e no README.
"""

import base64
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _carregar_env(caminho: Path) -> None:
    """Lê um .env simples (CHAVE=valor) sem sobrescrever o ambiente."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip())


_carregar_env(BASE_DIR / ".env")

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY fora do modo de desenvolvimento.")
    SECRET_KEY = "dev-inseguro-nao-usar-em-producao"

ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "mutirao",
    "credenciamento",
    "acesso",
    "entregas",
    "auditoria",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Sem DATABASE_URL, SQLite para desenvolvimento. Em produção, PostgreSQL.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# RNF-08: senhas com bcrypt.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# RNF-08: sessão expira em 15 minutos sem uso.
SESSION_COOKIE_AGE = 15 * 60
SESSION_SAVE_EVERY_REQUEST = True

# RNF-08: HTTPS fora do desenvolvimento.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SSL_REDIRECT", "1") == "1"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# RNF-08: chave AES-256 das fotos e modelos faciais.
_chave = os.environ.get("CHAVE_DADOS_FACIAIS", "")
if _chave:
    CHAVE_DADOS_FACIAIS = base64.b64decode(_chave)
elif DEBUG:
    CHAVE_DADOS_FACIAIS = b"chave-de-desenvolvimento-32bytes"
else:
    raise ImproperlyConfigured("Defina CHAVE_DADOS_FACIAIS fora do modo de desenvolvimento.")
if len(CHAVE_DADOS_FACIAIS) != 32:
    raise ImproperlyConfigured("CHAVE_DADOS_FACIAIS precisa ter 32 bytes (AES-256).")

# Reconhecimento facial (OpenCV YuNet + SFace). Modelos baixados por scripts/baixar_modelos.py.
FACE_MODELO_DETECTOR = BASE_DIR / "modelos" / "face_detection_yunet_2023mar.onnx"
FACE_MODELO_RECONHECEDOR = BASE_DIR / "modelos" / "face_recognition_sface_2021dec.onnx"
# RNF-09: limiar ajustável. 0.363 é o valor indicado pelo OpenCV para o SFace (cosseno).
FACE_LIMIAR = float(os.environ.get("FACE_LIMIAR", "0.363"))
