"""
routes_auth.py — Authentication and dashboard routes.
"""
import re
import logging
from datetime import date as _date, timedelta, datetime

import mysql.connector
from flask import request, session, redirect, url_for, render_template, send_from_directory, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import app, UPLOAD_FOLDER
from config import EMAIL_REGEX, AUTH_SEND_LOGIN_ALERT, APP_URL
from db import get_db_connection
from utils import is_valid_password, generate_6_digit_code, format_currency
from auth_codes import save_auth_code, consume_auth_code
from session_service import auth_redirect, render_auth_page, _get_user_lotes, _set_active_lote_session
from mail_service import send_email
from email_utils import (
    render_login_alert_email,
    render_signup_code_email,
    render_reset_code_email,
    render_password_changed_email,
)

logger = logging.getLogger(__name__)

# ── Rate limiter (shared instance) ────────────────────────────────────────────
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[],
    storage_uri='memory://',
)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    from werkzeug.utils import safe_join
    safe_path = safe_join(UPLOAD_FOLDER, filename)
    if safe_path is None:
        abort(404)
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    form = request.args.get('form', 'login')
    return render_auth_page(
        form=form,
        message=request.args.get('message'),
        message_type=request.args.get('type', 'info')
    )


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion para continuar.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))

    lote_id = session['lote_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM lotes WHERE id=%s", (lote_id,))
    lote_info = cursor.fetchone() or {}
    HECTAREAS   = float(lote_info.get('hectareas') or 20)
    LIMITE_HA   = float(lote_info.get('limite_gasto_ha') or 11_000_000)
    META_CARGAS = int(HECTAREAS * (lote_info.get('meta_cargas_ha') or 100))

    cursor.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(neto_a_pagar),0) as total FROM recibos WHERE lote_id=%s", (lote_id,))
    rec_stats = cursor.fetchone()
    total_recibos = int(rec_stats['cnt'])
    total_gastos  = float(rec_stats['total'])

    hoy = _date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana    = inicio_semana + timedelta(days=6)
    cursor.execute(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(neto_a_pagar),0) as tot FROM recibos WHERE lote_id=%s AND fecha BETWEEN %s AND %s",
        (lote_id, inicio_semana, fin_semana)
    )
    sem = cursor.fetchone()
    recibos_semana = int(sem['cnt'])
    gasto_semana   = float(sem['tot'])

    cursor.execute(
        "SELECT COALESCE(SUM(neto_a_pagar),0) as tot FROM recibos WHERE lote_id=%s AND YEAR(fecha)=%s AND MONTH(fecha)=%s",
        (lote_id, hoy.year, hoy.month)
    )
    gasto_mes = float(cursor.fetchone()['tot'])

    cursor.execute("SELECT COUNT(*) as cnt FROM workers WHERE lote_id=%s AND activo=1", (lote_id,))
    total_workers = int(cursor.fetchone()['cnt'])

    cursor.execute("SELECT COALESCE(SUM(cargas),0) as tot FROM cosechas WHERE lote_id=%s", (lote_id,))
    total_cargas = int(cursor.fetchone()['tot'])

    cursor.execute("SELECT serial, fecha, proveedor, neto_a_pagar FROM recibos WHERE lote_id=%s ORDER BY serial DESC LIMIT 8", (lote_id,))
    recibos_recientes = cursor.fetchall()

    cursor.execute("SELECT COALESCE(SUM(monto),0) as ti FROM presupuesto_recargas WHERE lote_id=%s", (lote_id,))
    total_ingresado_dash = float(cursor.fetchone()['ti'])
    cursor.close(); conn.close()

    presupuesto_saldo   = total_ingresado_dash - total_gastos
    presupuesto_pct     = round(total_gastos / total_ingresado_dash * 100, 1) if total_ingresado_dash > 0 else 0
    presupuesto_activo  = total_ingresado_dash > 0

    gasto_x_ha = total_gastos / HECTAREAS if HECTAREAS else 0
    gasto_pct  = round(gasto_x_ha / LIMITE_HA * 100, 1) if LIMITE_HA else 0
    alerta_gasto = gasto_x_ha > LIMITE_HA
    cargas_pct  = round(total_cargas / META_CARGAS * 100, 1) if META_CARGAS else 0

    def fmt(v):
        try:    return '$ {:,.0f}'.format(float(v)).replace(',', '.')
        except: return '$ 0'

    stats = {
        'total_recibos':    total_recibos,
        'total_gastos_fmt': fmt(total_gastos),
        'total_workers':    total_workers,
        'total_cargas':     total_cargas,
        'recibos_semana':   recibos_semana,
        'gasto_semana_fmt': fmt(gasto_semana),
        'gasto_mes_fmt':    fmt(gasto_mes),
        'gasto_x_ha_fmt':   fmt(gasto_x_ha),
        'gasto_pct':        gasto_pct,
        'alerta_gasto':     alerta_gasto,
        'cargas_pct':       cargas_pct,
        'meta_cargas':      META_CARGAS,
        'limite_ha_fmt':    fmt(LIMITE_HA),
        'hectareas':        HECTAREAS,
    }

    return render_template('dashboard.html',
        user_name=session.get('user_name', 'Usuario'),
        lote_nombre=session.get('lote_nombre', ''),
        rol_lote=session.get('rol_lote', ''),
        today=hoy.strftime('%d/%m/%Y'),
        stats=stats,
        presupuesto_activo=presupuesto_activo,
        presupuesto_saldo=presupuesto_saldo,
        presupuesto_pct=presupuesto_pct,
        total_ingresado_dash=total_ingresado_dash,
        recibos_recientes=recibos_recientes,
        user_perms=session.get('user_perms', []),
    )


