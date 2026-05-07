"""
routes_produccion.py — Produccion (cosechas/siembras) routes.
"""
from datetime import date

from flask import request, session, redirect, url_for, render_template

from extensions import app
from db import get_db_connection
from config import TOTAL_HA, MIN_CARGAS, MIN_CARGAS_POR_HA, KG_POR_CARGA
from session_service import auth_redirect


@app.route('/produccion')
def lista_produccion():
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    lote_id = session['lote_id']
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cosechas WHERE lote_id=%s ORDER BY fecha DESC", (lote_id,))
    cosechas = cursor.fetchall()
    cursor.execute(
        "SELECT COALESCE(SUM(cargas),0) as tc, COALESCE(SUM(kg_total),0) as tk, "
        "COALESCE(SUM(valor_total),0) as tv FROM cosechas WHERE lote_id=%s", (lote_id,))
    totales = cursor.fetchone()
    cursor.execute("SELECT hectareas, meta_cargas_ha FROM lotes WHERE id=%s", (lote_id,))
    lote_row = cursor.fetchone() or {}
    cursor.close(); conn.close()

    for c in cosechas:
        for k in ['kg_total','precio_carga','valor_total','bultos_ha','total_bultos']:
            if c.get(k): c[k] = float(c[k])

    total_cargas = int(totales['tc'] or 0)
    lote_ha      = float(lote_row.get('hectareas') or TOTAL_HA)
    meta_cargas  = int(lote_ha * (lote_row.get('meta_cargas_ha') or MIN_CARGAS_POR_HA))
    pct_produccion = min(100, round(total_cargas / meta_cargas * 100, 1)) if meta_cargas else 0

    return render_template('produccion/index.html',
        cosechas=cosechas, totales=totales,
        min_cargas=meta_cargas, min_cargas_ha=MIN_CARGAS_POR_HA,
        kg_por_carga=KG_POR_CARGA, total_ha=lote_ha,
        total_cargas=total_cargas, pct_produccion=pct_produccion)


@app.route('/produccion/nueva', methods=['GET', 'POST'])
def nueva_cosecha():
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    lote_id = session['lote_id']
    error   = None
    success = None

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nombre, hectareas FROM lotes WHERE id=%s", (lote_id,))
        lote_row    = cursor.fetchone() or {}
        cursor.close(); conn.close()
        nombre_lote = lote_row.get('nombre', 'El Mangon')
        lote_ha     = float(lote_row.get('hectareas') or TOTAL_HA)
    except Exception:
        nombre_lote = 'El Mangon'
        lote_ha     = TOTAL_HA

    if request.method == 'POST':
        fecha_str        = request.form.get('fecha', '').strip()
        lote             = request.form.get('lote', nombre_lote).strip()
        hectareas        = request.form.get('hectareas', str(lote_ha)).strip()
        cargas_raw       = request.form.get('cargas', '').strip()
        precio_carga_raw = request.form.get('precio_carga', '').strip().replace('.','').replace(',','')
        fase             = request.form.get('fase', 'cosecha').strip()
        variedad_semilla = request.form.get('variedad_semilla', '').strip() or None
        origen_semilla   = request.form.get('origen_semilla',   '').strip() or None
        bultos_ha_raw    = request.form.get('bultos_ha', '').strip()
        metodo_siembra   = request.form.get('metodo_siembra', 'al_voleo').strip()
        fecha_siembra_str = request.form.get('fecha_siembra', '').strip() or None
        observaciones    = request.form.get('observaciones') or None

        if not fecha_str:
            error = "La fecha es obligatoria."
        elif fase == 'cosecha' and not cargas_raw:
            error = "El número de cargas es obligatorio para registrar una cosecha."
        else:
            try:
                fecha_obj   = date.fromisoformat(fecha_str)
                ha          = float(hectareas) if hectareas else lote_ha
                cargas      = int(cargas_raw)  if cargas_raw else 0
                kg_total    = cargas * KG_POR_CARGA if cargas else None
                precio      = float(precio_carga_raw) if precio_carga_raw else None
                valor_total = cargas * precio if (cargas and precio) else None
                bultos_ha   = float(bultos_ha_raw) if bultos_ha_raw else None
                total_bultos = round(bultos_ha * ha, 2) if (bultos_ha and ha) else None
                fecha_siembra_obj = date.fromisoformat(fecha_siembra_str) if fecha_siembra_str else None

                conn   = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO cosechas
                        (fecha, lote, hectareas, cargas, kg_total,
                         precio_carga, valor_total, observaciones,
                         fase, variedad_semilla, origen_semilla,
                         bultos_ha, total_bultos, metodo_siembra, fecha_siembra, lote_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (fecha_obj, lote, ha,
                      cargas if cargas else None, kg_total,
                      precio, valor_total, observaciones,
                      fase, variedad_semilla, origen_semilla,
                      bultos_ha, total_bultos, metodo_siembra, fecha_siembra_obj, lote_id))
                conn.commit(); cursor.close(); conn.close()
                if fase == 'cosecha':
                    success = f"Cosecha registrada: {cargas} cargas ({kg_total:,.0f} kg)."
                else:
                    success = f"Siembra registrada: {variedad_semilla or 'variedad sin especificar'} — {total_bultos or '?'} bultos totales."
            except Exception as e:
                error = f"Error: {e}"

    return render_template('produccion/nueva.html',
                           error=error, success=success,
                           today=date.today().isoformat(),
                           total_ha=lote_ha,
                           min_cargas=MIN_CARGAS,
                           min_cargas_ha=MIN_CARGAS_POR_HA)
