"""
Run once: python setup_templates.py
Creates all directories and template files. Overwrites existing templates.
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))

DIRS = [
    os.path.join(BASE, 'data'),
    os.path.join(BASE, 'uploads'),
    os.path.join(BASE, 'templates', 'recibos'),
    os.path.join(BASE, 'templates', 'config'),
    os.path.join(BASE, 'templates', 'reportes'),
    os.path.join(BASE, 'templates', 'produccion'),
    os.path.join(BASE, 'templates', 'workers'),
    os.path.join(BASE, 'templates', 'presupuesto'),
]
for d in DIRS:
    os.makedirs(d, exist_ok=True)
    print(f'  dir ok: {d}')

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  written: {path}')

# ── data/trabajadores.json ─────────────────────────────────────────────────
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

write_file(os.path.join(BASE, 'uploads', '.gitkeep'), '')

# ═══════════════════════════════════════════════════════════════
#  RECIBOS / LISTA
# ═══════════════════════════════════════════════════════════════
write_file(os.path.join(BASE, 'templates', 'recibos', 'lista.html'), """\
{% extends "base.html" %}
{% block title %}Recibos | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-list-check"></i></div>
    <div>
      <h1 class="page-hero__title">Recibos</h1>
      <p class="page-hero__sub" id="counterSub">{{ recibos|length }} recibo(s) registrado(s) en total.</p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('nuevo_recibo') }}" class="button button--primary">
        <i class="fa-solid fa-plus"></i> Nuevo recibo
      </a>
      <a href="{{ url_for('nuevo_recibo_lote') }}" class="button button--ghost">
        <i class="fa-solid fa-users-between-lines"></i> Por lote
      </a>
      <a href="{{ url_for('exportar_txt') }}" class="button button--ghost">
        <i class="fa-solid fa-file-export"></i> Exportar TXT
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container">

    {% if recibos %}

    <!-- Barra de búsqueda y resumen -->
    <div class="lista-toolbar">
      <div class="lista-search-wrap">
        <i class="fa-solid fa-magnifying-glass lista-search-icon"></i>
        <input type="text" id="searchInput" placeholder="Buscar por proveedor, NIT, concepto..." class="lista-search-input">
      </div>
      <div class="lista-summary">
        Total: <strong id="totalVisible">{{ recibos|length }}</strong> recibos &nbsp;|&nbsp;
        Suma: <strong id="sumaVisible">
          $ {{ "{:,.0f}".format(recibos | sum(attribute='neto_a_pagar') if recibos else 0).replace(",",".") }}
        </strong>
      </div>
    </div>

    <div class="table-wrap">
      <table class="data-table" id="recibosTable">
        <thead>
          <tr>
            <th class="col-serial">Serial</th>
            <th class="col-fecha">Fecha</th>
            <th>Proveedor</th>
            <th class="col-nit">NIT</th>
            <th class="col-concepto">Concepto</th>
            <th class="col-valor">Neto a pagar</th>
          </tr>
        </thead>
        <tbody id="recibosBody">
          {% for r in recibos %}
          <tr class="recibo-row" style="cursor:pointer"
              onclick="location.href='{{ url_for('detalle_recibo', serial=r.serial) }}'"
              data-proveedor="{{ r.proveedor | lower }}"
              data-nit="{{ r.nit or '' }}"
              data-concepto="{{ r.concepto | lower }}"
              data-valor="{{ r.neto_a_pagar or 0 }}">
            <td><span class="serial-badge">{{ r.serial }}</span></td>
            <td class="txt-muted">{{ r.fecha.strftime('%d/%m/%Y') if r.fecha else '\u2014' }}</td>
            <td><strong>{{ r.proveedor }}</strong></td>
            <td class="txt-muted small">{{ r.nit or '\u2014' }}</td>
            <td class="concepto-cell small">{{ r.concepto }}</td>
            <td class="valor-cell">
              {% if r.neto_a_pagar %}
                <strong>$ {{ "{:,.0f}".format(r.neto_a_pagar).replace(",",".") }}</strong>
              {% else %}\u2014{% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
        <tfoot>
          <tr class="table-foot" id="tableFoot">
            <td colspan="5" style="text-align:right;font-weight:600;color:var(--txt-muted)">Total visible:</td>
            <td class="valor-cell" id="footTotal">
              $ {{ "{:,.0f}".format(recibos | sum(attribute='neto_a_pagar') if recibos else 0).replace(",",".") }}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>

    <p id="noResultsMsg" style="display:none;text-align:center;padding:2rem;color:var(--txt-muted)">
      <i class="fa-solid fa-magnifying-glass"></i> Sin resultados para esa b\u00fasqueda.
    </p>

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

{% block scripts %}
<script>
(function() {
  const input  = document.getElementById('searchInput');
  const rows   = document.querySelectorAll('.recibo-row');
  const noMsg  = document.getElementById('noResultsMsg');
  const footTot= document.getElementById('footTotal');
  const sumVis = document.getElementById('sumaVisible');
  const totVis = document.getElementById('totalVisible');

  if (!input) return;

  input.addEventListener('input', function() {
    const q = this.value.toLowerCase().trim();
    let visible = 0;
    let suma = 0;

    rows.forEach(row => {
      const haystack = [
        row.dataset.proveedor,
        row.dataset.nit,
        row.dataset.concepto
      ].join(' ');

      const match = !q || haystack.includes(q);
      row.style.display = match ? '' : 'none';
      if (match) {
        visible++;
        suma += parseFloat(row.dataset.valor) || 0;
      }
    });

    noMsg.style.display = visible === 0 ? 'block' : 'none';
    totVis.textContent  = visible;
    const fmt = suma.toLocaleString('es-CO', {minimumFractionDigits:0, maximumFractionDigits:0});
    footTot.textContent = '$ ' + fmt;
    sumVis.textContent  = '$ ' + fmt;
  });
})();
</script>
{% endblock %}
""")

# ═══════════════════════════════════════════════════════════════
#  RECIBOS / NUEVO
# ═══════════════════════════════════════════════════════════════
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
      <p class="page-hero__sub">Registra un pago. El serial se asigna seg\u00fan la fecha.</p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('lista_recibos') }}" class="button button--ghost">
        <i class="fa-solid fa-list"></i> Ver recibos
      </a>
      <a href="{{ url_for('nuevo_recibo_lote') }}" class="button button--ghost">
        <i class="fa-solid fa-users-between-lines"></i> Por lote
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container" style="max-width:860px;">

    {% if success %}
    <div class="alert alert--success"><i class="fa-solid fa-circle-check"></i> {{ success }}</div>
    {% endif %}
    {% if error %}
    <div class="alert alert--danger"><i class="fa-solid fa-circle-xmark"></i> {{ error }}</div>
    {% endif %}

    {% if warning %}
    <div class="alert alert--warning" id="warningAlert">
      <i class="fa-solid fa-triangle-exclamation"></i> {{ warning }}
      <div style="margin-top:.6rem;display:flex;gap:.6rem;flex-wrap:wrap;">
        <button type="button" class="button button--sm button--primary" id="btnForceGuardar">
          <i class="fa-solid fa-floppy-disk"></i> Guardar de todas formas
        </button>
        <button type="button" class="button button--sm button--ghost-dark"
                onclick="document.getElementById('warningAlert').style.display='none'">
          Cancelar
        </button>
      </div>
    </div>
    {% endif %}

    <!-- Buscador de trabajadores -->
    <div class="trabajador-search-box">
      <label class="search-label">
        <i class="fa-solid fa-magnifying-glass"></i> Buscar trabajador por nombre o apodo
      </label>
      <div class="search-input-wrap">
        <input type="text" id="buscarTrabajador"
               placeholder="Ej: paisa, delio, Silvio\u2026"
               autocomplete="off" class="search-input">
        <ul id="trabajadorSuggestions" class="suggestions-list"></ul>
      </div>
      <p class="field-hint">Al seleccionar se autocompletan NIT, direcci\u00f3n, ciudad, tel\u00e9fono, concepto y valor.</p>
    </div>

    <form method="POST" id="reciboForm" class="form-card">
      <input type="hidden" name="force" id="forceField" value="false">

      <!-- SECCI\u00d3N 1: Identificaci\u00f3n -->
      <div class="form-section">
        <h3 class="form-section__title">
          <i class="fa-solid fa-hashtag"></i> Identificaci\u00f3n del recibo
        </h3>
        <div class="form-grid form-grid--3">
          <div class="form-group">
            <label for="serial">Serial <span class="req-star">*</span></label>
            <input type="number" id="serial" name="serial"
                   value="{{ form_data.get('serial', next_serial) }}" min="1" required>
            <p class="field-hint">Pr\u00f3ximo sugerido: <strong>{{ next_serial }}</strong></p>
          </div>
          <div class="form-group">
            <label for="fecha">Fecha del recibo</label>
            <input type="date" id="fecha" name="fecha"
                   value="{{ form_data.get('fecha', today) }}">
          </div>
        </div>
      </div>

      <!-- SECCI\u00d3N 2: Proveedor -->
      <div class="form-section">
        <h3 class="form-section__title">
          <i class="fa-solid fa-user-tie"></i> Proveedor / Trabajador
        </h3>
        <div class="form-grid form-grid--2">
          <div class="form-group">
            <label for="proveedor">Nombre completo <span class="req-star">*</span></label>
            <input type="text" id="proveedor" name="proveedor"
                   value="{{ form_data.get('proveedor','') }}"
                   placeholder="Nombre real (no apodo)" required>
          </div>
          <div class="form-group">
            <label for="nit">NIT / C\u00e9dula</label>
            <input type="text" id="nit" name="nit"
                   value="{{ form_data.get('nit','') }}"
                   placeholder="Ej: 93470637">
          </div>
          <div class="form-group">
            <label for="direccion">Direcci\u00f3n</label>
            <input type="text" id="direccion" name="direccion"
                   value="{{ form_data.get('direccion','') }}"
                   placeholder="Ej: El Tambo">
          </div>
          <div class="form-group">
            <label for="telefono">Tel\u00e9fono</label>
            <input type="text" id="telefono" name="telefono"
                   value="{{ form_data.get('telefono','') }}"
                   placeholder="Ej: 3001234567">
          </div>
          <div class="form-group">
            <label for="ciudad">Ciudad</label>
            <input type="text" id="ciudad" name="ciudad"
                   value="{{ form_data.get('ciudad','') }}"
                   placeholder="Ej: Natagaima">
          </div>
        </div>
      </div>

      <!-- SECCI\u00d3N 3: Concepto y Valor -->
      <div class="form-section">
        <h3 class="form-section__title">
          <i class="fa-solid fa-file-lines"></i> Concepto y valor
        </h3>
        <div class="form-group">
          <label for="concepto">Concepto <span class="req-star">*</span></label>
          <textarea id="concepto" name="concepto" rows="3" required
                    placeholder="Descripci\u00f3n detallada del trabajo o pago\u2026">{{ form_data.get('concepto','') }}</textarea>
          <p class="field-hint">
            <i class="fa-solid fa-circle-xmark" style="color:#c0392b"></i>
            No registrar compras de aceite ni ACPM directo. Solo el <em>transporte</em> de ACPM.
          </p>
        </div>
        <div class="form-grid form-grid--2">
          <div class="form-group">
            <label for="valor_operacion">Valor operaci\u00f3n (COP)</label>
            <input type="text" id="valor_operacion" name="valor_operacion"
                   value="{{ form_data.get('valor_operacion','') }}"
                   placeholder="Ej: 350.000" inputmode="numeric"
                   oninput="syncNeto(this)">
          </div>
          <div class="form-group">
            <label for="neto_a_pagar">Neto a pagar (COP)</label>
            <input type="text" id="neto_a_pagar" name="neto_a_pagar"
                   value="{{ form_data.get('neto_a_pagar','') }}"
                   placeholder="Igual al valor si no hay descuentos" inputmode="numeric">
            <p class="field-hint">Si se deja vac\u00edo se usa el valor de operaci\u00f3n.</p>
          </div>
        </div>
      </div>

      <!-- SECCI\u00d3N 4: Calculadora de jornales (colapsable) -->
      <div class="form-section form-section--collapsible" id="calcSection">
        <button type="button" class="form-section__toggle" onclick="toggleCalc()">
          <i class="fa-solid fa-calculator"></i> Calculadora de jornales
          <i class="fa-solid fa-chevron-down toggle-icon" id="calcIcon"></i>
        </button>
        <div class="calc-body" id="calcBody" style="display:none;">
          <p class="field-hint" style="margin-bottom:1rem">
            Calcula el valor basado en n\u00famero de trabajadores, d\u00edas y valor diario.
          </p>
          <div class="form-grid form-grid--3">
            <div class="form-group">
              <label for="calc_trabajadores">N\u00famero de trabajadores</label>
              <input type="number" id="calc_trabajadores" min="1" value="1" oninput="calcJornales()">
            </div>
            <div class="form-group">
              <label for="calc_dias">D\u00edas trabajados</label>
              <input type="number" id="calc_dias" min="1" value="1" oninput="calcJornales()">
            </div>
            <div class="form-group">
              <label for="calc_valor_dia">Valor por jornal/d\u00eda (COP)</label>
              <input type="text" id="calc_valor_dia" value="60.000" inputmode="numeric"
                     oninput="calcJornales()">
            </div>
          </div>
          <div class="calc-result" id="calcResult" style="display:none;">
            <span class="calc-result__label">Resultado:</span>
            <span class="calc-result__valor" id="calcValor">\u2014</span>
            <button type="button" class="button button--sm button--primary" onclick="aplicarCalculo()">
              <i class="fa-solid fa-arrow-right"></i> Aplicar al valor
            </button>
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

// Force-override desde warning
const btnForce = document.getElementById('btnForceGuardar');
if (btnForce) {
  btnForce.addEventListener('click', () => {
    document.getElementById('forceField').value = 'true';
    document.getElementById('reciboForm').submit();
  });
}

// Autocomplete
initTrabajadorAutocomplete(TRABAJADORES, {
  searchInput:     document.getElementById('buscarTrabajador'),
  suggestionsList: document.getElementById('trabajadorSuggestions'),
  fields: {
    proveedor:       document.getElementById('proveedor'),
    nit:             document.getElementById('nit'),
    direccion:       document.getElementById('direccion'),
    telefono:        document.getElementById('telefono'),
    ciudad:          document.getElementById('ciudad'),
    concepto:        document.getElementById('concepto'),
    valor_operacion: document.getElementById('valor_operacion'),
    neto_a_pagar:    document.getElementById('neto_a_pagar'),
  }
});

// Sincroniza neto cuando se escribe valor operacion (si neto est\u00e1 vac\u00edo)
function syncNeto(el) {
  const neto = document.getElementById('neto_a_pagar');
  if (!neto.value || neto.dataset.userEdited !== '1') {
    neto.value = el.value;
  }
}
document.getElementById('neto_a_pagar').addEventListener('input', function() {
  this.dataset.userEdited = '1';
});

// Calculadora de jornales
function toggleCalc() {
  const body = document.getElementById('calcBody');
  const icon = document.getElementById('calcIcon');
  const open = body.style.display === 'none';
  body.style.display = open ? 'block' : 'none';
  icon.style.transform = open ? 'rotate(180deg)' : '';
}

function parseCOP(str) {
  return parseFloat((str || '0').replace(/\./g, '').replace(',', '.')) || 0;
}

function formatCOP(n) {
  return Math.round(n).toLocaleString('es-CO');
}

function calcJornales() {
  const trab  = parseInt(document.getElementById('calc_trabajadores').value) || 0;
  const dias  = parseInt(document.getElementById('calc_dias').value) || 0;
  const vdia  = parseCOP(document.getElementById('calc_valor_dia').value);
  const total = trab * dias * vdia;
  const res   = document.getElementById('calcResult');
  const val   = document.getElementById('calcValor');
  if (total > 0) {
    val.textContent = '$ ' + formatCOP(total);
    res.style.display = 'flex';
  } else {
    res.style.display = 'none';
  }
}

function aplicarCalculo() {
  const trab  = parseInt(document.getElementById('calc_trabajadores').value) || 0;
  const dias  = parseInt(document.getElementById('calc_dias').value) || 0;
  const vdia  = parseCOP(document.getElementById('calc_valor_dia').value);
  const total = trab * dias * vdia;
  if (total <= 0) return;
  const fmt   = formatCOP(total);
  document.getElementById('valor_operacion').value = fmt;
  document.getElementById('neto_a_pagar').value    = fmt;
  // Actualizar concepto con desglose si est\u00e1 vac\u00edo
  const conc = document.getElementById('concepto');
  if (!conc.value) {
    conc.value = trab + ' trabajador(es) \u00d7 ' + dias + ' d\u00eda(s) \u00d7 $ ' + formatCOP(vdia) + '/d\u00eda';
  }
}
</script>
{% endblock %}
""")