@app.route('/auth/signup', methods=['POST'])
@limiter.limit('10 per hour')
def signup():
    full_name = (request.form.get('full_name') or '').strip()[:120]
    email     = (request.form.get('email') or '').strip().lower()[:254]
    password  = request.form.get('password') or ''
    confirm   = request.form.get('confirm_password') or ''

    form_data = {'signup': {'full_name': full_name, 'email': email}}

    if not full_name or not email or not password or not confirm:
        return render_auth_page('signup', 'Completa todos los campos obligatorios.', 'warning', form_data)
    if not EMAIL_REGEX.match(email):
        return render_auth_page('signup', 'Ingresa un correo valido.', 'warning', form_data)
    if password != confirm:
        return render_auth_page('signup', 'Las contrasenas no coinciden.', 'warning', form_data)
    if not is_valid_password(password):
        return render_auth_page('signup', 'La contrasena debe tener minimo 8 caracteres, mayuscula, minuscula y numero.', 'warning', form_data)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_user, email_verified FROM users WHERE email = %s", (email,))
        existing = cursor.fetchone()
        cursor.close(); conn.close()
    except mysql.connector.Error as err:
        logger.error('[signup] DB error: %s', err)
        return render_auth_page('signup', 'Error interno al crear la cuenta. Intentalo de nuevo.', 'danger', form_data)

    if existing and existing.get('email_verified'):
        return render_auth_page('signup', 'Ese correo ya esta registrado y verificado.', 'warning', form_data)

    code = generate_6_digit_code()
    payload = {'full_name': full_name, 'email': email, 'password_hash': generate_password_hash(password)}
    try:
        save_auth_code(email, 'signup', code, payload)
    except mysql.connector.Error as err:
        logger.error('[signup] save_auth_code error: %s', err)
        return render_auth_page('signup', 'No se pudo generar el codigo. Intentalo de nuevo.', 'danger', form_data)

    html_body = render_signup_code_email(full_name, code)
    sent_ok, send_err = send_email(email, 'Codigo de verificacion - Contabilidad Arroceras', html_body)
    if sent_ok:
        return render_auth_page('signup_code',
            f'Revisamos tu correo {email}. Ingresa el codigo de 6 digitos para activar la cuenta.',
            'success', {'signup_code': {'email': email, 'code': ''}})
    return render_auth_page('signup',
        f'No se pudo enviar el codigo de verificacion a {email}. Detalle: {send_err}',
        'warning', form_data)


