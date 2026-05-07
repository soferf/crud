"""
routes_ai.py — Asistente IA general (dashboard chat).
Endpoints: POST /ai/chat  GET /ai/history  POST /ai/history/clear
"""
import json
import logging
from datetime import datetime

from flask import request, session, jsonify

from extensions import app, csrf
from db import get_db_connection

_MAX_HISTORY = 16   # mensajes guardados (8 turnos)
_MAX_CONTENT = 300  # chars por mensaje almacenado


def _history_key(lote_id) -> str:
    return f'ai_hist_{lote_id}'


def _load_session_history(lote_id) -> list:
    return session.get(_history_key(lote_id), [])


def _save_session_history(lote_id, history: list):
    session[_history_key(lote_id)] = history[-_MAX_HISTORY:]
    session.modified = True

logger = logging.getLogger(__name__)


def _build_lote_context() -> str:
    """Construye un resumen del lote activo para darle contexto al modelo."""
    lote_id   = session.get('lote_id')
    lote_nom  = session.get('lote_nombre', 'Sin nombre')
    lote_ha   = session.get('lote_ha', '?')

    if not lote_id:
        return f"Lote activo: {lote_nom}"

    try:
        conn   = get_db_connection()
        cur    = conn.cursor(dictionary=True)

        # Stats básicos del lote
        cur.execute("""
            SELECT
                COUNT(*) AS total_recibos,
                COALESCE(SUM(neto_a_pagar), 0) AS total_gastado,
                COALESCE(SUM(CASE WHEN MONTH(fecha)=MONTH(CURDATE()) AND YEAR(fecha)=YEAR(CURDATE())
                               THEN neto_a_pagar ELSE 0 END), 0) AS gasto_mes
            FROM recibos WHERE lote_id = %s
        """, (lote_id,))
        stats = cur.fetchone() or {}

        # Trabajadores activos
        cur.execute("SELECT COUNT(*) AS n FROM workers WHERE lote_id = %s AND activo = 1", (lote_id,))
        workers = (cur.fetchone() or {}).get('n', 0)

        # Producción
        cur.execute("SELECT COALESCE(SUM(cargas), 0) AS total_cargas FROM produccion WHERE lote_id = %s", (lote_id,))
        cargas = (cur.fetchone() or {}).get('total_cargas', 0)

        # Presupuesto
        cur.execute("""
            SELECT COALESCE(SUM(monto), 0) AS total_ingresado
            FROM presupuesto WHERE lote_id = %s AND tipo = 'ingreso'
        """, (lote_id,))
        ingresado = (cur.fetchone() or {}).get('total_ingresado', 0)

        cur.close(); conn.close()

        saldo      = float(ingresado) - float(stats.get('total_gastado', 0))
        gasto_ha   = float(stats.get('total_gastado', 0)) / float(lote_ha) if lote_ha else 0

        return (
            f"Lote activo: {lote_nom}\n"
            f"Hectáreas: {lote_ha}\n"
            f"Recibos registrados: {stats.get('total_recibos', 0)}\n"
            f"Total gastado: ${float(stats.get('total_gastado', 0)):,.0f} COP\n"
            f"Gasto este mes: ${float(stats.get('gasto_mes', 0)):,.0f} COP\n"
            f"Gasto por hectárea: ${gasto_ha:,.0f} COP (límite: $11.000.000)\n"
            f"Presupuesto ingresado: ${float(ingresado):,.0f} COP\n"
            f"Saldo disponible: ${saldo:,.0f} COP\n"
            f"Trabajadores activos: {workers}\n"
            f"Cargas cosechadas: {cargas} (meta: 2.000 cargas)\n"
        )
    except Exception as e:
        logger.warning(f'[routes_ai] No se pudo cargar contexto del lote: {e}')
        return f"Lote activo: {lote_nom} ({lote_ha} ha)"


@csrf.exempt
@app.route('/ai/chat', methods=['POST'])
def ai_dashboard_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    from ai_service import AI_ENABLED, ai_client, DASHBOARD_SYSTEM_PROMPT

    if not AI_ENABLED:
        return jsonify({'mensaje': '⚙️ El asistente de IA está deshabilitado (AI_ENABLED=false).'}), 200

    data     = request.get_json(force=True, silent=True) or {}
    user_msg = (data.get('message') or '').strip()[:2000]

    if not user_msg:
        return jsonify({'error': 'Mensaje vacío'}), 400

    lote_id = session.get('lote_id')

    # Historial guardado en sesión (fuente de verdad, no el frontend)
    saved = _load_session_history(lote_id)

    # Construir contexto del lote
    contexto = _build_lote_context()
    system   = DASHBOARD_SYSTEM_PROMPT + f"\n\nDatos actuales del lote:\n{contexto}"

    # Armar mensajes para el modelo: system + últimos 6 turnos del historial + pregunta actual
    messages = [{'role': 'system', 'content': system}]
    for m in saved[-12:]:
        messages.append({'role': m['role'], 'content': m['content']})
    messages.append({'role': 'user', 'content': user_msg})

    ok, respuesta = ai_client.generate_text(messages)

    if not ok:
        return jsonify({
            'mensaje': (
                '⚠️ El asistente no pudo responder en este momento.\n\n'
                'Asegúrate de haber descargado el modelo GPT4All '
                f'({ai_client.model_name}) desde la app GPT4All Desktop.\n\n'
                f'Detalle: {respuesta}'
            )
        }), 200

    # Guardar turno en sesión
    ts = datetime.now().strftime('%H:%M')
    saved.append({'role': 'user',      'content': user_msg[:_MAX_CONTENT],  'ts': ts})
    saved.append({'role': 'assistant', 'content': respuesta[:_MAX_CONTENT], 'ts': ts})
    _save_session_history(lote_id, saved)

    return jsonify({'mensaje': respuesta}), 200


@app.route('/ai/history', methods=['GET'])
def ai_history():
    if 'user_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    lote_id = session.get('lote_id')
    return jsonify({'history': _load_session_history(lote_id)}), 200


@csrf.exempt
@app.route('/ai/history/clear', methods=['POST'])
def ai_history_clear():
    if 'user_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    lote_id = session.get('lote_id')
    session.pop(_history_key(lote_id), None)
    session.modified = True
    return jsonify({'ok': True}), 200


@app.route('/ai/status', methods=['GET'])
def ai_status():
    """Verifica si el asistente está disponible."""
    if 'user_id' not in session:
        return jsonify({'available': False}), 401
    from ai_service import AI_ENABLED, ai_client
    if not AI_ENABLED:
        return jsonify({'available': False, 'reason': 'IA deshabilitada'})
    ok, msg = ai_client.health_check()
    return jsonify({'available': ok, 'reason': msg if not ok else 'OK'})