# ═══════════════════════════════════════════════════════════════
#  RECIBOS / LOTE
# ═══════════════════════════════════════════════════════════════
write_file(os.path.join(BASE, 'templates', 'recibos', 'lote.html'), """\
{% extends "base.html" %}
{% block title %}Recibo por Lote | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-users-between-lines"></i></div>
    <div>
      <h1 class="page-hero__title">Recibo por Lote</h1>
      <p class="page-hero__sub">Mismo concepto, varios trabajadores \u2014 un recibo por cada uno.</p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('lista_recibos') }}" class="button button--ghost">
        <i class="fa-solid fa-list"></i> Ver recibos
      </a>
      <a href="{{ url_for('nuevo_recibo') }}" class="button button--ghost">
        <i class="fa-solid fa-file-invoice-dollar"></i> Recibo individual
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

    <form method="POST" id="loteForm">

      <!-- PASO 1: Datos comunes -->
      <div class="form-card" style="margin-bottom:var(--s6)">
        <div class="form-section">
          <h3 class="form-section__title">
            <span class="step-badge">1</span> Datos comunes del lote
          </h3>
          <div class="form-grid form-grid--3">
            <div class="form-group">
              <label for="serial_inicio">Serial de inicio <span class="req-star">*</span></label>
              <input type="number" id="serial_inicio" name="serial_inicio"
                     value="{{ next_serial }}" min="1" required>
              <p class="field-hint">Se asignan seriales consecutivos por cada trabajador.</p>
            </div>
            <div class="form-group">
              <label for="fecha">Fecha</label>
              <input type="date" id="fecha" name="fecha" value="{{ today }}">
            </div>
            <div class="form-group">
              <label for="valor_por_trabajador">Valor por trabajador (COP)</label>
              <input type="text" id="valor_por_trabajador" name="valor_por_trabajador"
                     placeholder="Ej: 60.000" inputmode="numeric">
              <p class="field-hint">Deja vac\u00edo para usar el valor habitual de cada uno.</p>
            </div>
            <div class="form-group" style="grid-column:1/-1">
              <label for="concepto">Concepto <span class="req-star">*</span></label>
              <textarea id="concepto" name="concepto" rows="2" required
                        placeholder="Ej: Despalillada 3 jornales x semana en el lote El Mangon"></textarea>
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

          <!-- Calculadora inline de jornales para lotes -->
          <details class="calc-inline" style="margin-top:1rem">
            <summary class="calc-inline__toggle">
              <i class="fa-solid fa-calculator"></i> Calculadora de jornales
            </summary>
            <div class="calc-inline__body">
              <div class="form-grid form-grid--3" style="margin-top:.8rem">
                <div class="form-group">
                  <label>D\u00edas trabajados</label>
                  <input type="number" id="lc_dias" min="1" value="1" oninput="calcLote()">
                </div>
                <div class="form-group">
                  <label>Valor por jornal/d\u00eda (COP)</label>
                  <input type="text" id="lc_vdia" value="60.000" oninput="calcLote()">
                </div>
                <div class="form-group">
                  <label>Resultado por trabajador</label>
                  <input type="text" id="lc_resultado" readonly
                         style="background:var(--clr-50);font-weight:600">
                </div>
              </div>
              <button type="button" class="button button--sm button--primary"
                      onclick="aplicarLoteCalc()">
                <i class="fa-solid fa-arrow-right"></i> Aplicar al valor por trabajador
              </button>
            </div>
          </details>

        </div>
      </div>

      <!-- PASO 2: Seleccionar trabajadores -->
      <div class="form-card">
        <div class="form-section">
          <div class="worker-selector-header">
            <h3 class="worker-selector-title">
              <span class="step-badge">2</span> Seleccionar trabajadores
            </h3>
            <span class="selection-counter" id="selCounter">0 seleccionados</span>
          </div>

          <!-- Filtros por cargo -->
          <div class="cargo-filters" id="cargoFilters">
            <button type="button" class="cargo-filter-btn is-active" data-cargo="todos">Todos</button>
            {% set cargos_vistos = namespace(lista=[]) %}
            {% for w in db_workers %}
              {% if w.trabajo_desarrolla and w.trabajo_desarrolla not in cargos_vistos.lista %}
                {% set cargos_vistos.lista = cargos_vistos.lista + [w.trabajo_desarrolla] %}
                <button type="button" class="cargo-filter-btn" data-cargo="{{ w.trabajo_desarrolla }}">
                  {{ w.trabajo_desarrolla | replace('_', ' ') | title }}
                </button>
              {% endif %}
            {% endfor %}
          </div>

          <!-- B\u00fasqueda r\u00e1pida de trabajadores -->
          <div style="margin:.6rem 0 1rem">
            <input type="text" id="workerSearch" placeholder="Filtrar trabajadores por nombre\u2026"
                   class="lista-search-input" style="max-width:320px" oninput="filterWorkers()">
          </div>

          {% if db_workers %}
          <div class="workers-grid" id="workersGrid">
            {% for w in db_workers %}
            <div class="worker-card-sel"
                 data-id="{{ w.id_worker }}"
                 data-cargo="{{ w.trabajo_desarrolla or '' }}"
                 data-nombre="{{ (w.name ~ ' ' ~ w.lastname) | lower }}"
                 onclick="toggleWorker(this)">
              <i class="fa-solid fa-check worker-card-sel__check"></i>
              <div class="worker-card-sel__name">{{ w.name }} {{ w.lastname }}</div>
              <span class="worker-card-sel__cargo">
                {{ (w.trabajo_desarrolla or 'sin cargo') | replace('_', ' ') }}
              </span>
            </div>
            {% endfor %}
          </div>
          <div id="hiddenWorkerInputs"></div>

          <!-- Resumen de selecci\u00f3n -->
          <div id="selResumen" style="display:none;margin-top:1rem"
               class="alert alert--info">
            <i class="fa-solid fa-circle-info"></i>
            Se crear\u00e1n <strong id="numRecibos">0</strong> recibos
            (seriales <strong id="serialRange">\u2014</strong>)
            con serial de inicio <strong id="serialInicio2">\u2014</strong>.
          </div>

          {% else %}
          <div class="empty-state" style="padding:var(--s12)">
            <i class="fa-solid fa-user-plus empty-state__icon"></i>
            <h3>No hay trabajadores registrados</h3>
            <p>Registra trabajadores primero.</p>
            <a href="{{ url_for('create_worker') }}" class="button button--primary">
              Registrar trabajador
            </a>
          </div>
          {% endif %}
        </div>

        <div class="form-actions">
          <button type="submit" class="button button--primary"
                  id="btnSubmitLote" disabled>
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
let activeCargo = 'todos';
let searchTerm  = '';

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
  updateResumen();
}

function updateCounter() {
  const n = selectedIds.size;
  document.getElementById('selCounter').textContent =
    n + ' seleccionado' + (n !== 1 ? 's' : '');
  document.getElementById('btnSubmitLote').disabled = n === 0;
}

function updateHiddenInputs() {
  const c = document.getElementById('hiddenWorkerInputs');
  c.innerHTML = '';
  selectedIds.forEach(id => {
    const inp = document.createElement('input');
    inp.type = 'hidden'; inp.name = 'worker_ids'; inp.value = id;
    c.appendChild(inp);
  });
}

function updateResumen() {
  const n   = selectedIds.size;
  const res = document.getElementById('selResumen');
  if (!res) return;
  if (n === 0) { res.style.display = 'none'; return; }
  const ini = parseInt(document.getElementById('serial_inicio').value) || 1;
  res.style.display = 'block';
  document.getElementById('numRecibos').textContent  = n;
  document.getElementById('serialInicio2').textContent = ini;
  document.getElementById('serialRange').textContent   =
    n === 1 ? ini : ini + ' \u2013 ' + (ini + n - 1);
}

document.getElementById('serial_inicio').addEventListener('input', updateResumen);

document.getElementById('cargoFilters').addEventListener('click', function(e) {
  const btn = e.target.closest('.cargo-filter-btn');
  if (!btn) return;
  document.querySelectorAll('.cargo-filter-btn').forEach(b => b.classList.remove('is-active'));
  btn.classList.add('is-active');
  activeCargo = btn.dataset.cargo;
  applyFilters();
});

function filterWorkers() {
  searchTerm = document.getElementById('workerSearch').value.toLowerCase();
  applyFilters();
}

function applyFilters() {
  document.querySelectorAll('.worker-card-sel').forEach(card => {
    const cargoOk  = activeCargo === 'todos' || card.dataset.cargo === activeCargo;
    const searchOk = !searchTerm || card.dataset.nombre.includes(searchTerm);
    card.style.display = (cargoOk && searchOk) ? '' : 'none';
  });
}

// Calculadora lote
function parseCOP(s) { return parseFloat((s||'0').replace(/\./g,'').replace(',','.')) || 0; }
function formatCOP(n) { return Math.round(n).toLocaleString('es-CO'); }

function calcLote() {
  const dias = parseInt(document.getElementById('lc_dias').value) || 0;
  const vdia = parseCOP(document.getElementById('lc_vdia').value);
  const res  = dias * vdia;
  document.getElementById('lc_resultado').value = res > 0 ? '$ ' + formatCOP(res) : '';
}

function aplicarLoteCalc() {
  const dias = parseInt(document.getElementById('lc_dias').value) || 0;
  const vdia = parseCOP(document.getElementById('lc_vdia').value);
  const res  = dias * vdia;
  if (res > 0) {
    document.getElementById('valor_por_trabajador').value = formatCOP(res);
  }
}
</script>
{% endblock %}
""")

