"""
routes_config.py — App configuration route.
"""
from flask import request, session, redirect, url_for, render_template

from extensions import app
from db import get_db_connection
from utils import get_next_serial
from session_service import auth_redirect


@app.route('/config', methods=['GET', 'POST'])
def config_app():
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion para acceder a la configuracion.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    if not has_permission('config.manage'):
        return redirect(url_for('dashboard', msg='Sin permiso para configurar.', msg_type='danger'))
    lote_id = session['lote_id']

    message = None
    error   = None

    if request.method == 'POST':
        serial_inicial = request.form.get('serial_inicial', '').strip()
        if not serial_inicial or not serial_inicial.isdigit():
            error = "El serial inicial debe ser un número entero positivo."
        else:
            try:
                conn   = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO config (clave, valor, lote_id) VALUES ('serial_inicial', %s, %s)
                    ON DUPLICATE KEY UPDATE valor = VALUES(valor)
                """, (serial_inicial, lote_id))
                conn.commit(); cursor.close(); conn.close()
                message = f"Serial inicial actualizado a {serial_inicial}."
            except Exception as e:
                error = f"Error: {e}"

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT clave, valor FROM config WHERE lote_id=%s", (lote_id,))
        config_rows = {row['clave']: row['valor'] for row in cursor.fetchall()}
        cursor.execute("SELECT COUNT(*) as total FROM recibos WHERE lote_id=%s", (lote_id,))
        total_recibos        = cursor.fetchone()['total']
        next_serial_effective = get_next_serial(lote_id)
        cursor.close(); conn.close()
    except Exception:
        config_rows           = {'serial_inicial': '1'}
        total_recibos         = 0
        next_serial_effective = 1

    return render_template('config/index.html',
                           config=config_rows,
                           total_recibos=total_recibos,
                           next_serial_effective=next_serial_effective,
                           lote_nombre=session.get('lote_nombre', 'Lote activo'),
                           message=message,
                           error=error)
