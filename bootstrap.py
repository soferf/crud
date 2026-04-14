"""
Run once: python bootstrap.py
Creates all directories and template files needed by the app.
Always overwrites existing templates to keep them up-to-date.
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# ── 1. Create directories ──────────────────────────────────────────────────
DIRS = [
    os.path.join(BASE, 'data'),
    os.path.join(BASE, 'uploads'),
    os.path.join(BASE, 'templates', 'recibos'),
    os.path.join(BASE, 'templates', 'config'),
    os.path.join(BASE, 'templates', 'reportes'),
    os.path.join(BASE, 'templates', 'produccion'),
    os.path.join(BASE, 'templates', 'workers'),
]
for d in DIRS:
    os.makedirs(d, exist_ok=True)
    print(f'  dir ok: {d}')

# ── 2. Helper (always overwrites) ─────────────────────────────────────────
def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  written: {path}')

# ── 3. data/trabajadores.json ──────────────────────────────────────────────
write_file(os.path.join(BASE, 'data', 'trabajadores.json'), """\
[
  {"key":"elias_castano","nombre":"Elias Casta\u00f1o","alias":["paisa"],"nit":"5962798","direccion":"El Tambo","telefono":"3173041545","ciudad":"Natagaima","concepto_habitual":"Pago por cuidar el motor x semana en el lote El Mangon (motor lister de 38 hp a diesel)","valor_habitual":350000},
  {"key":"eliodoro_aroca","nombre":"Eliodoro Aroca Alape","alias":["delio"],"nit":"93345400","direccion":"El Tambo","telefono":"","ciudad":"Natagaima","concepto_habitual":"Pago de moje corrido x semana en el lote El Mangon en 20 hectareas a motor","valor_habitual":370000},
  {"key":"alexander_botache","nombre":"Alexander Botache Yara","alias":["alex"],"nit":"93470959","direccion":"El Tambo","telefono":"3157051538","ciudad":"Natagaima","concepto_habitual":"Pago de transporte de 24 bidones de ACPM de Angostura a El Lote El Mangon","valor_habitual":100000},
  {"key":"jorge_delvasto","nombre":"Jorge Enrique Delvasto","alias":[],"nit":"93471018","direccion":"El Tambo","telefono":"3164936224","ciudad":"Natagaima","concepto_habitual":"Arrego de via + transporte canal de la Cevedo","valor_habitual":null},
  {"key":"silvio_zorrillo","nombre":"Silvio Zorrillo Carrillo","alias":[],"nit":"93470637","direccion":"El Tambo","telefono":"","ciudad":"Natagaima","concepto_habitual":"Despalillada x jornales x semana","valor_habitual":null},
  {"key":"gilberto_guarnizo","nombre":"Gilberto Guarnizo Rojas","alias":[],"nit":"93152907","direccion":"Cra 9A #11B Abonanza","telefono":"3123978471","ciudad":"Salda\u00f1a","concepto_habitual":"Carga de camiones de arroz paddy en Salda\u00f1a en corta del Tambo","valor_habitual":null},
  {"key":"joany_cuevas","nombre":"Joany Andres Cuevas Vanegas","alias":[],"nit":"1081182208","direccion":"Guasimal","telefono":"3001392542","ciudad":"Natagaima","concepto_habitual":"Pago de corta de arroz en el Lote El Mangon","valor_habitual":null},
  {"key":"humberto_yara","nombre":"Humberto Yara Tique","alias":[],"nit":"11293591","direccion":"El Tambo","telefono":"3166422455","ciudad":"Natagaima","concepto_habitual":"Asofructo parcela Lote El Mangon","valor_habitual":null},
  {"key":"jose_medina","nombre":"Jose Maria Medina Santos","alias":["chepe"],"nit":"93151067","direccion":"Carrera 10 #11","telefono":"3132429292","ciudad":"Natagaima","concepto_habitual":"Reparaciones motor lister de 38 hp a diesel","valor_habitual":null},
  {"key":"vicente_andrade","nombre":"Vicente Andrade Lozano","alias":["agronomo"],"nit":"","direccion":"El Tambo","telefono":"","ciudad":"Natagaima","concepto_habitual":"Pago porcentaje agr\u00f3nomo final de corta de arroz","valor_habitual":null},
  {"key":"fernando_lozano","nombre":"Fernando Lozano","alias":[],"nit":"","direccion":"El Tambo","telefono":"","ciudad":"Natagaima","concepto_habitual":"Bordeada a motosierra en el lote El Mangon","valor_habitual":880000},
  {"key":"raquel_cumaco","nombre":"Raquel Cumaco Tacuma","alias":[],"nit":"65789347","direccion":"El Tambo","telefono":"3154910540","ciudad":"Natagaima","concepto_habitual":"Cancelaci\u00f3n de asofructo","valor_habitual":null},
  {"key":"cabildo_tambo","nombre":"Cabildo de Tambo","alias":["cabildo"],"nit":"809005671","direccion":"El Tambo","telefono":"3123525731","ciudad":"Natagaima","concepto_habitual":"Cancelaci\u00f3n de asofructo","valor_habitual":null}
]
""")

# ── 4. uploads/.gitkeep ────────────────────────────────────────────────────
write_file(os.path.join(BASE, 'uploads', '.gitkeep'), '')

# ── 5. templates/recibos/nuevo.html ───────────────────────────────────────
write_file(os.path.join(BASE, 'templates', 'recibos', 'nuevo.html'), """\
{% extends "base.html" %}
{% block title %}Nuevo Recibo | Contabilidad Arroceras{% endblock %}

