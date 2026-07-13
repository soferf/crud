"""
routes_humedad.py — Módulo de medidor de humedad y gestión de riego.

Provee la interfaz web y las APIs JSON del sistema de sensores de humedad para
lotes de arroz. Hoy se alimenta de datos simulados (humedad_sim) con lógica
agronómica real; el endpoint /humedad/api/ingest queda listo para recibir
lecturas reales desde dispositivos Arduino/ESP32.
"""
from datetime import datetime

from flask import request, session, redirect, url_for, render_template, jsonify

from extensions import app, csrf
from db import get_db_connection
from session_service import auth_redirect
from auth_middleware import has_permission
import humedad_sim as hs


def _require_humedad():
    """Valida login + lote activo. Devuelve (lote_id, None) o (None, respuesta)."""
    if 'user_id' not in session:
        return None, auth_redirect('login', 'Inicia sesión para continuar.', 'warning')
    if not session.get('lote_id'):
        return None, redirect(url_for('select_lote'))
    return session['lote_id'], None


# ── Vista principal ───────────────────────────────────────────────────────────
@app.route('/humedad')
def humedad_panel():
    lote_id, err = _require_humedad()
    if err:
        return err
    if not has_permission('humedad.view'):
        return redirect(url_for('dashboard'))

    # Asegura configuración y al menos una malla de sensores.
    hs.get_config(lote_id)
    if not hs.get_sensores(lote_id):
        hs.crear_sensores(lote_id, 6, forma='rectangular')

    estado = hs.avanzar_simulacion(lote_id)
    serie = hs.serie_promedio(lote_id)
    eventos = hs.historial_riego(lote_id)
    recs = hs.recomendaciones(estado)
    puede_gestionar = has_permission('humedad.manage')

    return render_template('humedad/index.html',
        lote_nombre=session.get('lote_nombre', ''),
        estado=estado, serie=serie, eventos=eventos,
        recomendaciones=recs, fases=hs.FASES_ARROZ,
        puede_gestionar=puede_gestionar)


@app.route('/humedad/sensores')
def humedad_sensores():
    lote_id, err = _require_humedad()
    if err:
        return err
    if not has_permission('humedad.manage'):
        return redirect(url_for('humedad_panel'))
    cfg = hs.get_config(lote_id)
    sensores = hs.get_sensores(lote_id, solo_activos=False)
    return render_template('humedad/sensores.html',
        lote_nombre=session.get('lote_nombre', ''),
        cfg=cfg, sensores=sensores,
        n_sensores=len(sensores))


# ── APIs JSON ─────────────────────────────────────────────────────────────────
@app.route('/humedad/api/estado')
def humedad_api_estado():
    """Avanza la simulación y devuelve el estado actual + serie temporal."""
    lote_id, err = _require_humedad()
    if err:
        return jsonify({'error': 'no-auth'}), 401
    if not has_permission('humedad.view'):
        return jsonify({'error': 'forbidden'}), 403
    estado = hs.avanzar_simulacion(lote_id)
    estado['serie'] = hs.serie_promedio(lote_id)
    estado['recomendaciones'] = [
        {'nivel': n, 'icono': i, 'texto': t} for (n, i, t) in hs.recomendaciones(estado)
    ]
    return jsonify(estado)


@csrf.exempt
@app.route('/humedad/api/riego', methods=['POST'])
def humedad_api_riego():
    """Inicia o detiene el riego manualmente."""
    lote_id, err = _require_humedad()
    if err:
        return jsonify({'error': 'no-auth'}), 401
    if not has_permission('humedad.manage'):
        return jsonify({'error': 'Sin permiso para controlar el riego'}), 403

    data = request.get_json(force=True, silent=True) or {}
    accion = data.get('accion')  # 'inicio' | 'fin'
    if accion not in ('inicio', 'fin'):
        return jsonify({'error': 'Acción inválida'}), 400

    estado = hs.avanzar_simulacion(lote_id)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE humedad_config SET riego_activo=%s WHERE lote_id=%s",
                (1 if accion == 'inicio' else 0, lote_id))
    cur.execute("""INSERT INTO riego_eventos
        (lote_id, tipo, modo, humedad_prom, usuario_id, nota)
        VALUES (%s,%s,'manual',%s,%s,%s)""",
        (lote_id, accion, estado['humedad_promedio'], session['user_id'],
         f"Riego {'iniciado' if accion=='inicio' else 'detenido'} manualmente por "
         f"{session.get('user_name','usuario')}"))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'success': True, 'riego_activo': accion == 'inicio'})


