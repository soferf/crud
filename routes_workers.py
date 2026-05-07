"""
routes_workers.py — Worker CRUD and API routes.
"""
import io
import os
import uuid
import json
from datetime import date

from flask import request, session, redirect, url_for, render_template, jsonify, abort
from werkzeug.utils import secure_filename

from extensions import app, UPLOAD_FOLDER
from config import WORKER_OPTIONS, ALLOWED_EXTENSIONS
from db import get_db_connection
from utils import allowed_file
from session_service import auth_redirect

# Magic-byte signatures for allowed image types
_IMAGE_SIGNATURES = {
    b'\xff\xd8\xff':  'jpg',
    b'\x89PNG':       'png',
    b'RIFF':          'webp',  # webp: RIFF....WEBP
    b'\x00\x00\x00': 'mp4',   # placeholder — excluded by ALLOWED_EXTENSIONS
}
_ALLOWED_MAGIC = {
    b'\xff\xd8\xff',            # JPEG
    b'\x89\x50\x4e\x47',        # PNG
}


def _is_safe_image(file_stream) -> bool:
    """Return True only if the first bytes match a valid image signature."""
    header = file_stream.read(8)
    file_stream.seek(0)
    return (header[:3] in _ALLOWED_MAGIC
            or header[:4] == b'\x89\x50\x4e\x47'  # PNG
            or header[:4] in {b'RIFF'} and b'WEBP' in header)


def _save_upload(file_obj) -> str | None:
    """Validate and save an uploaded image; return the stored filename or None."""
    if not file_obj or not file_obj.filename:
        return None
    filename = secure_filename(file_obj.filename)
    if not filename or not allowed_file(filename):
        return None
    if not _is_safe_image(file_obj.stream):
        return None
    ext = filename.rsplit('.', 1)[1].lower()
    saved_name = f"{uuid.uuid4().hex}.{ext}"
    file_obj.save(os.path.join(UPLOAD_FOLDER, saved_name))
    return saved_name


def _get_trabajadores_for_autocomplete():
    """Returns active workers for the current lote in autocomplete-ready format."""
    lote_id = session.get('lote_id')
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if lote_id:
            cursor.execute("""
                SELECT id_worker, name, lastname, cc, phone_number, alias,
                       direccion, ciudad, concepto_habitual, valor_habitual,
                       rol, conceptos_pago
                FROM workers WHERE activo=1 AND lote_id=%s ORDER BY name
            """, (lote_id,))
        else:
            cursor.execute("""
                SELECT id_worker, name, lastname, cc, phone_number, alias,
                       direccion, ciudad, concepto_habitual, valor_habitual,
                       rol, conceptos_pago
                FROM workers WHERE activo=1 ORDER BY name
            """)
        rows = cursor.fetchall()
        cursor.close(); conn.close()
    except Exception:
        rows = []

    result = []
    for w in rows:
        alias_str  = (w.get('alias') or '').strip()
        alias_list = [a.strip() for a in alias_str.split(',') if a.strip()] if alias_str else []
        cpago = []
        if w.get('conceptos_pago'):
            try:
                cpago = json.loads(w['conceptos_pago'])
            except Exception:
                pass
        result.append({
            'id':                w['id_worker'],
            'nombre':            f"{w['name']} {w['lastname']}",
            'nit':               w.get('cc') or '',
            'alias':             alias_list,
            'telefono':          w.get('phone_number') or '',
            'direccion':         w.get('direccion') or '',
            'ciudad':            w.get('ciudad') or '',
            'rol':               w.get('rol') or '',
            'concepto_habitual': w.get('concepto_habitual') or '',
            'valor_habitual':    float(w['valor_habitual']) if w.get('valor_habitual') else None,
            'conceptos_pago':    cpago,
        })
    return result


