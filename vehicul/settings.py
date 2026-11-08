"""Setări Django – sistem hibrid de avertizare a vehiculelor (L4, driverele MCD)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or (
    "dev-only-schimba-in-productie" if os.environ.get("DJANGO_DEBUG", "0") == "1" else "set-DJANGO_SECRET_KEY"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
_allowed_host_env = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
if _allowed_host_env.strip() == "*":
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [host.strip() for host in _allowed_host_env.split(",") if host.strip()]

INSTALLED_APPS = [
    "mcd.apps.McdConfig",
    "web",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "vehicul.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    },
]

WSGI_APPLICATION = "vehicul.wsgi.application"

# Driverele nu folosesc baza de date.
DATABASES = {}

LANGUAGE_CODE = "ro"
TIME_ZONE = "Europe/Bucharest"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
