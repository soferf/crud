"""
utils.py — Funciones utilitarias de la aplicación.
"""
import os
import json
import secrets

from config import ALLOWED_EXTENSIONS, CONCEPTOS_PROHIBIDOS
from db import get_db_connection


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_valid_password(password):
    if len(password) < 8:
        return False
    return (any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password))


def generate_6_digit_code():
    return f"{secrets.randbelow(1000000):06d}"


def format_currency(value):
    try:
        return '$ {:,.0f}'.format(float(value or 0)).replace(',', '.')
    except Exception:
        return '$ 0'


def load_trabajadores():
    path = os.path.join(os.path.dirname(__file__), 'data', 'trabajadores.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def es_concepto_prohibido(concepto):
    """Returns True if concepto is a prohibited purchase (aceite/ACPM direct, not transport)."""
    c = concepto.lower()
    if 'transporte' in c and 'acpm' in c:
        return False
    for palabra in CONCEPTOS_PROHIBIDOS:
        if palabra in c:
            return True
    return False


def get_serial_inicial(lote_id=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if lote_id is not None:
            cursor.execute("""
                SELECT valor
                FROM config
                WHERE clave = 'serial_inicial'
                  AND (lote_id = %s OR lote_id IS NULL)
                ORDER BY CASE WHEN lote_id = %s THEN 0 ELSE 1 END
                LIMIT 1
            """, (lote_id, lote_id))
        else:
            cursor.execute("SELECT valor FROM config WHERE clave = 'serial_inicial'")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return int(row['valor']) if row else 1
    except Exception:
        return 1


def get_next_serial(lote_id=None):
    try:
        serial_configurado = get_serial_inicial(lote_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        if lote_id:
            cursor.execute("SELECT MAX(serial) FROM recibos WHERE lote_id = %s", (lote_id,))
        else:
            cursor.execute("SELECT MAX(serial) FROM recibos")
        max_serial = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        if max_serial is None:
            return serial_configurado
        return max(max_serial + 1, serial_configurado)
    except Exception:
        return get_serial_inicial(lote_id)
