"""
ai_service.py — Servicio Ollama para onboarding asistido de lotes.

Variables de entorno:
    OLLAMA_BASE_URL  → http://localhost:11434
    OLLAMA_MODEL     → qwen2.5:7b-instruct
    OLLAMA_TIMEOUT   → 30
    AI_ENABLED       → true
"""

import os
import json
import re
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL    = os.environ.get('OLLAMA_MODEL',    'qwen2.5:7b-instruct')
OLLAMA_TIMEOUT  = int(os.environ.get('OLLAMA_TIMEOUT', '30'))
AI_ENABLED      = os.environ.get('AI_ENABLED', 'true').lower() == 'true'

# ── Campos del formulario de configuración de lote ───────────────────────────
LOTE_FIELDS = {
    'nombre_lote':             {'label': 'Nombre del lote',           'tipo': 'str',   'requerido': True},
    'propietario':             {'label': 'Nombre del propietario',     'tipo': 'str',   'requerido': True},
    'hectareas':               {'label': 'Hectáreas totales',          'tipo': 'float', 'requerido': True,  'min': 0.1,   'max': 50000},
    'municipio':               {'label': 'Municipio',                  'tipo': 'str',   'requerido': True},
    'departamento':            {'label': 'Departamento',               'tipo': 'str',   'requerido': True},
    'cultivo_principal':       {'label': 'Cultivo principal',          'tipo': 'str',   'requerido': False, 'default': 'Arroz'},
    'fecha_inicio_operacion':  {'label': 'Fecha de inicio (YYYY-MM-DD)', 'tipo': 'date', 'requerido': False},
    'moneda':                  {'label': 'Moneda',                     'tipo': 'str',   'requerido': False, 'default': 'COP'},
    'meta_cargas_ha':          {'label': 'Meta de cargas por hectárea','tipo': 'int',   'requerido': False, 'default': 100, 'min': 1},
    'limite_gasto_ha':         {'label': 'Límite de gasto por ha ($)', 'tipo': 'float', 'requerido': False, 'default': 11000000, 'min': 1},
}

SYSTEM_PROMPT = """Eres un asistente amigable y profesional que ayuda a configurar un lote arrocero
en el sistema de contabilidad agrícola. Tu tarea es recopilar los datos del lote nuevo de forma
conversacional en español colombiano.

Campos a recopilar (en orden sugerido):
- nombre_lote: nombre del lote (ej: "El Mangón", "La Esperanza")
- propietario: nombre completo del dueño
- hectareas: número positivo (ej: 20.5)
- municipio y departamento: ubicación en Colombia
- cultivo_principal: por defecto "Arroz"
- fecha_inicio_operacion: fecha en formato YYYY-MM-DD (opcional)
- moneda: "COP" por defecto
- meta_cargas_ha: meta de cargas por hectárea (default 100)
- limite_gasto_ha: límite de gasto por ha en pesos (default 11000000)

Reglas:
1. Pregunta solo lo que falta, nunca repitas preguntas ya respondidas.
2. Valida que hectáreas sea un número positivo.
3. Acepta correcciones: si el usuario dice "cambia X a Y", actualiza el campo.
4. Cuando tengas todos los campos requeridos (nombre_lote, propietario, hectareas, municipio, departamento),
   presenta un resumen completo y pide confirmación.
5. Sé breve, amigable y profesional. Usa emojis moderadamente.

IMPORTANTE: Responde SIEMPRE en este JSON exacto (sin texto adicional):
{
  "mensaje": "texto de respuesta al usuario",
  "datos_detectados": {
    "nombre_lote": null,
    "propietario": null,
    "hectareas": null,
    "municipio": null,
    "departamento": null,
    "cultivo_principal": null,
    "fecha_inicio_operacion": null,
    "moneda": null,
    "meta_cargas_ha": null,
    "limite_gasto_ha": null
  },
  "paso_actual": "recopilando|confirmando|completado|cancelado",
  "campos_faltantes": [],
  "listo_para_guardar": false
}
"""

