"""Runner temporal: levanta la app en modo multihilo para las capturas."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("AUTH_SEND_LOGIN_ALERT", "false")
from templates_seeder import init_templates
from init_db import init_database
import app as _app  # registra rutas
from extensions import app

init_templates()
init_database()
app.run(host="127.0.0.1", port=5000, debug=False, threaded=True, use_reloader=False)
