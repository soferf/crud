"""
Email HTML templates for Contabilidad Arroceras.
Inline strings avoid the need for a templates/email/ subdirectory.
"""

_HEADER = """
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f0;padding:40px 0;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:12px;overflow:hidden;
                  box-shadow:0 4px 24px rgba(0,0,0,.10);">
      <tr>
        <td style="background:#1a3d2b;padding:36px 40px 28px;text-align:center;">
          <p style="margin:0 0 6px;font-size:11px;letter-spacing:3px;color:#a8c5a0;
                    text-transform:uppercase;font-weight:600;">Contabilidad Arroceras</p>
          <h1 style="margin:0;font-size:26px;color:#fff;font-weight:700;">{title}</h1>
          <div style="width:40px;height:3px;background:#c9a84c;margin:14px auto 0;border-radius:2px;"></div>
        </td>
      </tr>
"""

_FOOTER = """
      <tr>
        <td style="background:#f7faf7;padding:20px 40px;text-align:center;
                   border-top:1px solid #e0ebe0;">
          <p style="margin:0;font-size:12px;color:#999;">
            &copy; Contabilidad Arroceras &nbsp;&middot;&nbsp; Lote El Mangón, Natagaima
          </p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
"""

_WRAP_START = """<!DOCTYPE html><html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title></head>
<body style="margin:0;padding:0;background:#f0f4f0;font-family:'Segoe UI',Arial,sans-serif;">"""

_WRAP_END = "</body></html>"


def _cta_button(link: str, label: str) -> str:
    return f"""
    <table cellpadding="0" cellspacing="0" style="margin:0 auto 28px;">
      <tr>
        <td style="background:#1a3d2b;border-radius:8px;">
          <a href="{link}"
             style="display:inline-block;padding:14px 36px;font-size:15px;font-weight:700;
                    color:#fff;text-decoration:none;letter-spacing:.5px;border-radius:8px;">
            {label}
          </a>
        </td>
      </tr>
    </table>
    <p style="margin:0 0 8px;font-size:13px;color:#888;line-height:1.6;">
      Si el botón no funciona, copia este enlace en tu navegador:
    </p>
    <p style="margin:0 0 24px;font-size:12px;word-break:break-all;">
      <a href="{link}" style="color:#1a3d2b;">{link}</a>
    </p>"""


def render_verify_email(full_name: str, verify_link: str) -> str:
    """Returns HTML body for email verification message."""
    body = f"""
      <tr>
        <td style="padding:36px 40px 20px;">
          <p style="margin:0 0 16px;font-size:16px;color:#2d4a35;font-weight:600;">
            Hola, {full_name}
          </p>
          <p style="margin:0 0 24px;font-size:15px;color:#555;line-height:1.6;">
            Gracias por registrarte en <strong>Contabilidad Arroceras</strong>.<br>
            Haz clic en el botón de abajo para activar tu cuenta.
          </p>
          {_cta_button(verify_link, "✓ Verificar mi correo")}
          <div style="border-top:1px solid #e8f0e8;padding-top:18px;margin-top:4px;">
            <p style="margin:0;font-size:12px;color:#aaa;line-height:1.6;">
              Si no creaste esta cuenta, ignora este correo.<br>
              Este enlace es válido por <strong>24 horas</strong>.
            </p>
          </div>
        </td>
      </tr>"""
    return (
        _WRAP_START.format(title="Verifica tu correo")
        + _HEADER.format(title="Verifica tu correo")
        + body
        + _FOOTER
        + _WRAP_END
    )


def render_reset_email(full_name: str, reset_link: str) -> str:
    """Returns HTML body for password reset email."""
    body = f"""
      <tr>
        <td style="padding:36px 40px 20px;">
          <p style="margin:0 0 16px;font-size:16px;color:#2d4a35;font-weight:600;">
            Hola, {full_name}
          </p>
          <p style="margin:0 0 24px;font-size:15px;color:#555;line-height:1.6;">
            Recibimos una solicitud para restablecer la contraseña de tu cuenta.<br>
            Haz clic en el botón de abajo para crear una nueva contraseña.
          </p>
          {_cta_button(reset_link, "🔑 Restablecer contraseña")}
          <div style="border-top:1px solid #e8f0e8;padding-top:18px;margin-top:4px;">
            <p style="margin:0;font-size:12px;color:#aaa;line-height:1.6;">
              Si no solicitaste esto, ignora este correo: tu contraseña no cambiará.<br>
              Este enlace expira en <strong>1 hora</strong>.
            </p>
          </div>
        </td>
      </tr>"""
    return (
        _WRAP_START.format(title="Restablecer contraseña")
        + _HEADER.format(title="Restablecer contraseña")
        + body
        + _FOOTER
        + _WRAP_END
    )