# ── Cliente Ollama ─────────────────────────────────────────────────────────────

class OllamaClient:
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL.rstrip('/')
        self.model    = OLLAMA_MODEL
        self.timeout  = OLLAMA_TIMEOUT
        self._healthy = None

    def health_check(self) -> tuple[bool, str]:
        """Verifica que Ollama esté corriendo y el modelo disponible."""
        try:
            req = urllib.request.urlopen(f'{self.base_url}/api/tags', timeout=5)
            if req.status != 200:
                return False, f'Ollama responde con status {req.status}'
            tags = json.loads(req.read().decode()).get('models', [])
            names = [m.get('name', '') for m in tags]
            model_ok = any(self.model in n or n.startswith(self.model.split(':')[0]) for n in names)
            if not model_ok:
                return False, (f'Modelo "{self.model}" no encontrado. '
                               f'Disponibles: {", ".join(names) or "ninguno"}. '
                               f'Ejecuta: ollama pull {self.model}')
            self._healthy = True
            return True, 'OK'
        except urllib.error.URLError:
            self._healthy = False
            return False, f'No se puede conectar a Ollama en {self.base_url}. Asegúrate de que Ollama esté corriendo.'
        except Exception as e:
            self._healthy = False
            return False, str(e)

    def chat(self, messages: list[dict], retries: int = 2) -> tuple[bool, str]:
        """
        Envía mensajes al modelo y retorna (éxito, texto_respuesta).
        Reintentos con instrucción de corrección JSON si falla el parse.
        """
        payload = {
            'model': self.model,
            'messages': messages,
            'stream': False,
            'format': 'json',
            'options': {'temperature': 0.3, 'top_p': 0.9},
        }
        for attempt in range(retries + 1):
            try:
                body = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(
                    f'{self.base_url}/api/chat',
                    data=body,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status != 200:
                        if attempt < retries:
                            time.sleep(1)
                            continue
                        return False, f'Error Ollama HTTP {resp.status}'
                    content = json.loads(resp.read().decode()).get('message', {}).get('content', '')

                # Intentar parsear JSON
                try:
                    parsed = json.loads(content)
                    return True, json.dumps(parsed, ensure_ascii=False)
                except json.JSONDecodeError:
                    extracted = _extract_json_from_text(content)
                    if extracted:
                        return True, json.dumps(extracted, ensure_ascii=False)
                    if attempt < retries:
                        messages = messages + [{
                            'role': 'user',
                            'content': 'Tu respuesta anterior no era JSON válido. Responde ÚNICAMENTE con el JSON exacto, sin texto adicional.'
                        }]
                        continue
                    return False, content

            except urllib.error.URLError as e:
                if 'timed out' in str(e).lower() or isinstance(getattr(e, 'reason', None), Exception):
                    if attempt < retries:
                        time.sleep(1)
                        continue
                    return False, 'Tiempo de espera agotado. Ollama tardó demasiado en responder.'
                if attempt < retries:
                    time.sleep(1)
                    continue
                return False, str(e)
            except Exception as e:
                if attempt < retries:
                    time.sleep(1)
                    continue
                return False, str(e)

        return False, 'No se obtuvo respuesta del modelo.'


ollama = OllamaClient()


def _extract_json_from_text(text: str) -> dict | None:
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
    # Último recurso: encontrar el primer { ... } balanceado
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
                    return json.loads(text[start:i+1])
                except Exception:
                    pass
    return None


# ── Validadores de campos ──────────────────────────────────────────────────────

def validate_lote_payload(data: dict) -> tuple[bool, list[str]]:
    """
    Valida el payload de configuración de lote.
    Retorna (es_valido, lista_de_errores).
    """
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
    """Aplica valores por defecto a campos opcionales no especificados o vacíos."""
    result = dict(data)
    for field, meta in LOTE_FIELDS.items():
        val = result.get(field)
        # Apply default when field is absent, None, or an empty/whitespace string
        if (val is None or (isinstance(val, str) and val.strip() == '')) and 'default' in meta:
            result[field] = meta['default']
    return result


def missing_required_fields(data: dict) -> list[str]:
    """Retorna la lista de campos requeridos que faltan."""
    missing = []
    for field, meta in LOTE_FIELDS.items():
        if meta.get('requerido'):
            val = data.get(field)
            if val is None or str(val).strip() == '':
                missing.append(meta['label'])
    return missing


# ── Gestor de sesión de chat ──────────────────────────────────────────────────

class LoteOnboardingSession:
    """
    Encapsula el estado de una sesión de onboarding de lote.
    Mantiene el historial de mensajes y el payload acumulado.
    """

    def __init__(self, session_id: int, existing_payload: dict | None = None):
        self.session_id = session_id
        self.payload = existing_payload or {}
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

        # Inyectar contexto del estado actual en el último mensaje del sistema
        context_msg = {
            'role': 'system',
            'content': (
                f"Estado actual del formulario: {json.dumps(self.payload, ensure_ascii=False)}. "
                f"Campos faltantes requeridos: {missing_required_fields(self.payload)}. "
                f"Responde SOLO en JSON."
            )
        }
        messages_to_send = [self.messages[0], context_msg] + self.messages[1:]

        ok, raw = ollama.chat(messages_to_send)
        if not ok:
            logger.warning(f"[ai_service] Error Ollama: {raw}")
            return {
                'mensaje': f'⚠️ El asistente no pudo responder. Puedes continuar con el formulario manual o intentar de nuevo.\nDetalle: {raw}',
                'datos_detectados': {},
                'paso_actual': 'error',
                'campos_faltantes': missing_required_fields(self.payload),
                'listo_para_guardar': False,
                'error': raw,
            }

        try:
            result = json.loads(raw)
        except Exception:
            result = {'mensaje': raw, 'datos_detectados': {}, 'paso_actual': 'recopilando',
                      'campos_faltantes': missing_required_fields(self.payload), 'listo_para_guardar': False}

        # Merge datos_detectados con payload acumulado (no sobrescribir con null)
        nuevos = result.get('datos_detectados') or {}
        for k, v in nuevos.items():
            if v is not None and str(v).strip() not in ('', 'null', 'None'):
                self.payload[k] = v

        # Recalcular campos faltantes
        result['campos_faltantes'] = missing_required_fields(self.payload)
        result['payload_actual'] = self.payload
        result['listo_para_guardar'] = len(result['campos_faltantes']) == 0

        # Añadir respuesta del asistente al historial
        self.messages.append({'role': 'assistant', 'content': result.get('mensaje', '')})

        return result

    def _degraded_response(self) -> dict:
        return {
            'mensaje': '🔧 El asistente de IA no está disponible en este momento. Por favor completa el formulario manual.',
            'datos_detectados': {},
            'paso_actual': 'degradado',
            'campos_faltantes': missing_required_fields(self.payload),
            'payload_actual': self.payload,
            'listo_para_guardar': False,
            'degraded': True,
        }


# ── Health check al arrancar ──────────────────────────────────────────────────

def check_ollama_on_startup():
    """
    Verifica la disponibilidad de Ollama al iniciar la aplicación.
    No bloquea el arranque si Ollama no está disponible.
    """
    if not AI_ENABLED:
        logger.info('[ai_service] IA deshabilitada (AI_ENABLED=false)')
        return
    ok, msg = ollama.health_check()
    if ok:
        logger.info(f'[ai_service] Ollama OK — modelo: {OLLAMA_MODEL}')
    else:
        logger.warning(f'[ai_service] Ollama no disponible: {msg}. El modo degradado (formulario manual) estará activo.')