{% block head %}
<script src="{{ url_for('static', filename='css/js/autocomplete.js') }}" defer></script>
{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-file-invoice-dollar"></i></div>
    <div>
      <h1 class="page-hero__title">Nuevo Recibo</h1>
      <p class="page-hero__sub">Registra un pago. El serial se asigna autom\u00e1ticamente seg\u00fan la fecha.</p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('lista_recibos') }}" class="button button--ghost">
        <i class="fa-solid fa-list"></i> Ver recibos
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container">

    {% if success %}
    <div class="alert alert--success"><i class="fa-solid fa-circle-check"></i> {{ success }}</div>
    {% endif %}
    {% if error %}
    <div class="alert alert--danger"><i class="fa-solid fa-circle-xmark"></i> {{ error }}</div>
    {% endif %}

    {% if warning %}
    <div class="alert alert--warning" id="warningAlert">
      <i class="fa-solid fa-triangle-exclamation"></i> {{ warning }}
      <div class="warning-actions">
        <button type="button" class="button button--sm button--primary" id="btnForceGuardar">
          <i class="fa-solid fa-floppy-disk"></i> Guardar de todas formas
        </button>
        <button type="button" class="button button--sm button--ghost-dark" onclick="document.getElementById('warningAlert').style.display='none'">
          Cancelar
        </button>
      </div>
    </div>
    {% endif %}

    <div class="trabajador-search-box">
      <label class="search-label"><i class="fa-solid fa-magnifying-glass"></i> Buscar trabajador por nombre o apodo</label>
      <div class="search-input-wrap">
        <input type="text" id="buscarTrabajador" placeholder="Ej: paisa, delio, Silvio..." autocomplete="off" class="search-input">
        <ul id="trabajadorSuggestions" class="suggestions-list"></ul>
      </div>
      <p class="field-hint">Al seleccionar, se autocompletan NIT, direcci\u00f3n, ciudad, tel\u00e9fono, concepto y valor.</p>
    </div>

    <form method="POST" id="reciboForm" class="form-card">
      <input type="hidden" name="force" id="forceField" value="false">

      <div class="form-section">
        <h3 class="form-section__title"><i class="fa-solid fa-hashtag"></i> Identificaci\u00f3n del Recibo</h3>
        <div class="form-grid form-grid--3">
          <div class="form-group">
            <label for="serial">Serial <span class="req-star">*</span></label>
            <input type="number" id="serial" name="serial" value="{{ form_data.get('serial', next_serial) }}" min="1" required>
            <p class="field-hint">Pr\u00f3ximo sugerido: <strong>{{ next_serial }}</strong></p>
          </div>
          <div class="form-group">
            <label for="fecha">Fecha del recibo</label>
            <input type="date" id="fecha" name="fecha" value="{{ form_data.get('fecha', today) }}">
          </div>
        </div>
      </div>

      <div class="form-section">
        <h3 class="form-section__title"><i class="fa-solid fa-user-tie"></i> Proveedor / Trabajador</h3>
        <div class="form-grid form-grid--2">
          <div class="form-group">
            <label for="proveedor">Nombre completo <span class="req-star">*</span></label>
            <input type="text" id="proveedor" name="proveedor" value="{{ form_data.get('proveedor','') }}" placeholder="Nombre real (no apodo)" required>
          </div>
          <div class="form-group">
            <label for="nit">NIT / C\u00e9dula</label>
            <input type="text" id="nit" name="nit" value="{{ form_data.get('nit','') }}" placeholder="Ej: 93470637">
          </div>
          <div class="form-group">
            <label for="direccion">Direcci\u00f3n</label>
            <input type="text" id="direccion" name="direccion" value="{{ form_data.get('direccion','') }}" placeholder="Ej: El Tambo">
          </div>
          <div class="form-group">
            <label for="telefono">Tel\u00e9fono</label>
            <input type="text" id="telefono" name="telefono" value="{{ form_data.get('telefono','') }}" placeholder="Ej: 3001234567">
          </div>
          <div class="form-group">
            <label for="ciudad">Ciudad</label>
            <input type="text" id="ciudad" name="ciudad" value="{{ form_data.get('ciudad','') }}" placeholder="Ej: Natagaima">
          </div>
        </div>
      </div>

      <div class="form-section">
        <h3 class="form-section__title"><i class="fa-solid fa-file-lines"></i> Concepto y Valor</h3>
        <div class="form-group">
          <label for="concepto">Concepto <span class="req-star">*</span></label>
          <textarea id="concepto" name="concepto" rows="3" required placeholder="Descripci\u00f3n detallada del trabajo o pago...">{{ form_data.get('concepto','') }}</textarea>
          <p class="field-hint">\u26a0\ufe0f No registrar compras de aceite ni ACPM directo. Solo transporte de ACPM.</p>
        </div>
        <div class="form-grid form-grid--2">
          <div class="form-group">
            <label for="valor_operacion">Valor operaci\u00f3n (COP)</label>
            <input type="text" id="valor_operacion" name="valor_operacion" value="{{ form_data.get('valor_operacion','') }}" placeholder="Ej: 350.000" inputmode="numeric">
          </div>
          <div class="form-group">
            <label for="neto_a_pagar">Neto a pagar (COP)</label>
            <input type="text" id="neto_a_pagar" name="neto_a_pagar" value="{{ form_data.get('neto_a_pagar','') }}" placeholder="Igual al valor si no hay descuentos" inputmode="numeric">
            <p class="field-hint">Si se deja vac\u00edo, se usa el valor de operaci\u00f3n.</p>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="button button--primary">
          <i class="fa-solid fa-floppy-disk"></i> Guardar recibo
        </button>
        <a href="{{ url_for('lista_recibos') }}" class="button button--ghost-dark">
          <i class="fa-solid fa-list"></i> Ver todos los recibos
        </a>
      </div>
    </form>

  </div>
</section>
{% endblock %}

{% block scripts %}
<script>
  const TRABAJADORES = {{ trabajadores | tojson }};

  const btnForce = document.getElementById('btnForceGuardar');
  if (btnForce) {
    btnForce.addEventListener('click', function() {
      document.getElementById('forceField').value = 'true';
      document.getElementById('reciboForm').submit();
    });
  }

  initTrabajadorAutocomplete(TRABAJADORES, {
    searchInput: document.getElementById('buscarTrabajador'),
    suggestionsList: document.getElementById('trabajadorSuggestions'),
    fields: {
      proveedor: document.getElementById('proveedor'),
      nit: document.getElementById('nit'),
      direccion: document.getElementById('direccion'),
      telefono: document.getElementById('telefono'),
      ciudad: document.getElementById('ciudad'),
      concepto: document.getElementById('concepto'),
      valor_operacion: document.getElementById('valor_operacion'),
      neto_a_pagar: document.getElementById('neto_a_pagar'),
    }
  });