@csrf.exempt
@app.route('/humedad/api/config', methods=['POST'])
def humedad_api_config():
    """Actualiza umbrales, modo automático y fecha de siembra."""
    lote_id, err = _require_humedad()
    if err:
        return jsonify({'error': 'no-auth'}), 401
    if not has_permission('humedad.manage'):
        return jsonify({'error': 'Sin permiso'}), 403

    data = request.get_json(force=True, silent=True) or {}
    try:
        umin = float(data.get('umbral_min', 75))
        umax = float(data.get('umbral_max', 95))
        umin = max(10, min(95, umin))
        umax = max(umin + 2, min(100, umax))
        modo_auto = 1 if data.get('modo_auto') else 0
        fecha_siembra = data.get('fecha_siembra') or None
    except (TypeError, ValueError):
        return jsonify({'error': 'Datos inválidos'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    if fecha_siembra:
        cur.execute("""UPDATE humedad_config
            SET umbral_min_pct=%s, umbral_max_pct=%s, modo_auto=%s, fecha_siembra=%s
            WHERE lote_id=%s""", (umin, umax, modo_auto, fecha_siembra, lote_id))
    else:
        cur.execute("""UPDATE humedad_config
            SET umbral_min_pct=%s, umbral_max_pct=%s, modo_auto=%s
            WHERE lote_id=%s""", (umin, umax, modo_auto, lote_id))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'success': True})


@csrf.exempt
@app.route('/humedad/api/sensores', methods=['POST'])
def humedad_api_sensores():
    """Regenera la malla de sensores según cantidad y forma del lote."""
    lote_id, err = _require_humedad()
    if err:
        return jsonify({'error': 'no-auth'}), 401
    if not has_permission('humedad.manage'):
        return jsonify({'error': 'Sin permiso'}), 403

    data = request.get_json(force=True, silent=True) or {}
    try:
        n = int(data.get('cantidad', 6))
        n = max(1, min(24, n))
        forma = data.get('forma', 'rectangular')
        if forma not in ('rectangular', 'cuadrado', 'L', 'irregular'):
            forma = 'rectangular'
        prof = int(data.get('profundidad', 20))
        prof = max(5, min(60, prof))
        ancho = float(data.get('ancho_m', 0) or 0)
        largo = float(data.get('largo_m', 0) or 0)
        ancho = max(0, min(5000, ancho))
        largo = max(0, min(5000, largo))
    except (TypeError, ValueError):
        return jsonify({'error': 'Datos inválidos'}), 400

    creados = hs.crear_sensores(lote_id, n, forma=forma, profundidad=prof)
    # Persistir el tamaño del lote (crear_sensores ya guardó la forma).
    if ancho and largo:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE humedad_config SET ancho_m=%s, largo_m=%s WHERE lote_id=%s",
                    (ancho, largo, lote_id))
        conn.commit(); cur.close(); conn.close()
    return jsonify({'success': True, 'sensores': creados, 'redirect': url_for('humedad_panel')})


# ── Ingesta de lecturas reales (Arduino / ESP32) ──────────────────────────────
@csrf.exempt
@app.route('/humedad/api/ingest', methods=['POST'])
def humedad_api_ingest():
    """
    Endpoint para dispositivos físicos. Recibe lecturas reales de humedad.

    POST JSON:
      {
        "lote_id": 1,
        "token": "<HUMEDAD_INGEST_TOKEN>",
        "lecturas": [
          {"codigo": "S-01", "humedad_pct": 82.4, "temperatura_c": 29.1},
          ...
        ]
      }

    El sensor se identifica por su 'codigo' dentro del lote. Las lecturas se
    guardan con fuente='arduino'. Cuando un dispositivo real esté disponible,
    basta con apuntarlo a esta URL — el resto de la app no cambia.
    """
    import os
    data = request.get_json(force=True, silent=True) or {}
    token_cfg = os.environ.get('HUMEDAD_INGEST_TOKEN', '')
    if token_cfg and data.get('token') != token_cfg:
        return jsonify({'error': 'Token inválido'}), 403

    lote_id = data.get('lote_id')
    lecturas = data.get('lecturas') or []
    if not lote_id or not isinstance(lecturas, list):
        return jsonify({'error': 'Payload inválido'}), 400

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    guardadas = 0
    ahora = datetime.now()
    for l in lecturas:
        codigo = (l.get('codigo') or '').strip()
        if not codigo:
            continue
        cur.execute("SELECT id FROM humedad_sensores WHERE lote_id=%s AND codigo=%s",
                    (lote_id, codigo))
        s = cur.fetchone()
        if not s:
            continue
        try:
            hum = max(0, min(100, float(l.get('humedad_pct'))))
        except (TypeError, ValueError):
            continue
        temp = l.get('temperatura_c')
        cur.execute("""INSERT INTO humedad_lecturas
            (sensor_id, lote_id, humedad_pct, temperatura_c, fuente, fecha_hora)
            VALUES (%s,%s,%s,%s,'arduino',%s)""",
            (s['id'], lote_id, round(hum, 1),
             round(float(temp), 1) if temp is not None else None, ahora))
        guardadas += 1
    conn.commit(); cur.close(); conn.close()
    return jsonify({'success': True, 'guardadas': guardadas})
