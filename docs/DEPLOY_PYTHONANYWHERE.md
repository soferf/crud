# Desplegar la app en PythonAnywhere

> Reemplaza `USERNAME` por tu usuario de PythonAnywhere en todos los comandos.

## ⚠️ Antes de empezar: plan gratuito vs. de pago
- **MySQL**: funciona en todos los planes. ✅
- **Envío de correo (Gmail SMTP) y la IA (Gemini API)**: en el **plan gratuito**
  PythonAnywhere **bloquea** el internet saliente que no esté en su whitelist.
  Gmail y Gemini **no** están en esa lista → los **códigos de registro por email**
  y el **asistente de IA** NO funcionarán en el plan gratis.
- Para funcionalidad completa necesitas el plan **Hacker ($5/mes)** (internet sin
  restricciones). En gratis puedes probar todo lo demás y crear el usuario a mano.

---

## 1. Subir el código
En una consola **Bash** de PythonAnywhere:

```bash
# Opción A — con Git (recomendado). Antes debes haber hecho commit de TODOS
# los archivos nuevos (ciclo_service.py, security_service.py, backup_service.py, etc.)
git clone https://github.com/TU_USUARIO/TU_REPO.git ARROCERA
# la app queda en ~/ARROCERA/crud

# Opción B — subir un .zip desde la pestaña "Files" y descomprimir:
#   unzip crud.zip -d ~/ARROCERA
```

## 2. Crear la base de datos MySQL
Pestaña **Databases** → crea una base. Quedará como `USERNAME$arrocera_db`.
Define una contraseña. Anota estos datos:
- Host: `USERNAME.mysql.pythonanywhere-services.com`
- Usuario: `USERNAME`
- Base: `USERNAME$arrocera_db`

## 3. Crear el virtualenv e instalar dependencias
```bash
mkvirtualenv --python=/usr/bin/python3.10 arrocera
pip install -r ~/ARROCERA/crud/requirements.txt
```

## 4. Crear el archivo `.env`
```bash
cd ~/ARROCERA/crud
nano .env
```
Contenido (ajusta valores):
```
SECRET_KEY=pon-una-clave-larga-y-aleatoria
DB_HOST=USERNAME.mysql.pythonanywhere-services.com
DB_USER=USERNAME
DB_PASSWORD=tu-password-de-mysql
DB_NAME=USERNAME$arrocera_db
APP_URL=https://USERNAME.pythonanywhere.com

# Solo funcionan en plan de pago:
GEMINI_API_KEY=tu-api-key-de-google-ai-studio
AI_ENABLED=true
MAIL_USERNAME=tucorreo@gmail.com
MAIL_PASSWORD=tu-app-password-de-gmail
```

## 5. Inicializar tablas, triggers y plantillas (¡una sola vez!)
El servidor web NO corre el bloque `__main__`, así que hazlo manual:
```bash
cd ~/ARROCERA/crud
workon arrocera
mkdir -p uploads
python -c "from templates_seeder import init_templates; from init_db import init_database; init_templates(); init_database(); print('BD lista')"
```

## 6. Crear la Web App
Pestaña **Web** → **Add a new web app** → **Manual configuration** →
elige **Python 3.10**.

- **Virtualenv**: escribe `/home/USERNAME/.virtualenvs/arrocera`
- **WSGI configuration file**: haz clic para editarlo y **reemplaza todo** por el
  contenido de `wsgi_pythonanywhere.py` (cambiando `USERNAME`).
- **Static files**: agrega el mapeo
  - URL: `/static/`  →  Directory: `/home/USERNAME/ARROCERA/crud/static/`

## 7. Recargar
Botón verde **Reload** en la pestaña Web. Abre `https://USERNAME.pythonanywhere.com`.

---

## Si algo falla
- Revisa el **Error log** (enlace en la pestaña Web).
- `ModuleNotFoundError`: falta un archivo sin commitear, o el virtualenv no quedó
  seleccionado / faltó `pip install -r requirements.txt`.
- Error de MySQL: revisa host/usuario/base en `.env` (la base lleva `USERNAME$`).
- Login sin email (plan gratis): crea un usuario ya verificado por consola o
  márcalo con `UPDATE users SET email_verified=TRUE WHERE email='...';`.