</script>
{% endblock %}
""")

# ── 6. templates/recibos/lista.html ───────────────────────────────────────
write_file(os.path.join(BASE, 'templates', 'recibos', 'lista.html'), """\
{% extends "base.html" %}
{% block title %}Recibos | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-list-check"></i></div>
    <div>
      <h1 class="page-hero__title">Recibos</h1>
      <p class="page-hero__sub">{{ recibos|length }} recibo(s) registrado(s) en total.</p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('nuevo_recibo') }}" class="button button--primary">
        <i class="fa-solid fa-plus"></i> Nuevo recibo
      </a>
      <a href="{{ url_for('nuevo_recibo_lote') }}" class="button button--ghost">
        <i class="fa-solid fa-users-between-lines"></i> Por lote
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container">
    {% if recibos %}
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Serial</th>
            <th>Fecha</th>
            <th>Proveedor</th>
            <th>NIT</th>
            <th>Concepto</th>
            <th>Neto a pagar</th>
          </tr>
        </thead>
        <tbody>
          {% for r in recibos %}
          <tr style="cursor:pointer" onclick="location.href='{{ url_for('detalle_recibo', serial=r.serial) }}'">
            <td><span class="serial-badge">{{ r.serial }}</span></td>
            <td>{{ r.fecha.strftime('%d/%m/%Y') if r.fecha else '\u2014' }}</td>
            <td><strong>{{ r.proveedor }}</strong></td>
            <td class="txt-muted">{{ r.nit or '\u2014' }}</td>
            <td class="concepto-cell">{{ r.concepto }}</td>
            <td class="valor-cell">
              {% if r.neto_a_pagar %}
                <strong>$ {{ "{:,.0f}".format(r.neto_a_pagar).replace(",",".") }}</strong>
              {% else %}\u2014{% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="empty-state">
      <i class="fa-solid fa-file-circle-plus empty-state__icon"></i>
      <h3>No hay recibos a\u00fan</h3>
      <p>Crea el primer recibo haciendo clic en "Nuevo recibo".</p>
      <a href="{{ url_for('nuevo_recibo') }}" class="button button--primary">
        <i class="fa-solid fa-plus"></i> Crear primer recibo
      </a>
    </div>
    {% endif %}
  </div>
</section>
{% endblock %}
""")

# ── 7. templates/recibos/lote.html ────────────────────────────────────────
write_file(os.path.join(BASE, 'templates', 'recibos', 'lote.html'), """\
{% extends "base.html" %}
{% block title %}Recibo por Lote | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-users-between-lines"></i></div>
    <div>
      <h1 class="page-hero__title">Recibo por Lote</h1>
      <p class="page-hero__sub">Mismo concepto para varios trabajadores \u2014 crea un recibo por cada uno</p>
    </div>
  </div>
</div>

<section class="section">
  <div class="container">

    {% if success %}
    <div class="alert alert--success"><i class="fa-solid fa-circle-check"></i> {{ success }}</div>
    {% endif %}
    {% if error %}
    <div class="alert alert--danger"><i class="fa-solid fa-circle-xmark"></i> {{ error }}</div>
    {% endif %}

    <form method="POST" id="loteForm">

      <div class="form-card" style="margin-bottom: var(--s6);">
        <div class="form-section">
          <h3 class="form-section__title"><i class="fa-solid fa-circle-1"></i> Datos comunes del lote</h3>
          <div class="form-grid form-grid--3">
            <div class="form-group">
              <label for="serial_inicio">Serial de inicio <span class="req-star">*</span></label>
              <input type="number" id="serial_inicio" name="serial_inicio" value="{{ next_serial }}" min="1" required>
              <p class="field-hint">Los seriales se asignan consecutivamente por cada trabajador.</p>
            </div>
            <div class="form-group">
              <label for="fecha">Fecha</label>
              <input type="date" id="fecha" name="fecha" value="{{ today }}">
            </div>
            <div class="form-group">
              <label for="valor_por_trabajador">Valor por trabajador (COP)</label>
              <input type="text" id="valor_por_trabajador" name="valor_por_trabajador" placeholder="Ej: 60.000" inputmode="numeric">
              <p class="field-hint">Si se deja vac\u00edo, se usa el valor habitual de cada uno.</p>
            </div>
            <div class="form-group form-grid--full">
              <label for="concepto">Concepto <span class="req-star">*</span></label>
              <textarea id="concepto" name="concepto" rows="2" required placeholder="Ej: Despalillada 3 jornales x semana en el lote El Mangon"></textarea>
            </div>
            <div class="form-group">
              <label for="direccion">Direcci\u00f3n (opcional)</label>
              <input type="text" id="direccion" name="direccion" placeholder="Ej: El Tambo">
            </div>
            <div class="form-group">
              <label for="ciudad">Ciudad (opcional)</label>
              <input type="text" id="ciudad" name="ciudad" placeholder="Ej: Natagaima">
            </div>
          </div>
        </div>
      </div>

      <div class="form-card">
        <div class="form-section">
          <div class="worker-selector-header">
            <h3 class="worker-selector-title"><i class="fa-solid fa-circle-2" style="color:var(--clr-500)"></i> Seleccionar trabajadores</h3>
            <span class="selection-counter" id="selCounter">0 seleccionados</span>
          </div>

          <div class="cargo-filters" id="cargoFilters">
            <button type="button" class="cargo-filter-btn is-active" data-cargo="todos">Todos</button>
            {% set cargos_vistos = [] %}
            {% for w in db_workers %}
              {% if w.trabajo_desarrolla and w.trabajo_desarrolla not in cargos_vistos %}
                {% set _ = cargos_vistos.append(w.trabajo_desarrolla) %}
                <button type="button" class="cargo-filter-btn" data-cargo="{{ w.trabajo_desarrolla }}">
                  {{ w.trabajo_desarrolla | replace('_', ' ') | title }}
                </button>
              {% endif %}
            {% endfor %}
          </div>

          {% if db_workers %}
          <div class="workers-grid" id="workersGrid">
            {% for w in db_workers %}
            <div class="worker-card-sel"
                 data-id="{{ w.id_worker }}"
                 data-cargo="{{ w.trabajo_desarrolla }}"
                 onclick="toggleWorker(this)">
              <i class="fa-solid fa-check worker-card-sel__check"></i>
              <div class="worker-card-sel__name">{{ w.name }} {{ w.lastname }}</div>
              <span class="worker-card-sel__cargo">{{ (w.trabajo_desarrolla or '') | replace('_', ' ') }}</span>
            </div>
            {% endfor %}
          </div>
          <div id="hiddenWorkerInputs"></div>
          {% else %}
          <div class="empty-state" style="padding: var(--s12);">
            <i class="fa-solid fa-user-plus empty-state__icon"></i>
            <h3>No hay trabajadores registrados</h3>
            <p>Registra trabajadores primero para poder crear recibos por lote.</p>
            <a href="{{ url_for('create_worker') }}" class="button button--primary">Registrar trabajador</a>
          </div>
          {% endif %}
        </div>

        <div class="form-actions">
          <button type="submit" class="button button--primary" id="btnSubmitLote" disabled>
            <i class="fa-solid fa-floppy-disk"></i> Crear recibos del lote
          </button>
          <a href="{{ url_for('lista_recibos') }}" class="button button--ghost-dark">
            <i class="fa-solid fa-list"></i> Ver recibos
          </a>
        </div>
      </div>

    </form>
  </div>
</section>
{% endblock %}

{% block scripts %}
<script>
let selectedIds = new Set();

function toggleWorker(card) {
  const id = card.dataset.id;
  if (selectedIds.has(id)) {
    selectedIds.delete(id);
    card.classList.remove('is-selected');
  } else {
    selectedIds.add(id);
    card.classList.add('is-selected');
  }
  updateCounter();
  updateHiddenInputs();
}

function updateCounter() {
  document.getElementById('selCounter').textContent = selectedIds.size + ' seleccionado' + (selectedIds.size !== 1 ? 's' : '');
  document.getElementById('btnSubmitLote').disabled = selectedIds.size === 0;
}

function updateHiddenInputs() {
  const container = document.getElementById('hiddenWorkerInputs');
  container.innerHTML = '';
  selectedIds.forEach(id => {
    const inp = document.createElement('input');
    inp.type = 'hidden';
    inp.name = 'worker_ids';
    inp.value = id;
    container.appendChild(inp);
  });
}

document.getElementById('cargoFilters').addEventListener('click', function(e) {
  const btn = e.target.closest('.cargo-filter-btn');
  if (!btn) return;
  document.querySelectorAll('.cargo-filter-btn').forEach(b => b.classList.remove('is-active'));
  btn.classList.add('is-active');
  const cargo = btn.dataset.cargo;
  document.querySelectorAll('.worker-card-sel').forEach(card => {
    card.style.display = (cargo === 'todos' || card.dataset.cargo === cargo) ? '' : 'none';
  });
});
</script>
{% endblock %}
""")

# ── 8. templates/recibos/detalle.html ─────────────────────────────────────
write_file(os.path.join(BASE, 'templates', 'recibos', 'detalle.html'), """\
{% extends "base.html" %}
{% block title %}Recibo #{{ recibo.serial }} | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-file-invoice"></i></div>
    <div>
      <h1 class="page-hero__title">Recibo #{{ recibo.serial }}</h1>
      <p class="page-hero__sub">{{ recibo.fecha.strftime('%d/%m/%Y') if recibo.fecha else 'Sin fecha' }} \u00b7 {{ recibo.proveedor }}</p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('lista_recibos') }}" class="button button--ghost">
        <i class="fa-solid fa-arrow-left"></i> Volver
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container" style="max-width:700px;">

    <div class="form-card">
      <div class="form-section">
        <h3 class="form-section__title"><i class="fa-solid fa-receipt"></i> Detalle del recibo</h3>
        <dl class="recibo-dl">
          <div class="recibo-dl__row">
            <dt>serial</dt>
            <dd><span class="serial-badge">{{ recibo.serial }}</span></dd>
          </div>
          <div class="recibo-dl__row">
            <dt>fecha</dt>
            <dd>{{ recibo.fecha.strftime('%d/%m/%Y') if recibo.fecha else '\u2014' }}</dd>
          </div>
          <div class="recibo-dl__row">
            <dt>proveedor</dt>
            <dd><strong>{{ recibo.proveedor }}</strong></dd>
          </div>
          <div class="recibo-dl__row">
            <dt>nit</dt>
            <dd>{{ recibo.nit or '\u2014' }}</dd>
          </div>
          <div class="recibo-dl__row">
            <dt>direcci\u00f3n</dt>
            <dd>{{ recibo.direccion or '\u2014' }}</dd>
          </div>
          <div class="recibo-dl__row">
            <dt>tel\u00e9fono</dt>
            <dd>{{ recibo.telefono or '\u2014' }}</dd>
          </div>
          <div class="recibo-dl__row">
            <dt>ciudad</dt>
            <dd>{{ recibo.ciudad or '\u2014' }}</dd>
          </div>
          <div class="recibo-dl__row recibo-dl__row--full">
            <dt>concepto</dt>
            <dd>{{ recibo.concepto or '\u2014' }}</dd>
          </div>
          <div class="recibo-dl__row">
            <dt>valor operaci\u00f3n</dt>
            <dd class="valor-cell">{% if recibo.valor_operacion %}<strong>$ {{ "{:,.0f}".format(recibo.valor_operacion).replace(",",".") }}</strong>{% else %}\u2014{% endif %}</dd>
          </div>
          <div class="recibo-dl__row recibo-dl__row--highlight">
            <dt>neto a pagar</dt>
            <dd class="valor-cell">{% if recibo.neto_a_pagar %}<strong>$ {{ "{:,.0f}".format(recibo.neto_a_pagar).replace(",",".") }}</strong>{% else %}\u2014{% endif %}</dd>
          </div>
        </dl>
      </div>

      <div class="form-actions">
        <a href="{{ url_for('lista_recibos') }}" class="button button--ghost-dark">
          <i class="fa-solid fa-arrow-left"></i> Volver a la lista
        </a>
        <form method="POST" action="{{ url_for('eliminar_recibo', serial=recibo.serial) }}"
              onsubmit="return confirm('\\u00bfEliminar el recibo #{{ recibo.serial }}? Esta acci\\u00f3n no se puede deshacer.')"
              style="margin:0;">
          <button type="submit" class="button" style="background:#ffe4e1;color:#8f2d25;border:1.5px solid #f3a6a0;">
            <i class="fa-solid fa-trash"></i> Eliminar recibo
          </button>
        </form>
      </div>
    </div>

  </div>
