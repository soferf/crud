"""
db.py — Conexión a la base de datos MySQL.
"""
import mysql.connector
from config import DB_CONFIG


def get_db_connection():
    """Retorna una nueva conexión a arrocera_db."""
    return mysql.connector.connect(**DB_CONFIG)
