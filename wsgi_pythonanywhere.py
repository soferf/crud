"""
wsgi_pythonanywhere.py — Plantilla del archivo WSGI para PythonAnywhere.

NO se ejecuta localmente. Copia el CONTENIDO de este archivo dentro del
"WSGI configuration file" que PythonAnywhere crea en la pestaña "Web"
(ruta tipo: /var/www/USERNAME_pythonanywhere_com_wsgi.py), reemplazando
TODO lo que traiga por defecto.

Cambia USERNAME por tu usuario de PythonAnywhere.
"""
import os
import sys

# 1) Ruta del proyecto (carpeta que contiene app.py)
PROJECT_DIR = '/home/USERNAME/ARROCERA/crud'

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# 2) Trabajar desde la carpeta del proyecto para que .env, templates/,
#    static/ y uploads/ se resuelvan con rutas relativas.
os.chdir(PROJECT_DIR)

# 3) Importar la app Flask ya configurada. El objeto debe llamarse `application`.
from app import app as application  # noqa: E402