@app.route('/auth/verify-signup-code', methods=['POST'])
@limiter.limit('20 per hour')
def verify_signup_code():
    email = (request.form.get('email') or '').strip().lower()
    code  = re.sub(r'\D', '', request.form.get('code') or '')
    form_data = {'signup_code': {'email': email, 'code': code}}

    if not EMAIL_REGEX.match(email):
        return render_auth_page('signup_code', 'Correo no valido.', 'warning', form_data)
    if len(code) != 6:
        return render_auth_page('signup_code', 'El codigo debe tener 6 digitos.', 'warning', form_data)

    ok, err_msg, payload = consume_auth_code(email, 'signup', code)
    if not ok:
        return render_auth_page('signup_code', err_msg, 'warning', form_data)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_user, email_verified FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user and user.get('email_verified'):
            cursor.close(); conn.close()
            return render_auth_page('login', 'La cuenta ya esta verificada. Inicia sesion.', 'info')
        cursor2 = conn.cursor()
        if user:
            new_name = payload.get('full_name') or ''
            new_hash = payload.get('password_hash') or None
            if new_hash:
                cursor2.execute(
                    "UPDATE users SET full_name=%s, password_hash=%s, email_verified=TRUE, verify_token=NULL, is_active=TRUE WHERE id_user=%s",
                    (new_name, new_hash, user['id_user']))
            else:
                cursor2.execute(
                    "UPDATE users SET full_name=%s, email_verified=TRUE, verify_token=NULL, is_active=TRUE WHERE id_user=%s",
                    (new_name or user.get('full_name') or 'Usuario', user['id_user']))
        else:
            cursor2.execute(
                "INSERT INTO users (full_name, email, password_hash, email_verified, verify_token, is_active) VALUES (%s,%s,%s,TRUE,NULL,TRUE)",
                (payload.get('full_name', ''), email, payload.get('password_hash', '')))
        cursor2.close()
        conn.commit()
        cursor.close(); conn.close()
    except mysql.connector.Error as err:
        logger.error('[verify_signup_code] DB error: %s', err)
        return render_auth_page('signup_code', 'Error interno al verificar la cuenta. Intentalo de nuevo.', 'danger', form_data)

    return render_auth_page('login', 'Cuenta verificada correctamente. Ya puedes iniciar sesion.', 'success')


@app.route('/auth/login', methods=['POST'])
@limiter.limit('10 per minute; 50 per hour')
def login():
    email    = (request.form.get('email') or '').strip().lower()[:254]
    password = request.form.get('password') or ''
    remember = request.form.get('remember_me') == 'on'
    form_data = {'login': {'email': email, 'remember_me': remember}}

    if not email or not password:
        return render_auth_page('login', 'Ingresa correo y contrasena.', 'warning', form_data)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_user, full_name, password_hash, is_active, email_verified FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close(); conn.close()
    except mysql.connector.Error as err:
        logger.error('[login] DB error: %s', err)
        return render_auth_page('login', 'Error interno de acceso. Intentalo de nuevo.', 'danger', form_data)

    if not user or not check_password_hash(user['password_hash'], password):
        return render_auth_page('login', 'Credenciales invalidas.', 'danger', form_data)
    if not user['is_active']:
        return render_auth_page('login', 'Tu cuenta esta desactivada.', 'warning', form_data)
    if not user.get('email_verified'):
        resend_url = url_for('resend_verification', email=email)
        return render_auth_page('login',
            f'Debes verificar tu correo electronico antes de iniciar sesion. '
            f'<a href="{resend_url}" class="alert-link">Reenviar correo</a>',
            'warning', form_data)

    session.clear()
    session['user_id']   = user['id_user']
    session['user_name'] = user['full_name']
    session.permanent    = remember

    if AUTH_SEND_LOGIN_ALERT:
        try:
            when_text = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            send_email(email, 'Alerta de inicio de sesion - Contabilidad Arroceras',
                       render_login_alert_email(user['full_name'], when_text))
        except Exception:
            pass

    lotes = _get_user_lotes(user['id_user'])
    if len(lotes) == 0:
        return redirect(url_for('setup_lote_nuevo'))
    elif len(lotes) == 1:
        _set_active_lote_session(user['id_user'], lotes[0]['id'])
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('select_lote'))


