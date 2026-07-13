"""
backup_service.py — Genera un .zip de recuperación cifrado (AES) con el respaldo
de datos del lote y los códigos de recuperación de la cuenta.
"""
import io
import json
import logging
from datetime import datetime, date
from decimal import Decimal

import pyzipper

from db import get_db_connection
import security_service as sec

logger = logging.getLogger(__name__)

# Tablas del respaldo y la columna por la que se filtran por lote.
_BACKUP_TABLES = {
    'recibos':              'lote_id',
    'workers':              'lote_id',
    'cosechas':             'lote_id',
    'config':               'lote_id',
    'presupuesto_recargas': 'lote_id',
}


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (bytes, bytearray)):
        return o.decode('utf-8', 'replace')
    return str(o)


def _dump_table(cur, table, col, lote_id):
    try:
        cur.execute(f"SELECT * FROM {table} WHERE {col}=%s", (lote_id,))
        rows = cur.fetchall()
        return json.dumps(rows, default=_json_default, ensure_ascii=False, indent=2)
    except Exception as err:
        logger.error('[backup] error volcando %s: %s', table, err)
        return json.dumps({'error': str(err)}, ensure_ascii=False)


def build_recovery_zip(lote_id, user, password):
    """
    Construye un zip AES-256 cifrado con `password`. Devuelve (bytes, filename).
    `user` es un dict con al menos id_user, full_name, email.
    Incluye un respaldo de datos del lote + códigos de recuperación nuevos.
    """
    ts = datetime.now()
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Datos del lote (nombre legible para el nombre de archivo).
    lote_nombre = 'lote'
    try:
        cur.execute("SELECT nombre FROM lotes WHERE id=%s", (lote_id,))
        r = cur.fetchone()
        if r and r.get('nombre'):
            lote_nombre = r['nombre']
    except Exception:
        pass

    backups = {tbl: _dump_table(cur, tbl, col, lote_id)
               for tbl, col in _BACKUP_TABLES.items()}
    cur.close(); conn.close()

    # Códigos de recuperación nuevos (en claro, solo aquí).
    codes = sec.generate_recovery_codes(user['id_user'])

    manifest = {
        'generado_en': ts.isoformat(),
        'lote_id': lote_id,
        'lote_nombre': lote_nombre,
        'usuario': {'id': user['id_user'], 'nombre': user.get('full_name'),
                    'email': user.get('email')},
        'tablas': {t: (json.loads(b) if isinstance(b, str) and b.startswith('[') else 'error')
                   for t, b in backups.items()},
    }
    tabla_conteos = {t: (len(json.loads(b)) if b.startswith('[') else 0)
                     for t, b in backups.items()}

    codigos_txt = (
        "CÓDIGOS DE RECUPERACIÓN DE CUENTA — Contabilidad Arroceras\n"
        f"Cuenta: {user.get('email')}\n"
        f"Generados: {ts.strftime('%d/%m/%Y %H:%M')}\n"
        "\nGuarda estos códigos en un lugar seguro. Cada uno sirve UNA sola vez\n"
        "para recuperar el acceso si pierdes tu correo. Al generar este zip se\n"
        "invalidaron los códigos anteriores.\n\n"
        + "\n".join(f"  {i:>2}.  {c}" for i, c in enumerate(codes, 1))
        + "\n"
    )

    leeme_txt = (
        "RESPALDO DE RECUPERACIÓN — Contabilidad Arroceras\n"
        "=================================================\n\n"
        f"Lote: {lote_nombre} (id {lote_id})\n"
        f"Generado: {ts.strftime('%d/%m/%Y %H:%M')}\n\n"
        "Contenido:\n"
        "  - codigos_recuperacion.txt : códigos de un solo uso para tu cuenta.\n"
        "  - datos/*.json             : respaldo de la información del lote.\n"
        "  - manifest.json            : resumen e índice del respaldo.\n\n"
        "Conteo de registros respaldados:\n"
        + "\n".join(f"  - {t}: {n}" for t, n in tabla_conteos.items())
        + "\n\nEste archivo está cifrado con AES-256. Consérvalo en un lugar seguro.\n"
    )

    buf = io.BytesIO()
    with pyzipper.AESZipFile(buf, 'w', compression=pyzipper.ZIP_DEFLATED,
                            encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode('utf-8'))
        zf.writestr('LEEME.txt', leeme_txt)
        zf.writestr('codigos_recuperacion.txt', codigos_txt)
        zf.writestr('manifest.json',
                    json.dumps(manifest, default=_json_default, ensure_ascii=False, indent=2))
        for tbl, data in backups.items():
            zf.writestr(f'datos/{tbl}.json', data)

    buf.seek(0)
    safe_nombre = ''.join(ch for ch in lote_nombre if ch.isalnum() or ch in ' -_').strip().replace(' ', '_')
    filename = f"recuperacion_{safe_nombre or 'lote'}_{ts.strftime('%Y%m%d')}.zip"
    return buf.getvalue(), filename
