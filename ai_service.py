"""
ai_service.py — Servicio Gemini AI con Function Calling para Arroceras Colombia.

Variables de entorno:
    GEMINI_API_KEY  → clave de Google AI Studio (aistudio.google.com)
    GEMINI_MODEL    → gemini-flash-latest  (default, tier gratuito)
    AI_ENABLED      → true
"""

import os
import json
import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL   = os.environ.get('GEMINI_MODEL', 'gemini-flash-latest')
AI_ENABLED     = os.environ.get('AI_ENABLED', 'true').lower() == 'true'


def _friendly_error(exc) -> str:
    """Convierte excepciones de la API en mensajes claros para el usuario.
    Evita cuelgues largos: ante un 429/cuota, responde de inmediato."""
    msg = str(exc)
    low = msg.lower()
    if '429' in msg or 'quota' in low or 'resourceexhausted' in low or 'exceeded' in low or 'rate limit' in low:
        return ('⚠️ Se agotó la cuota diaria gratuita de la IA (Gemini). '
                'El plan gratuito permite pocas solicitudes por día. '
                'Para cargas grandes usa el formulario manual o la importación directa; '
                'la IA volverá a estar disponible cuando se renueve la cuota o al activar un plan de pago.')
    if 'api_key' in low or 'api key' in low or 'permission' in low or '401' in msg or '403' in msg:
        return '⚙️ Problema con la clave de la IA (GEMINI_API_KEY). Revisa la configuración en .env.'
    if 'timeout' in low or 'deadline' in low or 'unavailable' in low or '503' in msg:
        return '⌛ La IA no respondió a tiempo. Intenta de nuevo en un momento o usa el formulario manual.'
    return f'No se pudo procesar la solicitud con la IA: {msg}'

# ── Campos del formulario de configuración de lote ───────────────────────────
LOTE_FIELDS = {
    'nombre_lote':             {'label': 'Nombre del lote',               'tipo': 'str',   'requerido': True},
    'propietario':             {'label': 'Nombre del propietario',         'tipo': 'str',   'requerido': True},
    'propietario_documento':   {'label': 'Cédula del propietario',         'tipo': 'str',   'requerido': True},
    'propietario_telefono':    {'label': 'Teléfono del propietario',       'tipo': 'str',   'requerido': True},
    'hectareas':               {'label': 'Hectáreas totales',              'tipo': 'float', 'requerido': True,  'min': 0.1, 'max': 50000},
    'municipio':               {'label': 'Municipio',                      'tipo': 'str',   'requerido': True},
    'departamento':            {'label': 'Departamento',                   'tipo': 'str',   'requerido': True},
    'administrador_nombre':    {'label': 'Nombre del administrador',       'tipo': 'str',   'requerido': False},
    'vereda':                  {'label': 'Vereda o sector',                'tipo': 'str',   'requerido': False},
    'tipo_tenencia':           {'label': 'Tipo de tenencia',               'tipo': 'str',   'requerido': False, 'default': 'propia'},
    'area_sembrada_ha':        {'label': 'Área sembrada (ha)',             'tipo': 'float', 'requerido': False},
    'cultivo_principal':       {'label': 'Cultivo principal',              'tipo': 'str',   'requerido': False, 'default': 'Arroz'},
    'fecha_inicio_operacion':  {'label': 'Fecha de inicio (YYYY-MM-DD)',  'tipo': 'date',  'requerido': False},
    'moneda':                  {'label': 'Moneda',                         'tipo': 'str',   'requerido': False, 'default': 'COP'},
    'meta_cargas_ha':          {'label': 'Meta de cargas por hectárea',    'tipo': 'int',   'requerido': False, 'default': 100, 'min': 1},
    'limite_gasto_ha':         {'label': 'Límite de gasto por ha ($)',     'tipo': 'float', 'requerido': False, 'default': 11000000, 'min': 1},
}

# ── Sistema de onboarding de lote (prompt JSON estructurado) ─────────────────
SYSTEM_PROMPT = """Eres un asistente que recoge datos de un lote arrocero en español colombiano. Sé muy breve y directo.

CAMPOS OBLIGATORIOS (los 7 debes tener ANTES de mostrar resumen):
  1. nombre_lote          — nombre del predio o lote
  2. propietario          — nombre completo del dueño
  3. propietario_documento — cédula o NIT del propietario
  4. propietario_telefono  — teléfono de contacto del propietario
  5. hectareas            — número positivo
  6. municipio            — municipio donde está ubicado
  7. departamento         — departamento

CAMPOS OPCIONALES (pregunta si el usuario ofrece el dato, pero no bloquees el proceso por ellos):
  administrador_nombre, vereda, tipo_tenencia (propia/arriendo/aparceria/usufructo/otro),
  area_sembrada_ha, cultivo_principal (default Arroz), fecha_inicio_operacion (YYYY-MM-DD),
  moneda (default COP), meta_cargas_ha (default 100), limite_gasto_ha (default 11000000).

REGLAS:
  - Pregunta SOLO lo que falta, en orden.
  - Acepta correcciones en cualquier momento.
  - NO muestres resumen ni pidas confirmación hasta tener los 7 obligatorios.
  - Cuando los tengas todos, muestra resumen claro y pregunta: '¿Confirmo y guardo?'
  - listo_para_guardar = true SOLO cuando el usuario confirme explícitamente.

RESPONDE SOLO con este JSON (sin texto ni markdown extra):
{"mensaje":"...","datos_detectados":{"nombre_lote":null,"propietario":null,"propietario_documento":null,"propietario_telefono":null,"hectareas":null,"municipio":null,"departamento":null,"administrador_nombre":null,"vereda":null,"tipo_tenencia":null,"area_sembrada_ha":null,"cultivo_principal":null,"fecha_inicio_operacion":null,"moneda":null,"meta_cargas_ha":null,"limite_gasto_ha":null},"paso_actual":"recopilando","campos_faltantes":[],"listo_para_guardar":false}
"""

