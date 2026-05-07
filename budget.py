"""
budget.py — Construcción del libro de movimientos de presupuesto.
"""
from datetime import date

from db import get_db_connection
from utils import format_currency


def build_budget_movements(lote_id, start_date=None, end_date=None):
    """Builds a chronological ledger of budget top-ups and expenses for a lote."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    saldo_inicial = 0.0
    if start_date is not None:
        cursor.execute(
            "SELECT COALESCE(SUM(monto),0) AS total FROM presupuesto_recargas WHERE lote_id=%s AND fecha < %s",
            (lote_id, start_date)
        )
        ingresos_previos = float(cursor.fetchone()['total'] or 0)
        cursor.execute(
            "SELECT COALESCE(SUM(neto_a_pagar),0) AS total FROM recibos WHERE lote_id=%s AND fecha < %s",
            (lote_id, start_date)
        )
        gastos_previos = float(cursor.fetchone()['total'] or 0)
        saldo_inicial = ingresos_previos - gastos_previos

    where_fecha = []
    params = [lote_id]
    if start_date is not None:
        where_fecha.append("fecha >= %s")
        params.append(start_date)
    if end_date is not None:
        where_fecha.append("fecha <= %s")
        params.append(end_date)
    where_sql = f" AND {' AND '.join(where_fecha)}" if where_fecha else ""

    cursor.execute(
        f"""
        SELECT id, fecha, descripcion, monto
        FROM presupuesto_recargas
        WHERE lote_id=%s{where_sql}
        ORDER BY fecha ASC, id ASC
        """,
        tuple(params)
    )
    recargas = cursor.fetchall()

    cursor.execute(
        f"""
        SELECT serial, fecha, proveedor, concepto, neto_a_pagar
        FROM recibos
        WHERE lote_id=%s{where_sql}
        ORDER BY fecha ASC, serial ASC
        """,
        tuple(params)
    )
    recibos = cursor.fetchall()
    cursor.close()
    conn.close()

    movimientos = []
    for recarga in recargas:
        monto = float(recarga.get('monto') or 0)
        movimientos.append({
            'fecha':      recarga.get('fecha'),
            'tipo':       'ingreso',
            'tipo_label': 'Ingreso',
            'referencia': f"REC-{recarga.get('id')}",
            'detalle':    recarga.get('descripcion') or 'Recarga de presupuesto',
            'ingreso':    monto,
            'gasto':      0.0,
            'orden':      int(recarga.get('id') or 0),
            'origen':     'presupuesto',
        })

    for recibo in recibos:
        gasto = float(recibo.get('neto_a_pagar') or 0)
        movimientos.append({
            'fecha':             recibo.get('fecha'),
            'tipo':              'gasto',
            'tipo_label':        'Gasto',
            'referencia':        f"RCB-{recibo.get('serial')}",
            'detalle':           recibo.get('proveedor') or recibo.get('concepto') or 'Recibo',
            'detalle_secundario': recibo.get('concepto') or '',
            'ingreso':           0.0,
            'gasto':             gasto,
            'orden':             int(recibo.get('serial') or 0),
            'origen':            'recibo',
            'serial':            recibo.get('serial'),
        })

    movimientos.sort(key=lambda item: (
        item.get('fecha') or date.min,
        0 if item['tipo'] == 'ingreso' else 1,
        item.get('orden', 0)
    ))

    gasto_acumulado = 0.0
    saldo_actual = saldo_inicial
    for movimiento in movimientos:
        gasto_acumulado += movimiento['gasto']
        saldo_actual += movimiento['ingreso'] - movimiento['gasto']
        movimiento['gasto_acumulado']      = gasto_acumulado
        movimiento['saldo_despues']        = saldo_actual
        movimiento['ingreso_fmt']          = format_currency(movimiento['ingreso']) if movimiento['ingreso'] else '—'
        movimiento['gasto_fmt']            = format_currency(movimiento['gasto'])   if movimiento['gasto']   else '—'
        movimiento['gasto_acumulado_fmt']  = format_currency(movimiento['gasto_acumulado'])
        movimiento['saldo_despues_fmt']    = format_currency(movimiento['saldo_despues'])

    return {
        'saldo_inicial': saldo_inicial,
        'saldo_final':   saldo_actual,
        'movimientos':   movimientos,
    }
