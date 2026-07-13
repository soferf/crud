"""
humedad_sim.py — Motor de simulación de humedad de suelo para lotes de arroz.

Genera datos FICTICIOS pero con lógica agronómica real del cultivo de arroz
(fenología, evapotranspiración, dinámica de riego y variación espacial), de modo
que el módulo pueda alimentarse hoy con datos simulados y mañana con lecturas
reales de sensores Arduino/ESP32 (capacitivos o tensiómetros) sin cambiar la app.

Modelo de humedad: VWC (Volumetric Water Content) en % — proxy del contenido de
agua en el suelo / lámina de riego. El arroz es un cultivo semiacuático: durante
macollamiento y fase reproductiva se mantiene el suelo saturado; antes de cosecha
se realiza el desagüe (drenaje) y el suelo se seca.

La simulación avanza por "pasos" disparados desde las peticiones del frontend
(polling), por lo que no requiere hilos de fondo y es compatible con el modelo
request/response de Flask.
"""
import math
import random
from datetime import datetime, timedelta

from db import get_db_connection

# ── Constantes de simulación ──────────────────────────────────────────────────
# Factor de aceleración temporal: la dinámica real ocurre en horas/días, pero
# para una demo en vivo comprimimos el tiempo para que los cambios sean visibles.
SIM_ACCEL = 22.0
# Intervalo mínimo entre lecturas persistidas por sensor (segundos de reloj real).
MIN_STEP_SECONDS = 6
# Mínimo/Máximo físico de humedad.
HUM_MIN, HUM_MAX = 8.0, 100.0


# ── Fenología del arroz ───────────────────────────────────────────────────────
# Cada fase define: rango de días desde siembra, banda de humedad objetivo (%),
# tasa de evapotranspiración base (%/min de simulación) y una etiqueta de manejo.
FASES_ARROZ = [
    {'clave': 'germinacion',  'nombre': 'Germinación',        'dia_ini': 0,   'dia_fin': 12,
     'obj_min': 55, 'obj_max': 75, 'et': 0.22, 'manejo': 'Suelo húmedo sin lámina'},
    {'clave': 'plantula',     'nombre': 'Plántula',           'dia_ini': 12,  'dia_fin': 28,
     'obj_min': 68, 'obj_max': 88, 'et': 0.28, 'manejo': 'Lámina ligera de agua'},
    {'clave': 'macollamiento','nombre': 'Macollamiento',      'dia_ini': 28,  'dia_fin': 55,
     'obj_min': 82, 'obj_max': 98, 'et': 0.34, 'manejo': 'Lámina 5 cm — saturación'},
    {'clave': 'reproductiva', 'nombre': 'Reproductiva',       'dia_ini': 55,  'dia_fin': 85,
     'obj_min': 88, 'obj_max': 100,'et': 0.40, 'manejo': 'Fase crítica — no permitir sequía'},
    {'clave': 'llenado',      'nombre': 'Llenado de grano',   'dia_ini': 85,  'dia_fin': 105,
     'obj_min': 78, 'obj_max': 94, 'et': 0.33, 'manejo': 'Mantener humedad estable'},
    {'clave': 'maduracion',   'nombre': 'Maduración / Desagüe','dia_ini': 105, 'dia_fin': 130,
     'obj_min': 38, 'obj_max': 62, 'et': 0.52, 'manejo': 'Drenaje para cosecha'},
]


def fase_por_dia(dias):
    """Devuelve la fase fenológica correspondiente a los días desde siembra."""
    for f in FASES_ARROZ:
        if f['dia_ini'] <= dias < f['dia_fin']:
            return f
    # Antes de siembra o después de maduración
    return FASES_ARROZ[0] if dias < 0 else FASES_ARROZ[-1]


def clasificar_estado(hum, fase):
    """Clasifica una lectura respecto a la banda objetivo de la fase."""
    if hum < fase['obj_min'] - 12:
        return 'critico'      # peligrosamente seco
    if hum < fase['obj_min']:
        return 'seco'         # bajo el óptimo, requiere riego
    if hum > fase['obj_max'] + 4:
        return 'saturado'     # exceso de agua
    return 'optimo'