# ═══════════════════════════════════════════════════════════════
#  RECIBOS / DETALLE
# ═══════════════════════════════════════════════════════════════
write_file(os.path.join(BASE, 'templates', 'recibos', 'detalle.html'), """\
{% extends "base.html" %}
{% block title %}Recibo #{{ recibo.serial }} | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-file-invoice"></i></div>
    <div>
      <h1 class="page-hero__title">Recibo #{{ recibo.serial }}</h1>
      <p class="page-hero__sub">
        {{ recibo.fecha.strftime('%d/%m/%Y') if recibo.fecha else 'Sin fecha' }}
        &nbsp;&middot;&nbsp; {{ recibo.proveedor }}
      </p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('lista_recibos') }}" class="button button--ghost">
        <i class="fa-solid fa-arrow-left"></i> Volver
      </a>
      <button type="button" class="button button--ghost" onclick="window.print()">
        <i class="fa-solid fa-print"></i> Imprimir
      </button>
    </div>
  </div>
</div>

<section class="section">
  <div class="container" style="max-width:700px;">

    <!-- Tarjeta de recibo -->
    <div class="recibo-card print-area">
      <div class="recibo-card__header">
        <div class="recibo-card__logo">
          <i class="fa-solid fa-wheat-awn"></i>
        </div>
        <div class="recibo-card__empresa">
          <span class="recibo-card__empresa-nombre">Arrocera El Mang\u00f3n</span>
          <span class="recibo-card__empresa-sub">Contabilidad Interna</span>
        </div>
        <div class="recibo-card__serial">
          <span class="recibo-card__serial-label">RECIBO</span>
          <span class="recibo-card__serial-num">#{{ recibo.serial }}</span>
        </div>
      </div>

      <dl class="recibo-dl">
        <div class="recibo-dl__row">
          <dt>Fecha</dt>
          <dd>{{ recibo.fecha.strftime('%d/%m/%Y') if recibo.fecha else '\u2014' }}</dd>
        </div>
        <div class="recibo-dl__row">
          <dt>Proveedor</dt>
          <dd><strong>{{ recibo.proveedor }}</strong></dd>
        </div>
        <div class="recibo-dl__row">
          <dt>NIT / C\u00e9dula</dt>
          <dd>{{ recibo.nit or '\u2014' }}</dd>
        </div>
        <div class="recibo-dl__row">
          <dt>Direcci\u00f3n</dt>
          <dd>{{ recibo.direccion or '\u2014' }}</dd>
        </div>
        <div class="recibo-dl__row">
          <dt>Tel\u00e9fono</dt>
          <dd>{{ recibo.telefono or '\u2014' }}</dd>
        </div>
        <div class="recibo-dl__row">
          <dt>Ciudad</dt>
          <dd>{{ recibo.ciudad or '\u2014' }}</dd>
        </div>
        <div class="recibo-dl__row recibo-dl__row--full">
          <dt>Concepto</dt>
          <dd>{{ recibo.concepto or '\u2014' }}</dd>
        </div>
        <div class="recibo-dl__row">
          <dt>Valor operaci\u00f3n</dt>
          <dd class="valor-cell">
            {% if recibo.valor_operacion %}
              $ {{ "{:,.0f}".format(recibo.valor_operacion).replace(",",".") }}
            {% else %}\u2014{% endif %}
          </dd>
        </div>
        <div class="recibo-dl__row recibo-dl__row--highlight">
          <dt>Neto a pagar</dt>
          <dd class="valor-cell">
            {% if recibo.neto_a_pagar %}
              <strong>$ {{ "{:,.0f}".format(recibo.neto_a_pagar).replace(",",".") }}</strong>
            {% else %}\u2014{% endif %}
          </dd>
        </div>
      </dl>

      <div class="recibo-card__footer no-print">
        <div class="recibo-firma">
          <div class="recibo-firma__linea"></div>
          <span>Firma del trabajador</span>
        </div>
        <div class="recibo-firma">
          <div class="recibo-firma__linea"></div>
          <span>Firma del empleador</span>
        </div>
      </div>
    </div>

    <!-- Acciones -->
    <div class="form-actions no-print" style="margin-top:1.5rem">
      <a href="{{ url_for('lista_recibos') }}" class="button button--ghost-dark">
        <i class="fa-solid fa-arrow-left"></i> Volver a la lista
      </a>
      <form method="POST"
            action="{{ url_for('eliminar_recibo', serial=recibo.serial) }}"
            onsubmit="return confirm('\\u00bfEliminar el recibo #{{ recibo.serial }}? Esta acci\\u00f3n no se puede deshacer.')"
            style="margin:0">
        <button type="submit" class="button button--danger">
          <i class="fa-solid fa-trash"></i> Eliminar recibo
        </button>
      </form>
    </div>

  </div>
</section>
{% endblock %}
""")