</section>
{% endblock %}
""")

# ── 9. templates/reportes/index.html ──────────────────────────────────────
write_file(os.path.join(BASE, 'templates', 'reportes', 'index.html'), """\
{% extends "base.html" %}
{% block title %}Reportes | Contabilidad Arroceras{% endblock %}
{% block head %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-chart-line"></i></div>
    <div>
      <h1 class="page-hero__title">Reportes y Estad\u00edsticas</h1>
      <p class="page-hero__sub">Control financiero de la arrocera \u00b7 {{ total_ha }} hect\u00e1reas</p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('exportar_txt') }}" class="button button--ghost">
        <i class="fa-solid fa-file-export"></i> Exportar TXT
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container">

    <div class="stats-grid">
      <div class="stat-card {% if pct_gasto > 90 %}stat-card--danger{% elif pct_gasto > 70 %}stat-card--warning{% else %}stat-card--success{% endif %}">
        <span class="stat-card__label"><i class="fa-solid fa-peso-sign"></i> Total gastado</span>
        <span class="stat-card__value">$ {{ "{:,.0f}".format(total_gastado).replace(",",".") }}</span>
        <span class="stat-card__sub">de $ {{ "{:,.0f}".format(max_gasto).replace(",",".") }} m\u00e1ximo</span>
      </div>
      <div class="stat-card {% if pct_gasto > 90 %}stat-card--danger{% elif pct_gasto > 70 %}stat-card--warning{% else %}stat-card--success{% endif %}">
        <span class="stat-card__label"><i class="fa-solid fa-percent"></i> Presupuesto usado</span>
        <span class="stat-card__value">{{ pct_gasto }}%</span>
        <span class="stat-card__sub">M\u00e1x. $ {{ "{:,.0f}".format(max_gasto_ha).replace(",",".") }}/ha</span>
      </div>
      <div class="stat-card {% if pct_produccion >= 100 %}stat-card--success{% elif pct_produccion >= 60 %}stat-card--warning{% else %}stat-card--danger{% endif %}">
        <span class="stat-card__label"><i class="fa-solid fa-wheat-awn"></i> Cargas cosechadas</span>
        <span class="stat-card__value">{{ "{:,}".format(total_cargas).replace(",",".") }}</span>
        <span class="stat-card__sub">m\u00ednimo {{ "{:,}".format(min_cargas).replace(",",".") }} cargas</span>
      </div>
      <div class="stat-card {% if pct_produccion >= 100 and pct_gasto <= 90 %}stat-card--success{% else %}stat-card--warning{% endif %}">
        <span class="stat-card__label"><i class="fa-solid fa-seedling"></i> Rentabilidad</span>
        <span class="stat-card__value">{% if pct_produccion >= 100 and pct_gasto <= 90 %}\u2705 Ok{% elif pct_gasto > 90 %}\ud83d\udd34 Riesgo{% else %}\u26a0\ufe0f Seguir{% endif %}</span>
        <span class="stat-card__sub">Producci\u00f3n: {{ pct_produccion }}%</span>
      </div>
    </div>

    <div class="gauge-section">
      <div class="gauge-header">
        <span class="gauge-title"><i class="fa-solid fa-peso-sign"></i> Gasto total vs presupuesto m\u00e1ximo</span>
        <span class="gauge-amount">
          <strong>$ {{ "{:,.0f}".format(total_gastado).replace(",",".") }}</strong>
          / $ {{ "{:,.0f}".format(max_gasto).replace(",",".") }}
        </span>
      </div>
      <div class="gauge-bar-wrap">
        <div class="gauge-bar {% if pct_gasto > 90 %}gauge-bar--red{% elif pct_gasto > 70 %}gauge-bar--yellow{% else %}gauge-bar--green{% endif %}"
             style="width: {{ pct_gasto }}%">{{ pct_gasto }}%</div>
      </div>
      <p class="gauge-footnote">Presupuesto m\u00e1ximo: $ {{ "{:,.0f}".format(max_gasto_ha).replace(",",".") }} \u00d7 {{ total_ha }} ha = $ {{ "{:,.0f}".format(max_gasto).replace(",",".") }}</p>
    </div>

    <div class="gauge-section">
      <div class="gauge-header">
        <span class="gauge-title"><i class="fa-solid fa-wheat-awn"></i> Producci\u00f3n vs m\u00ednimo requerido</span>
        <span class="gauge-amount">
          <strong>{{ "{:,}".format(total_cargas).replace(",",".") }} cargas</strong>
          / {{ "{:,}".format(min_cargas).replace(",",".") }} m\u00ednimo
        </span>
      </div>
      <div class="gauge-bar-wrap">
        <div class="gauge-bar {% if pct_produccion >= 100 %}gauge-bar--green{% elif pct_produccion >= 60 %}gauge-bar--yellow{% else %}gauge-bar--red{% endif %}"
             style="width: {{ [pct_produccion, 100] | min }}%">{{ pct_produccion }}%</div>
      </div>
      <p class="gauge-footnote">M\u00ednimo: {{ min_cargas }} cargas (100 bultos/ha \u00d7 {{ total_ha }} ha). Cada carga = 62.5 kg.</p>
    </div>

    <div class="charts-row">
      <div class="chart-card">
        <h3 class="chart-card__title"><i class="fa-solid fa-chart-bar"></i> Gastos por mes</h3>
        <div class="chart-canvas-wrap">
          <canvas id="chartMes"></canvas>
        </div>
      </div>
      <div class="chart-card">
        <h3 class="chart-card__title"><i class="fa-solid fa-users"></i> Top trabajadores</h3>
        <div class="chart-canvas-wrap">
          <canvas id="chartTrabajadores"></canvas>
        </div>
      </div>
    </div>

    <div class="grid-3" style="margin-top: var(--s6);">
      <a href="{{ url_for('reporte_semana') }}" class="card" style="text-decoration:none;">
        <div class="card__icon"><i class="fa-solid fa-calendar-week"></i></div>
        <h3>Reporte semanal</h3>
        <p>Ver todos los pagos de la semana actual.</p>
      </a>
      <a href="{{ url_for('exportar_txt') }}" class="card" style="text-decoration:none;">
        <div class="card__icon"><i class="fa-solid fa-file-export"></i></div>
        <h3>Exportar TXT</h3>
        <p>Descargar todos los recibos en formato texto.</p>
      </a>
      <a href="{{ url_for('nueva_cosecha') }}" class="card" style="text-decoration:none;">
        <div class="card__icon"><i class="fa-solid fa-wheat-awn"></i></div>
        <h3>Registrar cosecha</h3>
        <p>A\u00f1adir producci\u00f3n de cargas y kg.</p>
      </a>
    </div>

  </div>