def _build_recibo_form_data(recibo):
    lineas = []
    if recibo.get('conceptos_json'):
        try:
            lineas = json.loads(recibo['conceptos_json'])
        except Exception:
            lineas = []
    if not lineas and recibo.get('concepto'):
        lineas = [{'concepto': recibo.get('concepto') or '',
                   'valor': float(recibo.get('valor_operacion') or recibo.get('neto_a_pagar') or 0)}]
    return {
        'serial':      recibo.get('serial', ''),
        'fecha':       recibo['fecha'].isoformat() if getattr(recibo.get('fecha'), 'isoformat', None) else '',
        'proveedor':   recibo.get('proveedor') or '',
        'nit':         recibo.get('nit') or '',
        'direccion':   recibo.get('direccion') or '',
        'telefono':    recibo.get('telefono') or '',
        'ciudad':      recibo.get('ciudad') or '',
        'lineas':      lineas,
        'rte_fte':     float(recibo.get('rte_fte') or 0),
        'neto_a_pagar': float(recibo.get('neto_a_pagar') or 0),
    }


@app.route('/api/trabajadores')
def api_trabajadores():
    if 'user_id' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    q    = request.args.get('q', '').strip().lower()[:100]
    todos = _get_trabajadores_for_autocomplete()
    if q:
        todos = [t for t in todos if q in t['nombre'].lower()
                 or any(q in a.lower() for a in t.get('alias', []))]
    return jsonify(todos)


@app.route('/api/workers')
def api_workers():
    if 'user_id' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    lote_id = session.get('lote_id')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if lote_id:
        cursor.execute("""SELECT id_worker, name, lastname, cc, direccion, ciudad, phone_number,
                                 concepto_habitual, valor_habitual, trabajo_desarrolla
                          FROM workers WHERE activo=1 AND lote_id=%s ORDER BY name""", (lote_id,))
    else:
        cursor.execute("""SELECT id_worker, name, lastname, cc, direccion, ciudad, phone_number,
                                 concepto_habitual, valor_habitual, trabajo_desarrolla
                          FROM workers WHERE activo=1 ORDER BY name""")
    workers = cursor.fetchall()
    cursor.close(); conn.close()
    for w in workers:
        if w.get('valor_habitual'):
            w['valor_habitual'] = float(w['valor_habitual'])
    return jsonify(workers)


@app.route('/workers/create', methods=['GET', 'POST'])
def create_worker():
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion para acceder al registro de trabajadores.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    if not has_permission('worker.create'):
        return redirect(url_for('lista_workers'))
    lote_id = session['lote_id']
    message = None
    error   = None

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        lastname    = request.form.get('lastname', '').strip()
        cc          = request.form.get('cc', '').strip()
        phone_number= request.form.get('phone_number', '').strip()
        email       = request.form.get('email') or None
        trabajo     = request.form.get('trabajo_desarrolla')
        fecha_ingreso = request.form.get('fecha_ingreso') or None
        activo      = request.form.get('activo') == 'on'
        observaciones = request.form.get('observaciones') or None
        alias       = request.form.get('alias') or None
        direccion   = request.form.get('direccion') or None
        ciudad      = request.form.get('ciudad') or None
        concepto_habitual = request.form.get('concepto_habitual') or None
        vh_raw      = request.form.get('valor_habitual') or None
        valor_habitual = float(vh_raw) if vh_raw else None

        foto_filename = None
        foto_file = request.files.get('foto')
        foto_filename = _save_upload(foto_file)

        if not name or not lastname or not cc or not phone_number:
            error = "Completa los campos obligatorios: nombre, apellido, CC/NIT y teléfono."
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO workers
                    (name, lastname, cc, phone_number, email, trabajo_desarrolla, fecha_ingreso, activo, observaciones,
                     foto, alias, direccion, ciudad, concepto_habitual, valor_habitual, lote_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (name, lastname, cc, phone_number, email, trabajo, fecha_ingreso, activo, observaciones,
                      foto_filename, alias, direccion, ciudad, concepto_habitual, valor_habitual, lote_id))
                conn.commit(); cursor.close(); conn.close()
                message = f"Trabajador {name} {lastname} registrado correctamente."
            except Exception as e:
                error = f"Error: {e}"

    return render_template('workers/create.html', message=message, error=error,
                           options=WORKER_OPTIONS, today=date.today().isoformat())


