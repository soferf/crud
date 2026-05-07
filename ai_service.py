"""
ai_service.py — Servicio GPT4All para onboarding asistido de lotes.

Variables de entorno:
    GPT4ALL_MODEL     → gpt4all-falcon-newbpe-q4_0.gguf
    AI_ENABLED        → true
"""

import os
import json
import re
import sys
import pathlib
import threading
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

logger = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────
GPT4ALL_MODEL = os.environ.get('GPT4ALL_MODEL', 'orca-mini-3b-gguf2-q4_0.gguf')
AI_ENABLED    = os.environ.get('AI_ENABLED', 'true').lower() == 'true'

# ── Campos del formulario de configuración de lote ───────────────────────────
LOTE_FIELDS = {
    'nombre_lote':             {'label': 'Nombre del lote',              'tipo': 'str',   'requerido': True},
    'propietario':             {'label': 'Nombre del propietario',        'tipo': 'str',   'requerido': True},
    'hectareas':               {'label': 'Hectáreas totales',             'tipo': 'float', 'requerido': True,  'min': 0.1,   'max': 50000},
    'municipio':               {'label': 'Municipio',                     'tipo': 'str',   'requerido': True},
    'departamento':            {'label': 'Departamento',                  'tipo': 'str',   'requerido': True},
    'cultivo_principal':       {'label': 'Cultivo principal',             'tipo': 'str',   'requerido': False, 'default': 'Arroz'},
    'fecha_inicio_operacion':  {'label': 'Fecha de inicio (YYYY-MM-DD)', 'tipo': 'date',  'requerido': False},
    'moneda':                  {'label': 'Moneda',                        'tipo': 'str',   'requerido': False, 'default': 'COP'},
    'meta_cargas_ha':          {'label': 'Meta de cargas por hectárea',   'tipo': 'int',   'requerido': False, 'default': 100, 'min': 1},
    'limite_gasto_ha':         {'label': 'Límite de gasto por ha ($)',    'tipo': 'float', 'requerido': False, 'default': 11000000, 'min': 1},
}

SYSTEM_PROMPT = """Eres un asistente que recoge datos de un lote arrocero en español colombiano. Sé muy breve.

Recopila en orden: nombre_lote, propietario, hectareas (número positivo), municipio, departamento.
Opcionales: cultivo_principal (default "Arroz"), fecha_inicio_operacion (YYYY-MM-DD), moneda (default "COP"), meta_cargas_ha (default 100), limite_gasto_ha (default 11000000).

Reglas: pregunta solo lo que falta. Acepta correcciones. Cuando tengas los 5 campos requeridos, muestra resumen y pide confirmación.

RESPONDE SOLO con este JSON (sin texto extra):
{"mensaje":"...","datos_detectados":{"nombre_lote":null,"propietario":null,"hectareas":null,"municipio":null,"departamento":null,"cultivo_principal":null,"fecha_inicio_operacion":null,"moneda":null,"meta_cargas_ha":null,"limite_gasto_ha":null},"paso_actual":"recopilando","campos_faltantes":[],"listo_para_guardar":false}
"""

# ── Singleton del modelo GPT4All ──────────────────────────────────────────────
_load_lock      = threading.Lock()
_generate_lock  = threading.Lock()
_model_instance = None

GENERATION_TIMEOUT = 25  # segundos máximos — modelo 3B q4_0 responde más rápido


def _get_model():
    """Carga el modelo GPT4All una sola vez y lo reutiliza."""
    global _model_instance
    if _model_instance is None:
        with _load_lock:
            if _model_instance is None:
                from gpt4all import GPT4All
                model_folder = _models_folder()
                logger.info(f'[ai_service] Cargando modelo: {GPT4ALL_MODEL} desde {model_folder}')
                _model_instance = GPT4All(
                    GPT4ALL_MODEL,
                    model_path=str(model_folder),
                    allow_download=False,
                    verbose=False,
                )
                logger.info('[ai_service] Modelo GPT4All listo.')
    return _model_instance


def _models_folder() -> pathlib.Path:
    """Retorna la carpeta de modelos por defecto de GPT4All."""
    candidates = []
    # Carpeta de la app de escritorio GPT4All en Windows (tiene prioridad si el modelo ya está ahí)
    if sys.platform == 'win32':
        desktop = pathlib.Path.home() / 'AppData' / 'Local' / 'nomic.ai' / 'GPT4All'
        candidates.append(desktop)
    # La librería gpt4all 2.x usa ~/.cache/gpt4all/
    cache = pathlib.Path.home() / '.cache' / 'gpt4all'
    candidates.append(cache)

    # Devolver la primera carpeta que contenga el modelo
    for folder in candidates:
        if (folder / GPT4ALL_MODEL).exists():
            return folder
    # Si no se encontró, devolver la primera existente o el cache por defecto
    for folder in candidates:
        if folder.exists():
            return folder
    return cache


# ── Cliente GPT4All ───────────────────────────────────────────────────────────

