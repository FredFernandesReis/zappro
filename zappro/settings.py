"""
Configurações do projeto ZapPro - SaaS de Autoresposta WhatsApp.
Preparado para futura integração com Mercado Pago e WhatsApp API Oficial.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv():
    """Carrega .env local sem depender de python-dotenv."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)
    except OSError:
        pass


_load_dotenv()

SECRET_KEY = "django-insecure-217m2hny331p8ynln3c7$hg*eg=24vxwcz%w^&sc_dt(^u5+0s"

# Produção: DEBUG=False esconde páginas de erro detalhadas do público
DEBUG = False

ALLOWED_HOSTS = [
    "zappro.sbs",
    "www.zappro.sbs",
    "187.124.11.110",
    "localhost",
    "127.0.0.1",
    ".ngrok-free.app",
    ".ngrok-free.dev",
    ".ngrok.app",
    ".ngrok.io",
]

CSRF_TRUSTED_ORIGINS = [
    "https://zappro.sbs",
    "https://www.zappro.sbs",
    "http://zappro.sbs",
    "http://www.zappro.sbs",
    # Domínios temporários do ngrok (preenchidos via NGROK_URL)
]

_ngrok_url = os.environ.get("NGROK_URL", "").rstrip("/")
if _ngrok_url:
    CSRF_TRUSTED_ORIGINS.append(_ngrok_url)
    # Também aceita http do mesmo host
    if _ngrok_url.startswith("https://"):
        CSRF_TRUSTED_ORIGINS.append("http://" + _ngrok_url[len("https://"):])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps ZapPro
    "accounts",
    "dashboard",
    "whatsapp",
    "subscriptions",
    "autorespostas",
    "reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "subscriptions.middleware.SubscriptionMiddleware",
]

ROOT_URLCONF = "zappro.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "subscriptions.context_processors.subscription_context",
            ],
        },
    },
]

WSGI_APPLICATION = "zappro.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# WhiteNoise: encontra arquivos mesmo com DEBUG=False (ngrok/VPS)
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Autenticação
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "dashboard:landing"

# E-mail (desenvolvimento - console)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "ZapPro <noreply@zappro.com.br>"

# Serviço WhatsApp (Baileys Node.js)
# API_SECRET do PM2 (ecosystem.config.cjs) DEVE ser igual a WHATSAPP_SERVICE_SECRET
WHATSAPP_SERVICE_URL = os.environ.get("WHATSAPP_SERVICE_URL", "http://127.0.0.1:3001")
WHATSAPP_SERVICE_SECRET = os.environ.get("WHATSAPP_SERVICE_SECRET", "um-segredo-forte")
WHATSAPP_SESSIONS_DIR = BASE_DIR / "sessoes"

# Autoresposta — atraso e "digitando..." (fixo, leve, anti-bloqueio)
AUTORESPOSTA_DELAY_SEGUNDOS = 4
AUTORESPOSTA_DELAY_VARIACAO_SEGUNDOS = 3
AUTORESPOSTA_MOSTRAR_DIGITANDO = True
BOAS_VINDAS_INTERVALO_MINUTOS = 20

# Contato do administrador para assinaturas
ADMIN_WHATSAPP = "5531986427264"
ADMIN_WHATSAPP_DISPLAY = "(31) 98642-7264"

# Cakto — pagamento (use variáveis de ambiente em produção)
CAKTO_CLIENT_ID = os.environ.get("CAKTO_CLIENT_ID", "")
CAKTO_CLIENT_SECRET = os.environ.get("CAKTO_CLIENT_SECRET", "")
CAKTO_CHECKOUT_URL = os.environ.get(
    "CAKTO_CHECKOUT_URL",
    "https://pay.cakto.com.br/h4c46wm_1021071",
)
# Secret que VOCÊ define no painel Cakto (Integrações > Webhooks)
CAKTO_WEBHOOK_SECRET = os.environ.get("CAKTO_WEBHOOK_SECRET", "zappro-cakto-webhook-secreto")
CAKTO_PLAN_DAYS = int(os.environ.get("CAKTO_PLAN_DAYS", "30"))
# True = tenta embutir o checkout em iframe na página do ZapPro
CAKTO_EMBED_IFRAME = os.environ.get("CAKTO_EMBED_IFRAME", "1") not in ("0", "false", "False")
