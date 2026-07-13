"""
routes_config.py — Configuración del lote y de la cuenta.

Secciones: Seguridad de cuenta (cambio de contraseña, códigos de recuperación,
auditoría), Respaldo y recuperación (.zip cifrado), Seriales y Preferencias.
"""
import io
from datetime import datetime

from flask import (request, session, redirect, url_for, render_template,
                   send_file, flash)
from werkzeug.security import check_password_hash

from extensions import app
from db import get_db_connection
from utils import get_next_serial, is_valid_password
from session_service import auth_redirect
from mail_service import send_email
from email_utils import (render_password_changed_email, render_backup_alert_email,
                         render_recovery_codes_email)
import security_service as sec
import backup_service


def _gen_hash(password):
    from werkzeug.security import generate_password_hash as _gen
    return _gen(password, method='pbkdf2:sha256')


# ── Preferencias (tabla config, por lote) ─────────────────────────────────────
_PREF_KEYS = {
    'pref_alert_login':    '1',   # alerta por correo al iniciar sesión
    'pref_alert_security': '1',   # alerta en eventos sensibles
}


def _load_config_rows(cursor, lote_id):
    cursor.execute("SELECT clave, valor FROM config WHERE lote_id=%s", (lote_id,))
    return {row['clave']: row['valor'] for row in cursor.fetchall()}


def _guard():
    """Valida login + lote + permiso. Devuelve (lote_id, None) o (None, respuesta)."""
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return None, auth_redirect('login', 'Inicia sesion para acceder a la configuracion.', 'warning')
    if not session.get('lote_id'):
        return None, redirect(url_for('select_lote'))
    if not has_permission('config.manage'):
        return None, redirect(url_for('dashboard', msg='Sin permiso para configurar.', msg_type='danger'))
    return session['lote_id'], None


def _render_config(message=None, error=None, generated_codes=None, active_tab='seguridad'):
    lote_id = session['lote_id']
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        config_rows = _load_config_rows(cursor, lote_id)
        cursor.execute("SELECT COUNT(*) AS total FROM recibos WHERE lote_id=%s", (lote_id,))
        total_recibos = cursor.fetchone()['total']
        cursor.execute("SELECT full_name, email, email_verified FROM users WHERE id_user=%s", (user_id,))
        cuenta = cursor.fetchone() or {}
        cursor.execute("SELECT nombre, hectareas FROM lotes WHERE id=%s", (lote_id,))
        lote_row = cursor.fetchone() or {}
        next_serial_effective = get_next_serial(lote_id)
    except Exception:
        config_rows, total_recibos, cuenta, lote_row, next_serial_effective = {}, 0, {}, {}, 1
    finally:
        cursor.close(); conn.close()

    total_codes, codes_disponibles = sec.recovery_codes_status(user_id)
    prefs = {k: config_rows.get(k, default) == '1' for k, default in _PREF_KEYS.items()}

    return render_template('config/index.html',
        config=config_rows,
        total_recibos=total_recibos,
        next_serial_effective=next_serial_effective,
        lote_nombre=session.get('lote_nombre', 'Lote activo'),
        lote_ha=(lote_row.get('hectareas') if lote_row else None),
        cuenta=cuenta,
        recovery_total=total_codes,
        recovery_disponibles=codes_disponibles,
        generated_codes=generated_codes,
        eventos=sec.recent_events(user_id, 8),
        prefs=prefs,
        active_tab=active_tab,
        message=message,
        error=error)