# ── Helpers de configuración / estado ─────────────────────────────────────────
def get_config(lote_id):
    """Carga (o crea con valores por defecto) la configuración de riego del lote."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM humedad_config WHERE lote_id=%s", (lote_id,))
    cfg = cur.fetchone()
    if not cfg:
        fecha_siembra = (datetime.now() - timedelta(days=42)).date()  # ~macollamiento
        cur2 = conn.cursor()
        cur2.execute("""
            INSERT INTO humedad_config
              (lote_id, fecha_siembra, umbral_min_pct, umbral_max_pct,
               modo_auto, riego_activo, forma_lote, ancho_m, largo_m)
            VALUES (%s,%s,75,95,1,0,'rectangular',200,400)
        """, (lote_id, fecha_siembra))
        conn.commit(); cur2.close()
        cur.execute("SELECT * FROM humedad_config WHERE lote_id=%s", (lote_id,))
        cfg = cur.fetchone()
    cur.close(); conn.close()
    return cfg


def dias_desde_siembra(cfg):
    fs = cfg.get('fecha_siembra')
    if not fs:
        return 42
    if isinstance(fs, datetime):
        fs = fs.date()
    return (datetime.now().date() - fs).days


def get_sensores(lote_id, solo_activos=True):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    q = "SELECT * FROM humedad_sensores WHERE lote_id=%s"
    if solo_activos:
        q += " AND activo=1"
    q += " ORDER BY codigo"
    cur.execute(q, (lote_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def _ultima_lectura(cur, sensor_id):
    cur.execute(
        "SELECT humedad_pct, temperatura_c, fecha_hora FROM humedad_lecturas "
        "WHERE sensor_id=%s ORDER BY fecha_hora DESC, id DESC LIMIT 1",
        (sensor_id,))
    return cur.fetchone()


# ── Generación de una nueva lectura por sensor ────────────────────────────────
def _siguiente_valor(prev_hum, dt_min, fase, sensor, riego_on, temp):
    """Calcula el siguiente valor de humedad para un sensor dado el estado previo."""
    # Variación espacial: el agua entra por el costado superior del lote (y=0).
    # Sensores lejanos al ingreso o en posiciones altas se secan más rápido y se
    # recargan más lento. factor_secado se almacena por sensor (0.8–1.6).
    f_secado = float(sensor.get('factor_secado') or 1.0)
    y = float(sensor.get('pos_y') or 50) / 100.0  # 0 = ingreso de agua, 1 = lejano

    # Pérdida por evapotranspiración (mayor con calor y en bordes/lejanía).
    et = fase['et'] * f_secado * (0.85 + 0.012 * (temp - 28))
    perdida = et * dt_min * (0.9 + 0.6 * y)

    # Recarga por riego (hacia saturación; más rápida cerca del ingreso).
    ganancia = 0.0
    if riego_on:
        proximidad = 1.25 - 0.45 * y
        ganancia = 1.35 * dt_min * proximidad * (1.05 - prev_hum / 130.0)

    ruido = random.uniform(-0.4, 0.4) * dt_min
    nuevo = prev_hum + ganancia - perdida + ruido
    return max(HUM_MIN, min(HUM_MAX, nuevo))


def avanzar_simulacion(lote_id):
    """
    Avanza la simulación: para cada sensor activo, si pasó MIN_STEP_SECONDS desde
    su última lectura, genera y persiste una nueva. Maneja el riego automático.
    Devuelve el estado actual completo del lote (para el frontend).
    """
    cfg = get_config(lote_id)
    sensores = get_sensores(lote_id)
    dias = dias_desde_siembra(cfg)
    fase = fase_por_dia(dias)

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    ins = conn.cursor()

    ahora = datetime.now()
    riego_on = bool(cfg.get('riego_activo'))
    temp_amb = round(random.uniform(27, 34), 1)

    # Promedio actual para decidir riego automático.
    valores_previos = []
    estados_sensores = []
    for s in sensores:
        prev = _ultima_lectura(cur, s['id'])
        if prev:
            prev_hum = float(prev['humedad_pct'])
            edad = (ahora - prev['fecha_hora']).total_seconds()
        else:
            prev_hum = random.uniform(fase['obj_min'] - 5, fase['obj_max'])
            edad = MIN_STEP_SECONDS + 1
        valores_previos.append(prev_hum)
        estados_sensores.append((s, prev_hum, edad))

    prom_prev = sum(valores_previos) / len(valores_previos) if valores_previos else 0

    # ── Lógica de riego automático ────────────────────────────────────────────
    riego_cambio = None
    if cfg.get('modo_auto'):
        if not riego_on and prom_prev < float(cfg['umbral_min_pct']):
            riego_on = True
            riego_cambio = ('inicio', 'automatico')
        elif riego_on and prom_prev >= float(cfg['umbral_max_pct']):
            riego_on = False
            riego_cambio = ('fin', 'automatico')
        if riego_cambio:
            ins.execute("UPDATE humedad_config SET riego_activo=%s WHERE lote_id=%s",
                        (1 if riego_on else 0, lote_id))
            ins.execute("""INSERT INTO riego_eventos
                (lote_id, tipo, modo, umbral_pct, humedad_prom, nota)
                VALUES (%s,%s,%s,%s,%s,%s)""",
                (lote_id, riego_cambio[0], riego_cambio[1],
                 cfg['umbral_min_pct'] if riego_cambio[0] == 'inicio' else cfg['umbral_max_pct'],
                 round(prom_prev, 1),
                 f"Riego {'iniciado' if riego_cambio[0]=='inicio' else 'detenido'} automáticamente"))
            conn.commit()

    # ── Generar lecturas nuevas ───────────────────────────────────────────────
    lecturas = []
    for s, prev_hum, edad in estados_sensores:
        if edad >= MIN_STEP_SECONDS:
            dt_min = min(edad, 90) / 60.0 * SIM_ACCEL
            nuevo = _siguiente_valor(prev_hum, dt_min, fase, s, riego_on, temp_amb)
            temp_s = round(temp_amb + random.uniform(-1.5, 1.0), 1)
            ins.execute("""INSERT INTO humedad_lecturas
                (sensor_id, lote_id, humedad_pct, temperatura_c, fuente, fecha_hora)
                VALUES (%s,%s,%s,%s,'simulado',%s)""",
                (s['id'], lote_id, round(nuevo, 1), temp_s, ahora))
            val = nuevo
        else:
            val = prev_hum
            temp_s = temp_amb
        lecturas.append({
            'sensor_id': s['id'], 'codigo': s['codigo'], 'nombre': s['nombre'],
            'pos_x': float(s['pos_x']), 'pos_y': float(s['pos_y']),
            'profundidad_cm': s.get('profundidad_cm'),
            'humedad_pct': round(val, 1), 'temperatura_c': temp_s,
            'estado': clasificar_estado(val, fase),
        })
    conn.commit()
    ins.close(); cur.close(); conn.close()

    prom = round(sum(l['humedad_pct'] for l in lecturas) / len(lecturas), 1) if lecturas else 0
    return {
        'lote_id': lote_id,
        'timestamp': ahora.isoformat(),
        'fase': fase, 'dias_siembra': dias,
        'humedad_promedio': prom,
        'estado_promedio': clasificar_estado(prom, fase) if lecturas else 'sin_datos',
        'riego_activo': riego_on,
        'modo_auto': bool(cfg.get('modo_auto')),
        'umbral_min': float(cfg['umbral_min_pct']),
        'umbral_max': float(cfg['umbral_max_pct']),
        'temperatura_amb': temp_amb,
        'forma_lote': cfg.get('forma_lote', 'rectangular'),
        'ancho_m': float(cfg.get('ancho_m') or 0),
        'largo_m': float(cfg.get('largo_m') or 0),
        'sensores': lecturas,
        'n_sensores': len(lecturas),
        'n_secos': sum(1 for l in lecturas if l['estado'] in ('seco', 'critico')),
        'n_saturados': sum(1 for l in lecturas if l['estado'] == 'saturado'),
    }


# ── Distribución automática de sensores según cantidad/forma del lote ─────────
def generar_malla(n, forma='rectangular'):
    """
    Devuelve una lista de posiciones (pos_x, pos_y, factor_secado) distribuidas
    según la forma del lote. Coordenadas normalizadas 0–100.
    """
    pts = []
    if forma in ('rectangular', 'cuadrado'):
        cols = max(1, round(math.sqrt(n)))
        rows = math.ceil(n / cols)
        idx = 0
        for r in range(rows):
            for c in range(cols):
                if idx >= n:
                    break
                x = (c + 0.5) / cols * 100
                y = (r + 0.5) / rows * 100
                pts.append((x, y))
                idx += 1
    elif forma == 'L':
        # Forma en L: dos brazos perpendiculares.
        for i in range(n):
            if i % 2 == 0:
                x = (i / max(1, n - 1)) * 60 + 10
                y = 75
            else:
                x = 20
                y = (i / max(1, n - 1)) * 70 + 10
            pts.append((x, y))
    else:  # irregular — distribución pseudo-aleatoria estable
        rnd = random.Random(42)
        for _ in range(n):
            pts.append((rnd.uniform(8, 92), rnd.uniform(8, 92)))

    salida = []
    for (x, y) in pts:
        # Sensores más alejados del ingreso de agua (y alto) se secan más.
        factor = round(0.85 + (y / 100) * 0.55 + random.uniform(-0.05, 0.1), 2)
        salida.append((round(x, 1), round(y, 1), factor))
    return salida


def crear_sensores(lote_id, n, forma='rectangular', profundidad=20):
    """(Re)crea la malla de sensores de un lote y siembra historial inicial."""
    malla = generar_malla(n, forma)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM humedad_sensores WHERE lote_id=%s", (lote_id,))
    sensor_ids = []
    for i, (x, y, factor) in enumerate(malla, start=1):
        codigo = f"S-{i:02d}"
        cur.execute("""INSERT INTO humedad_sensores
            (lote_id, codigo, nombre, pos_x, pos_y, profundidad_cm, factor_secado, activo)
            VALUES (%s,%s,%s,%s,%s,%s,%s,1)""",
            (lote_id, codigo, f"Sensor {i}", x, y, profundidad, factor))
        sensor_ids.append((cur.lastrowid, x, y, factor))
    conn.commit()
    cur.execute("UPDATE humedad_config SET forma_lote=%s WHERE lote_id=%s", (forma, lote_id))
    conn.commit()
    cur.close(); conn.close()
    sembrar_historial(lote_id)
    return len(sensor_ids)


def sembrar_historial(lote_id, horas=3, paso_min=10):
    """Genera lecturas históricas para que las gráficas no inicien vacías."""
    cfg = get_config(lote_id)
    sensores = get_sensores(lote_id)
    if not sensores:
        return
    dias = dias_desde_siembra(cfg)
    fase = fase_por_dia(dias)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM humedad_lecturas WHERE lote_id=%s", (lote_id,))

    n_pasos = int(horas * 60 / paso_min)
    ahora = datetime.now()
    # Estado inicial por sensor centrado en la banda objetivo.
    estado = {s['id']: random.uniform(fase['obj_min'] - 3, fase['obj_max'] - 2) for s in sensores}
    riego_on = False
    for p in range(n_pasos, 0, -1):
        ts = ahora - timedelta(minutes=paso_min * p)
        prom = sum(estado.values()) / len(estado)
        if cfg.get('modo_auto'):
            if not riego_on and prom < float(cfg['umbral_min_pct']):
                riego_on = True
            elif riego_on and prom >= float(cfg['umbral_max_pct']):
                riego_on = False
        temp = round(random.uniform(27, 34), 1)
        dt_min = paso_min  # tiempo simulado real (sin acelerar para el historial)
        for s in sensores:
            nuevo = _siguiente_valor(estado[s['id']], dt_min, fase, s, riego_on, temp)
            estado[s['id']] = nuevo
            cur.execute("""INSERT INTO humedad_lecturas
                (sensor_id, lote_id, humedad_pct, temperatura_c, fuente, fecha_hora)
                VALUES (%s,%s,%s,%s,'simulado',%s)""",
                (s['id'], lote_id, round(nuevo, 1), round(temp + random.uniform(-1, 1), 1), ts))
    conn.commit()
    cur.close(); conn.close()


def serie_promedio(lote_id, puntos=60):
    """Serie temporal del promedio de humedad del lote (para la gráfica en vivo)."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT fecha_hora, AVG(humedad_pct) AS prom
        FROM humedad_lecturas
        WHERE lote_id=%s
        GROUP BY fecha_hora
        ORDER BY fecha_hora DESC
        LIMIT %s
    """, (lote_id, puntos))
    rows = cur.fetchall()
    cur.close(); conn.close()
    rows.reverse()
    return [{'t': r['fecha_hora'].strftime('%H:%M:%S'), 'v': round(float(r['prom']), 1)} for r in rows]


def historial_riego(lote_id, limite=15):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT tipo, modo, umbral_pct, humedad_prom, nota, fecha_hora
                   FROM riego_eventos WHERE lote_id=%s
                   ORDER BY fecha_hora DESC LIMIT %s""", (lote_id, limite))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def recomendaciones(estado):
    """Genera recomendaciones de manejo de riego según el estado y la fenología."""
    recs = []
    fase = estado['fase']
    prom = estado['humedad_promedio']
    if estado['estado_promedio'] == 'critico':
        recs.append(('danger', 'fa-triangle-exclamation',
                     f"Humedad crítica ({prom}%). Inicie riego inmediato para proteger el cultivo en fase {fase['nombre'].lower()}."))
    elif estado['estado_promedio'] == 'seco':
        recs.append(('warning', 'fa-droplet-slash',
                     f"Humedad bajo el óptimo ({prom}%). Se recomienda regar; objetivo {fase['obj_min']}–{fase['obj_max']}%."))
    elif estado['estado_promedio'] == 'saturado':
        if fase['clave'] == 'maduracion':
            recs.append(('info', 'fa-water',
                         "Fase de maduración: realice desagüe para preparar la cosecha."))
        else:
            recs.append(('info', 'fa-water',
                         f"Suelo saturado ({prom}%). Suspenda riego para evitar exceso de agua."))
    else:
        recs.append(('success', 'fa-circle-check',
                     f"Humedad óptima ({prom}%) para la fase de {fase['nombre'].lower()}."))

    if estado['n_secos'] > 0 and estado['estado_promedio'] not in ('seco', 'critico'):
        recs.append(('warning', 'fa-map-pin',
                     f"{estado['n_secos']} zona(s) por debajo del óptimo pese al promedio aceptable: riego desuniforme."))
    if fase['clave'] == 'reproductiva':
        recs.append(('info', 'fa-seedling',
                     "Fase reproductiva (crítica): mantenga lámina de agua constante, no permita sequía."))
    return recs
