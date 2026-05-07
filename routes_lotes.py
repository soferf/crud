"""
routes_lotes.py — Lote selection, setup wizard, and invitation routes.
"""
import json
import secrets
from datetime import datetime, timedelta

from flask import request, session, redirect, url_for, render_template, jsonify

from extensions import app, csrf
from config import EMAIL_REGEX, APP_URL
from db import get_db_connection
from session_service import auth_redirect, render_auth_page, _get_user_lotes, _set_active_lote_session


@app.route('/select-lote')
def select_lote():
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion para continuar.', 'warning')
    lotes = _get_user_lotes(session['user_id'])
    if len(lotes) == 0:
        return redirect(url_for('setup_lote_nuevo'))
    if len(lotes) == 1:
        _set_active_lote_session(session['user_id'], lotes[0]['id'])
        return redirect(url_for('dashboard'))
    return render_template('select_lote.html', lotes=lotes, user_name=session.get('user_name', 'Usuario'))


@app.route('/select-lote/<int:lote_id>')
def cambiar_lote(lote_id):
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion para continuar.', 'warning')
    lotes = _get_user_lotes(session['user_id'])
    lote_ids = [l['id'] for l in lotes]
    if lote_id not in lote_ids and not session.get('is_superadmin'):
        return auth_redirect('login', 'Acceso denegado a ese lote.', 'danger')
    _set_active_lote_session(session['user_id'], lote_id)
    return redirect(url_for('dashboard'))


@app.route('/setup/lote', methods=['GET'])
def setup_lote_nuevo():
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion para continuar.', 'warning')
    from ai_service import AI_ENABLED, GPT4ALL_MODEL, ai_client as _ai_client
    if AI_ENABLED:
        ok_ai, ai_msg = _ai_client.health_check()
    else:
        ok_ai, ai_msg = False, 'IA deshabilitada'
    return render_template('setup_lote.html',
                           user_name=session.get('user_name', 'Usuario'),
                           ai_available=ok_ai, ai_message=ai_msg, ai_model=GPT4ALL_MODEL)


@csrf.exempt
@app.route('/setup/lote/chat', methods=['POST'])
def setup_lote_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    data = request.get_json(force=True) or {}
    user_message = (data.get('message') or '').strip()[:1000]
    if not user_message:
        return jsonify({'error': 'Mensaje vacío'}), 400

    user_id = session['user_id']
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM ai_sessions WHERE user_id=%s AND status='pending' ORDER BY id DESC LIMIT 1", (user_id,))
        ai_sess = cursor.fetchone()
        if not ai_sess:
            cursor2 = conn.cursor()
            cursor2.execute("INSERT INTO ai_sessions (user_id, status) VALUES (%s,'pending')", (user_id,))
            conn.commit()
            ai_sess_id = cursor2.lastrowid
            cursor2.execute("INSERT INTO ai_form_state (session_id, payload_json, step) VALUES (%s,'{}','recopilando')", (ai_sess_id,))
            conn.commit(); cursor2.close()
        else:
            ai_sess_id = ai_sess['id']

        cursor.execute("SELECT payload_json FROM ai_form_state WHERE session_id=%s", (ai_sess_id,))
        state = cursor.fetchone()
        current_payload = json.loads(state['payload_json'] or '{}') if state else {}
        cursor.execute("SELECT role, content FROM ai_messages WHERE session_id=%s ORDER BY id", (ai_sess_id,))
        history = cursor.fetchall()
        cursor.close(); conn.close()

        from ai_service import LoteOnboardingSession
        ai_session = LoteOnboardingSession(ai_sess_id, current_payload)
        for msg in history:
            ai_session.messages.append({'role': msg['role'], 'content': msg['content']})
        result = ai_session.process(user_message)

        conn2 = get_db_connection()
        c2 = conn2.cursor()
        c2.execute("INSERT INTO ai_messages (session_id, role, content) VALUES (%s,'user',%s)", (ai_sess_id, user_message))
        c2.execute("INSERT INTO ai_messages (session_id, role, content) VALUES (%s,'assistant',%s)", (ai_sess_id, result.get('mensaje', '')))
        c2.execute("UPDATE ai_form_state SET payload_json=%s, step=%s WHERE session_id=%s",
                   (json.dumps(ai_session.payload, ensure_ascii=False), result.get('paso_actual', 'recopilando'), ai_sess_id))
        conn2.commit(); c2.close(); conn2.close()

        return jsonify({
            'mensaje':            result.get('mensaje', ''),
            'paso_actual':        result.get('paso_actual', 'recopilando'),
            'campos_faltantes':   result.get('campos_faltantes', []),
            'payload_actual':     ai_session.payload,
            'listo_para_guardar': result.get('listo_para_guardar', False),
            'ai_session_id':      ai_sess_id,
            'degraded':           result.get('degraded', False),
        })
    except Exception as e:
        return jsonify({'error': f'Error interno: {e}', 'mensaje': f'Ocurrió un error: {e}'}), 500


