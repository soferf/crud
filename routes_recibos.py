"""
routes_recibos.py — Recibo CRUD and labor-specific routes.
"""
import json
from datetime import date

from flask import request, session, redirect, url_for, render_template, jsonify

from extensions import app
from db import get_db_connection
from utils import get_next_serial, es_concepto_prohibido, load_trabajadores
from session_service import auth_redirect

# Imported by routes_reportes and others
from routes_workers import _get_trabajadores_for_autocomplete, _build_recibo_form_data


TIPOS_LABOR_DIAS = {
    'desague':       {'label': 'Desagüe',          'vdia_default': 60000, 'dias_default': 1, 'icon': 'fa-droplet'},
    'despalillada':  {'label': 'Despalillada',      'vdia_default': 60000, 'dias_default': 1, 'icon': 'fa-hands'},
    'bordeada':      {'label': 'Bordeada',          'vdia_default': 80000, 'dias_default': 1, 'icon': 'fa-scissors'},
    'parche_maleza': {'label': 'Parche de maleza',  'vdia_default': 60000, 'dias_default': 1, 'icon': 'fa-leaf'},
    'chapola':       {'label': 'Chapola / rocería', 'vdia_default': 60000, 'dias_default': 1, 'icon': 'fa-tractor'},
    'otro':          {'label': 'Otro',              'vdia_default': 60000, 'dias_default': 1, 'icon': 'fa-ellipsis'},
}

TIPOS_LABOR_CANTIDAD = {
    'abonada':    {'label': 'Abonada',          'icon': 'fa-seedling',   'unit': 'bultos',    'vpunt_default': 13000},
    'fumigacion': {'label': 'Fumigación',        'icon': 'fa-spray-can', 'unit': 'jornales',  'vpunt_default': 60000},
    'corta':      {'label': 'Corta de arroz',    'icon': 'fa-wheat-awn', 'unit': 'hectáreas', 'vpunt_default': 650000},
    'carga':      {'label': 'Carga de camiones', 'icon': 'fa-truck',     'unit': 'camiones',  'vpunt_default': 0},
    'otro':       {'label': 'Otro',              'icon': 'fa-ellipsis',  'unit': 'unidades',  'vpunt_default': 0},
}


def _load_workers_for_form():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        lote_id = session.get('lote_id')
        if lote_id:
            cursor.execute("""SELECT id_worker, name, lastname, cc, trabajo_desarrolla,
                             valor_habitual, direccion, ciudad, phone_number as telefono, foto
                             FROM workers WHERE activo=1 AND lote_id=%s ORDER BY trabajo_desarrolla, name""", (lote_id,))
        else:
            cursor.execute("""SELECT id_worker, name, lastname, cc, trabajo_desarrolla,
                             valor_habitual, direccion, ciudad, phone_number as telefono, foto
                             FROM workers WHERE activo=1 ORDER BY trabajo_desarrolla, name""")
        workers = cursor.fetchall()
        cursor.close(); conn.close()
        for w in workers:
            if w.get('valor_habitual'):
                w['valor_habitual'] = float(w['valor_habitual'])
            w['nombre_completo'] = f"{w.get('name','')} {w.get('lastname','')}".strip()
            w['cargo']           = w.get('trabajo_desarrolla') or 'operario'
            w['foto_path']       = w.get('foto') or ''
        return workers
    except Exception:
        return []


@app.route('/recibos')
def lista_recibos():
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion para ver los recibos.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    if not has_permission('recibo.view'):
        return redirect(url_for('dashboard', msg='Sin permiso para ver recibos.', msg_type='danger'))
    lote_id = session['lote_id']
    error = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM recibos WHERE lote_id=%s ORDER BY serial", (lote_id,))
        recibos = cursor.fetchall()
        cursor.close(); conn.close()
        for r in recibos:
            r['neto_a_pagar']   = float(r['neto_a_pagar'] or 0)
            r['valor_operacion'] = float(r['valor_operacion'] or 0)
    except Exception as e:
        recibos = []; error = f"Error al cargar recibos: {e}"
    return render_template('recibos/lista.html', recibos=recibos, error=error,
                           lote_nombre=session.get('lote_nombre', f'Lote {lote_id}'))


