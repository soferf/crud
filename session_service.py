"""
session_service.py — Helpers de sesión y lotes del usuario.
"""
import re
from flask import redirect, url_for, render_template, session

from db import get_db_connection


def auth_redirect(form, message, message_type='info'):
    return redirect(url_for('home', form=form, message=message, type=message_type))


def render_auth_page(form='login', message=None, message_type='info', form_data=None):
    if form not in {'login', 'signup', 'forgot', 'signup_code', 'reset_code'}:
        form = 'login'
    safe_form_data = {
        'login':       {'email': '', 'remember_me': False},
        'signup':      {'full_name': '', 'email': ''},
        'forgot':      {'email': ''},
        'signup_code': {'email': '', 'code': ''},
        'reset_code':  {'email': '', 'code': ''}
    }
    if form_data:
        for key, values in form_data.items():
            if key in safe_form_data and isinstance(values, dict):
                safe_form_data[key].update(values)
    return render_template(
        'index.html',
        active_form=form,
        auth_message=message,
        auth_message_type=message_type,
        logged_in='user_id' in session,
        user_name=session.get('user_name'),
        form_data=safe_form_data
    )


def _get_user_lotes(user_id: int) -> list:
    """Retorna la lista de lotes del usuario con info del rol."""
    try:
        from auth_middleware import load_user_lotes
        return load_user_lotes(user_id)
    except Exception:
        return []


def _set_active_lote_session(user_id: int, lote_id: int):
    """Actualiza la sesión Flask con el lote activo y sus permisos."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nombre, hectareas FROM lotes WHERE id=%s", (lote_id,))
        lote = cursor.fetchone()

        cursor.execute("""
            SELECT r.nombre as rol_nombre FROM user_lote_roles ulr
            JOIN roles r ON ulr.role_id = r.id
            WHERE ulr.user_id=%s AND ulr.lote_id=%s
        """, (user_id, lote_id))
        rol_row = cursor.fetchone()
        cursor.close(); conn.close()

        if not lote:
            return False

        session['lote_id']     = lote_id
        session['lote_nombre'] = lote['nombre']
        session['lote_ha']     = float(lote['hectareas'] or 20)
        session['rol_lote']    = rol_row['rol_nombre'] if rol_row else 'operador_lote'

        from auth_middleware import load_user_lote_perms
        perms = load_user_lote_perms(user_id, lote_id)
        session['user_perms'] = perms

        conn2 = get_db_connection()
        c2 = conn2.cursor(dictionary=True)
        c2.execute("""
            SELECT 1 FROM user_global_roles ugr
            JOIN roles r ON ugr.role_id = r.id
            WHERE ugr.user_id=%s AND r.nombre='superadmin'
        """, (user_id,))
        session['is_superadmin'] = c2.fetchone() is not None
        c2.close(); conn2.close()
        return True
    except Exception as e:
        print(f'[set_active_lote] Error: {e}')
        return False


def _assign_user_to_initial_lote(user_id: int, role_nombre: str = 'admin_lote'):
    """
    Asigna un usuario recién registrado al lote inicial si es el primer usuario.
    Devuelve True si se asignó al lote inicial, False si necesita setup.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as cnt FROM user_lote_roles WHERE user_id=%s", (user_id,))
        if cursor.fetchone()['cnt'] > 0:
            cursor.close(); conn.close()
            return True

        cursor.execute("SELECT id FROM lotes WHERE nombre='El Mangon' LIMIT 1")
        lote_row = cursor.fetchone()

        if lote_row:
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM user_lote_roles ulr
                JOIN roles r ON ulr.role_id = r.id
                WHERE ulr.lote_id=%s AND r.nombre IN ('admin_lote','duenio_lote')
            """, (lote_row['id'],))
            tiene_admin = cursor.fetchone()['cnt'] > 0

            if not tiene_admin:
                cursor.execute("SELECT id FROM roles WHERE nombre=%s", (role_nombre,))
                role_row = cursor.fetchone()
                if role_row:
                    cursor.execute(
                        "INSERT IGNORE INTO user_lote_roles (user_id, lote_id, role_id) VALUES (%s,%s,%s)",
                        (user_id, lote_row['id'], role_row['id'])
                    )
                    conn.commit()
                    cursor.close(); conn.close()
                    return True

        cursor.close(); conn.close()
        return False
    except Exception as e:
        print(f'[assign_lote] Error: {e}')
        return False