@app.route('/auth/forgot-password', methods=['POST'])
@limiter.limit('5 per hour')
def forgot_password():
    email = (request.form.get('email') or '').strip().lower()[:254]
    form_data = {'forgot': {'email': email}}

    if not email or not EMAIL_REGEX.match(email):
        return render_auth_page('forgot', 'Ingresa un correo valido para continuar.', 'warning', form_data)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_user, full_name FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user:
            code = generate_6_digit_code()
            save_auth_code(email, 'reset', code, {'user_id': user['id_user'], 'full_name': user['full_name'], 'email': email})
            send_email(email, 'Codigo de recuperacion - Contabilidad Arroceras',
                       render_reset_code_email(user['full_name'], code))
        cursor.close(); conn.close()
    except mysql.connector.Error as err:
        logger.error('[forgot_password] DB error: %s', err)
        return render_auth_page('forgot', 'Error interno al procesar solicitud. Intentalo de nuevo.', 'danger', form_data)

    return render_auth_page('reset_code',
        'Si el correo esta registrado, recibiras un codigo de 6 digitos para restablecer tu contrasena.',
        'success', {'reset_code': {'email': email, 'code': ''}})


@app.route('/auth/reset-with-code', methods=['POST'])
@limiter.limit('10 per hour')
def reset_with_code():
    email    = (request.form.get('email') or '').strip().lower()
    code     = re.sub(r'\D', '', request.form.get('code') or '')
    password = request.form.get('password') or ''
    confirm  = request.form.get('confirm_password') or ''
    form_data = {'reset_code': {'email': email, 'code': code}}

    if not EMAIL_REGEX.match(email):
        return render_auth_page('reset_code', 'Correo no valido.', 'warning', form_data)
    if len(code) != 6:
        return render_auth_page('reset_code', 'El codigo debe tener 6 digitos.', 'warning', form_data)
    if not password or password != confirm:
        return render_auth_page('reset_code', 'Las contrasenas no coinciden.', 'warning', form_data)
    if not is_valid_password(password):
        return render_auth_page('reset_code', 'La contrasena debe tener minimo 8 caracteres, mayuscula, minuscula y numero.', 'warning', form_data)

    ok, err_msg, payload = consume_auth_code(email, 'reset', code)
    if not ok:
        return render_auth_page('reset_code', err_msg, 'warning', form_data)

    user_id = payload.get('user_id')
    if not user_id:
        return render_auth_page('reset_code', 'No se encontro un usuario valido para este codigo.', 'danger', form_data)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash=%s WHERE id_user=%s", (generate_password_hash(password), user_id))
        conn.commit(); cursor.close(); conn.close()
    except mysql.connector.Error as err:
        logger.error('[reset_with_code] DB error: %s', err)
        return render_auth_page('reset_code', 'Error interno al actualizar la contrasena. Intentalo de nuevo.', 'danger', form_data)

    try:
        send_email(email, 'Contrasena actualizada - Contabilidad Arroceras',
                   render_password_changed_email(payload.get('full_name') or 'Usuario'))
    except Exception:
        pass

    return render_auth_page('login', 'Contrasena actualizada correctamente. Ya puedes iniciar sesion.', 'success')


@app.route('/auth/logout')
def logout():
    session.clear()
    return auth_redirect('login', 'Sesion cerrada correctamente.', 'success')


