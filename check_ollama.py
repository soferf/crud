"""
check_ollama.py — Diagnóstico rápido de la integración Ollama.
Uso:  python check_ollama.py
"""
import os, sys, json

# Cargar .env igual que la app
def _load_dotenv():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())

_load_dotenv()

OK   = '\033[92m✔\033[0m'
FAIL = '\033[91m✘\033[0m'
WARN = '\033[93m⚠\033[0m'

def check(label, passed, detail=''):
    icon = OK if passed else FAIL
    print(f"  {icon}  {label}" + (f"\n       → {detail}" if detail else ''))
    return passed

print("\n══════════════════════════════════════════")
print("  Diagnóstico Ollama — Contabilidad Arroceras")
print("══════════════════════════════════════════\n")

# 1. Variables de entorno
ai_enabled     = os.environ.get('AI_ENABLED', 'true').lower() == 'true'
base_url       = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
model          = os.environ.get('OLLAMA_MODEL',    'qwen2.5:7b-instruct')
timeout        = int(os.environ.get('OLLAMA_TIMEOUT', '30'))

print("1. Variables de entorno:")
check("AI_ENABLED",      ai_enabled,          f"AI_ENABLED={os.environ.get('AI_ENABLED','(no definida, default true)')}")
check("OLLAMA_BASE_URL", bool(base_url),       base_url)
check("OLLAMA_MODEL",    bool(model),          model)
check("OLLAMA_TIMEOUT",  timeout > 0,          str(timeout) + 's')
print()

if not ai_enabled:
    print(f"  {WARN}  AI_ENABLED=false → el asistente está deshabilitado. Cambia a true para activarlo.\n")
    sys.exit(0)

# 2. Conectividad con Ollama
import urllib.request, urllib.error
print("2. Servicio Ollama:")
try:
    resp = urllib.request.urlopen(f'{base_url}/api/tags', timeout=5)
    body = json.loads(resp.read().decode())
    tags = [m.get('name','') for m in body.get('models', [])]
    check("Ollama responde en " + base_url, True)

    # 3. Modelo disponible
    print("\n3. Modelo:")
    model_found = any(model in n or n.startswith(model.split(':')[0]) for n in tags)
    check(f"Modelo '{model}' disponible", model_found,
          f"Modelos instalados: {', '.join(tags) or 'ninguno'}"
          + (f"\n       Ejecuta: ollama pull {model}" if not model_found else ''))

    # 4. Test de chat
    if model_found:
        print("\n4. Test de chat (respuesta rápida):")
        payload = json.dumps({
            'model': model,
            'messages': [{'role':'user','content':'Di solo: OK'}],
            'stream': False,
            'options': {'temperature': 0, 'num_predict': 5},
        }).encode()
        req = urllib.request.Request(
            f'{base_url}/api/chat', data=payload,
            headers={'Content-Type':'application/json'}, method='POST'
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            content = json.loads(r.read().decode()).get('message',{}).get('content','')
        check("Chat responde", bool(content.strip()), f"Respuesta: {content.strip()!r}")

except urllib.error.URLError as e:
    check("Ollama responde en " + base_url, False,
          f"{e}\n       Solución: ejecuta 'ollama serve' en una terminal y deja abierta.")
    print()
    sys.exit(1)

print("\n══════════════════════════════════════════")
print("  Todo OK — reinicia app.py y prueba el wizard IA")
print("══════════════════════════════════════════\n")