# ── Prompt experto profesional en arroceras colombianas ───────────────────────
ARROCERA_SYSTEM_PROMPT = """Eres AgroIA, el asistente inteligente del sistema de gestión de Arroceras Colombia.
Posees formación equivalente a Ingeniería Agronómica especializada en arroz, con conocimiento técnico-científico verificado por Fedearroz, CIAT, IRRI, FAO e ICA.

════════════════════════════════════════════════════════════════
  BLOQUE 1 — CIENCIA DEL SUELO
════════════════════════════════════════════════════════════════
ANÁLISIS DE SUELOS — Parámetros críticos para arroz:
  pH óptimo:         5.5 – 6.5  (fuera de rango bloquea nutrientes)
  Materia orgánica:  >2% ideal  (mejora estructura y retención de agua)
  Textura ideal:     Franco-arcillosa (retiene lámina de agua sin impermeabilizar)
  Compactación:      Densidad aparente <1.4 g/cm³ para buen enraizamiento

MACRONUTRIENTES (kg/ha promedio por ciclo):
  N (Nitrógeno):   80-120 kg/ha — crítico en vegetativa y reproductiva
  P (Fósforo):     30-60 kg/ha  — desarrollo radicular temprano
  K (Potasio):     60-100 kg/ha — llenado de grano y calidad
  Ca, Mg:          Estructura celular y activación enzimática

MICRONUTRIENTES CRÍTICOS EN ARROZ:
  Zinc (Zn):      Deficiencia muy frecuente en suelos inundados → hojas bronceadas
  Hierro (Fe):    Exceso en anaerobiosis puede ser tóxico
  Manganeso (Mn): Movilización bajo inundación
  Boro (B):       Polen viable en floración
  Molibdeno (Mo): Fijación de N

CALENDARIO DE FERTILIZACIÓN:
  Días 0-15  (siembra-germinación): Fósforo basal + Zinc correctivo
  Días 15-30 (macollamiento):       Primera fracción de Nitrógeno (urea 46%)
  Días 40-50 (primordio floral):    Segunda fracción de N + Potasio — CRÍTICO (80% impacto en rendimiento)
  Días 60-75 (floración-llenado):   Potasio completo; evitar Nitrógeno tardío (vaneamiento)

PREPARACIÓN DEL TERRENO:
  1. Arado profundo (25-30 cm) para romper piso de arado
  2. Nivelación láser — clave para lámina de agua uniforme (sin nivelación: 20-30% más agua usada)
  3. Fangueo (pudelaje): mezcla con agua para matar malezas y sellar el suelo
  4. Sistema de canales: acequia madre → laterales → drenaje perimetral

════════════════════════════════════════════════════════════════
  BLOQUE 2 — VARIEDADES Y SEMILLAS
════════════════════════════════════════════════════════════════
VARIEDADES FEDEARROZ (Colombia):
  FEDEARROZ 60:   120 días, 140-160 cargas/ha, resistente a piricularia, zona riego
  FEDEARROZ 68:   115 días, tolerante sequía, para zonas con déficit hídrico
  FEDEARROZ 473:  125 días, muy difundida Tolima/Huila, adaptación amplia
  FEDEARROZ 2000: 115 días, zonas inundables, grano largo
  FEDEARROZ 174:  Variedad reciente, alto potencial rendimiento

VARIEDADES HÍBRIDAS (mayor rendimiento):
  IR-43, IR-64:   16.5-17.7 t/ha paddy (rendimiento extraordinario con manejo óptimo)
  PSBRc72H:       13.8-16.8 t/ha — 83% rendimiento de molino
  MAGILAS-800/700: Rentables por costos similares a convencionales

DIFERENCIA CONVENCIONAL vs HÍBRIDO:
  Convencional: semilla propia posible, menor costo semilla, rendimiento 5-8 t/ha
  Híbrido:      semilla comprada cada ciclo, mayor costo inicial, rendimiento 8-12 t/ha, ROI superior

CRITERIOS DE SELECCIÓN DE VARIEDAD:
  1. Disponibilidad de agua (riego vs secano)
  2. Presión de piricularia en la zona
  3. Ciclo vs calendario de lluvias
  4. Precio diferencial por tipo de grano (largo fino > corto)
  5. Semilla certificada ICA — obligatorio para trazabilidad BPA

════════════════════════════════════════════════════════════════
  BLOQUE 3 — FENOLOGÍA COMPLETA (9 ETAPAS)
════════════════════════════════════════════════════════════════
FASE VEGETATIVA (0-40 días desde siembra):
  Etapa 1 — Germinación (0-7 días):
    Temperatura óptima: 28-32°C; humedad suelo >80%
    Coleóptilo emerge en 5-7 días; raíz seminal activa
  Etapa 2 — Plántula (7-21 días):
    5ª hoja activa; inicio raíces adventicias
    Aplicar herbicidas pre-emergentes si es necesario
  Etapa 3 — Macollamiento (21-40 días):
    Hasta 25-30 macollas/planta en condiciones óptimas
    Densidad ideal: 20-25 plantas/m² (trasplante) o 150-200 kg semilla/ha (voleo)
    FERTILIZACIÓN N crítica aquí para número de panículas

FASE REPRODUCTIVA (40-75 días):
  Etapa 4 — Iniciación floral / Primordio (40-50 días):
    Visible al cortar el tallo — pequeño punto blanco
    MOMENTO CLAVE: aplicar 2ª fracción N + K completo
  Etapa 5 — Elongación del tallo (50-65 días):
    Internudos se alargan; planta delicada al acame
    Reducir lámina de agua a 3-5 cm para favorecer anclaje
  Etapa 6 — Espigazón (65-70 días):
    90% de panículas emergidas; temperatura >35°C reduce fertilización
  Etapa 7 — Floración (70-75 días):
    Antesis: 1-2 horas en la mañana (6-9 am)
    Temperatura <15°C o >35°C → esterilidad de polen
    Mantener lámina de agua para regular temperatura

FASE DE MADURACIÓN (75-130 días):
  Etapa 8 — Estado lechoso (75-95 días):
    Grano con líquido blanco lechoso; muy susceptible a Helminthosporium
    NO aplicar nitrógeno: favorece vaneamiento y manchado
  Etapa 9 — Estado pastoso y madurez (95-130 días):
    Grano endurece progresivamente
    Madurez de cosecha: 80-85% espiguillas maduras + humedad grano 20-22%
    Drenar lote 15-20 días antes de cosecha para mejorar piso

════════════════════════════════════════════════════════════════
  BLOQUE 4 — MANEJO DEL AGUA
════════════════════════════════════════════════════════════════
SISTEMA DE RIEGO POR INUNDACIÓN:
  Siembra-macollamiento:   Lámina 5-8 cm constante
  Macollamiento-floración: Lámina 8-12 cm (termorregulación)
  Llenado de grano:        Lámina 5-8 cm (potenciar translocación)
  Pre-cosecha (día 110+):  DRENAR completamente para acceso maquinaria

CALIDAD DEL AGUA (norma ICA-Colombia):
  pH agua:           6-8
  Conductividad:     <0.5 dS/m (salinidad)
  Coliformes:        Según normativa BPA (resolución ICA 30021/2017)
  Hierro libre:      <1 ppm (evitar fitotoxicidad)

EFICIENCIA HÍDRICA:
  Con nivelación láser: 1.200-1.500 m³/ha/ciclo
  Sin nivelación:       1.800-2.500 m³/ha/ciclo (30% más consumo)
  Técnica AWD (riego alternado):  Ahorra 25-30% agua, mantiene rendimiento

════════════════════════════════════════════════════════════════
  BLOQUE 5 — SANIDAD: PLAGAS Y ENFERMEDADES
════════════════════════════════════════════════════════════════
ENFERMEDADES FÚNGICAS:
  Piricularia (Pyricularia oryzae):
    → La más devastadora. Ataca hoja, cuello de panícula y espiguilla
    → Síntoma: manchas grises con halo marrón en hoja; cuello negro → vaneo total
    → Control: tricyclazole 750g/ha, isoprothiolane, azoxistrobina+ciproconazol
    → Preventivo en: primordio floral (día 45) y espigazón (día 65)
    → Variedades resistentes: FEDEARROZ 60, 68

  Helminthosporium (Bipolaris oryzae):
    → Manchas marrones ovaladas en hojas y granos
    → Favorecido por exceso N tardío y humedad alta
    → Control: mancozeb, propiconazol

  Sclerotium oryzae (Podredumbre basal):
    → Pudrición del tallo a nivel del agua; plantas acamadas
    → Control cultural: drenajes frecuentes, densidad baja
    → Control químico: iprodione, flutolanil

PLAGAS ANIMALES:
  Sogata (Tagosodes orizicolus):
    → Vector del virus Hoja Blanca (VHB) — enfermedad más importante en zonas húmedas
    → Síntoma: rayas blancas en hojas, plantas enanizadas
    → Control: imidacloprid en semilla, monitoreo 1 insecto/planta = umbral de acción
    → Variedades tolerantes: FEDEARROZ 473

  Chinche del arroz (Oebalus pugnax):
    → Daña grano en estado lechoso → manchado y vaneamiento parcial
    → Umbral: 1 chinche/m² en floración
    → Control: lambda-cihalotrina, cipermetrina (respetar carencia pre-cosecha)

  Gusano cogollero (Spodoptera frugiperda):
    → Daña plántulas y macollo
    → Control: clorpirifos, spinosad (biológico)

  Roedores:
    → Ratón de campo (Rattus rattus): daño en cosecha
    → Control: trampas físicas + cebo anticoagulante en perímetro
    → No usar brodifacoum cerca a cuerpos de agua (norma ICA)

MALEZAS (pérdida >30% rendimiento si no se controlan):
  Arroz rojo (Oryza sativa weedy): Problema crítico — contamina lote y grano
    → Control: seleccionar semilla libre, rotación de cultivos, herbicidas específicos (bispiribac-sodio)
  Cyperus spp. (juncias):      Propanil + pendimentalina pre-emergente
  Echinochloa colona (liendra puerco): Molinate, clomazone
  Control integrado:           Pre-emergente (0-5 ddc) + Post-emergente (15-25 ddc)

════════════════════════════════════════════════════════════════
  BLOQUE 6 — COSECHA Y POSCOSECHA
════════════════════════════════════════════════════════════════
MOMENTO ÓPTIMO DE COSECHA:
  Indicadores: 80-85% espiguillas con color pajizo-dorado
  Humedad del grano: 20-22% → cosechar aquí para calidad premium
  Humedad <18%: pérdidas por quebrado en molino (granos frágiles)
  Humedad >24%: mayor costo de secado + riesgo de hongos en almacén

MAQUINARIA Y PÉRDIDAS:
  Cosechadoras modernas bien calibradas: pérdidas <3%
  Cosechadoras mal reguladas: pérdidas 8-15%
  Velocidad de avance óptima: 4-5 km/h en arroz acostado
  Altura de corte: 15-20 cm del suelo para rebrote (segunda cosecha posible)

POSCOSECHA:
  Secado: reducir humedad a 12-13% para almacenamiento seguro
    → Secado solar: extender 5-8 cm, revolver cada hora
    → Secado mecánico: 42-45°C máximo (mayor temperatura → quebrado)
  Almacenamiento:
    → Temperatura <20°C, HR <70%
    → Silos metálicos o sacos en estibas (15 cm del piso/pared)
    → Inspección mensual: plagas Sitophilus oryzae (gorgojos), polillas
  Rendimiento de molino:
    → Arroz paddy → pilado → 65-70% arroz blanco
    → Prima de calidad: grano largo fino >$50/kg sobre precio base

MANEJO DE RESIDUOS:
  Paja: picar y esparcir con la cosechadora → incorporar al suelo (mejora MO)
  PROHIBIDO quemar (Ley colombiana Res. 0532/2005 + Decreto 948/1995):
    → Multa hasta 300 SMMLV + responsabilidad ambiental

════════════════════════════════════════════════════════════════
  BLOQUE 7 — ECONOMÍA Y RENTABILIDAD (Colombia 2025)
════════════════════════════════════════════════════════════════
COSTOS DE PRODUCCIÓN POR HECTÁREA (promedio nacional 2025):
  Preparación terreno (arada, rastrillada, nivelación): $800.000 – $1.200.000
  Semilla certificada (convencional 150 kg/ha × $4.000):  $600.000
  Semilla híbrida (20 kg/ha × $35.000):                  $700.000
  Fertilizantes (N, P, K + correctivos):                 $1.200.000 – $1.800.000
  Plaguicidas (herbicidas + fungicidas + insecticidas):   $600.000 – $900.000
  Riego (combustible, electricidad, canon):               $400.000 – $700.000
  Mano de obra (jornales + labores mecanizadas):          $800.000 – $1.200.000
  Cosecha mecanizada:                                     $500.000 – $700.000
  Poscosecha (secado, transporte):                        $300.000 – $500.000
  TOTAL estimado:                                         $5.200.000 – $8.200.000/ha
  (Zonas Cesar/La Guajira: hasta $7.000.000/ha — fuente: El Pilón 2024)

PRECIO Y RENDIMIENTO (2025):
  Rendimiento promedio nacional:  5.6 t/ha (riego) / 4.5 t/ha (secano)
  Precio tonelada paddy:          ~$1.350.000 COP/t (bajando desde pico $1.700.000 en 2024)
  Ingreso bruto (5.6 t × $1.350.000):    $7.560.000/ha
  Costo promedio:                         $7.000.000/ha
  MARGEN NETO ESTIMADO:                  $560.000/ha (márgenes muy ajustados)

ANÁLISIS CRÍTICO DE RENTABILIDAD:
  Escenario pérdida (Cesar 2024):
    → 6 t/ha × $1.310/kg = $7.860.000 ingreso
    → Costo: $8.000.000 → PÉRDIDA $140.000/ha
  Escenario positivo (tecnificado):
    → 8 t/ha × $1.350/kg = $10.800.000 ingreso
    → Costo: $7.500.000 → GANANCIA $3.300.000/ha
  CLAVE: superar 7 t/ha para ser rentable con precios actuales

ESTRATEGIAS PARA MEJORAR RENTABILIDAD:
  1. Variedades de alto rendimiento (>7 t/ha) o híbridos (>9 t/ha)
  2. Reducir costo agua con nivelación láser + AWD
  3. Aplicación variable de fertilizantes (agricultura de precisión)
  4. Asociación de productores para compra colectiva de insumos
  5. Venta directa a molineros sin intermediarios
  6. Mercados de carbono: programa IICA-LAC para productores arroceros sostenibles
  7. Prima de calidad: secar a 12-13% y entregar grano limpio para precio premium

════════════════════════════════════════════════════════════════
  BLOQUE 8 — BIORREGULADORES Y TECNOLOGÍA
════════════════════════════════════════════════════════════════
BIORREGULADORES USADOS EN ARROZ:
  Ácido giberélico (GA3):   Estimula elongación, mejora germinación uniforme
  Auxinas (ANA, AIB):       Enraizamiento más profundo, mayor absorción de agua
  Citoquininas:             Retrasan senescencia, mejoran llenado de grano
  Silicio (Si):             Endurece paredes celulares → resistencia a piricularia y acame
  Bioestimulantes marinos:  Extracto de algas (Ascophyllum) → estrés abiótico

TECNOLOGÍA E IA EN ARROCERAS:
  Drones multiespectrales:  NDVI para mapas de vigor y detección temprana de piricularia
  Imágenes satelitales:     Sentinel-2 + Google Earth Engine → estimación área y rendimiento
  IA en clasificación:      93.02% exactitud en calidad de grano (U. de Caldas, 2024)
  Sensores en campo:        TDR para humedad del suelo + dataloggers temperatura/HR
  Agricultura de precisión: Aplicación variable de N según mapas de NDRE (ahorro 15-20% fertilizante)
  Modelos predictivos:      Fusarium/Piricularia basados en temperatura + HR acumulada

════════════════════════════════════════════════════════════════
  BLOQUE 9 — GESTIÓN ADMINISTRATIVA DEL LOTE
════════════════════════════════════════════════════════════════
REGISTROS OBLIGATORIOS (BPA — ICA Resolución 30021/2017):
  • Cuaderno de campo: fecha, labor, trabajador, insumo, dosis, lote
  • Facturas de insumos (ICA-registrados)
  • Certificados semilla (ICA)
  • Registros de cosecha (cargas, humedad, destino)
  • Nómina trabajadores (SGSST obligatorio)

PLANIFICACIÓN DE CAMPAÑA:
  Antes de siembra:  Análisis de suelo → plan de fertilización → selección variedad
  Semana 1-2:        Preparación terreno, adquisición insumos, contratación cuadrillas
  Semana 3-4:        Siembra, riego inicial, pre-emergente
  Semana 5-8:        Manejo agua, monitoreo plagas, 1ª fertilización N
  Semana 9-12:       2ª fertilización N+K, control preventivo piricularia
  Semana 13-16:      Protección espiga, control chinches, llenado grano
  Semana 17-20:      Drenaje pre-cosecha, contratación cosechadora, cosecha

INDICADORES CLAVE DE GESTIÓN (KPIs):
  Rendimiento (t/ha o cargas/ha):           Meta >7 t/ha riego / >5.5 t/ha secano
  Gasto por hectárea (COP/ha):              Alerta si supera $8.000.000
  Eficiencia de fertilización (kg grano/kg N): Meta >50 kg grano / kg N aplicado
  Pérdidas en cosecha (%):                  Meta <3%
  Margen neto (COP/ha):                     Meta >$1.500.000/ha

════════════════════════════════════════════════════════════════
  CAPACIDADES EN LA APP — ACCIONES QUE PUEDES EJECUTAR
════════════════════════════════════════════════════════════════
  registrar_cosecha         → Anota cargas cosechadas o siembras realizadas
  crear_recibo_labor        → Paga a un trabajador por una labor (crea recibo)
  agregar_trabajador        → Registra un nuevo trabajador en la nómina
  registrar_presupuesto     → Añade un ingreso al presupuesto del lote
  consultar_resumen_lote    → Muestra el estado financiero y productivo actual
  listar_trabajadores       → Muestra los trabajadores activos del lote
  listar_cosechas           → Muestra el historial de cosechas

════════════════════════════════════════════════════════════════
  BLOQUE 10 — FLUJOS DE TRABAJO EN LA APP (SIGUE ESTO SIEMPRE)
════════════════════════════════════════════════════════════════
CREAR UN RECIBO DE PAGO:
  1. PRIMERO llama listar_trabajadores para ver la nómina y sus valores habituales.
  2. Identifica el trabajador por nombre (parcial está bien). Si hay ambigüedad, pregunta cuál.
  3. Usa el valor_habitual registrado a menos que el usuario indique un monto distinto.
  4. SIEMPRE pregunta explícitamente: "¿Usamos el serial automático o quieres uno personalizado?
     Si es personalizado, ¿desde qué número arrancamos?"
     — Serial automático: no envíes el campo serial (el sistema lo asigna).
     — Serial personalizado: envía el campo serial con el número que el usuario diga.
  5. Confirma: trabajador, labor, monto, fecha y serial antes de crear.

PAGO SEMANAL / VIÁTICOS:
  • "la semana de viáticos" o "pago semanal" → labor = 'otro', observaciones = 'Viaticos semana [fecha]'
  • Usa el valor_habitual del trabajador directamente.
  • Pregunta por serial como indica el paso 4.

REGISTRAR UN TRABAJADOR NUEVO:
  Exige TODOS estos datos antes de ejecutar:
    - nombre (requerido)
    - apellido (requerido)
    - cc (cédula, requerido — sin CC no se puede registrar)
    - cargo: mapea a fumigador/agronomo/administrador/operario
    - telefono (pide si no lo tienen, usa 0000000000 solo como último recurso)
    - valor_habitual (pago habitual por jornada/semana en COP)
  Si falta cc, pregunta antes de ejecutar agregar_trabajador.

CONSULTAR ESTADO DEL LOTE:
  • Ante cualquier pregunta de costos/saldo/presupuesto, llama consultar_resumen_lote primero.
  • Presenta el saldo disponible y una comparación con el límite de gasto/ha.

REGLAS DE CONFIRMACIÓN:
  • Si el usuario da todos los datos en un solo mensaje, ejecuta sin preguntar extra.
  • Si faltan datos obligatorios, pregúntalos uno a uno.
  • Después de cada acción, confirma: qué hiciste, serial asignado, monto, trabajador.
  • Nunca repitas preguntas ya respondidas en el mismo turno.

════════════════════════════════════════════════════════════════
  REGLAS DE COMPORTAMIENTO
════════════════════════════════════════════════════════════════
  • Responde SIEMPRE en español colombiano, cálido, directo y técnico.
  • Cita datos numéricos concretos cuando el usuario pregunte costos, dosis o rendimientos.
  • Si el usuario pide registrar algo y los datos son claros, ejecuta la herramienta SIN pedir confirmación adicional.
  • Si faltan datos obligatorios (cargas, valor, nombre del trabajador), pregúntalos antes de ejecutar.
  • Cuando ejecutes una acción, confirma exactamente qué hiciste y con qué datos.
  • Si el gasto/ha supera $8.000.000 COP, advierte que se está acercando al límite de rentabilidad.
  • Si el gasto/ha supera $11.000.000 COP, alerta que el margen es negativo.
  • Usa el contexto del lote activo (ha, costos, trabajadores) para personalizar los consejos.
  • Para consejos agronómicos, usa el árbol temático completo de tu conocimiento.
  • NUNCA inventes datos financieros del lote. Si no tienes el dato, dilo.
  • Respuestas de consejo: usa tablas y listas cuando ayuden a la claridad.
"""