</section>
{% endblock %}

{% block scripts %}
<script>
const datosMes = {{ por_mes | tojson }};
const datosTrabajadores = {{ por_trabajador | tojson }};

const ctxMes = document.getElementById('chartMes');
if (ctxMes && datosMes.length > 0) {
  new Chart(ctxMes, {
    type: 'bar',
    data: {
      labels: datosMes.map(d => d.mes),
      datasets: [{
        label: 'Gasto (COP)',
        data: datosMes.map(d => d.total),
        backgroundColor: '#2D6A4F',
        borderColor: '#1B4332',
        borderWidth: 1,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { ticks: { callback: v => '$ ' + (v/1000000).toFixed(1) + 'M' } } }
    }
  });
} else if (ctxMes) {
  ctxMes.parentElement.innerHTML = '<p style="text-align:center;color:var(--txt-muted);padding:2rem">Sin datos de gastos a\u00fan.</p>';
}

const ctxTrab = document.getElementById('chartTrabajadores');
if (ctxTrab && datosTrabajadores.length > 0) {
  new Chart(ctxTrab, {
    type: 'bar',
    data: {
      labels: datosTrabajadores.map(d => d.proveedor.split(' ').slice(0,2).join(' ')),
      datasets: [{
        label: 'Total (COP)',
        data: datosTrabajadores.map(d => d.total),
        backgroundColor: '#E9A800',
        borderColor: '#C77F00',
        borderWidth: 1,
        borderRadius: 6,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { callback: v => '$ ' + (v/1000000).toFixed(1) + 'M' } } }
    }
  });
} else if (ctxTrab) {
  ctxTrab.parentElement.innerHTML = '<p style="text-align:center;color:var(--txt-muted);padding:2rem">Sin datos a\u00fan.</p>';
}
</script>
{% endblock %}
""")

# ── 10. templates/reportes/semana.html ────────────────────────────────────
write_file(os.path.join(BASE, 'templates', 'reportes', 'semana.html'), """\
{% extends "base.html" %}
{% block title %}Reporte Semanal | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-calendar-week"></i></div>
    <div>
      <h1 class="page-hero__title">Reporte Semanal</h1>
      <p class="page-hero__sub">
        {{ inicio.strftime('%d/%m/%Y') }} \u2014 {{ fin.strftime('%d/%m/%Y') }}
      </p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('reportes') }}" class="button button--ghost">
        <i class="fa-solid fa-chart-bar"></i> Reportes
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container">

    <div class="gauge-section" style="margin-bottom: var(--s6);">
      <form method="GET" style="display:flex;align-items:center;gap:var(--s4);flex-wrap:wrap;">
        <label style="font-weight:700;color:var(--clr-900);">
          <i class="fa-solid fa-calendar"></i> Ir a la semana del:
        </label>
        <input type="date" name="fecha" value="{{ fecha_str }}"
               style="border:1.5px solid var(--border);border-radius:var(--r-md);padding:.5rem .8rem;font-family:var(--ff-body);">
        <button type="submit" class="button button--primary">
          <i class="fa-solid fa-magnifying-glass"></i> Ver semana
        </button>
      </form>
    </div>

    {% if recibos %}
    <div class="table-wrap" style="margin-bottom: var(--s6);">
      <table class="data-table">
        <thead>
          <tr>
            <th>Serial</th>
            <th>Fecha</th>
            <th>Proveedor</th>
            <th>Concepto</th>
            <th>Neto a pagar</th>
          </tr>
        </thead>
        <tbody>
          {% for r in recibos %}
          <tr style="cursor:pointer" onclick="location.href='{{ url_for('detalle_recibo', serial=r.serial) }}'">
            <td><span class="serial-badge">{{ r.serial }}</span></td>
            <td>{{ r.fecha.strftime('%d/%m/%Y') if r.fecha else '\u2014' }}</td>
            <td><strong>{{ r.proveedor }}</strong></td>
            <td class="concepto-cell">{{ r.concepto }}</td>
            <td class="valor-cell">
              {% if r.neto_a_pagar %}
                <strong>$ {{ "{:,.0f}".format(r.neto_a_pagar).replace(",",".") }}</strong>
              {% else %}\u2014{% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
        <tfoot>
          <tr style="background:var(--clr-50);font-weight:700;">
            <td colspan="4" style="padding:var(--s3) var(--s4);text-align:right;">Total semana:</td>
            <td class="valor-cell" style="padding:var(--s3) var(--s4);">
              <strong>$ {{ "{:,.0f}".format(total).replace(",",".") }}</strong>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
    {% else %}
    <div class="empty-state">
      <i class="fa-solid fa-calendar-xmark empty-state__icon"></i>
      <h3>Sin recibos esta semana</h3>
      <p>No hay pagos registrados del {{ inicio.strftime('%d/%m/%Y') }} al {{ fin.strftime('%d/%m/%Y') }}.</p>
    </div>
    {% endif %}

  </div>
</section>
{% endblock %}
""")

# ── 11. templates/produccion/index.html ───────────────────────────────────
write_file(os.path.join(BASE, 'templates', 'produccion', 'index.html'), """\
{% extends "base.html" %}
{% block title %}Producci\u00f3n | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-wheat-awn"></i></div>
    <div>
      <h1 class="page-hero__title">Producci\u00f3n</h1>
      <p class="page-hero__sub">Registro de cosechas \u00b7 {{ total_ha }} hect\u00e1reas \u00b7 M\u00ednimo {{ min_cargas }} cargas</p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('nueva_cosecha') }}" class="button button--primary">
        <i class="fa-solid fa-seedling"></i> Registrar cosecha
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container">

    {% set total_cargas = totales.tc | int %}
    {% set pct = [[((total_cargas / min_cargas) * 100) | round(1), 100] | min, 0] | max %}

    <div class="gauge-section" style="margin-bottom: var(--s8);">
      <div class="gauge-header">
        <span class="gauge-title"><i class="fa-solid fa-wheat-awn"></i> Total cargas cosechadas</span>
        <span class="gauge-amount">
          <strong>{{ "{:,}".format(total_cargas).replace(",",".") }} cargas</strong>
          / {{ "{:,}".format(min_cargas).replace(",",".") }} m\u00ednimo
        </span>
      </div>
      <div class="gauge-bar-wrap">
        <div class="gauge-bar {% if pct >= 100 %}gauge-bar--green{% elif pct >= 60 %}gauge-bar--yellow{% else %}gauge-bar--red{% endif %}"
             style="width: {{ pct }}%">{{ pct }}%</div>
      </div>
      <p class="gauge-footnote">
        M\u00ednimo requerido: {{ min_cargas_ha }} cargas/ha \u00d7 {{ total_ha }} ha = {{ min_cargas }} cargas \u00b7
        Total kg: {{ "{:,.0f}".format(totales.tk | float).replace(",",".") }} kg
      </p>
    </div>

    {% if cosechas %}
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Lote</th>
            <th>Hect\u00e1reas</th>
            <th>Cargas</th>
            <th>Kg total</th>
            <th>Precio/carga</th>
            <th>Valor total</th>
            <th>Observaciones</th>
          </tr>
        </thead>
        <tbody>
          {% for c in cosechas %}
          <tr>
            <td>{{ c.fecha.strftime('%d/%m/%Y') if c.fecha else '\u2014' }}</td>
            <td>{{ c.lote or 'El Mangon' }}</td>
            <td>{{ c.hectareas }}</td>
            <td><strong>{{ c.cargas }}</strong></td>
            <td>{{ "{:,.0f}".format(c.kg_total).replace(",",".") if c.kg_total else '\u2014' }} kg</td>
            <td class="valor-cell">{% if c.precio_carga %}$ {{ "{:,.0f}".format(c.precio_carga).replace(",",".") }}{% else %}\u2014{% endif %}</td>
            <td class="valor-cell">{% if c.valor_total %}<strong>$ {{ "{:,.0f}".format(c.valor_total).replace(",",".") }}</strong>{% else %}\u2014{% endif %}</td>
            <td class="txt-muted" style="font-size:.85rem;">{{ c.observaciones or '' }}</td>
          </tr>
          {% endfor %}
        </tbody>
        <tfoot>
          <tr style="background:var(--clr-50);font-weight:700;">
            <td colspan="3" style="padding:var(--s3) var(--s4);">Totales</td>
            <td style="padding:var(--s3) var(--s4);">{{ "{:,}".format(totales.tc | int).replace(",",".") }}</td>
            <td style="padding:var(--s3) var(--s4);">{{ "{:,.0f}".format(totales.tk | float).replace(",",".") }} kg</td>
            <td></td>
            <td class="valor-cell" style="padding:var(--s3) var(--s4);">
              {% if totales.tv %}<strong>$ {{ "{:,.0f}".format(totales.tv | float).replace(",",".") }}</strong>{% endif %}
            </td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>
    {% else %}
    <div class="empty-state">
      <i class="fa-solid fa-wheat-awn empty-state__icon"></i>
      <h3>Sin cosechas registradas</h3>
      <p>Registra la primera cosecha para comenzar el seguimiento de producci\u00f3n.</p>
      <a href="{{ url_for('nueva_cosecha') }}" class="button button--primary">
        <i class="fa-solid fa-seedling"></i> Registrar cosecha
      </a>
    </div>
    {% endif %}

  </div>