@app.route('/config', methods=['GET', 'POST'])
def config_app():
    lote_id, err = _guard()
    if err:
        return err

    message = error = None
    if request.method == 'POST':
        serial_inicial = request.form.get('serial_inicial', '').strip()
        if not serial_inicial or not serial_inicial.isdigit():
            error = "El serial inicial debe ser un número entero positivo."
        else:
            try:
                conn = get_db_connection(); cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO config (clave, valor, lote_id) VALUES ('serial_inicial', %s, %s)
                    ON DUPLICATE KEY UPDATE valor = VALUES(valor)
                """, (serial_inicial, lote_id))
                conn.commit(); cursor.close(); conn.close()
                message = f"Serial inicial actualizado a {serial_inicial}."
                sec.log_security_event('config_changed', session['user_id'], lote_id,
                                       detail=f'serial_inicial={serial_inicial}')
            except Exception as e:
                error = f"Error: {e}"
        return _render_config(message=message, error=error, active_tab='seriales')

    return _render_config(active_tab='seguridad')


@app.route('/config/change-password', methods=['POST'])
def config_change_password():
    lote_id, err = _guard()
    if err:
        return err
    user_id = session['user_id']
    actual  = request.form.get('current_password') or ''
    nueva   = request.form.get('new_password') or ''
    confirm = request.form.get('confirm_password') or ''

    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT password_hash, full_name, email FROM users WHERE id_user=%s", (user_id,))
    user = cursor.fetchone(); cursor.close(); conn.close()

    if not user or not check_password_hash(user['password_hash'], actual):
        return _render_config(error='La contraseña actual es incorrecta.', active_tab='seguridad')
    if nueva != confirm:
        return _render_config(error='La nueva contraseña y su confirmación no coinciden.', active_tab='seguridad')
    if not is_valid_password(nueva):
        return _render_config(error='La nueva contraseña debe tener mínimo 8 caracteres, mayúscula, minúscula y número.', active_tab='seguridad')

    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash=%s WHERE id_user=%s", (_gen_hash(nueva), user_id))
    conn.commit(); cursor.close(); conn.close()
    sec.log_security_event('password_changed', user_id, lote_id, detail='Cambio desde configuración')
    if _pref_enabled(lote_id, 'pref_alert_security'):
        try:
            send_email(user['email'], 'Contrasena actualizada - Contabilidad Arroceras',
                       render_password_changed_email(user.get('full_name') or 'Usuario'))
        except Exception:
            pass
    return _render_config(message='Contraseña actualizada correctamente.', active_tab='seguridad')


@app.route('/config/recovery-codes/regenerate', methods=['POST'])
def config_regenerate_codes():
    lote_id, err = _guard()
    if err:
        return err
    user_id = session['user_id']
    codes = sec.generate_recovery_codes(user_id)
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT full_name, email FROM users WHERE id_user=%s", (user_id,))
    user = cursor.fetchone() or {}; cursor.close(); conn.close()
    if _pref_enabled(lote_id, 'pref_alert_security') and user.get('email'):
        try:
            send_email(user['email'], 'Codigos de recuperacion actualizados - Contabilidad Arroceras',
                       render_recovery_codes_email(user.get('full_name') or 'Usuario',
                                                   datetime.now().strftime('%d/%m/%Y %H:%M')))
        except Exception:
            pass
    return _render_config(
        message='Se generaron nuevos códigos de recuperación. Guárdalos ahora; no se volverán a mostrar.',
        generated_codes=codes, active_tab='seguridad')


@app.route('/config/preferences', methods=['POST'])
def config_preferences():
    lote_id, err = _guard()
    if err:
        return err
    conn = get_db_connection(); cursor = conn.cursor()
    for key in _PREF_KEYS:
        valor = '1' if request.form.get(key) == 'on' else '0'
        cursor.execute("""
            INSERT INTO config (clave, valor, lote_id) VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE valor = VALUES(valor)
        """, (key, valor, lote_id))
    conn.commit(); cursor.close(); conn.close()
    sec.log_security_event('config_changed', session['user_id'], lote_id, detail='Preferencias actualizadas')
    return _render_config(message='Preferencias guardadas.', active_tab='preferencias')


@app.route('/config/recovery-zip', methods=['POST'])
def config_recovery_zip():
    lote_id, err = _guard()
    if err:
        return err
    user_id = session['user_id']
    password = request.form.get('zip_password') or ''
    confirm  = request.form.get('zip_password_confirm') or ''
    if len(password) < 8:
        return _render_config(error='La contraseña del respaldo debe tener al menos 8 caracteres.',
                              active_tab='respaldo')
    if password != confirm:
        return _render_config(error='Las contraseñas del respaldo no coinciden.', active_tab='respaldo')

    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_user, full_name, email FROM users WHERE id_user=%s", (user_id,))
    user = cursor.fetchone(); cursor.close(); conn.close()

    try:
        data, filename = backup_service.build_recovery_zip(lote_id, user, password)
    except Exception as e:
        app.logger.error('[recovery-zip] %s', e)
        return _render_config(error=f'No se pudo generar el respaldo: {e}', active_tab='respaldo')

    sec.log_security_event('backup_downloaded', user_id, lote_id, detail=filename)
    if _pref_enabled(lote_id, 'pref_alert_security') and user.get('email'):
        try:
            send_email(user['email'], 'Respaldo de recuperacion generado - Contabilidad Arroceras',
                       render_backup_alert_email(user.get('full_name') or 'Usuario',
                                                 session.get('lote_nombre', 'Lote'),
                                                 datetime.now().strftime('%d/%m/%Y %H:%M')))
        except Exception:
            pass
    return send_file(io.BytesIO(data), mimetype='application/zip',
                     as_attachment=True, download_name=filename)


def _pref_enabled(lote_id, key):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT valor FROM config WHERE clave=%s AND lote_id=%s", (key, lote_id))
        row = cursor.fetchone(); cursor.close(); conn.close()
        if row is None:
            return _PREF_KEYS.get(key, '1') == '1'
        return row[0] == '1'
    except Exception:
        return True