@app.route('/recibos/nuevo', methods=['GET', 'POST'])
def nuevo_recibo():
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion para crear recibos.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    if request.method == 'POST' and not has_permission('recibo.create'):
        return redirect(url_for('lista_recibos'))

    lote_id     = session['lote_id']
    next_serial = get_next_serial(lote_id)
    error = warning = success = None
    form_data = {}

    if request.method == 'POST':
        serial      = request.form.get('serial', '').strip()
        fecha_str   = request.form.get('fecha', '').strip()
        proveedor   = request.form.get('proveedor', '').strip()
        nit         = request.form.get('nit', '').strip()
        direccion_r = request.form.get('direccion', '').strip()
        telefono    = request.form.get('telefono', '').strip()
        ciudad_r    = request.form.get('ciudad', '').strip()
        force       = request.form.get('force') == 'true'

        lineas = []
        for i in range(1, 8):
            c_text   = request.form.get(f'concepto_{i}', '').strip()
            c_val_raw = request.form.get(f'valor_{i}', '').strip().replace('.', '').replace(',', '')
            if c_text:
                lineas.append({'concepto': c_text, 'valor': float(c_val_raw) if c_val_raw else 0.0})

        concepto          = '\n'.join(l['concepto'] for l in lineas)
        valor_op          = sum(l['valor'] for l in lineas)
        conceptos_json_str = json.dumps(lineas, ensure_ascii=False)
        rte_raw   = request.form.get('rte_fte', '').strip().replace('.', '').replace(',', '')
        rte_fte   = float(rte_raw) if rte_raw else 0.0
        neto_raw  = request.form.get('neto_a_pagar', '').strip().replace('.', '').replace(',', '')

        form_data = {'serial': serial, 'fecha': fecha_str, 'proveedor': proveedor,
                     'nit': nit, 'direccion': direccion_r, 'telefono': telefono,
                     'ciudad': ciudad_r, 'lineas': lineas, 'rte_fte': rte_fte}

        if not serial or not proveedor or not lineas:
            error = "Serial, proveedor y al menos un concepto son obligatorios."
        elif not serial.isdigit():
            error = "El serial debe ser un número entero."
        elif any(es_concepto_prohibido(l['concepto']) for l in lineas):
            error = "⚠️ No se registran compras de aceite ni ACPM directo. Solo se registra el transporte de ACPM."
        else:
            serial_int = int(serial)
            fecha_obj  = None
            if fecha_str:
                try:
                    fecha_obj = date.fromisoformat(fecha_str)
                except ValueError:
                    error = "Formato de fecha inválido."

            if not error:
                neto = float(neto_raw) if neto_raw else max(0.0, valor_op - rte_fte)
                if fecha_obj and not force:
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor(dictionary=True)
                        cursor.execute("SELECT serial, fecha FROM recibos WHERE serial<%s AND lote_id=%s ORDER BY serial DESC LIMIT 1", (serial_int, lote_id))
                        prev = cursor.fetchone()
                        cursor.execute("SELECT serial, fecha FROM recibos WHERE serial>%s AND lote_id=%s ORDER BY serial ASC LIMIT 1", (serial_int, lote_id))
                        next_r = cursor.fetchone()
                        cursor.close(); conn.close()
                        msg_parts = []
                        if prev and prev['fecha'] and prev['fecha'] > fecha_obj:
                            msg_parts.append(f"el recibo anterior (serial {prev['serial']}) tiene fecha {prev['fecha'].strftime('%d/%m/%Y')}")
                        if next_r and next_r['fecha'] and next_r['fecha'] < fecha_obj:
                            msg_parts.append(f"el recibo siguiente (serial {next_r['serial']}) tiene fecha {next_r['fecha'].strftime('%d/%m/%Y')}")
                        if msg_parts:
                            warning = f"⚠️ Incongruencia serial-fecha: {'; '.join(msg_parts)}. ¿Deseas guardar de todas formas?"
                    except Exception:
                        pass

                if not warning or force:
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT serial FROM recibos WHERE serial=%s AND lote_id=%s", (serial_int, lote_id))
                        if cursor.fetchone():
                            cursor.execute("UPDATE recibos SET serial=serial+1 WHERE serial>=%s AND lote_id=%s ORDER BY serial DESC", (serial_int, lote_id))
                        cursor.execute("""
                            INSERT INTO recibos (serial, fecha, proveedor, nit, direccion, telefono, ciudad, concepto, valor_operacion, rte_fte, neto_a_pagar, conceptos_json, lote_id)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (serial_int, fecha_obj, proveedor, nit, direccion_r, telefono, ciudad_r, concepto, valor_op, rte_fte, neto, conceptos_json_str, lote_id))
                        conn.commit(); cursor.close(); conn.close()
                        success    = f"Recibo serial {serial_int} guardado correctamente."
                        form_data  = {}
                        next_serial = get_next_serial(lote_id)
                    except Exception as e:
                        error = f"Error al guardar: {e}"

    trabajadores = _get_trabajadores_for_autocomplete()
    return render_template('recibos/nuevo.html',
                           next_serial=next_serial, trabajadores=trabajadores,
                           error=error, warning=warning, success=success, form_data=form_data,
                           page_title='Nuevo Recibo',
                           page_subtitle='Registra un pago. El serial se asigna según la fecha.',
                           submit_label='Guardar recibo', serial_readonly=False,
                           page_mode='create', today=date.today().isoformat())


@app.route('/recibos/lote', methods=['GET', 'POST'])
def nuevo_recibo_lote():
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    lote_id     = session['lote_id']
    error = success = None
    next_serial = get_next_serial(lote_id)

    if request.method == 'POST':
        fecha_str   = request.form.get('fecha', '').strip()
        direccion_r = request.form.get('direccion', '').strip()
        ciudad_r    = request.form.get('ciudad', '').strip()
        vpt_raw     = request.form.get('valor_por_trabajador', '').strip().replace('.','').replace(',','')
        serial_inicio = request.form.get('serial_inicio', '').strip()
        worker_ids  = request.form.getlist('worker_ids')

        lineas_lote = []
        for i in range(1, 8):
            c_text   = request.form.get(f'concepto_{i}', '').strip()
            c_val_raw = request.form.get(f'valor_{i}', '').strip().replace('.', '').replace(',', '')
            if c_text:
                lineas_lote.append({'concepto': c_text, 'valor': float(c_val_raw) if c_val_raw else 0.0})
        concepto         = '\n'.join(l['concepto'] for l in lineas_lote)
        conceptos_json_lote = json.dumps(lineas_lote, ensure_ascii=False)

        if not worker_ids:
            error = "Selecciona al menos un trabajador."
        elif not lineas_lote:
            error = "El concepto es obligatorio."
        elif not serial_inicio or not serial_inicio.isdigit():
            error = "El serial de inicio debe ser un número."
        elif any(es_concepto_prohibido(l['concepto']) for l in lineas_lote):
            error = "⚠️ Las compras de aceite o ACPM directo no se registran."
        else:
            fecha_obj = None
            if fecha_str:
                try:
                    fecha_obj = date.fromisoformat(fecha_str)
                except ValueError:
                    error = "Formato de fecha inválido."

            if not error:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    placeholders = ','.join(['%s'] * len(worker_ids))
                    cursor.execute(
                        f"SELECT id_worker, name, lastname, cc, direccion, ciudad, phone_number as telefono, concepto_habitual, valor_habitual FROM workers WHERE id_worker IN ({placeholders}) AND lote_id=%s",
                        (*worker_ids, lote_id)
                    )
                    selected_workers = cursor.fetchall()
                    serial_int   = int(serial_inicio)
                    valor_lote   = sum(l['valor'] for l in lineas_lote)
                    valor_float  = float(vpt_raw) if vpt_raw else None
                    created = 0
                    for w in selected_workers:
                        wid_str = str(w['id_worker'])
                        proveedor_name = f"{w['name']} {w['lastname']}"
                        nit  = w['cc']
                        dir_w    = direccion_r or w.get('direccion') or ''
                        ciudad_w = ciudad_r    or w.get('ciudad') or ''
                        tel_w    = w.get('telefono') or ''
                        pworker_val_raw = request.form.get(f'valor_w_{wid_str}', '').strip()
                        if pworker_val_raw and pworker_val_raw not in ('0', '0.0'):
                            val = float(pworker_val_raw)
                            lineas_w = ([{'concepto': lineas_lote[0]['concepto'], 'valor': val}] + lineas_lote[1:]) if lineas_lote else [{'concepto': concepto, 'valor': val}]
                        elif valor_float:
                            lineas_w = [lineas_lote[0] | {'valor': valor_float}] + lineas_lote[1:]
                            val = valor_float
                        else:
                            lineas_w = lineas_lote
                            val = valor_lote or (float(w['valor_habitual']) if w.get('valor_habitual') else None)
                        cj = json.dumps(lineas_w, ensure_ascii=False)
                        cursor2 = conn.cursor()
                        cursor2.execute("SELECT serial FROM recibos WHERE serial=%s", (serial_int,))
                        if cursor2.fetchone():
                            cursor2.execute("UPDATE recibos SET serial=serial+1 WHERE serial>=%s ORDER BY serial DESC", (serial_int,))
                        cursor2.execute("""
                            INSERT INTO recibos (serial, fecha, proveedor, nit, direccion, telefono, ciudad, concepto, valor_operacion, rte_fte, neto_a_pagar, conceptos_json, lote_id)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (serial_int, fecha_obj, proveedor_name, nit, dir_w, tel_w, ciudad_w, concepto, val, 0, val, cj, lote_id))
                        cursor2.close(); serial_int += 1; created += 1
                    conn.commit(); cursor.close(); conn.close()
                    success    = f"✅ {created} recibo(s) creados correctamente (seriales {serial_inicio}–{serial_int-1})."
                    next_serial = get_next_serial(lote_id)
                except Exception as e:
                    error = f"Error: {e}"

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        lote_id_fetch = session.get('lote_id')
        if lote_id_fetch:
            cursor.execute("SELECT id_worker, name, lastname, cc, trabajo_desarrolla, concepto_habitual, valor_habitual, foto FROM workers WHERE activo=1 AND lote_id=%s ORDER BY trabajo_desarrolla, name", (lote_id_fetch,))
        else:
            cursor.execute("SELECT id_worker, name, lastname, cc, trabajo_desarrolla, concepto_habitual, valor_habitual, foto FROM workers WHERE activo=1 ORDER BY trabajo_desarrolla, name")
        db_workers = cursor.fetchall()
        cursor.close(); conn.close()
        for w in db_workers:
            if w.get('valor_habitual'): w['valor_habitual'] = float(w['valor_habitual'])
            w['nombre_completo'] = f"{w.get('name','')} {w.get('lastname','')}".strip()
            w['cargo']    = w.get('trabajo_desarrolla') or 'operario'
            w['foto_path'] = w.get('foto') or ''
    except Exception:
        db_workers = []

    trabajadores_json = load_trabajadores()
    return render_template('recibos/lote.html',
                           db_workers=db_workers, trabajadores_json=trabajadores_json,
                           next_serial=next_serial, error=error, success=success,
                           today=date.today().isoformat())


