"""
extensions.py — Instancia central de Flask.
Importar desde aquí en todos los módulos de rutas para evitar importaciones circulares.
"""
import os
from datetime import timedelta
from flask import Flask, session, redirect, url_for as _url_for
from flask_wtf.csrf import CSRFProtect, CSRFError
from config import SECRET_KEY, PERMANENT_SESSION_LIFETIME, UPLOAD_FOLDER

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = PERMANENT_SESSION_LIFETIME

# ── Upload / request limits ───────────────────────────────────────────────────
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024   # 8 MB max upload
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Session cookie hardening ──────────────────────────────────────────────────
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE']   = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

# ── CSRF protection ───────────────────────────────────────────────────────────
app.config['WTF_CSRF_TIME_LIMIT'] = None   # tokens never expire
csrf = CSRFProtect(app)

# ── Always make the session permanent so the cookie carries an Expires header ─
@app.before_request
def _make_session_permanent():
    session.permanent = True

# ── CSRF error handler — redirect instead of raw 400 Bad Request ──────────────
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return redirect(_url_for('home', form='login',
                             message='Tu sesión expiró o el formulario fue reenviado. '
                                     'La página se ha actualizado, intenta de nuevo.',
                             type='warning'))

# ── Security headers (applied to every response) ──────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options']         = 'DENY'
    response.headers['Referrer-Policy']         = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy']      = 'geolocation=(), microphone=(), camera=()'
    # Prevent browser from caching HTML pages that contain CSRF tokens
    if 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma']        = 'no-cache'
    # Content-Security-Policy: allow same-origin + trusted CDNs used by the app
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https://images.unsplash.com https://picsum.photos https://fastly.picsum.photos; "
        "connect-src 'self';"
    )
    return response
