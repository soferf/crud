"""
auth_middleware.py — Decoradores de autorización RBAC multi-lote.

Uso:
    from auth_middleware import require_login, require_permission, get_user_perms

    @app.route('/recibos/nuevo')
    @require_permission('recibo.create')
    def nuevo_recibo(): ...
"""
from functools import wraps
from flask import session, redirect, url_for, abort, request, flash
import mysql.connector


def get_db_connection():
    from db import get_db_connection as _gdc
    return _gdc()


# ── Helpers de sesión ─────────────────────────────────────────────────────────

def current_user_id():
    return session.get('user_id')


def current_lote_id():
    return session.get('lote_id')


def current_perms():
    """Devuelve el set de permisos del usuario en el lote activo."""
    return set(session.get('user_perms', []))


def has_permission(perm: str) -> bool:
    """Verifica si el usuario tiene el permiso en el lote activo."""
    perms = current_perms()
    return perm in perms or 'superadmin' in perms


def is_superadmin() -> bool:
    return session.get('is_superadmin', False)


# ── Carga de permisos desde BD ────────────────────────────────────────────────

def load_user_lote_perms(user_id: int, lote_id: int) -> list[str]:
    """
    Carga los permisos del usuario en un lote específico.
    Combina permisos del rol asignado en ese lote.
    Los superadmin reciben todos los permisos automáticamente.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar rol global (superadmin)
        cursor.execute("""
            SELECT r.nombre FROM user_global_roles ugr
            JOIN roles r ON ugr.role_id = r.id
            WHERE ugr.user_id = %s
        """, (user_id,))
        global_roles = [row['nombre'] for row in cursor.fetchall()]

        if 'superadmin' in global_roles:
            cursor.execute("SELECT clave FROM permissions")
            all_perms = [row['clave'] for row in cursor.fetchall()]
            cursor.close(); conn.close()
            return all_perms

        # Permisos del lote
        cursor.execute("""
            SELECT DISTINCT p.clave
            FROM user_lote_roles ulr
            JOIN role_permissions rp ON ulr.role_id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE ulr.user_id = %s AND ulr.lote_id = %s
        """, (user_id, lote_id))
        perms = [row['clave'] for row in cursor.fetchall()]
        cursor.close(); conn.close()
        return perms
    except Exception as e:
        print(f"[auth_middleware] Error cargando permisos: {e}")
        return []


def load_user_lotes(user_id: int) -> list[dict]:
    """
    Retorna la lista de lotes a los que tiene acceso el usuario,
    con el nombre del rol asignado.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Superadmin ve todos los lotes
        cursor.execute("""
            SELECT 1 FROM user_global_roles ugr
            JOIN roles r ON ugr.role_id = r.id
            WHERE ugr.user_id = %s AND r.nombre = 'superadmin'
        """, (user_id,))
        if cursor.fetchone():
            cursor.execute("""
                SELECT l.id, l.nombre, l.propietario_nombre, l.hectareas,
                       l.estado, 'superadmin' as rol_nombre
                FROM lotes l WHERE l.estado != 'inactivo'
            """)
        else:
            cursor.execute("""
                SELECT l.id, l.nombre, l.propietario_nombre, l.hectareas,
                       l.estado, r.nombre as rol_nombre
                FROM user_lote_roles ulr
                JOIN lotes l ON ulr.lote_id = l.id
                JOIN roles r ON ulr.role_id = r.id
                WHERE ulr.user_id = %s AND l.estado != 'inactivo'
                ORDER BY l.nombre
            """, (user_id,))
        lotes = cursor.fetchall()
        cursor.close(); conn.close()
        return lotes
    except Exception as e:
        print(f"[auth_middleware] Error cargando lotes: {e}")
        return []


def refresh_session_perms():
    """
    Recarga los permisos en la sesión para el lote activo.
    Llamar después de cambiar de lote o de modificar roles.
    """
    uid = current_user_id()
    lid = current_lote_id()
    if not uid or not lid:
        return
    perms = load_user_lote_perms(uid, lid)
    session['user_perms'] = perms

    # Marcar superadmin
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 1 FROM user_global_roles ugr
            JOIN roles r ON ugr.role_id = r.id
            WHERE ugr.user_id = %s AND r.nombre = 'superadmin'
        """, (uid,))
        session['is_superadmin'] = cursor.fetchone() is not None
        cursor.close(); conn.close()
    except Exception:
        session['is_superadmin'] = False


# ── Decoradores ───────────────────────────────────────────────────────────────

def require_login(f):
    """Requiere que el usuario esté autenticado."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user_id():
            return redirect(url_for('home', form='login',
                                    message='Inicia sesion para continuar.',
                                    type='warning'))
        return f(*args, **kwargs)
    return decorated


def require_lote(f):
    """Requiere que haya un lote activo en la sesión."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user_id():
            return redirect(url_for('home', form='login',
                                    message='Inicia sesion para continuar.',
                                    type='warning'))
        if not current_lote_id():
            return redirect(url_for('select_lote'))
        return f(*args, **kwargs)
    return decorated


def require_permission(perm: str):
    """
    Requiere login + lote activo + permiso específico.
    Si no tiene permiso, redirige con mensaje de acceso denegado.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user_id():
                return redirect(url_for('home', form='login',
                                        message='Inicia sesion para continuar.',
                                        type='warning'))
            if not current_lote_id():
                return redirect(url_for('select_lote'))
            if not has_permission(perm):
                # Para requests AJAX devolver 403
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    from flask import jsonify
                    return jsonify({'error': 'Acceso denegado', 'permiso_requerido': perm}), 403
                return redirect(url_for('dashboard',
                                        _anchor='',
                                        msg='No tienes permiso para realizar esta acción.',
                                        msg_type='danger'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_superadmin(f):
    """Solo superadmin puede acceder."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user_id():
            return redirect(url_for('home', form='login',
                                    message='Inicia sesion para continuar.',
                                    type='warning'))
        if not is_superadmin():
            abort(403)
        return f(*args, **kwargs)
    return decorated
