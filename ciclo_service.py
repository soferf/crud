"""
ciclo_service.py — Lógica de los ciclos/campañas de producción de arroz.

Un "ciclo de producción" es una campaña completa: empieza con la SIEMBRA,
avanza por las 9 etapas fenológicas del arroz y termina con la COSECHA.
Mientras un ciclo está ACTIVO, los recibos y cosechas del lote se le asignan
automáticamente (vía trigger de BD), permitiendo costear cada campaña por separado.
"""
from __future__ import annotations

from datetime import date, timedelta

from db import get_db_connection


# ── Duración del ciclo por variedad (días de siembra a cosecha) ───────────────
# Fuente: fichas Fedearroz (ver ARROCERA_SYSTEM_PROMPT, Bloque 2).
DURACION_VARIEDAD = {
    'fedearroz 60':   120,
    'fedearroz 68':   115,
    'fedearroz 473':  125,
    'fedearroz 2000': 115,
    'fedearroz 174':  120,
}
DURACION_DEFAULT = 120


# ── Las 9 etapas fenológicas (día_inicio inclusivo → día_fin) ─────────────────
# Cada etapa trae la labor/recomendación clave de esa ventana (Bloque 3 del prompt).
ETAPAS = [
    {'n': 1, 'fase': 'vegetativa',  'nombre': 'Germinación',        'ini': 0,   'fin': 7,
     'icono': 'sprout',   'clave': 'Fósforo basal + Zinc correctivo. Humedad de suelo >80%.'},
    {'n': 2, 'fase': 'vegetativa',  'nombre': 'Plántula',           'ini': 7,   'fin': 21,
     'icono': 'seedling', 'clave': 'Herbicidas pre-emergentes si hay presión de maleza.'},
    {'n': 3, 'fase': 'vegetativa',  'nombre': 'Macollamiento',      'ini': 21,  'fin': 40,
     'icono': 'wheat',    'clave': '1ª fracción de Nitrógeno (urea). Define número de panículas.'},
    {'n': 4, 'fase': 'reproductiva','nombre': 'Iniciación floral',  'ini': 40,  'fin': 50,
     'icono': 'flower-2', 'clave': 'CRÍTICO: 2ª fracción N + Potasio. Preventivo piricularia.'},
    {'n': 5, 'fase': 'reproductiva','nombre': 'Elongación del tallo','ini': 50, 'fin': 65,
     'icono': 'move-up',  'clave': 'Bajar lámina de agua a 3-5 cm para favorecer anclaje.'},
    {'n': 6, 'fase': 'reproductiva','nombre': 'Espigazón',          'ini': 65,  'fin': 70,
     'icono': 'wheat',    'clave': 'Control preventivo de piricularia en cuello de panícula.'},
    {'n': 7, 'fase': 'reproductiva','nombre': 'Floración',          'ini': 70,  'fin': 75,
     'icono': 'flower',   'clave': 'Mantener lámina de agua. Control de chinche (Oebalus).'},
    {'n': 8, 'fase': 'maduración',  'nombre': 'Estado lechoso',     'ini': 75,  'fin': 95,
     'icono': 'droplets', 'clave': 'NO aplicar nitrógeno (favorece vaneamiento y manchado).'},
    {'n': 9, 'fase': 'maduración',  'nombre': 'Madurez / Cosecha',  'ini': 95,  'fin': 999,
     'icono': 'combine',  'clave': 'Drenar 15-20 días antes. Cosechar a 20-22% de humedad.'},
]


def duracion_variedad(variedad: str | None) -> int:
    """Días estimados de ciclo para la variedad (o el default)."""
    if not variedad:
        return DURACION_DEFAULT
    return DURACION_VARIEDAD.get(variedad.strip().lower(), DURACION_DEFAULT)


def etapa_por_dia(dias: int) -> dict:
    """Retorna la etapa fenológica correspondiente a los días transcurridos."""
    dias = max(0, int(dias))
    for etapa in ETAPAS:
        if etapa['ini'] <= dias < etapa['fin']:
            return etapa
    return ETAPAS[-1]


def estado_ciclo(ciclo: dict, hoy: date | None = None) -> dict:
    """
    Enriquece un registro de ciclo con su estado calculado:
    días transcurridos, etapa actual, progreso %, fecha estimada de cosecha y días restantes.
    """
    hoy = hoy or date.today()
    fecha_siembra = ciclo.get('fecha_siembra')
    if isinstance(fecha_siembra, str):
        fecha_siembra = date.fromisoformat(fecha_siembra)

    duracion = int(ciclo.get('duracion_estimada_dias') or duracion_variedad(ciclo.get('variedad_semilla')))
    cerrado  = ciclo.get('estado') == 'cerrado'

    # Para ciclos cerrados, el "corte" es la fecha de cierre.
    corte = ciclo.get('fecha_cierre') if cerrado else hoy
    if isinstance(corte, str):
        corte = date.fromisoformat(corte)
    corte = corte or hoy

    dias = (corte - fecha_siembra).days if fecha_siembra else 0
    dias = max(0, dias)
    etapa = etapa_por_dia(dias)
    fecha_cosecha_est = (fecha_siembra + timedelta(days=duracion)) if fecha_siembra else None
    dias_restantes = (fecha_cosecha_est - hoy).days if (fecha_cosecha_est and not cerrado) else None
    progreso = 100 if cerrado else min(100, round(dias / duracion * 100)) if duracion else 0

    return {
        **ciclo,
        'dias_transcurridos':     dias,
        'etapa':                  etapa,
        'progreso_pct':           progreso,
        'fecha_cosecha_estimada': fecha_cosecha_est,
        'dias_restantes':         dias_restantes,
        'duracion_estimada_dias': duracion,
    }


# ── Consultas ─────────────────────────────────────────────────────────────────

def get_ciclo_activo(lote_id, conn=None) -> dict | None:
    """Retorna el ciclo ACTIVO del lote (o None). No incluye el estado calculado."""
    if not lote_id:
        return None
    own = conn is None
    conn = conn or get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM ciclos_produccion WHERE lote_id=%s AND estado='activo' "
            "ORDER BY id DESC LIMIT 1", (lote_id,))
        row = cur.fetchone()
        cur.close()
        return row
    finally:
        if own:
            conn.close()


def costos_ciclo(ciclo_id, conn=None) -> dict:
    """Suma los gastos (recibos) y la producción (cosechas) atribuidos a un ciclo."""
    own = conn is None
    conn = conn or get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT COUNT(*) tot, COALESCE(SUM(neto_a_pagar),0) gasto "
            "FROM recibos WHERE ciclo_id=%s", (ciclo_id,))
        r = cur.fetchone() or {}
        cur.execute(
            "SELECT COALESCE(SUM(cargas),0) cargas, COALESCE(SUM(valor_total),0) ingreso "
            "FROM cosechas WHERE ciclo_id=%s AND fase='cosecha'", (ciclo_id,))
        c = cur.fetchone() or {}
        cur.close()
        return {
            'total_recibos': int(r.get('tot') or 0),
            'gasto_total':   float(r.get('gasto') or 0),
            'cargas':        int(c.get('cargas') or 0),
            'ingreso':       float(c.get('ingreso') or 0),
        }
    finally:
        if own:
            conn.close()