@app.route('/recibos/labores/desague', methods=['GET', 'POST'])
def labores_desague():
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    lote_id = session.get('lote_id')
    error = success = None
    next_serial = get_next_serial(lote_id)

    if request.method == 'POST':
        tipo_labor    = request.form.get('tipo_labor', 'desague')
        fecha_str     = request.form.get('fecha', '').strip()
        serial_ini    = request.form.get('serial_inicio', '').strip()
        direccion_r   = request.form.get('direccion', '').strip()
        ciudad_r      = request.form.get('ciudad', '').strip()
        lote_nombre   = request.form.get('lote_nombre', 'El Mangon').strip()
        concepto_base = request.form.get('concepto_base', '').strip()
        worker_ids    = request.form.getlist('worker_ids')
        labor_info    = TIPOS_LABOR_DIAS.get(tipo_labor, TIPOS_LABOR_DIAS['otro'])

        if not worker_ids:
            error = "Selecciona al menos un trabajador."
        elif not serial_ini or not serial_ini.isdigit():
            error = "El serial de inicio debe ser un número válido."
        else:
            rte_pct = float(request.form.get('rte_fte', '0') or '0')
            fecha_obj = None
            if fecha_str:
                try:
                    fecha_obj = date.fromisoformat(fecha_str)
                except ValueError:
                    error = "Formato de fecha inválido."

            if not error:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    placeholders = ','.join(['%s'] * len(worker_ids))
                    cursor.execute(
                        f"SELECT id_worker, name, lastname, cc, direccion, ciudad, phone_number as telefono FROM workers WHERE id_worker IN ({placeholders}) AND lote_id=%s",
                        (*worker_ids, lote_id)
                    )
                    selected_workers = cursor.fetchall()
                    serial_int = int(serial_ini)
                    created = 0
                    for w in selected_workers:
                        wid_str = str(w['id_worker'])
                        try:
                            dias = float(request.form.get(f'dias_w_{wid_str}', str(labor_info['dias_default'])) or labor_info['dias_default'])
                            frac = float(request.form.get(f'frac_w_{wid_str}', '0') or 0)
                            vdia = float((request.form.get(f'vdia_w_{wid_str}', str(labor_info['vdia_default'])) or str(labor_info['vdia_default'])).replace('.','').replace(',',''))
                        except Exception:
                            dias, frac, vdia = 1.0, 0.0, float(labor_info['vdia_default'])
                        total_dias = dias + frac
                        valor      = total_dias * vdia
                        rte_amount = round(valor * rte_pct / 100)
                        neto       = valor - rte_amount
                        frac_txt   = {0.25: ' y ¼ día', 0.5: ' y ½ día', 0.75: ' y ¾ día'}.get(frac, '')
                        dias_int   = int(dias)
                        dias_txt   = f"{dias_int} {'día' if dias_int == 1 else 'días'}{frac_txt}"
                        concepto_txt = concepto_base or f"{labor_info['label']} {dias_txt} en el lote {lote_nombre}"
                        proveedor_name = f"{w['name']} {w['lastname']}"
                        dir_w    = direccion_r or w.get('direccion') or ''
                        ciudad_w = ciudad_r    or w.get('ciudad')    or ''
                        tel_w    = w.get('telefono') or ''
                        lineas   = [{'concepto': concepto_txt, 'valor': valor}]
                        cj       = json.dumps(lineas, ensure_ascii=False)
                        cursor2 = conn.cursor()
                        cursor2.execute("SELECT serial FROM recibos WHERE serial=%s AND lote_id=%s", (serial_int, lote_id))
                        if cursor2.fetchone():
                            cursor2.execute("UPDATE recibos SET serial=serial+1 WHERE serial>=%s AND lote_id=%s ORDER BY serial DESC", (serial_int, lote_id))
                        cursor2.execute("""
                            INSERT INTO recibos (serial, fecha, proveedor, nit, direccion, telefono, ciudad, concepto, valor_operacion, rte_fte, neto_a_pagar, conceptos_json, lote_id)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (serial_int, fecha_obj, proveedor_name, w['cc'], dir_w, tel_w, ciudad_w, concepto_txt, valor, rte_amount, neto, cj, lote_id))
                        cursor2.close(); serial_int += 1; created += 1
                    conn.commit(); cursor.close(); conn.close()
                    success    = f"✅ {created} recibo(s) creados para {labor_info['label']} (seriales {serial_ini}–{serial_int-1})."
                    next_serial = get_next_serial(lote_id)
                except Exception as e:
                    error = f"Error al guardar: {e}"

    db_workers = _load_workers_for_form()
    return render_template('recibos/labores_desague.html',
                           db_workers=db_workers, tipos_labor=TIPOS_LABOR_DIAS,
                           next_serial=next_serial, error=error, success=success,
                           today=date.today().isoformat())


@app.route('/recibos/labores/abonada', methods=['GET', 'POST'])
def labores_abonada():
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    lote_id = session.get('lote_id')
    error = success = None
    next_serial = get_next_serial(lote_id)

    if request.method == 'POST':
        tipo_labor    = request.form.get('tipo_labor', 'abonada')
        fecha_str     = request.form.get('fecha', '').strip()
        serial_ini    = request.form.get('serial_inicio', '').strip()
        direccion_r   = request.form.get('direccion', '').strip()
        ciudad_r      = request.form.get('ciudad', '').strip()
        lote_nombre   = request.form.get('lote_nombre', 'El Mangon').strip()
        concepto_base = request.form.get('concepto_base', '').strip()
        worker_ids    = request.form.getlist('worker_ids')
        labor_info    = TIPOS_LABOR_CANTIDAD.get(tipo_labor, TIPOS_LABOR_CANTIDAD['otro'])

        if not worker_ids:
            error = "Selecciona al menos un trabajador."
        elif not serial_ini or not serial_ini.isdigit():
            error = "El serial de inicio debe ser un número válido."
        else:
            rte_pct = float(request.form.get('rte_fte', '0') or '0')
            fecha_obj = None
            if fecha_str:
                try:
                    fecha_obj = date.fromisoformat(fecha_str)
                except ValueError:
                    error = "Formato de fecha inválido."

            if not error:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    placeholders = ','.join(['%s'] * len(worker_ids))
                    cursor.execute(
                        f"SELECT id_worker, name, lastname, cc, direccion, ciudad, phone_number as telefono FROM workers WHERE id_worker IN ({placeholders}) AND lote_id=%s",
                        (*worker_ids, lote_id)
                    )
                    selected_workers = cursor.fetchall()
                    serial_int = int(serial_ini)
                    created = 0
                    for w in selected_workers:
                        wid_str = str(w['id_worker'])
                        try:
                            valor = float(request.form.get(f'valor_w_{wid_str}', '0') or '0')
                            cant  = float((request.form.get(f'cant_w_{wid_str}', '0') or '0').replace('.','').replace(',',''))
                            vpunt = float((request.form.get(f'vpunt_w_{wid_str}', str(labor_info['vpunt_default'])) or str(labor_info['vpunt_default'])).replace('.','').replace(',',''))
                        except Exception:
                            valor, cant, vpunt = 0.0, 0.0, float(labor_info['vpunt_default'])
                        rte_amount   = round(valor * rte_pct / 100)
                        neto         = valor - rte_amount
                        unit_label   = labor_info['unit']
                        vpunt_fmt    = f"{int(vpunt):,}".replace(',','.')
                        concepto_txt = concepto_base or f"{labor_info['label']} {cant:.0f} {unit_label} × $ {vpunt_fmt} c/u en el lote {lote_nombre}"
                        proveedor_name = f"{w['name']} {w['lastname']}"
                        dir_w    = direccion_r or w.get('direccion') or ''
                        ciudad_w = ciudad_r    or w.get('ciudad')    or ''
                        tel_w    = w.get('telefono') or ''
                        lineas   = [{'concepto': concepto_txt, 'valor': valor}]
                        cj       = json.dumps(lineas, ensure_ascii=False)
                        cursor2 = conn.cursor()
                        cursor2.execute("SELECT serial FROM recibos WHERE serial=%s AND lote_id=%s", (serial_int, lote_id))
                        if cursor2.fetchone():
                            cursor2.execute("UPDATE recibos SET serial=serial+1 WHERE serial>=%s AND lote_id=%s ORDER BY serial DESC", (serial_int, lote_id))
                        cursor2.execute("""
                            INSERT INTO recibos (serial, fecha, proveedor, nit, direccion, telefono, ciudad, concepto, valor_operacion, rte_fte, neto_a_pagar, conceptos_json, lote_id)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (serial_int, fecha_obj, proveedor_name, w['cc'], dir_w, tel_w, ciudad_w, concepto_txt, valor, rte_amount, neto, cj, lote_id))
                        cursor2.close(); serial_int += 1; created += 1
                    conn.commit(); cursor.close(); conn.close()
                    success    = f"✅ {created} recibo(s) creados para {labor_info['label']} (seriales {serial_ini}–{serial_int-1})."
                    next_serial = get_next_serial(lote_id)
                except Exception as e:
                    error = f"Error al guardar: {e}"

    db_workers = _load_workers_for_form()
    return render_template('recibos/labores_abonada.html',
                           db_workers=db_workers, tipos_labor=TIPOS_LABOR_CANTIDAD,
                           next_serial=next_serial, error=error, success=success,
                           today=date.today().isoformat())