</section>
{% endblock %}
""")

# ── 12. templates/produccion/nueva.html ───────────────────────────────────
write_file(os.path.join(BASE, 'templates', 'produccion', 'nueva.html'), """\
{% extends "base.html" %}
{% block title %}Registrar Cosecha | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-seedling"></i></div>
    <div>
      <h1 class="page-hero__title">Registrar Cosecha</h1>
      <p class="page-hero__sub">M\u00ednimo requerido: {{ min_cargas }} cargas ({{ min_cargas_ha }}/ha en {{ total_ha }} ha)</p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('lista_produccion') }}" class="button button--ghost">
        <i class="fa-solid fa-list"></i> Ver producci\u00f3n
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container" style="max-width: 720px;">

    {% if success %}
    <div class="alert alert--success"><i class="fa-solid fa-circle-check"></i> {{ success }}</div>
    {% endif %}
    {% if error %}
    <div class="alert alert--danger"><i class="fa-solid fa-circle-xmark"></i> {{ error }}</div>
    {% endif %}

    <div class="form-card">
      <form method="POST">
        <div class="form-section">
          <h3 class="form-section__title"><i class="fa-solid fa-wheat-awn"></i> Datos de la cosecha</h3>
          <div class="form-grid form-grid--2">
            <div class="form-group">
              <label for="fecha">Fecha <span class="req-star">*</span></label>
              <input type="date" id="fecha" name="fecha" value="{{ today }}" required>
            </div>
            <div class="form-group">
              <label for="lote">Lote</label>
              <input type="text" id="lote" name="lote" value="El Mangon" placeholder="El Mangon">
            </div>
            <div class="form-group">
              <label for="hectareas">Hect\u00e1reas</label>
              <input type="number" id="hectareas" name="hectareas" value="{{ total_ha }}" min="0.1" step="0.01">
            </div>
            <div class="form-group">
              <label for="cargas">Cargas <span class="req-star">*</span></label>
              <input type="number" id="cargas" name="cargas" min="1" required placeholder="Ej: 2500"
                     oninput="calcKg()">
              <p class="field-hint" id="kgPreview" style="color:var(--clr-700);font-weight:700;"></p>
            </div>
            <div class="form-group">
              <label for="precio_carga">Precio por carga (COP)</label>
              <input type="text" id="precio_carga" name="precio_carga" placeholder="Ej: 85.000" inputmode="numeric">
            </div>
            <div class="form-group form-grid--full">
              <label for="observaciones">Observaciones</label>
              <textarea id="observaciones" name="observaciones" rows="3" placeholder="Notas adicionales sobre esta cosecha..."></textarea>
            </div>
          </div>
          <div class="config-info-box" style="margin-top: var(--s4);">
            <i class="fa-solid fa-circle-info"></i>
            <div>
              <strong>Referencia:</strong> M\u00ednimo {{ min_cargas }} cargas ({{ min_cargas_ha }}/ha \u00d7 {{ total_ha }} ha) \u00b7
              Cada carga = 62.5 kg
            </div>
          </div>
        </div>
        <div class="form-actions">
          <button type="submit" class="button button--primary">
            <i class="fa-solid fa-floppy-disk"></i> Registrar cosecha
          </button>
          <a href="{{ url_for('lista_produccion') }}" class="button button--ghost-dark">
            <i class="fa-solid fa-list"></i> Ver producci\u00f3n
          </a>
        </div>
      </form>
    </div>

  </div>
</section>
{% endblock %}

