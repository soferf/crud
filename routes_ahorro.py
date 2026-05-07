"""
routes_ahorro.py — CRUD mínimo para la tabla ahorro.
"""
from datetime import date
from flask import request, session, redirect, url_for, render_template
from extensions import app
from db import get_db_connection
from session_service import auth_redirect


def _ensure_table():
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ahorro (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            valor      DECIMAL(12,1) NOT NULL,
            categoria  VARCHAR(255)  NOT NULL,
            fecha      DATE          NOT NULL,
            creado_en  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


@app.route('/ahorro', methods=['GET', 'POST'])
def ahorro_index():
    if 'user_id' not in session:
        return auth_redirect('login', 'Inicia sesión para acceder.', 'warning')

    _ensure_table()
    message = error = None
    form    = {}

    if request.method == 'POST':
        valor     = request.form.get('valor',     '').strip()
        categoria = request.form.get('categoria', '').strip()
        fecha     = request.form.get('fecha',     '').strip()
        form      = {'valor': valor, 'categoria': categoria, 'fecha': fecha}
        try:
            conn = get_db_connection()
            cur  = conn.cursor()
            cur.execute(
                "INSERT INTO ahorro (valor, categoria, fecha) VALUES (%s, %s, %s)",
                (float(valor), categoria, fecha)
            )
            conn.commit()
            cur.close()
            conn.close()
            message = "Ahorro registrado correctamente."
            form    = {}
        except Exception as e:
            error = f"Error al guardar: {e}"

    # Últimos 10 registros
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT fecha, categoria, valor FROM ahorro ORDER BY fecha DESC, id DESC LIMIT 10")
        registros = cur.fetchall()
        cur.close()
        conn.close()
    except Exception:
        registros = []

    return render_template('ahorro/index.html',
                           message=message,
                           error=error,
                           form=form,
                           registros=registros,
                           today=date.today().isoformat())
