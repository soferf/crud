"""
routes_produccion.py — Produccion (cosechas/siembras) routes.
"""
from datetime import date, timedelta

from flask import request, session, redirect, url_for, render_template

from extensions import app
from db import get_db_connection
from config import TOTAL_HA, MIN_CARGAS, MIN_CARGAS_POR_HA, KG_POR_CARGA
from session_service import auth_redirect
from ciclo_service import (get_ciclo_activo, duracion_variedad,
                           estado_ciclo, costos_ciclo, ETAPAS)

# Exponer las 9 etapas fenológicas a las plantillas (stepper de campaña)
app.jinja_env.globals.setdefault('ETAPAS_ARROZ', ETAPAS)


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

                conn   = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                ciclo_activo = get_ciclo_activo(lote_id, conn)

                if fase == 'siembra':
                    # SIEMBRA → abre una campaña (ciclo de producción).
                    if ciclo_activo:
                        error = (f"Ya hay una campaña activa (#{ciclo_activo['id']}: "
                                 f"{ciclo_activo.get('variedad_semilla') or 'sin variedad'}, "
                                 f"sembrada el {ciclo_activo['fecha_siembra']}). "
                                 f"Ciérrala registrando su cosecha antes de iniciar una nueva.")
                    else:
                        fsiembra = (date.fromisoformat(fecha_siembra_str)
                                    if fecha_siembra_str else fecha_obj)
                        dur          = duracion_variedad(variedad_semilla)
                        fcosecha_est = fsiembra + timedelta(days=dur)
                        nombre_ciclo = f"Campaña {variedad_semilla or 'Arroz'} · {fsiembra.isoformat()}"
                        cursor.execute("""
                            INSERT INTO ciclos_produccion
                                (lote_id, nombre, variedad_semilla, origen_semilla, metodo_siembra,
                                 hectareas, bultos_ha, total_bultos, fecha_siembra,
                                 duracion_estimada_dias, fecha_cosecha_estimada, estado, observaciones)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'activo',%s)
                        """, (lote_id, nombre_ciclo, variedad_semilla, origen_semilla, metodo_siembra,
                              ha, bultos_ha, total_bultos, fsiembra, dur, fcosecha_est, observaciones))
                        conn.commit()
                        success = (f"🌱 Campaña iniciada: {variedad_semilla or 'variedad sin especificar'} "
                                   f"({total_bultos or '?'} bultos). Cosecha estimada ~{fcosecha_est.isoformat()}. "
                                   f"Desde ahora los gastos del lote se cargan a esta campaña.")
                else:
                    # COSECHA → se registra (el trigger la asigna al ciclo activo) y cierra la campaña.
                    cursor.execute("""
                        INSERT INTO cosechas
                            (fecha, lote, hectareas, cargas, kg_total,
                             precio_carga, valor_total, observaciones,
                             fase, variedad_semilla, origen_semilla,
                             bultos_ha, total_bultos, metodo_siembra, fecha_siembra, lote_id)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (fecha_obj, lote, ha,
                          cargas, kg_total,
                          precio, valor_total, observaciones,
                          fase, variedad_semilla, origen_semilla,
                          bultos_ha, total_bultos, metodo_siembra,
                          (ciclo_activo['fecha_siembra'] if ciclo_activo else None), lote_id))
                    conn.commit()

                    if ciclo_activo:
                        cursor.execute("""
                            SELECT COALESCE(SUM(cargas),0) c, COALESCE(SUM(kg_total),0) k,
                                   COALESCE(SUM(valor_total),0) v
                            FROM cosechas WHERE ciclo_id=%s AND fase='cosecha'
                        """, (ciclo_activo['id'],))
                        tot = cursor.fetchone() or {}
                        cursor.execute("""
                            UPDATE ciclos_produccion
                            SET estado='cerrado', fecha_cierre=%s,
                                cargas_total=%s, kg_total=%s, valor_cosecha=%s
                            WHERE id=%s
                        """, (fecha_obj, int(tot.get('c') or 0), float(tot.get('k') or 0),
                              float(tot.get('v') or 0), ciclo_activo['id']))
                        conn.commit()
                        success = (f"🌾 Cosecha registrada: {cargas} cargas ({kg_total:,.0f} kg). "
                                   f"Campaña #{ciclo_activo['id']} cerrada — ya puedes ver su costo total.")
                    else:
                        success = f"🌾 Cosecha registrada: {cargas} cargas ({kg_total:,.0f} kg)."

                cursor.close(); conn.close()
            except Exception as e:
                error = f"Error: {e}"

    # Campaña activa (para mostrar el estado y guiar el formulario)
    ciclo_activo = get_ciclo_activo(lote_id)
    ciclo_estado = estado_ciclo(ciclo_activo) if ciclo_activo else None

    return render_template('produccion/nueva.html',
                           error=error, success=success,
                           today=date.today().isoformat(),
                           total_ha=lote_ha,
                           min_cargas=MIN_CARGAS,
                           min_cargas_ha=MIN_CARGAS_POR_HA,
                           ciclo=ciclo_estado)


@app.route('/produccion/ciclos')
def lista_ciclos():
    """Línea de tiempo de campañas (ciclos) con su etapa y costo por campaña."""
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    lote_id = session['lote_id']

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM ciclos_produccion WHERE lote_id=%s ORDER BY estado='activo' DESC, fecha_siembra DESC",
        (lote_id,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()

    ciclos = []
    for r in rows:
        est = estado_ciclo(r)
        est['costos'] = costos_ciclo(r['id'])
        for k in ('kg_total', 'valor_cosecha'):
            if est.get(k) is not None:
                est[k] = float(est[k])
        ciclos.append(est)

    activo = next((c for c in ciclos if c['estado'] == 'activo'), None)
    return render_template('produccion/ciclos.html', ciclos=ciclos, activo=activo)