@app.route('/workers')
def lista_workers():
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    if not has_permission('worker.view'):
        return redirect(url_for('dashboard', msg='Sin permiso para ver trabajadores.', msg_type='danger'))
    lote_id = session['lote_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM workers WHERE lote_id=%s ORDER BY name, lastname", (lote_id,))
    workers = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('workers/lista.html', workers=workers)


@app.route('/workers/<int:wid>/edit', methods=['GET', 'POST'])
def edit_worker(wid):
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    lote_id = session['lote_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM workers WHERE id_worker=%s AND lote_id=%s", (wid, lote_id))
    worker = cursor.fetchone()
    if not worker:
        cursor.close(); conn.close()
        return redirect(url_for('lista_workers'))

    message = None
    error   = None
    if request.method == 'POST':
        name              = request.form.get('name', '').strip()
        lastname          = request.form.get('lastname', '').strip()
        cc                = request.form.get('cc', '').strip()
        phone_number      = request.form.get('phone_number', '').strip()
        email             = request.form.get('email') or None
        trabajo           = request.form.get('trabajo_desarrolla')
        fecha_ingreso     = request.form.get('fecha_ingreso') or None
        activo            = 1 if request.form.get('activo') == 'on' else 0
        observaciones     = request.form.get('observaciones') or None
        alias             = request.form.get('alias') or None
        direccion         = request.form.get('direccion') or None
        ciudad            = request.form.get('ciudad') or None
        concepto_habitual = request.form.get('concepto_habitual') or None
        vh_raw            = request.form.get('valor_habitual') or None
        valor_habitual    = float(vh_raw.replace('.','').replace(',','')) if vh_raw else None

        foto_filename = worker['foto']
        foto_file = request.files.get('foto')
        if foto_file and foto_file.filename and allowed_file(foto_file.filename):
            if foto_filename:
                old = os.path.join(UPLOAD_FOLDER, foto_filename)
                if os.path.exists(old):
                    os.remove(old)
            ext = foto_file.filename.rsplit('.', 1)[1].lower()
            foto_filename = f"{uuid.uuid4().hex}.{ext}"
            foto_file.save(os.path.join(UPLOAD_FOLDER, foto_filename))

        if not name or not lastname or not cc:
            error = "Nombre, apellido y CC/NIT son obligatorios."
        else:
            try:
                cursor2 = conn.cursor()
                cursor2.execute("""
                    UPDATE workers SET name=%s, lastname=%s, cc=%s, phone_number=%s, email=%s,
                    trabajo_desarrolla=%s, fecha_ingreso=%s, activo=%s, observaciones=%s,
                    foto=%s, alias=%s, direccion=%s, ciudad=%s,
                    concepto_habitual=%s, valor_habitual=%s
                    WHERE id_worker=%s AND lote_id=%s
                """, (name, lastname, cc, phone_number, email, trabajo, fecha_ingreso, activo,
                      observaciones, foto_filename, alias, direccion, ciudad,
                      concepto_habitual, valor_habitual, wid, lote_id))
                conn.commit(); cursor2.close()
                message = "Trabajador actualizado correctamente."
                cursor.execute("SELECT * FROM workers WHERE id_worker=%s", (wid,))
                worker = cursor.fetchone()
            except Exception as e:
                error = f"Error al actualizar: {e}"

    cursor.close(); conn.close()
    return render_template('workers/edit.html', worker=worker, message=message, error=error,
                           options=WORKER_OPTIONS)


@app.route('/workers/<int:wid>/toggle', methods=['POST'])
def toggle_worker(wid):
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    lote_id = session.get('lote_id')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if lote_id:
            cursor.execute("UPDATE workers SET activo=NOT activo WHERE id_worker=%s AND lote_id=%s", (wid, lote_id))
        else:
            cursor.execute("UPDATE workers SET activo=NOT activo WHERE id_worker=%s", (wid,))
        conn.commit(); cursor.close(); conn.close()
    except Exception:
        pass
    return redirect(url_for('lista_workers'))