# ═══════════════════════════════════════════════════════════════
#  REPORTES / INDEX
# ═══════════════════════════════════════════════════════════════
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
      <p class="page-hero__sub">Control financiero de la arrocera &middot; {{ total_ha }} hect\u00e1reas</p>
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
        <span class="stat-card__value">
          {% if pct_produccion >= 100 and pct_gasto <= 90 %}\u2705 Rentable
          {% elif pct_gasto > 90 %}\ud83d\udd34 Riesgo
          {% else %}\u26a0\ufe0f En curso{% endif %}
        </span>
        <span class="stat-card__sub">Producci\u00f3n: {{ pct_produccion }}%</span>
      </div>
    </div>

    <!-- Gauge gastos -->
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
             style="width:{{ [pct_gasto,100]|min }}%">{{ pct_gasto }}%</div>
      </div>
      <p class="gauge-footnote">
        Presupuesto m\u00e1ximo: $\u00a0{{ "{:,.0f}".format(max_gasto_ha).replace(",",".") }}
        &times; {{ total_ha }}\u00a0ha = $\u00a0{{ "{:,.0f}".format(max_gasto).replace(",",".") }}
      </p>
    </div>

    <!-- Gauge producci\u00f3n -->
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
             style="width:{{ [pct_produccion,100]|min }}%">{{ pct_produccion }}%</div>
      </div>
      <p class="gauge-footnote">
        M\u00ednimo: {{ min_cargas }} cargas (100 bultos/ha &times; {{ total_ha }}\u00a0ha).
        Cada carga = 62.5\u00a0kg.
      </p>
    </div>

    <!-- Gr\u00e1ficas -->
    <div class="charts-row">
      <div class="chart-card">
        <h3 class="chart-card__title"><i class="fa-solid fa-chart-bar"></i> Gastos por mes</h3>
        <div class="chart-canvas-wrap"><canvas id="chartMes"></canvas></div>
      </div>
      <div class="chart-card">
        <h3 class="chart-card__title"><i class="fa-solid fa-users"></i> Top trabajadores</h3>
        <div class="chart-canvas-wrap"><canvas id="chartTrabajadores"></canvas></div>
      </div>
    </div>

    <!-- Accesos r\u00e1pidos -->
    <div class="grid-3" style="margin-top:var(--s6)">
      <a href="{{ url_for('reporte_semana') }}" class="card" style="text-decoration:none">
        <div class="card__icon"><i class="fa-solid fa-calendar-week"></i></div>
        <h3>Reporte semanal</h3>
        <p>Ver todos los pagos de la semana actual.</p>
      </a>
      <a href="{{ url_for('exportar_txt') }}" class="card" style="text-decoration:none">
        <div class="card__icon"><i class="fa-solid fa-file-export"></i></div>
        <h3>Exportar TXT</h3>
        <p>Descargar todos los recibos en formato texto.</p>
      </a>
      <a href="{{ url_for('nueva_cosecha') }}" class="card" style="text-decoration:none">
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
const datosMes          = {{ por_mes | tojson }};
const datosTrabajadores = {{ por_trabajador | tojson }};