{% block scripts %}
<script>
function calcKg() {
  const cargas = parseInt(document.getElementById('cargas').value) || 0;
  const kg = cargas * 62.5;
  const preview = document.getElementById('kgPreview');
  if (cargas > 0) {
    preview.textContent = '\u2248 ' + kg.toLocaleString('es-CO') + ' kg totales';
  } else {
    preview.textContent = '';
  }
}
</script>
{% endblock %}
""")

# ── 13. templates/config/index.html ───────────────────────────────────────
write_file(os.path.join(BASE, 'templates', 'config', 'index.html'), """\
{% extends "base.html" %}
{% block title %}Configuraci\u00f3n | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-gear"></i></div>
    <div>
      <h1 class="page-hero__title">Configuraci\u00f3n</h1>
      <p class="page-hero__sub">Ajustes generales del sistema de recibos.</p>
    </div>
  </div>
</div>

<section class="section">
  <div class="container" style="max-width: 720px;">

    {% if message %}
    <div class="alert alert--success"><i class="fa-solid fa-circle-check"></i> {{ message }}</div>
    {% endif %}
    {% if error %}
    <div class="alert alert--danger"><i class="fa-solid fa-circle-xmark"></i> {{ error }}</div>
    {% endif %}

    <div class="form-card">
      <div class="form-section">
        <h3 class="form-section__title"><i class="fa-solid fa-hashtag"></i> Serial de recibos</h3>

        <div class="config-info-box">
          <i class="fa-solid fa-circle-info"></i>
          <div>
            <strong>Total de recibos registrados:</strong> {{ total_recibos }}<br>
            <strong>Serial inicial configurado:</strong> {{ config.get('serial_inicial', '1') }}
          </div>
        </div>

        <form method="POST">
          <div class="form-group" style="max-width: 280px; margin-top: 1.5rem;">
            <label for="serial_inicial">Serial inicial para nuevos recibos</label>
            <input type="number" id="serial_inicial" name="serial_inicial"
                   value="{{ config.get('serial_inicial', '1') }}" min="1" required>
            <p class="field-hint">
              Define desde qu\u00e9 n\u00famero empezar\u00e1n los seriales cuando no haya recibos previos.
              {% if total_recibos > 0 %}
              <strong>Nota:</strong> ya hay {{ total_recibos }} recibo(s) registrado(s), el pr\u00f3ximo serial se calcula autom\u00e1ticamente.
              {% endif %}
            </p>
          </div>
          <div class="form-actions">
            <button type="submit" class="button button--primary">
              <i class="fa-solid fa-floppy-disk"></i> Guardar configuraci\u00f3n
            </button>
          </div>
        </form>
      </div>
    </div>

  </div>
</section>
{% endblock %}
""")

print('\n' + '='*60)
print('Bootstrap completo! Todos los directorios y templates escritos.')
print('='*60)
print('\nSiguientes pasos:')
print('  1. python app.py     (iniciar la app Flask)')
print('  2. Visita http://127.0.0.1:5000')
print('\nRutas disponibles:')
print('  /workers            - Lista de trabajadores')
print('  /recibos/lote       - Recibo por lote')
print('  /recibos/<serial>   - Detalle de recibo')
print('  /reportes           - Dashboard de reportes')
print('  /reportes/semana    - Reporte semanal')
print('  /reportes/exportar_txt - Exportar TXT')
print('  /produccion         - Lista cosechas')
print('  /produccion/nueva   - Registrar cosecha')

{% block content %}
<section class="section">
  <div class="container">

    <div class="page-header">
      <div class="page-header__icon"><i class="fa-solid fa-file-invoice-dollar"></i></div>
      <div>
        <h1 class="page-header__title">Nuevo Recibo</h1>
        <p class="page-header__sub">Registra un pago. El serial se asigna autom\u00e1ticamente seg\u00fan la fecha.</p>
      </div>
    </div>

    {% if success %}
    <div class="alert alert--success"><i class="fa-solid fa-circle-check"></i> {{ success }}</div>
    {% endif %}
    {% if error %}
    <div class="alert alert--danger"><i class="fa-solid fa-circle-xmark"></i> {{ error }}</div>
    {% endif %}

    {% if warning %}
    <div class="alert alert--warning" id="warningAlert">
      <i class="fa-solid fa-triangle-exclamation"></i> {{ warning }}
      <div class="warning-actions">
        <button type="button" class="button button--sm button--primary" id="btnForceGuardar">
          <i class="fa-solid fa-floppy-disk"></i> Guardar de todas formas
        </button>
        <button type="button" class="button button--sm button--ghost-dark" onclick="document.getElementById('warningAlert').style.display='none'">
          Cancelar
        </button>
      </div>
    </div>
    {% endif %}

    <div class="trabajador-search-box">
      <label class="search-label"><i class="fa-solid fa-magnifying-glass"></i> Buscar trabajador por nombre o apodo</label>
      <div class="search-input-wrap">
        <input type="text" id="buscarTrabajador" placeholder="Ej: paisa, delio, Silvio..." autocomplete="off" class="search-input">
        <ul id="trabajadorSuggestions" class="suggestions-list"></ul>
      </div>
      <p class="field-hint">Al seleccionar, se autocompletan NIT, direcci\u00f3n, ciudad, tel\u00e9fono, concepto y valor.</p>
    </div>

    <form method="POST" id="reciboForm" class="form-card">
      <input type="hidden" name="force" id="forceField" value="false">

      <div class="form-section">
        <h3 class="form-section__title"><i class="fa-solid fa-hashtag"></i> Identificaci\u00f3n del Recibo</h3>
        <div class="form-grid form-grid--3">
          <div class="form-group">
            <label for="serial">Serial <span class="req-star">*</span></label>
            <input type="number" id="serial" name="serial" value="{{ form_data.get('serial', next_serial) }}" min="1" required>
            <p class="field-hint">Pr\u00f3ximo sugerido: <strong>{{ next_serial }}</strong></p>
          </div>
          <div class="form-group">
            <label for="fecha">Fecha del recibo</label>
            <input type="date" id="fecha" name="fecha" value="{{ form_data.get('fecha', today) }}">
          </div>
        </div>
      </div>

      <div class="form-section">
        <h3 class="form-section__title"><i class="fa-solid fa-user-tie"></i> Proveedor / Trabajador</h3>
        <div class="form-grid form-grid--2">
          <div class="form-group">
            <label for="proveedor">Nombre completo <span class="req-star">*</span></label>
            <input type="text" id="proveedor" name="proveedor" value="{{ form_data.get('proveedor','') }}" placeholder="Nombre real (no apodo)" required>
          </div>
          <div class="form-group">
            <label for="nit">NIT / C\u00e9dula</label>
            <input type="text" id="nit" name="nit" value="{{ form_data.get('nit','') }}" placeholder="Ej: 93470637">
          </div>
          <div class="form-group">
            <label for="direccion">Direcci\u00f3n</label>
            <input type="text" id="direccion" name="direccion" value="{{ form_data.get('direccion','') }}" placeholder="Ej: El Tambo">
          </div>
          <div class="form-group">
            <label for="telefono">Tel\u00e9fono</label>
            <input type="text" id="telefono" name="telefono" value="{{ form_data.get('telefono','') }}" placeholder="Ej: 3001234567">
          </div>
          <div class="form-group">
            <label for="ciudad">Ciudad</label>
            <input type="text" id="ciudad" name="ciudad" value="{{ form_data.get('ciudad','') }}" placeholder="Ej: Natagaima">
          </div>
        </div>
      </div>

      <div class="form-section">
        <h3 class="form-section__title"><i class="fa-solid fa-file-lines"></i> Concepto y Valor</h3>
        <div class="form-group">
          <label for="concepto">Concepto <span class="req-star">*</span></label>
          <textarea id="concepto" name="concepto" rows="3" required placeholder="Descripci\u00f3n detallada del trabajo o pago...">{{ form_data.get('concepto','') }}</textarea>
          <p class="field-hint">\u26a0\ufe0f No registrar compras de aceite ni ACPM directo. Solo transporte de ACPM.</p>
        </div>
        <div class="form-grid form-grid--2">
          <div class="form-group">
            <label for="valor_operacion">Valor operaci\u00f3n (COP)</label>
            <input type="text" id="valor_operacion" name="valor_operacion" value="{{ form_data.get('valor_operacion','') }}" placeholder="Ej: 350.000" inputmode="numeric">
          </div>
          <div class="form-group">
            <label for="neto_a_pagar">Neto a pagar (COP)</label>
            <input type="text" id="neto_a_pagar" name="neto_a_pagar" value="{{ form_data.get('neto_a_pagar','') }}" placeholder="Igual al valor si no hay descuentos" inputmode="numeric">
            <p class="field-hint">Si se deja vac\u00edo, se usa el valor de operaci\u00f3n.</p>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="button button--primary">
          <i class="fa-solid fa-floppy-disk"></i> Guardar recibo
        </button>
        <a href="{{ url_for('lista_recibos') }}" class="button button--ghost-dark">
          <i class="fa-solid fa-list"></i> Ver todos los recibos
        </a>
      </div>
    </form>

  </div>
</section>
{% endblock %}

{% block scripts %}
<script>
  const TRABAJADORES = {{ trabajadores | tojson }};

  const btnForce = document.getElementById('btnForceGuardar');
  if (btnForce) {
    btnForce.addEventListener('click', function() {
      document.getElementById('forceField').value = 'true';
      document.getElementById('reciboForm').submit();
    });
  }

  initTrabajadorAutocomplete(TRABAJADORES, {
    searchInput: document.getElementById('buscarTrabajador'),
    suggestionsList: document.getElementById('trabajadorSuggestions'),
    fields: {
      proveedor: document.getElementById('proveedor'),
      nit: document.getElementById('nit'),
      direccion: document.getElementById('direccion'),
      telefono: document.getElementById('telefono'),
      ciudad: document.getElementById('ciudad'),
      concepto: document.getElementById('concepto'),
      valor_operacion: document.getElementById('valor_operacion'),
      neto_a_pagar: document.getElementById('neto_a_pagar'),
    }
  });
</script>
{% endblock %}
""")

