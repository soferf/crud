# CRUD Arrocera (Flask + MySQL)

Aplicacion web para gestionar trabajadores, recibos, produccion y reportes en un contexto arrocero.

## Tecnologias
- Python
- Flask
- MySQL
- HTML, CSS y JavaScript

## Modulos principales
- Autenticacion de usuarios (registro, login, recuperacion)
- Gestion de trabajadores
- Registro y consulta de recibos
- Produccion y reportes
- Generacion de PDF

## Ejecucion local
1. Crear y activar entorno virtual.
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Configurar variables en `.env` (puedes partir de `.env.example`).
4. Ejecutar la app:
   ```bash
   python app.py
   ```

## Notas
- La base de datos por defecto es `arrocera_db` en MySQL local.
- El proyecto crea tablas necesarias en el arranque.

## Autor
Proyecto personal para portafolio.