class GPT4AllClient:

    def __init__(self):
        self.model_name = GPT4ALL_MODEL

    def health_check(self) -> tuple[bool, str]:
        """Verifica que el paquete gpt4all esté instalado y el modelo disponible."""
        try:
            import gpt4all  # noqa
        except ImportError:
            return False, 'Paquete gpt4all no instalado. Ejecuta: pip install gpt4all'

        folder = _models_folder()
        model_path = folder / self.model_name
        if model_path.exists():
            return True, 'OK'

        return False, (
            f'Modelo "{self.model_name}" no encontrado en {folder}. '
            f'Descárgalo desde la aplicación GPT4All Desktop o ejecuta el chat una vez '
            f'para que se descargue automáticamente (puede tardar varios minutos).'
        )

    def chat(self, messages: list[dict]) -> tuple[bool, str]:
        """
        Genera una respuesta usando GPT4All con timeout.
        Acepta el mismo formato de mensajes que Ollama:
          [{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        system_parts = [m['content'] for m in messages if m['role'] == 'system']
        system_msg   = '\n\n'.join(system_parts) if system_parts else ''
        non_system   = [m for m in messages if m['role'] != 'system']

        if not non_system:
            return False, 'No hay mensajes de conversación.'
        if non_system[-1]['role'] != 'user':
            return False, 'El último mensaje debe ser del usuario.'

        new_user_msg  = non_system[-1]['content']
        prior_history = non_system[:-1]

        def _run():
            with _generate_lock:
                model = _get_model()
                with model.chat_session(system_prompt=system_msg):
                    model._history.extend(prior_history)
                    resp = model.generate(
                        new_user_msg,
                        max_tokens=60,
                        temp=0.1,
                        top_p=0.85,
                        top_k=20,
                        repeat_penalty=1.18,
                    )
            # Intentar parsear JSON
            try:
                parsed = json.loads(resp)
                return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                extracted = _extract_json_from_text(resp)
                if extracted:
                    return json.dumps(extracted, ensure_ascii=False)
                return resp

        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(_run)
                result = future.result(timeout=GENERATION_TIMEOUT)
            return True, result
        except FuturesTimeoutError:
            logger.warning('[ai_service] chat: timeout alcanzado')
            return False, f'El modelo tardó más de {GENERATION_TIMEOUT}s. Intenta con una pregunta más corta.'
        except Exception as e:
            logger.error(f'[ai_service] chat error: {e}')
            return False, str(e)

    def generate_text(self, messages: list[dict]) -> tuple[bool, str]:
        """
        Genera una respuesta en texto libre con timeout.
        Ideal para el asistente general del dashboard.
        """
        system_parts = [m['content'] for m in messages if m['role'] == 'system']
        system_msg   = '\n\n'.join(system_parts) if system_parts else ''
        non_system   = [m for m in messages if m['role'] != 'system']

        if not non_system or non_system[-1]['role'] != 'user':
            return False, 'Mensaje inválido.'

        new_user_msg  = non_system[-1]['content']
        prior_history = non_system[:-1]

        def _run():
            with _generate_lock:
                model = _get_model()
                with model.chat_session(system_prompt=system_msg):
                    model._history.extend(prior_history)
                    resp = model.generate(
                        new_user_msg,
                        max_tokens=160,
                        temp=0.1,
                        top_p=0.85,
                        top_k=20,
                        repeat_penalty=1.18,
                    )
            return resp.strip()

        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(_run)
                result = future.result(timeout=GENERATION_TIMEOUT)
            return True, result
        except FuturesTimeoutError:
            logger.warning('[ai_service] generate_text: timeout alcanzado')
            return False, f'El modelo tardó más de {GENERATION_TIMEOUT}s. Intenta con una pregunta más corta.'
        except Exception as e:
            logger.error(f'[ai_service] generate_text error: {e}')
            return False, str(e)


ai_client = GPT4AllClient()

DASHBOARD_SYSTEM_PROMPT = """Eres "AgroIA", asistente agrícola del sistema Arroceras Colombia.
Ayudas con: gastos, presupuesto, producción (cargas), trabajadores y recibos del lote.
Responde en español colombiano, breve (máx 2 párrafos). No inventes datos fuera del contexto dado.
"""


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
    # Último recurso: primer bloque { ... } balanceado
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

    def __init__(self, session_id: int, existing_payload: dict | None = None):
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
            logger.warning(f'[ai_service] Error GPT4All: {raw}')
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
    Verifica la disponibilidad de GPT4All al iniciar la aplicación.
    No bloquea el arranque si el modelo no está disponible.
    """
    if not AI_ENABLED:
        logger.info('[ai_service] IA deshabilitada (AI_ENABLED=false)')
        return
    ok, msg = ai_client.health_check()
    if ok:
        logger.info(f'[ai_service] GPT4All OK — modelo: {GPT4ALL_MODEL}')
    else:
        logger.warning(
            f'[ai_service] GPT4All no disponible: {msg}. '
            f'El modo degradado (formulario manual) estará activo.'
        )