@app.route('/auth/verify-email/<token>')
def verify_email(token):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_user, email_verified FROM users WHERE verify_token=%s", (token,))
        user = cursor.fetchone()
        if not user:
            cursor.close(); conn.close()
            return render_auth_page('login', 'Enlace de verificacion invalido o ya utilizado.', 'danger')
        if user['email_verified']:
            cursor.close(); conn.close()
            return render_auth_page('login', 'Tu correo ya fue verificado. Inicia sesion.', 'info')
        cursor.execute("UPDATE users SET email_verified=TRUE, verify_token=NULL WHERE id_user=%s", (user['id_user'],))
        conn.commit(); cursor.close(); conn.close()
    except mysql.connector.Error as err:
        logger.error('[verify_email] DB error: %s', err)
        return render_auth_page('login', 'Error interno de verificacion. Intentalo de nuevo.', 'danger')
    return render_auth_page('login', '¡Correo verificado correctamente! Ya puedes iniciar sesion.', 'success')


@app.route('/auth/resend-verification')
@limiter.limit('5 per hour')
def resend_verification():
    email = (request.args.get('email') or '').strip().lower()
    if not email or not EMAIL_REGEX.match(email):
        return auth_redirect('login', 'Correo no valido.', 'warning')
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_user, full_name, email_verified FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        if user and not user['email_verified']:
            code = generate_6_digit_code()
            save_auth_code(email, 'signup', code, {'full_name': user['full_name'], 'email': email, 'password_hash': ''})
            send_email(email, 'Codigo de verificacion - Contabilidad Arroceras',
                       render_signup_code_email(user['full_name'], code))
        cursor.close(); conn.close()
    except Exception:
        pass
    return render_auth_page('signup_code',
        f'Si la cuenta existe y no esta verificada, se reenviara un codigo de seguridad a {email}.',
        'success', {'signup_code': {'email': email, 'code': ''}})


@app.route('/auth/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT prt.id, prt.user_id, prt.expires_at, prt.used, u.full_name, u.email
            FROM password_reset_tokens prt
            JOIN users u ON u.id_user = prt.user_id
            WHERE prt.token = %s
        """, (token,))
        row = cursor.fetchone()
    except mysql.connector.Error as err:
        return render_template('reset_password.html', error=f'Error de base de datos: {err}', token=token, valid=False)

    if not row:
        cursor.close(); conn.close()
        return render_template('reset_password.html', error='Enlace invalido o ya utilizado.', token=token, valid=False)
    if row['used']:
        cursor.close(); conn.close()
        return render_template('reset_password.html', error='Este enlace ya fue utilizado.', token=token, valid=False)
    if datetime.utcnow() > row['expires_at']:
        cursor.close(); conn.close()
        return render_template('reset_password.html', error='El enlace ha expirado. Solicita uno nuevo.', token=token, valid=False)

    if request.method == 'GET':
        cursor.close(); conn.close()
        return render_template('reset_password.html', token=token, valid=True, full_name=row['full_name'])

    password = request.form.get('password') or ''
    confirm  = request.form.get('confirm_password') or ''
    if not password or password != confirm:
        cursor.close(); conn.close()
        return render_template('reset_password.html', error='Las contrasenas no coinciden.', token=token, valid=True, full_name=row['full_name'])
    if not is_valid_password(password):
        cursor.close(); conn.close()
        return render_template('reset_password.html', error='La contrasena debe tener minimo 8 caracteres, mayuscula, minuscula y numero.', token=token, valid=True, full_name=row['full_name'])

    try:
        cursor.execute("UPDATE users SET password_hash=%s WHERE id_user=%s", (generate_password_hash(password), row['user_id']))
        cursor.execute("UPDATE password_reset_tokens SET used=TRUE WHERE id=%s", (row['id'],))
        conn.commit()
    except mysql.connector.Error as err:
        cursor.close(); conn.close()
        return render_template('reset_password.html', error=f'Error al actualizar: {err}', token=token, valid=True)

    try:
        send_email(row['email'], 'Contrasena actualizada - Contabilidad Arroceras',
                   render_password_changed_email(row['full_name']))
    except Exception:
        pass

    cursor.close(); conn.close()
    return render_auth_page('login', '¡Contrasena actualizada! Ya puedes iniciar sesion con tu nueva contrasena.', 'success')