const GREEN  = '#2D6A4F';
const DARK   = '#1B4332';
const GREENS = ['#1B4332','#2D6A4F','#40916C','#52B788','#74C69D','#95D5B2','#B7E4C7','#D8F3DC'];

const ctxMes = document.getElementById('chartMes');
if (ctxMes && datosMes.length > 0) {
  new Chart(ctxMes, {
    type: 'bar',
    data: {
      labels: datosMes.map(d => d.mes),
      datasets: [{
        label: 'Gasto (COP)',
        data: datosMes.map(d => d.total),
        backgroundColor: GREEN, borderColor: DARK,
        borderWidth: 1, borderRadius: 6,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { ticks: { callback: v => '$ ' + (v/1000000).toFixed(1) + 'M' } } }
    }
  });
} else if (ctxMes) {
  ctxMes.parentElement.innerHTML =
    '<p style="text-align:center;color:var(--txt-muted);padding:2rem">Sin datos de gastos a\u00fan.</p>';
}

const ctxTrab = document.getElementById('chartTrabajadores');
if (ctxTrab && datosTrabajadores.length > 0) {
  new Chart(ctxTrab, {
    type: 'bar',
    data: {
      labels: datosTrabajadores.map(d => d.proveedor.split(' ')[0]),
      datasets: [{
        label: 'Total (COP)',
        data: datosTrabajadores.map(d => d.total),
        backgroundColor: GREENS,
        borderWidth: 0, borderRadius: 6,
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
  ctxTrab.parentElement.innerHTML =
    '<p style="text-align:center;color:var(--txt-muted);padding:2rem">Sin datos a\u00fan.</p>';
}
</script>
{% endblock %}
""")

# ═══════════════════════════════════════════════════════════════
#  REPORTES / SEMANA
# ═══════════════════════════════════════════════════════════════
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
        {% if semana_inicio and semana_fin %}
          {{ semana_inicio.strftime('%d/%m/%Y') }} al {{ semana_fin.strftime('%d/%m/%Y') }}
        {% else %}Selecciona una fecha{% endif %}
      </p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('reportes') }}" class="button button--ghost">
        <i class="fa-solid fa-chart-line"></i> Dashboard
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container">

    <form method="GET" class="form-card" style="max-width:480px;margin-bottom:var(--s6)">
      <div class="form-group">
        <label for="fecha">Semana que contiene esta fecha</label>
        <input type="date" id="fecha" name="fecha" value="{{ fecha_sel or '' }}">
      </div>
      <div class="form-actions" style="margin-top:0">
        <button type="submit" class="button button--primary">
          <i class="fa-solid fa-search"></i> Ver semana
        </button>
      </div>
    </form>

    {% if recibos %}
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Serial</th><th>Fecha</th><th>Proveedor</th>
            <th>Concepto</th><th>Neto a pagar</th>
          </tr>
        </thead>
        <tbody>
          {% for r in recibos %}
          <tr style="cursor:pointer"
              onclick="location.href='{{ url_for('detalle_recibo', serial=r.serial) }}'">
            <td><span class="serial-badge">{{ r.serial }}</span></td>
            <td class="txt-muted">{{ r.fecha.strftime('%d/%m/%Y') if r.fecha else '\u2014' }}</td>
            <td><strong>{{ r.proveedor }}</strong></td>
            <td class="concepto-cell small">{{ r.concepto }}</td>
            <td class="valor-cell">
              {% if r.neto_a_pagar %}
                <strong>$ {{ "{:,.0f}".format(r.neto_a_pagar).replace(",",".") }}</strong>
              {% else %}\u2014{% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
        <tfoot>
          <tr class="table-foot">
            <td colspan="4" style="text-align:right;font-weight:600">Total semana:</td>
            <td class="valor-cell">
              <strong>$ {{ "{:,.0f}".format(recibos | sum(attribute='neto_a_pagar')).replace(",",".") }}</strong>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
    {% elif fecha_sel %}
    <div class="empty-state">
      <i class="fa-solid fa-calendar-xmark empty-state__icon"></i>
      <h3>Sin recibos esa semana</h3>
      <p>No hay pagos registrados para la semana seleccionada.</p>
    </div>
    {% endif %}

  </div>
</section>
{% endblock %}
""")

# ═══════════════════════════════════════════════════════════════
#  PRODUCCION / INDEX
# ═══════════════════════════════════════════════════════════════
write_file(os.path.join(BASE, 'templates', 'produccion', 'index.html'), """\
{% extends "base.html" %}
{% block title %}Producci\u00f3n | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-wheat-awn"></i></div>
    <div>
      <h1 class="page-hero__title">Producci\u00f3n / Cosechas</h1>
      <p class="page-hero__sub">
        {{ total_cargas }} cargas cosechadas de {{ min_cargas }} requeridas ({{ pct_produccion }}%)
      </p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('nueva_cosecha') }}" class="button button--primary">
        <i class="fa-solid fa-plus"></i> Registrar cosecha
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container">

    <div class="gauge-section" style="margin-bottom:var(--s6)">
      <div class="gauge-header">
        <span class="gauge-title"><i class="fa-solid fa-wheat-awn"></i> Avance de producci\u00f3n</span>
        <span class="gauge-amount">
          <strong>{{ total_cargas }} cargas</strong> / {{ min_cargas }} m\u00ednimo
        </span>
      </div>
      <div class="gauge-bar-wrap">
        <div class="gauge-bar {% if pct_produccion >= 100 %}gauge-bar--green{% elif pct_produccion >= 60 %}gauge-bar--yellow{% else %}gauge-bar--red{% endif %}"
             style="width:{{ [pct_produccion,100]|min }}%">{{ pct_produccion }}%</div>
      </div>
    </div>

    {% if cosechas %}
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Fecha</th><th>Lote</th>
            <th>Cargas</th><th>Kg totales</th><th>Notas</th>
          </tr>
        </thead>
        <tbody>
          {% for c in cosechas %}
          <tr>
            <td class="txt-muted">{{ c.fecha.strftime('%d/%m/%Y') if c.fecha else '\u2014' }}</td>
            <td>{{ c.lote or '\u2014' }}</td>
            <td><strong>{{ c.cargas }}</strong></td>
            <td class="txt-muted">{{ "{:,.1f}".format(c.kg_totales).replace(",",".") if c.kg_totales else '\u2014' }}</td>
            <td class="small txt-muted">{{ c.notas or '' }}</td>
          </tr>
          {% endfor %}
        </tbody>
        <tfoot>
          <tr class="table-foot">
            <td colspan="2" style="text-align:right;font-weight:600">Totales:</td>
            <td><strong>{{ total_cargas }}</strong></td>
            <td class="txt-muted">{{ "{:,.1f}".format(cosechas | sum(attribute='kg_totales')).replace(",",".") if cosechas else 0 }} kg</td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>
    {% else %}
    <div class="empty-state">
      <i class="fa-solid fa-seedling empty-state__icon"></i>
      <h3>Sin cosechas registradas</h3>
      <p>Registra la primera cosecha para hacer seguimiento de producci\u00f3n.</p>
      <a href="{{ url_for('nueva_cosecha') }}" class="button button--primary">
        <i class="fa-solid fa-plus"></i> Registrar cosecha
      </a>
    </div>
    {% endif %}

  </div>
</section>
{% endblock %}
""")

# ═══════════════════════════════════════════════════════════════
#  PRODUCCION / NUEVA
# ═══════════════════════════════════════════════════════════════
write_file(os.path.join(BASE, 'templates', 'produccion', 'nueva.html'), """\
{% extends "base.html" %}
{% block title %}Nueva Cosecha | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-seedling"></i></div>
    <div>
      <h1 class="page-hero__title">Registrar Cosecha</h1>
      <p class="page-hero__sub">Ingresa los bultos / cargas recolectados.</p>
    </div>
    <div class="page-hero__actions">
      <a href="{{ url_for('lista_produccion') }}" class="button button--ghost">
        <i class="fa-solid fa-wheat-awn"></i> Ver producci\u00f3n
      </a>
    </div>
  </div>
</div>

<section class="section">
  <div class="container" style="max-width:600px">

    {% if success %}
    <div class="alert alert--success"><i class="fa-solid fa-circle-check"></i> {{ success }}</div>
    {% endif %}
    {% if error %}
    <div class="alert alert--danger"><i class="fa-solid fa-circle-xmark"></i> {{ error }}</div>
    {% endif %}

    <form method="POST" class="form-card">
      <div class="form-section">
        <div class="form-grid form-grid--2">
          <div class="form-group">
            <label for="fecha">Fecha de cosecha <span class="req-star">*</span></label>
            <input type="date" id="fecha" name="fecha" required
                   value="{{ today }}">
          </div>
          <div class="form-group">
            <label for="lote">Lote / Parcela</label>
            <input type="text" id="lote" name="lote" placeholder="Ej: El Mang\u00f3n">
          </div>
          <div class="form-group">
            <label for="cargas">Cargas (bultos) <span class="req-star">*</span></label>
            <input type="number" id="cargas" name="cargas" min="1" required
                   oninput="calcKg()">
            <p class="field-hint">1 carga = 62.5 kg</p>
          </div>
          <div class="form-group">
            <label for="kg_totales">Kg totales (calculado)</label>
            <input type="text" id="kg_totales" name="kg_totales" readonly
                   style="background:var(--clr-50)">
          </div>
          <div class="form-group" style="grid-column:1/-1">
            <label for="notas">Notas</label>
            <textarea id="notas" name="notas" rows="2"
                      placeholder="Observaciones opcionales\u2026"></textarea>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="button button--primary">
          <i class="fa-solid fa-floppy-disk"></i> Guardar cosecha
        </button>
        <a href="{{ url_for('lista_produccion') }}" class="button button--ghost-dark">Cancelar</a>
      </div>
    </form>

  </div>
</section>
{% endblock %}

{% block scripts %}
<script>
function calcKg() {
  const c = parseFloat(document.getElementById('cargas').value) || 0;
  document.getElementById('kg_totales').value = c > 0 ? (c * 62.5).toFixed(1) : '';
}
</script>
{% endblock %}
""")

# ═══════════════════════════════════════════════════════════════
#  CONFIG / INDEX
# ═══════════════════════════════════════════════════════════════
write_file(os.path.join(BASE, 'templates', 'config', 'index.html'), """\
{% extends "base.html" %}
{% block title %}Configuraci\u00f3n | Contabilidad Arroceras{% endblock %}

{% block content %}
<div class="page-hero">
  <div class="container page-hero__inner">
    <div class="page-hero__icon"><i class="fa-solid fa-gear"></i></div>
    <div>
      <h1 class="page-hero__title">Configuraci\u00f3n</h1>
      <p class="page-hero__sub">Par\u00e1metros del sistema</p>
    </div>
  </div>
</div>

<section class="section">
  <div class="container" style="max-width:580px">

    {% if success %}
    <div class="alert alert--success"><i class="fa-solid fa-circle-check"></i> {{ success }}</div>
    {% endif %}

    <div class="form-card">
      <div class="form-section">
        <h3 class="form-section__title"><i class="fa-solid fa-hashtag"></i> Seriales</h3>

        <div class="config-info-box">
          <i class="fa-solid fa-circle-info"></i>
          <div>
            <strong>Total de recibos:</strong> {{ total_recibos }}<br>
            <strong>Serial inicial configurado:</strong> {{ config.get('serial_inicial', '1') }}
          </div>
        </div>

        <form method="POST">
          <div class="form-group" style="max-width:280px;margin-top:1.5rem">
            <label for="serial_inicial">Serial inicial para nuevos recibos</label>
            <input type="number" id="serial_inicial" name="serial_inicial"
                   value="{{ config.get('serial_inicial', '1') }}" min="1" required>
            <p class="field-hint">
              Define desde qu\u00e9 n\u00famero empezar\u00e1n los seriales cuando no haya recibos previos.
              {% if total_recibos > 0 %}
              <strong>Nota:</strong> ya hay {{ total_recibos }} recibo(s); el pr\u00f3ximo
              serial se calcula autom\u00e1ticamente.
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
print('setup_templates.py completado!')
print('='*60)
print('\nDirectorios y templates creados:')
print('  templates/recibos/  (lista, nuevo, lote, detalle)')
print('  templates/reportes/ (index, semana)')
print('  templates/produccion/ (index, nueva)')
print('  templates/config/   (index)')
print('  data/trabajadores.json')
print('\nSiguiente paso:')
print('  python app.py   -> http://127.0.0.1:5000')
