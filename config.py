"""
config.py — Configuración central de la aplicación.
Carga variables de entorno y define todas las constantes de negocio.
"""
import os
import re
from datetime import timedelta


# ── .env loader (sin dependencias externas) ───────────────────────────────────
def _load_dotenv():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _, _v = _line.partition('=')
                    os.environ.setdefault(_k.strip(), _v.strip())


_load_dotenv()

# ── Flask ─────────────────────────────────────────────────────────────────────
SECRET_KEY                = os.environ.get('SECRET_KEY', 'cambia-esta-clave-en-produccion')
PERMANENT_SESSION_LIFETIME = timedelta(days=30)

# ── Base de datos ─────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host':     os.environ.get('DB_HOST',     'localhost'),
    'user':     os.environ.get('DB_USER',     'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME',     'arrocera_db'),
}

# ── Archivos ──────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# ── Email ─────────────────────────────────────────────────────────────────────
MAIL_SERVER   = os.environ.get('MAIL_SERVER',   'smtp.gmail.com')
MAIL_PORT     = int(os.environ.get('MAIL_PORT', '587'))
MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS',  'true').lower()  == 'true'
MAIL_USE_SSL  = os.environ.get('MAIL_USE_SSL',  'false').lower() == 'true'
MAIL_TIMEOUT  = int(os.environ.get('MAIL_TIMEOUT', '20'))
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
MAIL_FROM_NAME = os.environ.get('MAIL_FROM_NAME', 'Contabilidad Arroceras')
APP_URL        = os.environ.get('APP_URL',       'http://localhost:5000')
AUTH_SEND_LOGIN_ALERT = os.environ.get('AUTH_SEND_LOGIN_ALERT', 'true').lower() == 'true'

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_CODE_TTL_MINUTES = 10
AUTH_CODE_MAX_ATTEMPTS = 5

# ── Trabajadores ──────────────────────────────────────────────────────────────
WORKER_OPTIONS = [
    'administrador', 'agronomo', 'bombero', 'despalillador',
    'fumigador', 'operario', 'operario_maquinas', 'polivalente',
    'regador', 'transportador', 'versatil',
]

# ── Negocio ───────────────────────────────────────────────────────────────────
MAX_GASTO_POR_HA  = 11_000_000
TOTAL_HA          = 20
MAX_GASTO_TOTAL   = 220_000_000
MIN_CARGAS        = 2000
MIN_CARGAS_POR_HA = 100
KG_POR_CARGA      = 62.5
CONCEPTOS_PROHIBIDOS = ['aceite', 'acpm']

# ── Validación ────────────────────────────────────────────────────────────────
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
