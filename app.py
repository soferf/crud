"""
app.py — Thin orchestrator. Imports all route modules to register
         their routes on the shared Flask app instance from extensions.py.

Original monolith has been split into:
  config.py, extensions.py, db.py, utils.py, mail_service.py, auth_codes.py,
  session_service.py, budget.py, init_db.py, templates_seeder.py,
  routes_auth.py, routes_lotes.py, routes_workers.py, routes_recibos.py,
  routes_reportes.py, routes_produccion.py, routes_presupuesto.py, routes_config.py
"""
from extensions import app  # noqa: F401 — creates and configures the Flask app

# Import route modules as side effects so their @app.route decorators register
import routes_auth        # noqa: F401
import routes_lotes       # noqa: F401
import routes_workers     # noqa: F401
import routes_recibos     # noqa: F401
import routes_reportes    # noqa: F401
import routes_produccion  # noqa: F401
import routes_presupuesto # noqa: F401
import routes_config      # noqa: F401
import routes_ai          # noqa: F401
import routes_ahorro      # noqa: F401

if __name__ == '__main__':
    import os
    from templates_seeder import init_templates
    from init_db import init_database
    init_templates()
    init_database()
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode)
