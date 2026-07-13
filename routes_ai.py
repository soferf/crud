"""
routes_ai.py — Asistente IA Gemini con Function Calling (dashboard chat).
Endpoints: POST /ai/chat  GET /ai/history  POST /ai/history/clear  GET /ai/status
"""
import json
import logging
from datetime import datetime, date

from flask import request, session, jsonify

from extensions import app, csrf
from db import get_db_connection
from utils import get_next_serial

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

        # Trabajadores activos (con valor habitual)
        cur.execute("""
            SELECT name, lastname, trabajo_desarrolla, valor_habitual, cc, phone_number
            FROM workers WHERE lote_id = %s AND activo = 1
            ORDER BY name
        """, (lote_id,))
        workers_rows = cur.fetchall()
        workers = len(workers_rows)
        workers_txt = ''
        if workers_rows:
            lines = []
            for w in workers_rows:
                val = f"${float(w['valor_habitual']):,.0f}/semana" if w.get('valor_habitual') else 'valor no registrado'
                lines.append(f"  - {w['name']} {w['lastname']} ({w['trabajo_desarrolla']}) → {val}")
            workers_txt = '\n' + '\n'.join(lines)

        # Producción
        cur.execute("SELECT COALESCE(SUM(cargas), 0) AS total_cargas FROM cosechas WHERE lote_id = %s", (lote_id,))
        cargas = (cur.fetchone() or {}).get('total_cargas', 0)

        # Presupuesto
        cur.execute("""
            SELECT COALESCE(SUM(monto), 0) AS total_ingresado
            FROM presupuesto_recargas WHERE lote_id = %s
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
            f"Trabajadores activos: {workers}{workers_txt}\n"
            f"Cargas cosechadas: {cargas} (meta: 2.000 cargas)\n"
        )
    except Exception as e:
        logger.warning(f'[routes_ai] No se pudo cargar contexto del lote: {e}')
        return f"Lote activo: {lote_nom} ({lote_ha} ha)"


# ── Ejecutor de herramientas (Function Calling) ───────────────────────────────

def _execute_tool(fn_name: str, fn_args: dict) -> dict:
    """
    Ejecuta la herramienta solicitada por Gemini y retorna un dict con el resultado.
    Esta función tiene acceso al contexto de sesión Flask.
    """
    lote_id = session.get('lote_id')
    if not lote_id:
        return {'error': 'No hay lote activo. Selecciona un lote primero.'}

    conn = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)

        # ── Consultas de solo lectura ──────────────────────────────────────────
        if fn_name == 'consultar_resumen_lote':
            return {'resumen': _build_lote_context()}

        elif fn_name == 'listar_trabajadores':
            cur.execute("""
                SELECT name, lastname, trabajo_desarrolla, valor_habitual, cc, phone_number
                FROM workers WHERE lote_id = %s AND activo = 1
                ORDER BY trabajo_desarrolla, name
            """, (lote_id,))
            rows = cur.fetchall()
            for r in rows:
                if r.get('valor_habitual'):
                    r['valor_habitual'] = float(r['valor_habitual'])
            return {'trabajadores': rows, 'total': len(rows)}

        elif fn_name == 'listar_cosechas':
            cur.execute("""
                SELECT fecha, cargas, kg_total, precio_carga, valor_total, fase,
                       variedad_semilla, observaciones
                FROM cosechas WHERE lote_id = %s ORDER BY fecha DESC LIMIT 20
            """, (lote_id,))
            rows = cur.fetchall()
            for r in rows:
                for k in ('kg_total', 'precio_carga', 'valor_total'):
                    if r.get(k) is not None:
                        r[k] = float(r[k])
                if r.get('fecha'):
                    r['fecha'] = str(r['fecha'])
            return {'cosechas': rows, 'total': len(rows)}

        # ── Escrituras ─────────────────────────────────────────────────────────
        elif fn_name == 'registrar_cosecha':
            fecha_str = (fn_args.get('fecha') or date.today().isoformat()).strip()
            try:
                fecha_obj = date.fromisoformat(fecha_str)
            except ValueError:
                return {'error': f'Fecha inválida: {fecha_str}. Usa YYYY-MM-DD.'}

            cargas = int(fn_args.get('cargas', 0))
            if cargas <= 0:
                return {'error': 'El número de cargas debe ser mayor a cero.'}

            KG_POR_CARGA = 200
            precio      = float(fn_args['precio_carga']) if fn_args.get('precio_carga') else None
            kg_total    = cargas * KG_POR_CARGA
            valor_total = cargas * precio if precio else None
            fase        = fn_args.get('fase', 'cosecha') or 'cosecha'
            variedad    = fn_args.get('variedad_semilla') or None
            obs         = fn_args.get('observaciones') or None
            lote_nom    = session.get('lote_nombre', 'Lote')
            lote_ha     = float(session.get('lote_ha') or 0) or None

            cur.execute("""
                INSERT INTO cosechas
                    (fecha, lote, hectareas, cargas, kg_total, precio_carga, valor_total,
                     observaciones, fase, variedad_semilla, lote_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (fecha_obj, lote_nom, lote_ha, cargas, kg_total,
                  precio, valor_total, obs, fase, variedad, lote_id))
            conn.commit()
            return {
                'ok': True,
                'mensaje': f'Cosecha registrada: {cargas} cargas ({kg_total:,} kg)',
                'cargas': cargas, 'kg_total': kg_total, 'fecha': str(fecha_obj),
            }

        elif fn_name == 'crear_recibo_labor':
            proveedor = (fn_args.get('nombre_trabajador') or '').strip()
            if not proveedor:
                return {'error': 'El nombre del trabajador es requerido.'}

            labor = (fn_args.get('labor') or 'otro').strip()
            valor = float(fn_args.get('valor', 0))
            if valor <= 0:
                return {'error': 'El valor a pagar debe ser mayor a cero.'}

            fecha_str = (fn_args.get('fecha') or date.today().isoformat()).strip()
            try:
                fecha_obj = date.fromisoformat(fecha_str)
            except ValueError:
                fecha_obj = date.today()

            obs      = fn_args.get('observaciones') or labor
            # Serial: personalizado si el usuario lo especificó, automático si no
            serial_custom = str(fn_args.get('serial') or '').strip()
            serial = serial_custom if serial_custom else get_next_serial(lote_id)
            conceptos = json.dumps([{'concepto': obs, 'valor': valor}], ensure_ascii=False)

            cur.execute("""
                INSERT INTO recibos
                    (serial, fecha, proveedor, concepto, valor_operacion,
                     rte_fte, neto_a_pagar, conceptos_json, lote_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (serial, fecha_obj, proveedor, obs, valor, 0.0, valor, conceptos, lote_id))
            conn.commit()
            return {
                'ok': True,
                'mensaje': f'Recibo #{serial} creado — {proveedor}: ${valor:,.0f} COP ({labor})',
                'serial': serial, 'proveedor': proveedor, 'valor': valor,
            }

        elif fn_name == 'agregar_trabajador':
            nombre   = (fn_args.get('nombre') or '').strip()
            apellido = (fn_args.get('apellido') or '').strip()
            if not nombre or not apellido:
                return {'error': 'Nombre y apellido son requeridos.'}

            cc             = (fn_args.get('cc') or '').strip()[:20] or None
            if not cc:
                return {'error': 'La cédula (CC) es obligatoria para registrar un trabajador.'}
            cargo_raw      = (fn_args.get('cargo') or 'operario').lower()
            # trabajo_desarrolla es ENUM — mapear texto libre al valor más cercano.
            # El orden importa: las claves más específicas van primero.
            _ENUM_MAP = {
                'despalillad': 'despalillador', 'despalill': 'despalillador',
                'fumiga': 'fumigador', 'fumigador': 'fumigador', 'dron': 'fumigador',
                'agronom': 'agronomo', 'agrónom': 'agronomo', 'ingeniero': 'agronomo',
                'administrad': 'administrador', 'admin': 'administrador',
                'gerente': 'administrador', 'logística': 'administrador', 'logistica': 'administrador',
                'transport': 'transportador', 'conductor': 'transportador', 'camión': 'transportador',
                'maquina': 'operario_maquinas', 'máquina': 'operario_maquinas',
                'tractor': 'operario_maquinas', 'sembrad': 'operario_maquinas',
                'regador': 'regador', 'riego': 'regador',
                'bombero': 'bombero', 'motobomba': 'bombero',
                'versátil': 'versatil', 'versatil': 'versatil', 'polivalente': 'polivalente',
                'jornalero': 'operario', 'operario': 'operario', 'cosechero': 'operario',
                'propietari': 'versatil', 'arrendad': 'versatil', 'arrendatari': 'versatil',
            }
            cargo = next((v for k, v in _ENUM_MAP.items() if k in cargo_raw), 'operario')
            valor_habitual = float(fn_args['valor_habitual']) if fn_args.get('valor_habitual') else None
            telefono       = str(fn_args.get('telefono') or '')[:20] or '0000000000'

            cur.execute("""
                INSERT INTO workers
                    (name, lastname, cc, phone_number, trabajo_desarrolla,
                     fecha_ingreso, activo, valor_habitual, lote_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (nombre, apellido, cc, telefono, cargo,
                  date.today(), 1, valor_habitual, lote_id))
            conn.commit()
            return {
                'ok': True,
                'mensaje': f'Trabajador {nombre} {apellido} registrado como {cargo}.',
                'nombre': f'{nombre} {apellido}', 'cargo': cargo,
            }

        elif fn_name == 'registrar_presupuesto':
            concepto = (fn_args.get('concepto') or '').strip()[:255]
            monto    = float(fn_args.get('monto', 0))
            tipo     = (fn_args.get('tipo') or 'ingreso').strip()
            if monto <= 0:
                return {'error': 'El monto debe ser mayor a cero.'}
            if tipo != 'ingreso':
                return {'error': 'Los egresos se registran como recibos. Usa crear_recibo_labor.'}

            fecha_str = (fn_args.get('fecha') or date.today().isoformat()).strip()
            try:
                fecha_obj = date.fromisoformat(fecha_str)
            except ValueError:
                fecha_obj = date.today()

            cur.execute(
                "INSERT INTO presupuesto_recargas (lote_id, monto, descripcion, fecha) VALUES (%s,%s,%s,%s)",
                (lote_id, monto, concepto, fecha_obj),
            )
            conn.commit()
            return {
                'ok': True,
                'mensaje': f'Ingreso de ${monto:,.0f} COP registrado: {concepto}',
                'monto': monto, 'concepto': concepto,
            }

        else:
            return {'error': f'Herramienta desconocida: {fn_name}'}

    except Exception as e:
        # Loguear detalle completo en consola del servidor
        logger.error(f'[_execute_tool] {fn_name} falló (detalle técnico): {e}', exc_info=True)

        # Mapear errores MySQL a mensajes amigables para el usuario
        err_str = str(e)
        err_code = getattr(e, 'errno', None)

        if err_code == 1062 or 'Duplicate entry' in err_str:
            campo = 'cédula' if 'cc' in err_str.lower() else 'un campo único'
            msg = f'Ya existe un registro con ese valor de {campo}. Verifica el dato e intenta de nuevo.'
        elif err_code in (1265, 1406) or 'Data truncated' in err_str or 'Data too long' in err_str:
            msg = 'Uno de los datos enviados es demasiado largo para ese campo. Intenta con un texto más corto.'
        elif err_code == 1048 or 'cannot be null' in err_str.lower():
            msg = 'Falta un dato obligatorio. Por favor proporciona todos los campos requeridos.'
        elif err_code == 1292 or 'Incorrect date' in err_str:
            msg = 'El formato de fecha no es válido. Usa el formato AAAA-MM-DD.'
        elif err_code == 2003 or 'Can\'t connect' in err_str:
            msg = 'No se pudo conectar a la base de datos. Contacta al administrador.'
        else:
            msg = 'Ocurrió un problema al guardar el registro. El administrador puede ver los detalles en la consola del servidor.'

        return {'error': msg}
    finally:
        if conn:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass




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

    # Ejecutor de tools (solo activo si hay lote seleccionado)
    executor = _execute_tool if lote_id else None

    ok, respuesta = ai_client.generate_text(messages, tool_executor=executor)

    if not ok:
        return jsonify({
            'mensaje': (
                '⚠️ El asistente no pudo responder en este momento.\n\n'
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