@app.route('/recibos/<int:serial>')
def detalle_recibo(serial):
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    lote_id = session.get('lote_id')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if lote_id:
        cursor.execute("SELECT * FROM recibos WHERE serial=%s AND lote_id=%s", (serial, lote_id))
    else:
        cursor.execute("SELECT * FROM recibos WHERE serial=%s", (serial,))
    recibo = cursor.fetchone()
    cursor.close(); conn.close()
    if not recibo:
        return redirect(url_for('lista_recibos'))
    for field in ('neto_a_pagar', 'valor_operacion', 'rte_fte'):
        if recibo.get(field) is not None:
            recibo[field] = float(recibo[field])
    conceptos_lineas = []
    if recibo.get('conceptos_json'):
        try:
            conceptos_lineas = json.loads(recibo['conceptos_json'])
        except Exception:
            pass
    return render_template('recibos/detalle.html', recibo=recibo, conceptos_lineas=conceptos_lineas,
                           can_edit=has_permission('recibo.edit'),
                           can_delete=has_permission('recibo.delete'))


@app.route('/recibos/<int:serial>/editar', methods=['GET', 'POST'])
def editar_recibo(serial):
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion para editar recibos.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    if not has_permission('recibo.edit'):
        return redirect(url_for('lista_recibos'))

    lote_id = session['lote_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recibos WHERE serial=%s AND lote_id=%s", (serial, lote_id))
    recibo = cursor.fetchone()
    if not recibo:
        cursor.close(); conn.close()
        return redirect(url_for('lista_recibos'))

    success = error = warning = None
    form_data = _build_recibo_form_data(recibo)

    if request.method == 'POST':
        fecha_str   = request.form.get('fecha', '').strip()
        proveedor   = request.form.get('proveedor', '').strip()
        nit         = request.form.get('nit', '').strip()
        direccion_r = request.form.get('direccion', '').strip()
        telefono    = request.form.get('telefono', '').strip()
        ciudad_r    = request.form.get('ciudad', '').strip()

        lineas = []
        for i in range(1, 8):
            c_text   = request.form.get(f'concepto_{i}', '').strip()
            c_val_raw = request.form.get(f'valor_{i}', '').strip().replace('.', '').replace(',', '')
            if c_text:
                lineas.append({'concepto': c_text, 'valor': float(c_val_raw) if c_val_raw else 0.0})
        concepto          = '\n'.join(l['concepto'] for l in lineas)
        valor_op          = sum(l['valor'] for l in lineas)
        conceptos_json_str = json.dumps(lineas, ensure_ascii=False)
        rte_raw  = request.form.get('rte_fte', '').strip().replace('.', '').replace(',', '')
        rte_fte  = float(rte_raw) if rte_raw else 0.0
        neto_raw = request.form.get('neto_a_pagar', '').strip().replace('.', '').replace(',', '')

        form_data = {'serial': serial, 'fecha': fecha_str, 'proveedor': proveedor,
                     'nit': nit, 'direccion': direccion_r, 'telefono': telefono,
                     'ciudad': ciudad_r, 'lineas': lineas, 'rte_fte': rte_fte,
                     'neto_a_pagar': float(neto_raw) if neto_raw else max(0.0, valor_op - rte_fte)}

        if not proveedor or not lineas:
            error = 'Proveedor y al menos un concepto son obligatorios.'
        elif any(es_concepto_prohibido(l['concepto']) for l in lineas):
            error = '⚠️ No se registran compras de aceite ni ACPM directo.'
        else:
            fecha_obj = None
            if fecha_str:
                try:
                    fecha_obj = date.fromisoformat(fecha_str)
                except ValueError:
                    error = 'Formato de fecha inválido.'
            if not error:
                neto = float(neto_raw) if neto_raw else max(0.0, valor_op - rte_fte)
                try:
                    cursor2 = conn.cursor()
                    cursor2.execute("""
                        UPDATE recibos
                        SET fecha=%s, proveedor=%s, nit=%s, direccion=%s, telefono=%s, ciudad=%s,
                            concepto=%s, valor_operacion=%s, rte_fte=%s, neto_a_pagar=%s, conceptos_json=%s
                        WHERE serial=%s AND lote_id=%s
                    """, (fecha_obj, proveedor, nit, direccion_r, telefono, ciudad_r,
                          concepto, valor_op, rte_fte, neto, conceptos_json_str, serial, lote_id))
                    conn.commit(); cursor2.close()
                    cursor.execute("SELECT * FROM recibos WHERE serial=%s AND lote_id=%s", (serial, lote_id))
                    recibo    = cursor.fetchone()
                    form_data = _build_recibo_form_data(recibo)
                    success   = f'Recibo #{serial} actualizado correctamente.'
                except Exception as e:
                    error = f'Error al actualizar: {e}'

    cursor.close(); conn.close()
    trabajadores = _get_trabajadores_for_autocomplete()
    return render_template('recibos/nuevo.html',
                           next_serial=serial, trabajadores=trabajadores,
                           error=error, warning=warning, success=success, form_data=form_data,
                           page_title=f'Editar Recibo #{serial}',
                           page_subtitle='Corrige los datos del recibo sin depender de la base manual.',
                           submit_label='Guardar cambios', serial_readonly=True,
                           page_mode='edit',
                           form_action=url_for('editar_recibo', serial=serial),
                           back_url=url_for('detalle_recibo', serial=serial),
                           back_label='Ver detalle',
                           today=date.today().isoformat())


@app.route('/recibos/<int:serial>/eliminar', methods=['POST'])
def eliminar_recibo(serial):
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    lote_id = session.get('lote_id')
    if lote_id and not has_permission('recibo.delete'):
        return redirect(url_for('lista_recibos'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if lote_id:
        cursor.execute("DELETE FROM recibos WHERE serial=%s AND lote_id=%s", (serial, lote_id))
    else:
        cursor.execute("DELETE FROM recibos WHERE serial=%s", (serial,))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('lista_recibos'))


@app.route('/recibos/conciliacion')
def conciliacion_recibos():
    from auth_middleware import has_permission
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion para conciliar recibos.', 'warning')
    if not has_permission('recibo.view'):
        return redirect(url_for('dashboard', msg='Sin permiso para ver recibos.', msg_type='danger'))

    q        = request.args.get('q', '').strip().lower()
    lote_sel = request.args.get('lote_id', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if session.get('is_superadmin'):
        cursor.execute("SELECT id, nombre FROM lotes ORDER BY nombre")
        lotes = cursor.fetchall()
    else:
        from session_service import _get_user_lotes
        lotes = _get_user_lotes(session['user_id'])
        lotes = [{'id': l.get('id'), 'nombre': l.get('nombre')} for l in lotes]
        if not lotes and session.get('lote_id'):
            lotes = [{'id': session['lote_id'], 'nombre': session.get('lote_nombre', f"Lote {session['lote_id']}")}]

    lote_ids = [int(l['id']) for l in lotes if l.get('id') is not None]
    if not lote_ids:
        cursor.close(); conn.close()
        return render_template('recibos/conciliacion.html', recibos=[], lotes=[], resumen_lotes=[],
                               selected_lote='', search=q, total_recibos=0, total_neto=0)

    placeholders = ','.join(['%s'] * len(lote_ids))
    params = list(lote_ids)
    sql = f"""
        SELECT r.serial, r.fecha, r.proveedor, r.nit, r.concepto, r.neto_a_pagar,
               r.lote_id, l.nombre AS lote_nombre
        FROM recibos r
        LEFT JOIN lotes l ON l.id = r.lote_id
        WHERE r.lote_id IN ({placeholders})
    """
    if lote_sel and lote_sel.isdigit() and int(lote_sel) in lote_ids:
        sql += " AND r.lote_id = %s"; params.append(int(lote_sel))
    if q:
        like = f'%{q}%'
        sql += " AND (LOWER(r.proveedor) LIKE %s OR LOWER(IFNULL(r.nit,'')) LIKE %s OR LOWER(IFNULL(r.concepto,'')) LIKE %s OR CAST(r.serial AS CHAR) LIKE %s)"
        params.extend([like, like, like, like])
    sql += " ORDER BY r.lote_id, r.serial DESC"
    cursor.execute(sql, tuple(params))
    recibos = cursor.fetchall()

    resumen = {}
    for row in recibos:
        row['neto_a_pagar'] = float(row.get('neto_a_pagar') or 0)
        lk = row['lote_id']
        item = resumen.setdefault(lk, {'lote_id': lk, 'lote_nombre': row.get('lote_nombre') or f'Lote {lk}',
                                        'total_recibos': 0, 'total_neto': 0.0,
                                        'min_serial': row['serial'], 'max_serial': row['serial']})
        item['total_recibos'] += 1
        item['total_neto']    += row['neto_a_pagar']
        item['min_serial'] = min(item['min_serial'], row['serial'])
        item['max_serial'] = max(item['max_serial'], row['serial'])

    resumen_lotes = sorted(resumen.values(), key=lambda item: (item['lote_nombre'] or '', item['lote_id']))
    total_neto    = sum(row['neto_a_pagar'] for row in recibos)
    cursor.close(); conn.close()
    return render_template('recibos/conciliacion.html',
                           recibos=recibos, lotes=lotes, resumen_lotes=resumen_lotes,
                           selected_lote=lote_sel, search=q,
                           total_recibos=len(recibos), total_neto=total_neto)
