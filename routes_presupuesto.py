"""
routes_presupuesto.py — Presupuesto (budget) management route.
"""
from datetime import date

from flask import request, session, redirect, url_for, render_template

from extensions import app
from db import get_db_connection
from session_service import auth_redirect


@app.route('/presupuesto', methods=['GET', 'POST'])
def presupuesto_view():
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesion.', 'warning')
    if not session.get('lote_id'):
        return redirect(url_for('select_lote'))
    lote_id = session['lote_id']

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    error   = None
    success = None

    if request.method == 'POST':
        monto_raw   = (request.form.get('monto') or '').replace('.', '').replace(',', '').strip()
        descripcion = (request.form.get('descripcion') or '').strip()[:255]
        fecha       = (request.form.get('fecha') or '').strip() or date.today().isoformat()
        try:
            monto = float(monto_raw)
            if monto <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            error = 'Ingresa un monto válido mayor a cero.'
        else:
            cursor.execute(
                "INSERT INTO presupuesto_recargas (lote_id, monto, descripcion, fecha) VALUES (%s,%s,%s,%s)",
                (lote_id, monto, descripcion, fecha))
            conn.commit()
            success = f'Recarga de $ {monto:,.0f} registrada correctamente.'.replace(',', '.')

    cursor.execute("SELECT COALESCE(SUM(monto),0) as ti FROM presupuesto_recargas WHERE lote_id=%s", (lote_id,))
    total_ingresado = float(cursor.fetchone()['ti'])
    cursor.execute("SELECT COALESCE(SUM(neto_a_pagar),0) as tg FROM recibos WHERE lote_id=%s", (lote_id,))
    total_gastado = float(cursor.fetchone()['tg'])
    saldo    = total_ingresado - total_gastado
    pct_usado = round(total_gastado / total_ingresado * 100, 1) if total_ingresado > 0 else 0
    alerta   = total_ingresado > 0 and saldo < total_ingresado * 0.15

    cursor.execute("SELECT * FROM presupuesto_recargas WHERE lote_id=%s ORDER BY fecha DESC, id DESC", (lote_id,))
    recargas = cursor.fetchall()
    cursor.close(); conn.close()

    return render_template('presupuesto/index.html',
        total_ingresado=total_ingresado,
        total_gastado=total_gastado,
        saldo=saldo,
        pct_usado=pct_usado,
        alerta=alerta,
        recargas=recargas,
        error=error,
        success=success,
        today=date.today().isoformat(),
        lote_nombre=session.get('lote_nombre', ''),
    )
