"""Genera las capturas del Anexo C conduciendo la app con Playwright."""
import os, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = os.path.join(os.path.dirname(__file__), "capturas")
os.makedirs(OUT, exist_ok=True)

PAGES = [
    ("01_landing_login", "/?form=login", "Pantalla de inicio / autenticación"),
    ("02_dashboard",     "/dashboard",   "Panel principal (dashboard)"),
    ("03_recibos_lista", "/recibos",     "Registro de operaciones — lista de recibos"),
    ("04_recibo_nuevo",  "/recibos/nuevo","Registro de operación — nuevo recibo"),
    ("05_trabajadores",  "/workers",     "Consulta de inventario de trabajadores"),
    ("06_produccion",    "/produccion",  "Producción / cosechas"),
    ("07_presupuesto",   "/presupuesto", "Presupuesto"),
    ("08_reportes",      "/reportes",    "Generación de reportes financieros"),
    ("09_humedad",       "/humedad",     "Módulo de humedad y riego"),
    ("10_config",        "/config",      "Configuración del sistema"),
]


def shoot(pg, name):
    """Intenta full_page; si falla, captura el viewport."""
    path = f"{OUT}/{name}.png"
    try:
        pg.screenshot(path=path, full_page=True, animations="disabled", timeout=12000)
    except Exception:
        pg.screenshot(path=path, full_page=False, animations="disabled", timeout=12000)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1366, "height": 900}, device_scale_factor=2)
    # Aborta cualquier petición a hosts externos (CDN/fonts) para que no
    # bloqueen el render dentro del sandbox sin red saliente.
    def _route(route):
        url = route.request.url
        if url.startswith("http://127.0.0.1:5000") or url.startswith("data:"):
            route.continue_()
        else:
            route.abort()
    ctx.route("**/*", _route)

    pg = ctx.new_page()
    pg.set_default_navigation_timeout(15000)

    # --- Captura del login (sin sesión) ---
    pg.goto(f"{BASE}/?form=login", wait_until="commit")
    time.sleep(2.0)
    shoot(pg, "01_landing_login")
    print("OK 01_landing_login")

    # --- Login: POST compartiendo las cookies del contexto ---
    pg.wait_for_selector("#login-email", state="attached", timeout=15000)
    token = pg.get_attribute('form[data-form="login"] input[name="csrf_token"]', "value")
    resp = pg.request.post(
        f"{BASE}/auth/login",
        form={"email": "demo@arrocera.test", "password": "Demo1234", "csrf_token": token},
    )
    print("login POST status:", resp.status, "url:", resp.url)

    if "select-lote" in pg.url:
        try:
            pg.goto(f"{BASE}/select-lote/1", wait_until="commit")
            time.sleep(1.5)
        except Exception as e:
            print("select-lote err", e)

    # --- Resto de páginas autenticadas ---
    for name, path, _desc in PAGES[1:]:
        try:
            pg.goto(f"{BASE}{path}", wait_until="commit")
            time.sleep(1.8)
            shoot(pg, name)
            print("OK", name, "->", pg.url)
        except Exception as e:
            print("ERR", name, repr(e)[:120])

    b.close()
print("DONE")
