"""
Configurações do projeto ZapPro - SaaS de Autoresposta WhatsApp.
Preparado para futura integração com Mercado Pago e WhatsApp API Oficial.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-217m2hny331p8ynln3c7$hg*eg=24vxwcz%w^&sc_dt(^u5+0s"

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

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

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Autenticação
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "accounts:login"

# E-mail (desenvolvimento - console)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "ZapPro <noreply@zappro.com.br>"

# Serviço WhatsApp (Baileys Node.js)
WHATSAPP_SERVICE_URL = "http://localhost:3001"
WHATSAPP_SERVICE_SECRET = "zappro-secret-key-change-in-production"
WHATSAPP_SESSIONS_DIR = BASE_DIR / "sessoes"

# Autoresposta — atraso e "digitando..." (fixo, leve, anti-bloqueio)
AUTORESPOSTA_DELAY_SEGUNDOS = 2
AUTORESPOSTA_MOSTRAR_DIGITANDO = True

# Contato do administrador para assinaturas
ADMIN_WHATSAPP = "5531982435468"
ADMIN_WHATSAPP_DISPLAY = "(31) 98243-5468"

# Futura integração Mercado Pago
# MERCADOPAGO_ACCESS_TOKEN = ""
# MERCADOPAGO_WEBHOOK_SECRET = ""

# Futura integração WhatsApp API Oficial
# WHATSAPP_OFFICIAL_API_URL = ""
# WHATSAPP_OFFICIAL_TOKEN = ""
