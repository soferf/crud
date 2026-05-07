"""
auth_codes.py — Generación y consumo de códigos de verificación por email.
"""
import hmac
import json
from datetime import datetime, timedelta

from config import AUTH_CODE_TTL_MINUTES, AUTH_CODE_MAX_ATTEMPTS
from db import get_db_connection


def save_auth_code(email, purpose, code, payload=None):
    expires_at = datetime.utcnow() + timedelta(minutes=AUTH_CODE_TTL_MINUTES)
    payload_json = json.dumps(payload or {}, ensure_ascii=False)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO auth_email_codes (email, purpose, code, payload_json, expires_at, max_attempts)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (email, purpose, code, payload_json, expires_at, AUTH_CODE_MAX_ATTEMPTS)
    )
    conn.commit()
    cursor.close()
    conn.close()


def consume_auth_code(email, purpose, code):
    """Validate and consume a one-time 6-digit code."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, code, payload_json, expires_at, used, attempts, max_attempts
        FROM auth_email_codes
        WHERE email = %s AND purpose = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (email, purpose)
    )
    row = cursor.fetchone()

    if not row:
        cursor.close(); conn.close()
        return False, 'No se encontró un código activo para este correo.', None

    if row['used']:
        cursor.close(); conn.close()
        return False, 'Este código ya fue utilizado. Solicita uno nuevo.', None

    if datetime.utcnow() > row['expires_at']:
        cursor.close(); conn.close()
        return False, 'El código expiró. Solicita uno nuevo.', None

    if row['attempts'] >= row['max_attempts']:
        cursor.close(); conn.close()
        return False, 'Se alcanzó el número máximo de intentos. Solicita un nuevo código.', None

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest((code or '').strip(), row['code']):
        cursor.execute(
            "UPDATE auth_email_codes SET attempts = attempts + 1 WHERE id = %s",
            (row['id'],)
        )
        conn.commit()
        attempts_left = max(0, row['max_attempts'] - (row['attempts'] + 1))
        cursor.close(); conn.close()
        return False, f'Código incorrecto. Intentos restantes: {attempts_left}.', None

    cursor.execute(
        "UPDATE auth_email_codes SET used = TRUE WHERE id = %s",
        (row['id'],)
    )
    conn.commit()
    payload = json.loads(row['payload_json'] or '{}')
    cursor.close(); conn.close()
    return True, None, payload
