"""Formal email templates for account auth flows in Contabilidad Arroceras."""

_WRAP_START = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#f8f5ef;font-family:'Segoe UI',Arial,sans-serif;">
"""

_WRAP_END = "</body></html>"


def _cta_button(link: str, label: str) -> str:
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0 16px;">
      <tr>
        <td style="background:#2d6a4f;border:1px solid #1b4332;border-radius:10px;">
          <a href="{link}" style="display:inline-block;padding:14px 24px;color:#ffffff;
             text-decoration:none;font-size:14px;font-weight:700;letter-spacing:.2px;">
            {label}
          </a>
        </td>
      </tr>
    </table>
    <p style="margin:0 0 8px;color:#4a6b52;font-size:12px;line-height:1.6;">
      Si el boton no abre correctamente, copia este enlace en tu navegador:
    </p>
    <p style="margin:0 0 16px;word-break:break-all;">
      <a href="{link}" style="color:#1b4332;font-size:12px;">{link}</a>
    </p>
    """


def _build_email(title: str, preheader: str, greeting: str, body_html: str, notes_html: str = "") -> str:
    return (
        _WRAP_START.format(title=title)
        + f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8f5ef;padding:28px 12px;">
  <tr>
    <td align="center">
      <span style="display:none;visibility:hidden;opacity:0;color:transparent;height:0;width:0;overflow:hidden;">{preheader}</span>
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;background:#ffffff;border:1px solid #d8f3dc;border-radius:14px;overflow:hidden;">
        <tr>
          <td style="background:#1b4332;padding:22px 28px;">
            <p style="margin:0;font-size:11px;letter-spacing:2.2px;color:#d8f3dc;text-transform:uppercase;font-weight:600;">Contabilidad Arroceras</p>
            <h1 style="margin:8px 0 0;color:#ffffff;font-size:26px;line-height:1.2;font-weight:700;">{title}</h1>
            <div style="width:54px;height:4px;background:#e9a800;border-radius:4px;margin-top:14px;"></div>
          </td>
        </tr>
        <tr>
          <td style="padding:28px 28px 8px;">
            <p style="margin:0 0 14px;font-size:16px;color:#1b2d1e;font-weight:700;">{greeting}</p>
            <div style="font-size:14px;line-height:1.7;color:#4a6b52;">{body_html}</div>
          </td>
        </tr>
        <tr>
          <td style="padding:0 28px 24px;">
            {notes_html}
          </td>
        </tr>
        <tr>
          <td style="padding:18px 28px;background:#eef7f2;border-top:1px solid #d8f3dc;">
            <p style="margin:0 0 6px;color:#2d6a4f;font-size:12px;font-weight:700;">Mensaje automatico de seguridad</p>
            <p style="margin:0;color:#4a6b52;font-size:12px;line-height:1.5;">
              Contabilidad Arroceras<br>
              Natagaima, Tolima - Colombia
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
"""
        + _WRAP_END
    )


def render_verify_email(full_name: str, verify_link: str) -> str:
    body = (
        "<p style='margin:0 0 12px;'>"
        "Gracias por registrarte en nuestra plataforma. Para activar tu cuenta, confirma tu direccion de correo."
        "</p>"
        + _cta_button(verify_link, "Verificar correo")
    )
    notes = (
        "<div style='border:1px solid #d8f3dc;background:#eef7f2;border-radius:10px;padding:12px 14px;'>"
        "<p style='margin:0;color:#2d6a4f;font-size:12px;line-height:1.6;'>"
        "Este enlace tiene vigencia de 24 horas. Si no creaste una cuenta, ignora este mensaje."
        "</p></div>"
    )
    return _build_email(
        title="Verificacion de correo",
        preheader="Activa tu cuenta en Contabilidad Arroceras.",
        greeting=f"Hola, {full_name}",
        body_html=body,
        notes_html=notes,
    )


def render_reset_email(full_name: str, reset_link: str) -> str:
    body = (
        "<p style='margin:0 0 12px;'>"
        "Recibimos una solicitud para restablecer la contrasena de tu cuenta."
        " Si reconoces esta solicitud, continua desde el siguiente boton."
        "</p>"
        + _cta_button(reset_link, "Restablecer contrasena")
    )
    notes = (
        "<div style='border:1px solid #d8f3dc;background:#eef7f2;border-radius:10px;padding:12px 14px;'>"
        "<p style='margin:0;color:#2d6a4f;font-size:12px;line-height:1.6;'>"
        "Este enlace expira en 1 hora. Si no solicitaste este cambio, puedes ignorar este mensaje."
        "</p></div>"
    )
    return _build_email(
        title="Recuperacion de contrasena",
        preheader="Restablece el acceso a tu cuenta.",
        greeting=f"Hola, {full_name}",
        body_html=body,
        notes_html=notes,
    )


def render_password_changed_email(full_name: str) -> str:
    body = (
        "<p style='margin:0 0 12px;'>"
        "Tu contrasena fue actualizada correctamente. Este correo confirma que el cambio ya fue aplicado."
        "</p>"
    )
    notes = (
        "<div style='border:1px solid #f4c842;background:#fff9e9;border-radius:10px;padding:12px 14px;'>"
        "<p style='margin:0;color:#7a5a00;font-size:12px;line-height:1.6;'>"
        "Si no realizaste esta accion, contacta al administrador inmediatamente y restablece tu acceso."
        "</p></div>"
    )
    return _build_email(
        title="Cambio de contrasena confirmado",
        preheader="La contrasena de tu cuenta fue cambiada.",
        greeting=f"Hola, {full_name}",
        body_html=body,
        notes_html=notes,
    )


def render_login_alert_email(full_name: str, when_text: str) -> str:
    body = (
        "<p style='margin:0 0 12px;'>"
        "Tu cuenta inicio sesion correctamente en la plataforma."
        "</p>"
        f"<p style='margin:0 0 12px;'><strong>Fecha y hora:</strong> {when_text}</p>"
    )
    notes = (
        "<div style='border:1px solid #f4c842;background:#fff9e9;border-radius:10px;padding:12px 14px;'>"
        "<p style='margin:0;color:#7a5a00;font-size:12px;line-height:1.6;'>"
        "Si no reconoces este acceso, cambia tu contrasena de inmediato y revisa tu seguridad."
        "</p></div>"
    )
    return _build_email(
        title="Alerta de inicio de sesion",
        preheader="Se detecto un acceso a tu cuenta.",
        greeting=f"Hola, {full_name}",
        body_html=body,
        notes_html=notes,
    )


def render_signup_code_email(full_name: str, code: str) -> str:
    body = (
        "<p style='margin:0 0 12px;'>"
        "Para completar la creacion de tu cuenta, ingresa el siguiente codigo de seguridad en la aplicacion."
        "</p>"
        f"<div style='margin:16px 0 18px;padding:14px 16px;border:1px dashed #2d6a4f;border-radius:10px;"
        "background:#eef7f2;display:inline-block;'>"
        f"<span style='font-size:30px;letter-spacing:8px;color:#1b4332;font-weight:800;'>{code}</span>"
        "</div>"
    )
    notes = (
        "<div style='border:1px solid #d8f3dc;background:#eef7f2;border-radius:10px;padding:12px 14px;'>"
        "<p style='margin:0;color:#2d6a4f;font-size:12px;line-height:1.6;'>"
        "El codigo expira en 10 minutos y solo puede usarse una vez."
        "</p></div>"
    )
    return _build_email(
        title="Codigo de verificacion",
        preheader="Codigo de 6 digitos para activar tu cuenta.",
        greeting=f"Hola, {full_name}",
        body_html=body,
        notes_html=notes,
    )


def render_reset_code_email(full_name: str, code: str) -> str:
    body = (
        "<p style='margin:0 0 12px;'>"
        "Recibimos una solicitud para recuperar tu contrasena."
        " Usa el siguiente codigo de seguridad en la aplicacion para continuar."
        "</p>"
        f"<div style='margin:16px 0 18px;padding:14px 16px;border:1px dashed #2d6a4f;border-radius:10px;"
        "background:#eef7f2;display:inline-block;'>"
        f"<span style='font-size:30px;letter-spacing:8px;color:#1b4332;font-weight:800;'>{code}</span>"
        "</div>"
    )
    notes = (
        "<div style='border:1px solid #f4c842;background:#fff9e9;border-radius:10px;padding:12px 14px;'>"
        "<p style='margin:0;color:#7a5a00;font-size:12px;line-height:1.6;'>"
        "El codigo expira en 10 minutos. Si no solicitaste este cambio, ignora este correo."
        "</p></div>"
    )
    return _build_email(
        title="Codigo de recuperacion",
        preheader="Codigo de 6 digitos para restablecer tu contrasena.",
        greeting=f"Hola, {full_name}",
        body_html=body,
        notes_html=notes,
    )
