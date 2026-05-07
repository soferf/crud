"""
init_db.py — Inicialización y migración de la base de datos.
"""
import os
import json
from datetime import datetime

import mysql.connector

from config import DB_CONFIG
from db import get_db_connection


def init_database():
    conn = mysql.connector.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'],
                                   password=DB_CONFIG['password'])
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    cursor.close()
    conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()

    datadir_cache = None

    def _fix_orphan_tablespace(table_name):
        nonlocal datadir_cache
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                (DB_CONFIG['database'], table_name),
            )
            if cursor.fetchone()[0] > 0:
                return False
            if datadir_cache is None:
                cursor.execute("SHOW VARIABLES LIKE 'datadir'")
                datadir_cache = cursor.fetchone()[1]
            ibd_path = os.path.join(datadir_cache, DB_CONFIG['database'], f"{table_name}.ibd")
            if not os.path.exists(ibd_path):
                return False
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup = ibd_path + f'.orphan.{stamp}.bak'
            os.replace(ibd_path, backup)
            print(f"[db-repair] tablespace huerfano movido: {backup}")
            return True
        except Exception:
            return False

    def ensure_table(table_name, create_sql):
        try:
            cursor.execute(create_sql)
            cursor.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
            cursor.fetchone()
        except mysql.connector.Error as e:
            errno = getattr(e, 'errno', None)
            if errno in (1813, 1932):
                if errno == 1813:
                    _fix_orphan_tablespace(table_name)
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                try:
                    cursor.execute(create_sql.replace("IF NOT EXISTS ", "", 1))
                    cursor.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
                    cursor.fetchone()
                except mysql.connector.Error as e2:
                    if getattr(e2, 'errno', None) == 1813 and _fix_orphan_tablespace(table_name):
                        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                        cursor.execute(create_sql.replace("IF NOT EXISTS ", "", 1))
                        cursor.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
                        cursor.fetchone()
                    else:
                        raise
            else:
                raise

    ensure_table("workers", """
        CREATE TABLE IF NOT EXISTS workers (
            id_worker INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            lastname VARCHAR(100) NOT NULL,
            cc VARCHAR(20) UNIQUE NOT NULL,
            phone_number VARCHAR(20) NOT NULL,
            email VARCHAR(100),
            trabajo_desarrolla ENUM('fumigador','agronomo','administrador','operario') NOT NULL,
            fecha_ingreso DATE,
            activo BOOLEAN DEFAULT TRUE,
            observaciones TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for col_name, col_type in [
        ("foto",              "VARCHAR(255)"),
        ("alias",             "VARCHAR(100)"),
        ("direccion",         "VARCHAR(100)"),
        ("ciudad",            "VARCHAR(50)"),
        ("concepto_habitual", "TEXT"),
        ("valor_habitual",    "DECIMAL(12,2)"),
        ("rol",               "VARCHAR(60)"),
        ("roles_adicionales", "TEXT"),
        ("conceptos_pago",    "TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE workers ADD COLUMN {col_name} {col_type}")
        except mysql.connector.Error:
            pass

    ensure_table("users", """
        CREATE TABLE IF NOT EXISTS users (
            id_user INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(120) NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for col_name, col_def in [("email_verified", "BOOLEAN DEFAULT FALSE"), ("verify_token", "VARCHAR(100)")]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass

    try:
        cursor.execute("""
            UPDATE users SET email_verified = TRUE
            WHERE email_verified = FALSE AND verify_token IS NULL
        """)
    except Exception:
        pass

    ensure_table("password_reset_tokens", """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    INT NOT NULL,
            token      VARCHAR(100) UNIQUE NOT NULL,
            expires_at DATETIME NOT NULL,
            used       BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id_user) ON DELETE CASCADE
        )
    """)

    ensure_table("auth_email_codes", """
        CREATE TABLE IF NOT EXISTS auth_email_codes (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            email        VARCHAR(120) NOT NULL,
            purpose      ENUM('signup','reset') NOT NULL,
            code         VARCHAR(6) NOT NULL,
            payload_json TEXT,
            expires_at   DATETIME NOT NULL,
            used         BOOLEAN DEFAULT FALSE,
            attempts     INT DEFAULT 0,
            max_attempts INT DEFAULT 5,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_auth_codes_email_purpose (email, purpose)
        )
    """)

    ensure_table("recibos", """
        CREATE TABLE IF NOT EXISTS recibos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            serial INT NOT NULL,
            fecha DATE,
            proveedor VARCHAR(100) NOT NULL,
            nit VARCHAR(20),
            direccion VARCHAR(100),
            telefono VARCHAR(20),
            ciudad VARCHAR(50),
            concepto TEXT,
            valor_operacion DECIMAL(12,2),
            neto_a_pagar DECIMAL(12,2),
            tipo VARCHAR(20) DEFAULT 'normal',
            lote_id INT DEFAULT NULL,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_serial_lote (serial, lote_id)
        )
    """)

    # Migration: if recibos exists with serial as PRIMARY KEY (old schema),
    # convert to auto-increment id + composite unique key.
    try:
        cursor.execute("SHOW KEYS FROM recibos WHERE Key_name='PRIMARY' AND Column_name='serial'")
        if cursor.fetchone():
            # serial is the PK — need to migrate
            cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=%s AND table_name='recibos' AND column_name='id'",
                           (DB_CONFIG['database'],))
            has_id_col = cursor.fetchone()[0] > 0
            if not has_id_col:
                cursor.execute("ALTER TABLE recibos MODIFY COLUMN serial INT NOT NULL")
                cursor.execute("ALTER TABLE recibos DROP PRIMARY KEY")
                cursor.execute("ALTER TABLE recibos ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST")
                try:
                    cursor.execute("ALTER TABLE recibos ADD UNIQUE KEY uq_serial_lote (serial, lote_id)")
                except Exception:
                    pass
                conn.commit()
                print("[db-migrate] recibos: serial PK migrado a id AUTO_INCREMENT + UNIQUE(serial, lote_id)")
    except Exception as _me:
        print(f"[db-migrate] recibos migration skipped: {_me}")

    ensure_table("config", """
        CREATE TABLE IF NOT EXISTS config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            clave VARCHAR(50) NOT NULL,
            valor VARCHAR(200),
            lote_id INT DEFAULT NULL,
            UNIQUE KEY uq_config_clave_lote (clave, lote_id)
        )
    """)

    try:
        cursor.execute("ALTER TABLE config ADD COLUMN lote_id INT DEFAULT NULL")
        cursor.execute("ALTER TABLE config ADD UNIQUE KEY uq_config_clave_lote (clave, lote_id)")
        conn.commit()
    except mysql.connector.Error as _e:
        if getattr(_e, 'errno', None) not in (1060, 1061):
            raise

    try:
        cursor.execute("SHOW COLUMNS FROM config LIKE 'id'")
        has_id = cursor.fetchone() is not None
        cursor.execute("SHOW INDEX FROM config WHERE Key_name = 'PRIMARY'")
        primary_cols = [row[4] for row in cursor.fetchall()]
        if primary_cols == ['clave']:
            cursor.execute("ALTER TABLE config DROP PRIMARY KEY")
            if not has_id:
                cursor.execute("ALTER TABLE config ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST")
            else:
                cursor.execute("ALTER TABLE config ADD PRIMARY KEY (id)")
            conn.commit()
        elif not has_id:
            cursor.execute("ALTER TABLE config ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST")
            conn.commit()
    except mysql.connector.Error as _e:
        if getattr(_e, 'errno', None) not in (1060, 1068, 1091):
            raise

    try:
        cursor.execute("ALTER TABLE config DROP INDEX clave")
        conn.commit()
    except mysql.connector.Error as _e:
        if getattr(_e, 'errno', None) != 1091:
            raise

    try:
        cursor.execute("ALTER TABLE config ADD UNIQUE KEY uq_config_clave_lote (clave, lote_id)")
        conn.commit()
    except mysql.connector.Error as _e:
        if getattr(_e, 'errno', None) != 1061:
            raise

    ensure_table("cosechas", """
        CREATE TABLE IF NOT EXISTS cosechas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fecha DATE NOT NULL,
            lote VARCHAR(100) DEFAULT 'El Mangon',
            hectareas DECIMAL(6,2) DEFAULT 20.00,
            cargas INT NOT NULL,
            kg_total DECIMAL(10,2),
            precio_carga DECIMAL(10,2),
            valor_total DECIMAL(14,2),
            observaciones TEXT,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    try:
        cursor.execute("""ALTER TABLE workers MODIFY trabajo_desarrolla
            ENUM('fumigador','agronomo','administrador','operario','regador',
                 'bombero','despalillador','operario_maquinas','transportador',
                 'versatil','polivalente')""")
    except Exception:
        pass

    for col_def in [
        ("roles_adicionales", "TEXT"),
        ("telefono",          "VARCHAR(20)"),
        ("rol",               "VARCHAR(150)"),
        ("conceptos_pago",    "TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE workers ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass

    for col_def in [
        ("conceptos_json", "TEXT"),
        ("rte_fte",        "DECIMAL(12,2) DEFAULT 0"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE recibos ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass

    for col_def in [
        ("variedad_semilla",  "VARCHAR(100)"),
        ("origen_semilla",    "VARCHAR(100)"),
        ("bultos_ha",         "DECIMAL(8,2)"),
        ("total_bultos",      "DECIMAL(8,2)"),
        ("metodo_siembra",    "ENUM('al_voleo','sembradora','labranza_minima','otro') DEFAULT 'al_voleo'"),
        ("fase",              "ENUM('siembra','cosecha') DEFAULT 'cosecha'"),
        ("fecha_siembra",     "DATE"),
        ("precio_carga",      "DECIMAL(10,2)"),
        ("valor_total",       "DECIMAL(14,2)"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE cosechas ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass

    ensure_table("lotes", """
        CREATE TABLE IF NOT EXISTS lotes (
            id                    INT AUTO_INCREMENT PRIMARY KEY,
            nombre                VARCHAR(120) NOT NULL,
            propietario_nombre    VARCHAR(120),
            propietario_documento VARCHAR(30),
            propietario_telefono  VARCHAR(20),
            propietario_email     VARCHAR(120),
            propietario_direccion VARCHAR(150),
            administrador_nombre  VARCHAR(120),
            administrador_telefono VARCHAR(20),
            administrador_email   VARCHAR(120),
            hectareas             DECIMAL(8,2) DEFAULT 20.00,
            area_sembrada_ha      DECIMAL(8,2),
            municipio             VARCHAR(100),
            departamento          VARCHAR(100),
            vereda                VARCHAR(100),
            tipo_tenencia         ENUM('propia','arriendo','aparceria','usufructo','otro') DEFAULT 'propia',
            cultivo_principal     VARCHAR(80) DEFAULT 'Arroz',
            fecha_inicio_operacion DATE,
            moneda                VARCHAR(10) DEFAULT 'COP',
            meta_cargas_ha        INT DEFAULT 100,
            limite_gasto_ha       DECIMAL(14,2) DEFAULT 11000000,
            estado                ENUM('activo','inactivo') DEFAULT 'activo',
            created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for _col, _typedef in [
        ("propietario_documento",  "VARCHAR(30)"),
        ("propietario_telefono",   "VARCHAR(20)"),
        ("propietario_email",      "VARCHAR(120)"),
        ("propietario_direccion",  "VARCHAR(150)"),
        ("administrador_nombre",   "VARCHAR(120)"),
        ("administrador_telefono", "VARCHAR(20)"),
        ("administrador_email",    "VARCHAR(120)"),
        ("area_sembrada_ha",       "DECIMAL(8,2)"),
        ("vereda",                 "VARCHAR(100)"),
        ("tipo_tenencia",          "ENUM('propia','arriendo','aparceria','usufructo','otro') DEFAULT 'propia'"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE lotes ADD COLUMN {_col} {_typedef}")
        except mysql.connector.Error:
            pass

    ensure_table("roles", """
        CREATE TABLE IF NOT EXISTS roles (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            nombre      VARCHAR(60) UNIQUE NOT NULL,
            descripcion VARCHAR(200),
            es_global   BOOLEAN DEFAULT FALSE
        )
    """)

    ensure_table("permissions", """
        CREATE TABLE IF NOT EXISTS permissions (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            clave       VARCHAR(60) UNIQUE NOT NULL,
            descripcion VARCHAR(200)
        )
    """)

    ensure_table("role_permissions", """
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id       INT NOT NULL,
            permission_id INT NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id)       REFERENCES roles(id)       ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(id)  ON DELETE CASCADE
        )
    """)

    ensure_table("user_lote_roles", """
        CREATE TABLE IF NOT EXISTS user_lote_roles (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    INT NOT NULL,
            lote_id    INT NOT NULL,
            role_id    INT NOT NULL,
            invited_by INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_user_lote (user_id, lote_id),
            FOREIGN KEY (user_id)    REFERENCES users(id_user) ON DELETE CASCADE,
            FOREIGN KEY (lote_id)    REFERENCES lotes(id)      ON DELETE CASCADE,
            FOREIGN KEY (role_id)    REFERENCES roles(id)      ON DELETE RESTRICT
        )
    """)

    ensure_table("user_global_roles", """
        CREATE TABLE IF NOT EXISTS user_global_roles (
            user_id    INT NOT NULL,
            role_id    INT NOT NULL,
            PRIMARY KEY (user_id, role_id),
            FOREIGN KEY (user_id)  REFERENCES users(id_user) ON DELETE CASCADE,
            FOREIGN KEY (role_id)  REFERENCES roles(id)      ON DELETE CASCADE
        )
    """)

    ensure_table("labor_catalog_global", """
        CREATE TABLE IF NOT EXISTS labor_catalog_global (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            nombre      VARCHAR(120) NOT NULL,
            descripcion TEXT,
            valor_base  DECIMAL(12,2),
            unidad      VARCHAR(40) DEFAULT 'jornal',
            activo      BOOLEAN DEFAULT TRUE,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    ensure_table("labor_lote_overrides", """
        CREATE TABLE IF NOT EXISTS labor_lote_overrides (
            lote_id        INT NOT NULL,
            labor_id       INT NOT NULL,
            valor_override DECIMAL(12,2) NOT NULL,
            PRIMARY KEY (lote_id, labor_id),
            FOREIGN KEY (lote_id)  REFERENCES lotes(id)                ON DELETE CASCADE,
            FOREIGN KEY (labor_id) REFERENCES labor_catalog_global(id) ON DELETE CASCADE
        )
    """)

    ensure_table("lote_invitations", """
        CREATE TABLE IF NOT EXISTS lote_invitations (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            lote_id     INT NOT NULL,
            email       VARCHAR(120) NOT NULL,
            role_id     INT NOT NULL,
            token       VARCHAR(100) UNIQUE NOT NULL,
            invited_by  INT NOT NULL,
            expires_at  DATETIME NOT NULL,
            used        BOOLEAN DEFAULT FALSE,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lote_id)    REFERENCES lotes(id)      ON DELETE CASCADE,
            FOREIGN KEY (role_id)    REFERENCES roles(id)      ON DELETE RESTRICT,
            FOREIGN KEY (invited_by) REFERENCES users(id_user) ON DELETE CASCADE
        )
    """)

    ensure_table("ai_sessions", """
        CREATE TABLE IF NOT EXISTS ai_sessions (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    INT NOT NULL,
            status     ENUM('pending','confirmed','cancelled') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id_user) ON DELETE CASCADE
        )
    """)

    ensure_table("ai_messages", """
        CREATE TABLE IF NOT EXISTS ai_messages (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            session_id INT NOT NULL,
            role       ENUM('user','assistant','system') NOT NULL,
            content    TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES ai_sessions(id) ON DELETE CASCADE
        )
    """)

    ensure_table("presupuesto_recargas", """
        CREATE TABLE IF NOT EXISTS presupuesto_recargas (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            lote_id     INT NOT NULL,
            monto       DECIMAL(15,2) NOT NULL,
            descripcion VARCHAR(255) DEFAULT '',
            fecha       DATE NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_prec_lote (lote_id)
        )
    """)

    ensure_table("ai_form_state", """
        CREATE TABLE IF NOT EXISTS ai_form_state (
            session_id   INT PRIMARY KEY,
            payload_json TEXT,
            step         VARCHAR(40) DEFAULT 'recopilando',
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES ai_sessions(id) ON DELETE CASCADE
        )
    """)

    for tbl in ['recibos', 'workers', 'cosechas']:
        try:
            cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN lote_id INT DEFAULT NULL")
        except Exception:
            pass

    for tbl in ['recibos', 'workers', 'cosechas']:
        try:
            cursor.execute(f"""
                ALTER TABLE {tbl}
                ADD CONSTRAINT fk_{tbl}_lote
                FOREIGN KEY (lote_id) REFERENCES lotes(id) ON DELETE SET NULL
            """)
        except Exception:
            pass

    conn.commit()
    cursor.close()
    conn.close()

    _seed_roles_and_permissions()
    _import_trabajadores_from_json()
    _migrate_existing_data_to_initial_lote()


def _seed_roles_and_permissions():
    """Inserta roles, permisos y asignaciones iniciales si no existen."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        roles = [
            ('superadmin',    'Acceso total al sistema',                          True),
            ('duenio_lote',   'Propietario del lote — acceso completo al lote',   False),
            ('admin_lote',    'Administrador operativo del lote',                  False),
            ('operador_lote', 'Puede crear/editar recibos, trabajadores, cosechas',False),
            ('consulta_lote', 'Solo lectura',                                      False),
        ]
        for nombre, desc, es_global in roles:
            cursor.execute(
                "INSERT IGNORE INTO roles (nombre, descripcion, es_global) VALUES (%s,%s,%s)",
                (nombre, desc, es_global)
            )

        perms = [
            ('lote.view',         'Ver información del lote'),
            ('lote.manage',       'Gestionar configuración del lote'),
            ('worker.view',       'Ver trabajadores'),
            ('worker.create',     'Registrar trabajadores'),
            ('worker.edit',       'Editar trabajadores'),
            ('worker.toggle',     'Activar/desactivar trabajadores'),
            ('recibo.view',       'Ver recibos'),
            ('recibo.create',     'Crear recibos'),
            ('recibo.edit',       'Editar recibos'),
            ('recibo.delete',     'Eliminar recibos'),
            ('produccion.view',   'Ver registros de producción'),
            ('produccion.create', 'Registrar producción/cosechas'),
            ('produccion.edit',   'Editar registros de producción'),
            ('report.view',       'Ver reportes y estadísticas'),
            ('user.invite',       'Invitar usuarios al lote'),
            ('user.assign_role',  'Asignar roles a usuarios del lote'),
            ('config.manage',     'Gestionar configuración de la aplicación'),
        ]
        for clave, desc in perms:
            cursor.execute(
                "INSERT IGNORE INTO permissions (clave, descripcion) VALUES (%s,%s)",
                (clave, desc)
            )
        conn.commit()

        role_perm_map = {
            'superadmin':    [p[0] for p in perms],
            'duenio_lote':   [p[0] for p in perms],
            'admin_lote':    [
                'lote.view','lote.manage','worker.view','worker.create','worker.edit',
                'worker.toggle','recibo.view','recibo.create','recibo.edit','recibo.delete',
                'produccion.view','produccion.create','produccion.edit','report.view',
                'user.invite','config.manage',
            ],
            'operador_lote': [
                'lote.view','worker.view','worker.create','worker.edit',
                'recibo.view','recibo.create','recibo.edit',
                'produccion.view','produccion.create','report.view',
            ],
            'consulta_lote': [
                'lote.view','worker.view','recibo.view','produccion.view','report.view',
            ],
        }
        for rol_nombre, perm_claves in role_perm_map.items():
            cursor.execute("SELECT id FROM roles WHERE nombre=%s", (rol_nombre,))
            row = cursor.fetchone()
            if not row:
                continue
            role_id = row[0]
            for clave in perm_claves:
                cursor.execute("SELECT id FROM permissions WHERE clave=%s", (clave,))
                prow = cursor.fetchone()
                if prow:
                    cursor.execute(
                        "INSERT IGNORE INTO role_permissions (role_id, permission_id) VALUES (%s,%s)",
                        (role_id, prow[0])
                    )
        conn.commit()

        cursor.execute("SELECT id FROM lotes WHERE nombre='El Mangon'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO lotes
                  (nombre, propietario_nombre, hectareas, municipio, departamento,
                   cultivo_principal, moneda, meta_cargas_ha, limite_gasto_ha, estado)
                VALUES ('El Mangon','Fernando',20,'','','Arroz','COP',100,11000000,'activo')
            """)
            conn.commit()

        labores = [
            ('Despalillada',   'Labor de despalille del arroz',          40000, 'jornal'),
            ('Desagüe',        'Labor de desagüe del lote',              45000, 'jornal'),
            ('Abonada',        'Aplicación de abono al cultivo',         40000, 'jornal'),
            ('Fumigación',     'Aplicación de agroquímicos',             50000, 'jornal'),
            ('Regada',         'Labor de riego del cultivo',             40000, 'jornal'),
            ('Cosecha',        'Labor de cosecha del arroz',             55000, 'jornal'),
            ('Transporte',     'Transporte de insumos o cosecha',        80000, 'viaje'),
            ('Maquinaria',     'Uso de maquinaria agrícola',            200000, 'hora'),
            ('Administración', 'Gestión administrativa del lote',       800000, 'mes'),
        ]
        for nombre, desc, valor, unidad in labores:
            cursor.execute(
                "INSERT IGNORE INTO labor_catalog_global (nombre, descripcion, valor_base, unidad) VALUES (%s,%s,%s,%s)",
                (nombre, desc, valor, unidad)
            )
        conn.commit()
        cursor.close(); conn.close()
        print('[seed] Roles, permisos y lote inicial configurados.')
    except Exception as e:
        print(f'[seed] Error: {e}')


def _migrate_existing_data_to_initial_lote():
    """Asigna lote_id=1 (El Mangon) a todos los registros que no tienen lote_id."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM lotes WHERE nombre='El Mangon' LIMIT 1")
        row = cursor.fetchone()
        if not row:
            cursor.close(); conn.close()
            return
        lote_id = row[0]
        for tbl in ['recibos', 'workers', 'cosechas']:
            cursor.execute(f"UPDATE {tbl} SET lote_id=%s WHERE lote_id IS NULL", (lote_id,))
        cursor.execute("""
            DELETE c_null FROM config c_null
            JOIN config c_lote ON c_null.clave = c_lote.clave
             AND c_null.lote_id IS NULL AND c_lote.lote_id = %s
        """, (lote_id,))
        cursor.execute("""
            UPDATE config c
            LEFT JOIN config c_existing ON c_existing.clave = c.clave AND c_existing.lote_id = %s
            SET c.lote_id = %s
            WHERE c.lote_id IS NULL AND c_existing.clave IS NULL
        """, (lote_id, lote_id))
        conn.commit()
        cursor.close(); conn.close()
        print(f'[migration] Datos existentes asignados al lote_id={lote_id} (El Mangon).')
    except Exception as e:
        print(f'[migration] Error: {e}')


def _import_trabajadores_from_json():
    """Import/update workers from data/trabajadores_arrocera.json into DB."""
    json_path = os.path.join(os.path.dirname(__file__), 'data', 'trabajadores_arrocera.json')
    if not os.path.exists(json_path):
        return
    try:
        with open(json_path, encoding='utf-8') as f:
            workers_data = json.load(f)
    except Exception as e:
        print(f"[import] Error reading JSON: {e}")
        return

    ROL_TO_ENUM = {
        'agronomo': 'agronomo', 'ingeniero': 'agronomo',
        'regador': 'regador', 'bombero': 'bombero',
        'despalillador': 'despalillador', 'fumigador': 'fumigador',
        'transportador': 'transportador', 'transporte': 'transportador',
        'maquinas': 'operario_maquinas', 'motosierra': 'operario',
        'administrador': 'administrador', 'arrendador': 'administrador',
        'arrendatario': 'administrador', 'propietario': 'operario',
    }

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        imported = 0
        updated = 0
        for w in workers_data:
            nit = (w.get('nit') or w.get('cedula') or '').strip()
            if not nit:
                continue
            nombre_completo = w.get('nombre_completo', '').strip()
            parts = nombre_completo.split(' ', 1)
            name = parts[0]
            lastname = parts[1] if len(parts) > 1 else ''
            alias_str = ','.join(w.get('alias', []))
            cpago = w.get('conceptos_pago', [])
            cpago_json = json.dumps(cpago, ensure_ascii=False)
            concepto_h = cpago[0]['descripcion'] if cpago else ''
            valor_h = cpago[0].get('valor_base') if cpago else None
            rol_str = w.get('rol', '').lower()
            trabajo = 'operario'
            for key, val in ROL_TO_ENUM.items():
                if key in rol_str:
                    trabajo = val
                    break

            cursor.execute("SELECT id_worker FROM workers WHERE cc = %s", (nit,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE workers SET rol = %s, conceptos_pago = %s,
                        concepto_habitual = COALESCE(NULLIF(concepto_habitual,''), %s)
                    WHERE cc = %s
                """, (w.get('rol', ''), cpago_json, concepto_h, nit))
                updated += 1
            else:
                cursor.execute("""
                    INSERT INTO workers
                        (name, lastname, cc, phone_number, alias, direccion, ciudad,
                         trabajo_desarrolla, activo, concepto_habitual, valor_habitual,
                         rol, conceptos_pago, fecha_ingreso)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'2025-01-01')
                """, (name, lastname, nit, w.get('telefono','') or '',
                      alias_str, w.get('direccion',''), w.get('ciudad',''),
                      trabajo, w.get('activo', True),
                      concepto_h, valor_h,
                      w.get('rol',''), cpago_json))
                imported += 1
        conn.commit()
        cursor.close(); conn.close()
        if imported or updated:
            print(f"[import] Trabajadores: {imported} nuevos, {updated} actualizados.")
    except Exception as e:
        print(f"[import] Error: {e}")
