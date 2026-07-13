"""
security_service.py — Utilidades de hardening: auditoría, bloqueo por intentos
fallidos de login y códigos de recuperación de cuenta.
"""
import logging
import secrets
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

from config import MAX_LOGIN_ATTEMPTS, LOCKOUT_MINUTES, RECOVERY_CODES_COUNT
from db import get_db_connection

logger = logging.getLogger(__name__)


# ── Auditoría ─────────────────────────────────────────────────────────────────
def log_security_event(event, user_id=None, lote_id=None, detail=''):
    """Registra un evento de seguridad. Nunca lanza (best-effort)."""
    ip = None
    try:
        from flask import request, has_request_context
        if has_request_context():
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    except Exception:
        ip = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO security_audit (user_id, lote_id, event, detail, ip) "
            "VALUES (%s,%s,%s,%s,%s)",
            (user_id, lote_id, str(event)[:60], str(detail)[:2000], (ip or '')[:45]))
        conn.commit(); cur.close(); conn.close()
    except Exception as err:
        logger.error('[audit] no se pudo registrar %s: %s', event, err)


def recent_events(user_id, limit=8):
    """Últimos eventos de auditoría de un usuario."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT event, detail, ip, created_at FROM security_audit "
            "WHERE user_id=%s ORDER BY id DESC LIMIT %s", (user_id, int(limit)))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return rows
    except Exception:
        return []


# ── Bloqueo por intentos fallidos ─────────────────────────────────────────────
def is_locked(email):
    """Devuelve (locked: bool, minutes_left: int) para el correo dado."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT locked_until FROM users WHERE email=%s", (email,))
        row = cur.fetchone()
        cur.close(); conn.close()
    except Exception:
        return False, 0
    if not row or not row.get('locked_until'):
        return False, 0
    locked_until = row['locked_until']
    if datetime.now() < locked_until:
        mins = int((locked_until - datetime.now()).total_seconds() // 60) + 1
        return True, mins
    return False, 0


def record_failed_login(email):
    """Incrementa el contador y bloquea si supera el máximo. Devuelve dict de estado."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_user, failed_attempts FROM users WHERE email=%s", (email,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return {'locked': False, 'attempts': 0}
        attempts = (row['failed_attempts'] or 0) + 1
        cur2 = conn.cursor()
        if attempts >= MAX_LOGIN_ATTEMPTS:
            locked_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
            cur2.execute("UPDATE users SET failed_attempts=%s, locked_until=%s WHERE id_user=%s",
                         (attempts, locked_until, row['id_user']))
            conn.commit(); cur2.close(); cur.close(); conn.close()
            log_security_event('login_locked', row['id_user'],
                               detail=f'Cuenta bloqueada por {LOCKOUT_MINUTES} min tras {attempts} intentos')
            return {'locked': True, 'attempts': attempts, 'minutes': LOCKOUT_MINUTES}
        cur2.execute("UPDATE users SET failed_attempts=%s WHERE id_user=%s",
                     (attempts, row['id_user']))
        conn.commit(); cur2.close(); cur.close(); conn.close()
        return {'locked': False, 'attempts': attempts,
                'remaining': max(0, MAX_LOGIN_ATTEMPTS - attempts)}
    except Exception as err:
        logger.error('[lockout] record_failed_login error: %s', err)
        return {'locked': False, 'attempts': 0}


def clear_failures(email):
    """Resetea el contador de intentos tras un login exitoso."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE email=%s", (email,))
        conn.commit(); cur.close(); conn.close()
    except Exception:
        pass


# ── Códigos de recuperación de cuenta ─────────────────────────────────────────
def _new_code():
    """Código legible de 10 caracteres: XXXXX-XXXXX (sin caracteres ambiguos)."""
    alphabet = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
    raw = ''.join(secrets.choice(alphabet) for _ in range(10))
    return f'{raw[:5]}-{raw[5:]}'


def generate_recovery_codes(user_id, n=None):
    """Invalida los códigos previos y crea n nuevos. Devuelve la lista en CLARO
    (solo se muestran/guardan una vez; en BD se almacena el hash)."""
    n = n or RECOVERY_CODES_COUNT
    codes = [_new_code() for _ in range(n)]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM recovery_codes WHERE user_id=%s", (user_id,))
    for c in codes:
        cur.execute("INSERT INTO recovery_codes (user_id, code_hash) VALUES (%s,%s)",
                    (user_id, generate_password_hash(c, method='pbkdf2:sha256')))
    conn.commit(); cur.close(); conn.close()
    log_security_event('recovery_codes_generated', user_id, detail=f'{n} códigos generados')
    return codes


def recovery_codes_status(user_id):
    """Devuelve (total, disponibles) de códigos de recuperación del usuario."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), SUM(used=0) FROM recovery_codes WHERE user_id=%s", (user_id,))
        total, avail = cur.fetchone()
        cur.close(); conn.close()
        return int(total or 0), int(avail or 0)
    except Exception:
        return 0, 0


def verify_recovery_code(email, code):
    """Valida y consume un código de recuperación para el correo dado.
    Devuelve (ok, user_dict_or_None)."""
    code = (code or '').strip().upper()
    if not code:
        return False, None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_user, full_name, email FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        if not user:
            cur.close(); conn.close()
            return False, None
        cur.execute("SELECT id, code_hash FROM recovery_codes WHERE user_id=%s AND used=0",
                    (user['id_user'],))
        rows = cur.fetchall()
        for r in rows:
            if check_password_hash(r['code_hash'], code):
                cur2 = conn.cursor()
                cur2.execute("UPDATE recovery_codes SET used=1, used_at=NOW() WHERE id=%s", (r['id'],))
                conn.commit(); cur2.close(); cur.close(); conn.close()
                log_security_event('recovery_code_used', user['id_user'],
                                   detail='Inicio de recuperación con código')
                return True, user
        cur.close(); conn.close()
        return False, None
    except Exception as err:
        logger.error('[recovery] verify error: %s', err)
        return False, None
