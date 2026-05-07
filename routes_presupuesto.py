"""
routes_presupuesto.py — Presupuesto (budget) management route.
"""
import os
from datetime import date

from flask import request, session, redirect, url_for, render_template_string

from extensions import app
from db import get_db_connection
from session_service import auth_redirect

_PRES_TMPL = r"""{% extends 'base.html' %}
{% block title %}Presupuesto{% endblock %}
{% block content %}
<div class="container py-4" style="max-width:900px">

  <div class="d-flex align-items-center gap-3 mb-4">
    <div class="rounded-3 p-3" style="background:#1B4332">
      <i class="bi bi-wallet2 fs-3 text-white"></i>
    </div>
    <div>
      <h3 class="mb-0 fw-bold" style="color:#1B4332">Presupuesto</h3>
      <small class="text-muted">{{ lote_nombre }}</small>
    </div>
    <a href="{{ url_for('reportes') }}" class="btn btn-sm btn-outline-secondary ms-auto">
      <i class="bi bi-bar-chart me-1"></i>Reportes
    </a>
  </div>

  {% if error %}
  <div class="alert alert-warning alert-dismissible fade show"><i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>
  {% endif %}
  {% if success %}
  <div class="alert alert-success alert-dismissible fade show"><i class="bi bi-check-circle me-2"></i>{{ success }}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>
  {% endif %}

  {# ── Balance Cards ── #}
  <div class="row g-3 mb-4">
    <div class="col-md-4">
      <div class="card border-0 shadow-sm h-100" style="border-top:4px solid #2D6A4F!important">
        <div class="card-body text-center">
          <div class="text-muted small mb-1">Total Ingresado</div>
          <div class="fw-bold fs-4" style="color:#2D6A4F">$ {{ '{:,.0f}'.format(total_ingresado).replace(',','.') }}</div>
        </div>
      </div>
    </div>
    <div class="col-md-4">
      <div class="card border-0 shadow-sm h-100" style="border-top:4px solid #E9A800!important">
        <div class="card-body text-center">
          <div class="text-muted small mb-1">Total Gastado</div>
          <div class="fw-bold fs-4" style="color:#8B6000">$ {{ '{:,.0f}'.format(total_gastado).replace(',','.') }}</div>
        </div>
      </div>
    </div>
    <div class="col-md-4">
      <div class="card border-0 shadow-sm h-100" style="border-top:4px solid {% if alerta %}#DC3545{% elif saldo < 0 %}#DC3545{% else %}#1B4332{% endif %}!important">
        <div class="card-body text-center">
          <div class="text-muted small mb-1">Saldo Disponible</div>
          <div class="fw-bold fs-4" style="color:{% if saldo < 0 %}#DC3545{% else %}#1B4332{% endif %}">
            $ {{ '{:,.0f}'.format(saldo).replace(',','.') }}
          </div>
          {% if alerta %}<div class="badge bg-danger mt-1">¡Saldo bajo!</div>{% endif %}
        </div>
      </div>
    </div>
  </div>

  {# ── Progress bar ── #}
  {% if total_ingresado > 0 %}
  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body">
      <div class="d-flex justify-content-between mb-1">
        <small class="fw-semibold">Uso del presupuesto</small>
        <small class="fw-bold {% if pct_usado > 85 %}text-danger{% elif pct_usado > 60 %}text-warning{% else %}text-success{% endif %}">{{ pct_usado }}%</small>
      </div>
      <div class="progress" style="height:14px;border-radius:8px">
        <div class="progress-bar {% if pct_usado > 85 %}bg-danger{% elif pct_usado > 60 %}bg-warning{% else %}bg-success{% endif %}"
          style="width:{{ [pct_usado,100]|min }}%;border-radius:8px"></div>
      </div>
    </div>
  </div>
  {% endif %}

  <div class="row g-4">
    {# ── Agregar recarga ── #}
    <div class="col-md-5">
      <div class="card border-0 shadow-sm">
        <div class="card-header border-0 fw-bold" style="background:#1B4332;color:#fff">
          <i class="bi bi-plus-circle me-2"></i>Agregar Presupuesto
        </div>
        <div class="card-body">
          <form method="POST" action="{{ url_for('presupuesto_view') }}">
            <div class="mb-3">
              <label class="form-label fw-semibold">Monto ($)</label>
              <input type="number" name="monto" class="form-control" placeholder="Ej: 40000000" min="1" step="1000" required>
            </div>
            <div class="mb-3">
              <label class="form-label fw-semibold">Descripción</label>
              <input type="text" name="descripcion" class="form-control" placeholder="Ej: Capital inicial lote">
            </div>
            <div class="mb-3">
              <label class="form-label fw-semibold">Fecha</label>
              <input type="date" name="fecha" class="form-control" value="{{ today }}">
            </div>
            <button type="submit" class="btn w-100 text-white fw-bold" style="background:#2D6A4F">
              <i class="bi bi-plus-lg me-2"></i>Registrar Recarga
            </button>
          </form>
        </div>
      </div>
    </div>

    {# ── Historial recargas ── #}
    <div class="col-md-7">
      <div class="card border-0 shadow-sm">
        <div class="card-header border-0 fw-bold" style="background:#2D6A4F;color:#fff">
          <i class="bi bi-clock-history me-2"></i>Historial de Recargas
        </div>
        <div class="card-body p-0">
          {% if recargas %}
          <div class="table-responsive">
            <table class="table table-sm table-hover mb-0 align-middle">
              <thead style="background:#F0F8F4">
                <tr>
                  <th class="px-3">Fecha</th>
                  <th>Descripción</th>
                  <th class="text-end pe-3">Monto</th>
                </tr>
              </thead>
              <tbody>
                {% for r in recargas %}
                <tr>
                  <td class="px-3 text-muted small">{{ r.fecha.strftime('%d/%m/%Y') if r.fecha else '-' }}</td>
                  <td class="small">{{ r.descripcion or '—' }}</td>
                  <td class="text-end pe-3 fw-semibold text-success">$ {{ '{:,.0f}'.format(r.monto|float).replace(',','.') }}</td>
                </tr>
                {% endfor %}
              </tbody>
              <tfoot style="background:#1B4332;color:#fff">
                <tr>
                  <td colspan="2" class="px-3 fw-bold">Total Ingresado</td>
                  <td class="text-end pe-3 fw-bold">$ {{ '{:,.0f}'.format(total_ingresado).replace(',','.') }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          {% else %}
          <div class="text-center py-5 text-muted">
            <i class="bi bi-wallet2 fs-1 d-block mb-2" style="color:#ccc"></i>
            Aún no hay recargas registradas.<br>
            <small>Agrega tu presupuesto inicial para comenzar el seguimiento.</small>
          </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>

</div>
{% endblock %}"""


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

    # Persist template file for future use
    _tmpl_dir  = os.path.join(os.path.dirname(__file__), 'templates', 'presupuesto')
    os.makedirs(_tmpl_dir, exist_ok=True)
    _tmpl_path = os.path.join(_tmpl_dir, 'index.html')
    if not os.path.exists(_tmpl_path):
        with open(_tmpl_path, 'w', encoding='utf-8') as _tf:
            _tf.write(_PRES_TMPL)

    return render_template_string(_PRES_TMPL,
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