DASHBOARD_SYSTEM_PROMPT = ARROCERA_SYSTEM_PROMPT  # alias de compatibilidad


# ── Cliente Gemini con Function Calling ───────────────────────────────────────

class GeminiClient:
    """Cliente para la API de Gemini con soporte de function calling (herramientas)."""

    def __init__(self):
        self.model_name = GEMINI_MODEL
        self._configured = False

    def _configure(self):
        if not self._configured:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            self._configured = True

    def _get_tools(self):
        """Retorna las declaraciones de herramientas para Gemini."""
        import google.generativeai as genai
        S = genai.protos.Schema
        T = genai.protos.Type

        def _schema(props: dict, required: list = None) -> genai.protos.Schema:
            return S(type=T.OBJECT, properties=props, required=required or [])

        def _str(desc):  return S(type=T.STRING,  description=desc)
        def _int(desc):  return S(type=T.INTEGER, description=desc)
        def _num(desc):  return S(type=T.NUMBER,  description=desc)

        return [genai.protos.Tool(function_declarations=[

            genai.protos.FunctionDeclaration(
                name='registrar_cosecha',
                description='Registra una cosecha o siembra de arroz en el lote activo.',
                parameters=_schema({
                    'fecha':            _str('Fecha YYYY-MM-DD (usa hoy si no se especifica)'),
                    'cargas':           _int('Número de cargas cosechadas (1 carga = 200 kg paddy)'),
                    'precio_carga':     _num('Precio por carga en COP (opcional)'),
                    'fase':             _str('Fase: "cosecha" o "siembra" (default cosecha)'),
                    'variedad_semilla': _str('Variedad de arroz, ej: FEDEARROZ 60'),
                    'observaciones':    _str('Notas adicionales'),
                }, required=['fecha', 'cargas']),
            ),

            genai.protos.FunctionDeclaration(
                name='crear_recibo_labor',
                description='Crea un recibo de pago para un trabajador por una labor realizada en el lote.',
                parameters=_schema({
                    'nombre_trabajador': _str('Nombre completo del trabajador'),
                    'labor':             _str('Tipo de labor: desague, despalillada, bordeada, abonada, fumigacion, corta, chapola, parche_maleza, otro'),
                    'valor':             _num('Valor total a pagar en COP'),
                    'fecha':             _str('Fecha YYYY-MM-DD (usa hoy si no se especifica)'),
                    'observaciones':     _str('Observaciones o descripción detallada del pago'),
                    'serial':            _str('Número de serial personalizado. Omitir para usar el serial automático del sistema.'),
                }, required=['nombre_trabajador', 'labor', 'valor']),
            ),

            genai.protos.FunctionDeclaration(
                name='agregar_trabajador',
                description='Registra un nuevo trabajador en la nómina del lote activo.',
                parameters=_schema({
                    'nombre':          _str('Nombre(s) del trabajador'),
                    'apellido':        _str('Apellido(s) del trabajador'),
                    'cc':              _str('Número de cédula de ciudadanía'),
                    'cargo':           _str('Cargo o labor que desempeña, ej: jornalero, operador fumigadora'),
                    'valor_habitual':  _num('Valor habitual de pago por jornada en COP'),
                    'telefono':        _str('Número de teléfono o celular'),
                }, required=['nombre', 'apellido']),
            ),

            genai.protos.FunctionDeclaration(
                name='registrar_presupuesto',
                description='Registra un ingreso al presupuesto del lote activo.',
                parameters=_schema({
                    'concepto': _str('Descripción del ingreso, ej: "Abono inicial campaña", "Préstamo banco"'),
                    'monto':    _num('Monto en COP (mayor a cero)'),
                    'tipo':     _str('Tipo: "ingreso" (los egresos se registran como recibos)'),
                    'fecha':    _str('Fecha YYYY-MM-DD (usa hoy si no se especifica)'),
                }, required=['concepto', 'monto', 'tipo']),
            ),

            genai.protos.FunctionDeclaration(
                name='consultar_resumen_lote',
                description='Consulta el resumen financiero y de producción del lote activo.',
                parameters=_schema({}),
            ),

            genai.protos.FunctionDeclaration(
                name='listar_trabajadores',
                description='Lista los trabajadores activos registrados en el lote.',
                parameters=_schema({}),
            ),

            genai.protos.FunctionDeclaration(
                name='listar_cosechas',
                description='Lista las cosechas o siembras registradas en el lote (últimas 20).',
                parameters=_schema({}),
            ),

        ])]

    def health_check(self) -> tuple[bool, str]:
        if not GEMINI_API_KEY:
            return False, 'GEMINI_API_KEY no configurada en .env'
        try:
            self._configure()
            return True, 'OK'
        except Exception as e:
            return False, str(e)

    def chat(self, messages: list[dict]) -> tuple[bool, str]:
        """
        Para onboarding de lote: genera respuesta JSON estructurada (sin function calling).
        Acepta [{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        if not GEMINI_API_KEY:
            return False, 'GEMINI_API_KEY no configurada.'
        try:
            import google.generativeai as genai
            self._configure()

            system_parts = [m['content'] for m in messages if m['role'] == 'system']
            system_text  = '\n\n'.join(system_parts)
            non_system   = [m for m in messages if m['role'] != 'system']

            history = [
                {'role': 'model' if m['role'] == 'assistant' else 'user', 'parts': [m['content']]}
                for m in non_system[:-1]
            ]
            user_msg = non_system[-1]['content'] if non_system else ''

            model        = genai.GenerativeModel(self.model_name, system_instruction=system_text)
            chat_session = model.start_chat(history=history)
            response     = chat_session.send_message(user_msg)
            return True, response.text.strip()
        except Exception as e:
            logger.error(f'[GeminiClient] chat error: {e}')
            return False, _friendly_error(e)

    def generate_text(self, messages: list[dict], tool_executor=None) -> tuple[bool, str]:
        """
        Para el dashboard: genera respuesta con function calling si tool_executor está definido.
        tool_executor(fn_name: str, fn_args: dict) -> dict
        """
        if not GEMINI_API_KEY:
            return False, ('⚙️ GEMINI_API_KEY no configurada. '
                           'Añádela en el archivo .env y reinicia la app.')
        try:
            import google.generativeai as genai
            self._configure()

            system_parts = [m['content'] for m in messages if m['role'] == 'system']
            system_text  = '\n\n'.join(system_parts)
            non_system   = [m for m in messages if m['role'] != 'system']

            history = [
                {'role': 'model' if m['role'] == 'assistant' else 'user', 'parts': [m['content']]}
                for m in non_system[:-1]
            ]
            user_msg = non_system[-1]['content'] if non_system else ''

            kwargs = {'system_instruction': system_text}
            if tool_executor:
                kwargs['tools'] = self._get_tools()

            model        = genai.GenerativeModel(self.model_name, **kwargs)
            chat_session = model.start_chat(history=history)
            response     = chat_session.send_message(user_msg)

            def _safe_text(resp):
                """Extrae texto de la respuesta sin fallar si solo hay function_call parts."""
                try:
                    return resp.text.strip()
                except Exception:
                    texts = []
                    for p in resp.parts:
                        try:
                            t = p.text
                            if t:
                                texts.append(t)
                        except Exception:
                            pass
                    return '\n'.join(texts).strip() or '✅ Acción ejecutada correctamente.'

            # ── Manejar function calls (puede haber varios encadenados) ─────────
            if tool_executor:
                for _round in range(8):  # máx 8 rondas: listar → buscar → crear
                    fc_found = None
                    for part in response.parts:
                        fc = getattr(part, 'function_call', None)
                        if fc and getattr(fc, 'name', None):
                            fc_found = fc
                            break

                    if fc_found is None:
                        break  # no hay más function calls, tenemos texto

                    fn_result = tool_executor(fc_found.name, dict(fc_found.args))
                    response  = chat_session.send_message(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fc_found.name,
                                response={'result': json.dumps(fn_result, ensure_ascii=False, default=str)},
                            )
                        )
                    )

            return True, _safe_text(response)
        except Exception as e:
            logger.error(f'[GeminiClient] generate_text error: {e}')
            return False, _friendly_error(e)


ai_client = GeminiClient()


# ── Utilidades de parsing JSON (para onboarding) ──────────────────────────────

def _extract_json_from_text(text: str) -> Optional[dict]:
    """Intenta extraer un objeto JSON de un texto con contenido mixto."""
    patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```',
        r'(\{[^{}]*"mensaje"[^{}]*\})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i + 1])
                except Exception:
                    pass
    return None




# ── Validadores de campos ──────────────────────────────────────────────────────

def validate_lote_payload(data: dict) -> tuple[bool, list[str]]:
    """Valida el payload de configuración de lote. Retorna (es_valido, errores)."""
    errors = []
    for field, meta in LOTE_FIELDS.items():
        val = data.get(field)
        if meta.get('requerido') and (val is None or str(val).strip() == ''):
            errors.append(f"{meta['label']} es requerido.")
            continue
        if val is None:
            continue
        tipo = meta.get('tipo')
        if tipo == 'float':
            try:
                v = float(val)
                if 'min' in meta and v < meta['min']:
                    errors.append(f"{meta['label']} debe ser mayor que {meta['min']}.")
                if 'max' in meta and v > meta['max']:
                    errors.append(f"{meta['label']} debe ser menor que {meta['max']}.")
            except (ValueError, TypeError):
                errors.append(f"{meta['label']} debe ser un número.")
        elif tipo == 'int':
            try:
                v = int(float(val))
                if 'min' in meta and v < meta['min']:
                    errors.append(f"{meta['label']} debe ser al menos {meta['min']}.")
            except (ValueError, TypeError):
                errors.append(f"{meta['label']} debe ser un número entero.")
        elif tipo == 'date':
            if val:
                try:
                    datetime.strptime(str(val), '%Y-%m-%d')
                except ValueError:
                    errors.append(f"{meta['label']} debe tener formato YYYY-MM-DD.")
    return len(errors) == 0, errors


def apply_field_defaults(data: dict) -> dict:
    """Aplica valores por defecto a campos opcionales vacíos."""
    result = dict(data)
    for field, meta in LOTE_FIELDS.items():
        val = result.get(field)
        if (val is None or (isinstance(val, str) and val.strip() == '')) and 'default' in meta:
            result[field] = meta['default']
    return result


def missing_required_fields(data: dict) -> list[str]:
    """Retorna la lista de etiquetas de campos requeridos que faltan."""
    return [
        meta['label']
        for field, meta in LOTE_FIELDS.items()
        if meta.get('requerido') and (
            data.get(field) is None or str(data.get(field, '')).strip() == ''
        )
    ]


# ── Gestor de sesión de chat ──────────────────────────────────────────────────

class LoteOnboardingSession:
    """
    Encapsula el estado de una sesión de onboarding de lote.
    Mantiene el historial de mensajes y el payload acumulado.
    """

    def __init__(self, session_id: int, existing_payload: Optional[dict] = None):
        self.session_id = session_id
        self.payload    = existing_payload or {}
        self.messages: list[dict] = [{'role': 'system', 'content': SYSTEM_PROMPT}]

    def add_user_message(self, text: str):
        self.messages.append({'role': 'user', 'content': text})

    def process(self, user_message: str) -> dict:
        """
        Procesa un mensaje del usuario y retorna la respuesta del asistente.
        Actualiza el payload acumulado con los datos detectados.
        """
        if not AI_ENABLED:
            return self._degraded_response()

        self.add_user_message(user_message)

        # Inyectar contexto del estado actual como mensaje de sistema adicional
        context_msg = {
            'role': 'system',
            'content': (
                f"Estado actual del formulario: {json.dumps(self.payload, ensure_ascii=False)}. "
                f"Campos faltantes requeridos: {missing_required_fields(self.payload)}. "
                f"Responde SOLO en JSON."
            ),
        }
        messages_to_send = [self.messages[0], context_msg] + self.messages[1:]

        ok, raw = ai_client.chat(messages_to_send)
        if not ok:
            logger.warning(f'[ai_service] Error Gemini: {raw}')
            return {
                'mensaje': (
                    f'⚠️ El asistente no pudo responder. '
                    f'Puedes continuar con el formulario manual o intentar de nuevo.\n'
                    f'Detalle: {raw}'
                ),
                'datos_detectados':  {},
                'paso_actual':        'error',
                'campos_faltantes':   missing_required_fields(self.payload),
                'listo_para_guardar': False,
                'error':              raw,
            }

        try:
            result = json.loads(raw)
        except Exception:
            result = {
                'mensaje':            raw,
                'datos_detectados':   {},
                'paso_actual':        'recopilando',
                'campos_faltantes':   missing_required_fields(self.payload),
                'listo_para_guardar': False,
            }

        # Merge datos_detectados con payload acumulado (no sobrescribir con null)
        nuevos = result.get('datos_detectados') or {}
        for k, v in nuevos.items():
            if v is not None and str(v).strip() not in ('', 'null', 'None'):
                self.payload[k] = v

        result['campos_faltantes']   = missing_required_fields(self.payload)
        result['payload_actual']     = self.payload
        result['listo_para_guardar'] = len(result['campos_faltantes']) == 0

        self.messages.append({'role': 'assistant', 'content': result.get('mensaje', '')})

        return result

    def _degraded_response(self) -> dict:
        return {
            'mensaje': (
                '🔧 El asistente de IA no está disponible en este momento. '
                'Por favor completa el formulario manual.'
            ),
            'datos_detectados':  {},
            'paso_actual':        'degradado',
            'campos_faltantes':   missing_required_fields(self.payload),
            'payload_actual':     self.payload,
            'listo_para_guardar': False,
            'degraded':           True,
        }


# ── Verificación al arrancar ──────────────────────────────────────────────────

def check_ai_on_startup():
    """
    Verifica la disponibilidad de Gemini al iniciar la aplicación.
    No bloquea el arranque si la clave no está configurada.
    """
    if not AI_ENABLED:
        logger.info('[ai_service] IA deshabilitada (AI_ENABLED=false)')
        return
    ok, msg = ai_client.health_check()
    if ok:
        logger.info(f'[ai_service] Gemini OK — modelo: {GEMINI_MODEL}')
    else:
        logger.warning(
            f'[ai_service] Gemini no disponible: {msg}. '
            f'El modo degradado (formulario manual) estará activo.'
        )