@csrf.exempt
@app.route('/setup/lote/confirmar', methods=['POST'])
def setup_lote_confirmar():
    if 'user_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    is_json = 'application/json' in (request.content_type or '')
    if is_json:
        data = request.get_json(force=True, silent=True) or {}
        payload = data.get('payload') or {}
        ai_session_id = data.get('ai_session_id')
    else:
        ubicacion_raw = request.form.get('ubicacion', '')
        municipio_val  = request.form.get('municipio', ubicacion_raw.split(',')[0].strip())
        departamento_val = request.form.get('departamento',
                          ubicacion_raw.split(',')[1].strip() if ',' in ubicacion_raw else '')
        payload = {
            'nombre_lote':            request.form.get('nombre_lote', '').strip(),
            'propietario':            request.form.get('propietario', '').strip(),
            'propietario_documento':  request.form.get('propietario_documento', '').strip(),
            'propietario_telefono':   request.form.get('propietario_telefono', '').strip(),
            'propietario_email':      request.form.get('propietario_email', '').strip(),
            'propietario_direccion':  request.form.get('propietario_direccion', '').strip(),
            'administrador_nombre':   request.form.get('administrador_nombre', '').strip(),
            'administrador_telefono': request.form.get('administrador_telefono', '').strip(),
            'administrador_email':    request.form.get('administrador_email', '').strip(),
            'hectareas':              request.form.get('hectareas', ''),
            'area_sembrada_ha':       request.form.get('area_sembrada_ha', '').strip() or None,
            'municipio':              municipio_val,
            'departamento':           departamento_val,
            'vereda':                 request.form.get('vereda', '').strip(),
            'tipo_tenencia':          request.form.get('tipo_tenencia', 'propia').strip(),
            'cultivo_principal':      request.form.get('cultivo_principal', 'Arroz').strip(),
            'fecha_inicio_operacion': request.form.get('fecha_inicio_operacion', '').strip() or None,
            'moneda':                 request.form.get('moneda', 'COP').strip(),
            'meta_cargas_ha':         request.form.get('meta_cargas_ha', ''),
            'limite_gasto_ha':        request.form.get('limite_gasto_ha', ''),
        }
        ai_session_id = None

    from ai_service import validate_lote_payload, apply_field_defaults
    payload = apply_field_defaults(payload)
    valid, errors = validate_lote_payload(payload)
    if not valid:
        return jsonify({'error': 'Datos inválidos', 'errores': errors}), 400

    user_id = session['user_id']
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lotes
              (nombre, propietario_nombre, propietario_documento,
               propietario_telefono, propietario_email, propietario_direccion,
               administrador_nombre, administrador_telefono, administrador_email,
               hectareas, area_sembrada_ha,
               municipio, departamento, vereda, tipo_tenencia,
               cultivo_principal, fecha_inicio_operacion, moneda,
               meta_cargas_ha, limite_gasto_ha, estado)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'activo')
        """, (
            str(payload.get('nombre_lote', 'Mi Lote')),
            str(payload.get('propietario', '')),
            str(payload.get('propietario_documento', '') or ''),
            str(payload.get('propietario_telefono', '') or ''),
            str(payload.get('propietario_email', '') or ''),
            str(payload.get('propietario_direccion', '') or ''),
            str(payload.get('administrador_nombre', '') or ''),
            str(payload.get('administrador_telefono', '') or ''),
            str(payload.get('administrador_email', '') or ''),
            float(payload.get('hectareas', 20)),
            float(payload.get('area_sembrada_ha')) if payload.get('area_sembrada_ha') else None,
            str(payload.get('municipio', '')),
            str(payload.get('departamento', '')),
            str(payload.get('vereda', '') or ''),
            str(payload.get('tipo_tenencia', 'propia') or 'propia'),
            str(payload.get('cultivo_principal', 'Arroz')),
            payload.get('fecha_inicio_operacion') or None,
            str(payload.get('moneda', 'COP')),
            int(payload.get('meta_cargas_ha', 100)),
            float(payload.get('limite_gasto_ha', 11000000)),
        ))
        new_lote_id = cursor.lastrowid
        cursor.execute("INSERT IGNORE INTO config (clave, valor, lote_id) VALUES ('serial_inicial','1',%s)", (new_lote_id,))
        cursor.execute("SELECT id FROM roles WHERE nombre='duenio_lote'")
        role_row = cursor.fetchone()
        if role_row:
            cursor.execute("INSERT IGNORE INTO user_lote_roles (user_id, lote_id, role_id) VALUES (%s,%s,%s)", (user_id, new_lote_id, role_row[0]))
        if ai_session_id:
            cursor.execute("UPDATE ai_sessions SET status='confirmed' WHERE id=%s AND user_id=%s", (ai_session_id, user_id))
        conn.commit(); cursor.close(); conn.close()
        _set_active_lote_session(user_id, new_lote_id)
        if not is_json:
            return redirect(url_for('dashboard'))
        return jsonify({'success': True, 'lote_id': new_lote_id, 'redirect': url_for('dashboard')})
    except Exception as e:
        return jsonify({'error': f'Error al guardar: {e}'}), 500


@csrf.exempt
@app.route('/setup/lote/cancelar', methods=['POST'])
def setup_lote_cancelar():
    if 'user_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    data = request.get_json(force=True) or {}
    ai_session_id = data.get('ai_session_id')
    if ai_session_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE ai_sessions SET status='cancelled' WHERE id=%s AND user_id=%s", (ai_session_id, session['user_id']))
            conn.commit(); cursor.close(); conn.close()
        except Exception:
            pass
    lotes = _get_user_lotes(session['user_id'])
    if lotes:
        return jsonify({'success': True, 'redirect': url_for('select_lote')})
    return jsonify({'success': True, 'redirect': url_for('home')})


@app.route('/lote/invitar', methods=['POST'])
def lote_invitar():
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    if not session.get('lote_id'):
        return jsonify({'error': 'Sin lote activo'}), 400
    if not has_permission('user.invite'):
        return jsonify({'error': 'Sin permiso para invitar'}), 403

    data = request.get_json(force=True) or {}
    email_inv  = (data.get('email') or '').strip().lower()
    rol_nombre = data.get('rol', 'operador_lote')
    if not email_inv or not EMAIL_REGEX.match(email_inv):
        return jsonify({'error': 'Correo inválido'}), 400

    lote_id = session['lote_id']
    user_id = session['user_id']
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM roles WHERE nombre=%s", (rol_nombre,))
        role_row = cursor.fetchone()
        if not role_row:
            cursor.close(); conn.close()
            return jsonify({'error': 'Rol no válido'}), 400
        token      = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=7)
        cursor2 = conn.cursor()
        cursor2.execute("INSERT INTO lote_invitations (lote_id, email, role_id, token, invited_by, expires_at) VALUES (%s,%s,%s,%s,%s,%s)",
                        (lote_id, email_inv, role_row['id'], token, user_id, expires_at))
        conn.commit(); cursor.close(); cursor2.close(); conn.close()
        invite_url = f"{APP_URL}/invitacion/{token}"
        return jsonify({'success': True, 'invite_url': invite_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/invitacion/<token>', methods=['GET', 'POST'])
def aceptar_invitacion(token):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT li.*, l.nombre as lote_nombre, r.nombre as rol_nombre
            FROM lote_invitations li
            JOIN lotes l ON li.lote_id = l.id
            JOIN roles r ON li.role_id = r.id
            WHERE li.token = %s
        """, (token,))
        inv = cursor.fetchone()
        cursor.close(); conn.close()
    except Exception as e:
        return render_auth_page('login', f'Error al procesar invitación: {e}', 'danger')

    if not inv:
        return render_auth_page('login', 'Invitación no válida.', 'danger')
    if inv['used']:
        return render_auth_page('login', 'Esta invitación ya fue utilizada.', 'warning')
    if datetime.utcnow() > inv['expires_at']:
        return render_auth_page('login', 'Esta invitación ha expirado.', 'warning')

    if request.method == 'GET':
        return render_template('invitacion.html', inv=inv, token=token)

    if 'user_id' not in session:
        return render_auth_page('login', 'Inicia sesión para aceptar la invitación.', 'info')
    user_id = session['user_id']
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT IGNORE INTO user_lote_roles (user_id, lote_id, role_id, invited_by) VALUES (%s,%s,%s,%s)",
                       (user_id, inv['lote_id'], inv['role_id'], inv['invited_by']))
        cursor.execute("UPDATE lote_invitations SET used=TRUE WHERE token=%s", (token,))
        conn.commit(); cursor.close(); conn.close()
        _set_active_lote_session(user_id, inv['lote_id'])
        return redirect(url_for('dashboard'))
    except Exception as e:
        return render_auth_page('login', f'Error al aceptar invitación: {e}', 'danger')