# ── 6. templates/recibos/lista.html ───────────────────────────────────────
write_file(os.path.join(BASE, 'templates', 'recibos', 'lista.html'), """\
{% extends "base.html" %}
{% block title %}Recibos | Contabilidad Arroceras{% endblock %}

{% block content %}
<section class="section">
  <div class="container">

    <div class="page-header">
      <div class="page-header__icon"><i class="fa-solid fa-list-check"></i></div>
      <div>
        <h1 class="page-header__title">Recibos</h1>
        <p class="page-header__sub">{{ recibos|length }} recibo(s) registrado(s) en total.</p>
      </div>
      <a href="{{ url_for('nuevo_recibo') }}" class="button button--primary" style="margin-left:auto;">
        <i class="fa-solid fa-plus"></i> Nuevo recibo
      </a>
    </div>

    {% if recibos %}
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Serial</th>
            <th>Fecha</th>
            <th>Proveedor</th>
            <th>NIT</th>
            <th>Concepto</th>
            <th>Neto a pagar</th>
          </tr>
        </thead>
        <tbody>
          {% for r in recibos %}
          <tr>
            <td><span class="serial-badge">{{ r.serial }}</span></td>
            <td>{{ r.fecha.strftime('%d/%m/%Y') if r.fecha else '\u2014' }}</td>
            <td><strong>{{ r.proveedor }}</strong></td>
            <td class="txt-muted">{{ r.nit or '\u2014' }}</td>
            <td class="concepto-cell">{{ r.concepto }}</td>
            <td class="valor-cell">
              {% if r.neto_a_pagar %}
                <strong>${{ "{:,.0f}".format(r.neto_a_pagar) }}</strong>
              {% else %}\u2014{% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="empty-state">
      <i class="fa-solid fa-file-circle-plus empty-state__icon"></i>
      <h3>No hay recibos a\u00fan</h3>
      <p>Crea el primer recibo haciendo clic en "Nuevo recibo".</p>
      <a href="{{ url_for('nuevo_recibo') }}" class="button button--primary">
        <i class="fa-solid fa-plus"></i> Crear primer recibo
      </a>
    </div>
    {% endif %}

  </div>
</section>
{% endblock %}
""")

# ── 7. templates/config/index.html ────────────────────────────────────────
write_file(os.path.join(BASE, 'templates', 'config', 'index.html'), """\
{% extends "base.html" %}
{% block title %}Configuraci\u00f3n | Contabilidad Arroceras{% endblock %}

{% block content %}
<section class="section">
  <div class="container" style="max-width: 720px;">

    <div class="page-header">
      <div class="page-header__icon"><i class="fa-solid fa-gear"></i></div>
      <div>
        <h1 class="page-header__title">Configuraci\u00f3n</h1>
        <p class="page-header__sub">Ajustes generales del sistema de recibos.</p>
      </div>
    </div>

    {% if message %}
    <div class="alert alert--success"><i class="fa-solid fa-circle-check"></i> {{ message }}</div>
    {% endif %}
    {% if error %}
    <div class="alert alert--danger"><i class="fa-solid fa-circle-xmark"></i> {{ error }}</div>
    {% endif %}

    <div class="form-card">
      <div class="form-section">
        <h3 class="form-section__title"><i class="fa-solid fa-hashtag"></i> Serial de recibos</h3>

        <div class="config-info-box">
          <i class="fa-solid fa-circle-info"></i>
          <div>
            <strong>Total de recibos registrados:</strong> {{ total_recibos }}<br>
            <strong>Serial inicial configurado:</strong> {{ config.get('serial_inicial', '1') }}
          </div>
        </div>

        <form method="POST">
          <div class="form-group" style="max-width: 280px; margin-top: 1.5rem;">
            <label for="serial_inicial">Serial inicial para nuevos recibos</label>
            <input type="number" id="serial_inicial" name="serial_inicial"
                   value="{{ config.get('serial_inicial', '1') }}" min="1" required>
            <p class="field-hint">
              Define desde qu\u00e9 n\u00famero empezar\u00e1n los seriales cuando no haya recibos previos.
              {% if total_recibos > 0 %}
              <strong>Nota:</strong> ya hay {{ total_recibos }} recibo(s) registrado(s), el pr\u00f3ximo serial se calcula autom\u00e1ticamente.
              {% endif %}
            </p>
          </div>
          <div class="form-actions">
            <button type="submit" class="button button--primary">
              <i class="fa-solid fa-floppy-disk"></i> Guardar configuraci\u00f3n
            </button>
          </div>
        </form>
      </div>
    </div>

  </div>
</section>
{% endblock %}
""")

print('\nBootstrap complete. All directories and template files created.')
print('You can now run: python app.py')
