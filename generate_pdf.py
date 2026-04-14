"""
Genera tmp/design-system.pdf con la paleta de colores y tipografia
del proyecto Contabilidad Arroceras.

Uso:
    pip install fpdf2
    python generate_pdf.py
"""

import os
from fpdf import FPDF, XPos, YPos

os.makedirs("tmp", exist_ok=True)

NX = XPos.LMARGIN
NY = YPos.NEXT

# ──────────────────────────────────────────
# Definicion del Design System
# ──────────────────────────────────────────

PALETTE = [
    # (nombre,                       hex,       (R,G,B),        uso)
    ("Primary 900 - Deep Forest",  "#1B4332", (27,  67,  50),  "Hero, footer, encabezados oscuros"),
    ("Primary 700 - Forest Green", "#2D6A4F", (45, 106,  79),  "Nav, botones, iconos principales"),
    ("Primary 500 - Medium Green", "#40916C", (64, 145, 108),  "Hover, acentos secundarios"),
    ("Primary 300 - Sage Green",   "#52B788", (82, 183, 136),  "Bordes tarjetas accent"),
    ("Primary 100 - Mint",         "#D8F3DC", (216,243, 220),  "Fondo de iconos de tarjeta"),
    ("Primary 50  - Soft Mint",    "#EEF7F2", (238,247, 242),  "Secciones alternas (--muted)"),
    ("Accent 500  - Gold",         "#E9A800", (233,168,   0),  "Boton primario, numeros estadisticos"),
    ("Accent 300  - Light Gold",   "#F4C842", (244,200,  66),  "Texto accent en hero, hover CTA"),
    ("Background  - Warm Cream",   "#F8F5EF", (248,245, 239),  "Fondo general del body"),
    ("Surface     - White",        "#FFFFFF", (255,255, 255),  "Tarjetas, nav, modales"),
    ("Text        - Dark",         "#1B2D1E", (27,  45,  30),  "Encabezados y texto principal"),
    ("Text        - Muted",        "#4A6B52", (74, 107,  82),  "Cuerpo, subtitulos, placeholders"),
]

FONTS = [
    {
        "nombre": "Playfair Display",
        "tipo": "Serif - Google Fonts",
        "pesos": "500 Medium  700 Bold  500 Italic",
        "uso": "Titulos (h1-h3), brand name, numeros estadisticos.",
        "import": "https://fonts.google.com/specimen/Playfair+Display",
        "css": "--ff-heading: 'Playfair Display', Georgia, serif;",
    },
    {
        "nombre": "Nunito",
        "tipo": "Sans-serif - Google Fonts",
        "pesos": "400 Regular  500 Medium  600 SemiBold  700 Bold",
        "uso": "Cuerpo de texto, nav, etiquetas, botones, parrafos.",
        "import": "https://fonts.google.com/specimen/Nunito",
        "css": "--ff-body: 'Nunito', system-ui, sans-serif;",
    },
]

# ──────────────────────────────────────────
# PDF
# ──────────────────────────────────────────

class DesignPDF(FPDF):
    PAGE_W = 210

    def header(self):
        self.set_fill_color(27, 67, 50)
        self.rect(0, 0, self.PAGE_W, 18, "F")
        self.set_xy(0, 4)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.cell(self.PAGE_W, 10, "  Contabilidad Arroceras  -  Design System", align="L", new_x=NX, new_y=NY)
        self.ln(6)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Pagina {self.page_no()}  |  Contabilidad Arroceras 2026", align="C")

    # ── Helpers ────────────────────────────

    def section_title(self, text):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(27, 67, 50)
        self.ln(4)
        self.cell(0, 10, text, new_x=NX, new_y=NY)
        self.set_draw_color(82, 183, 136)
        self.set_line_width(0.6)
        x = self.get_x()
        y = self.get_y()
        self.line(x, y, x + 180, y)
        self.ln(6)

    def body_text(self, text, color=(74, 107, 82)):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*color)
        self.multi_cell(0, 5, text)
        self.ln(2)

    # ── Portada ────────────────────────────

    def cover(self):
        # Fondo completo
        self.set_fill_color(27, 67, 50)
        self.rect(0, 0, 210, 297, "F")

        # Patrón decorativo (puntos)
        self.set_fill_color(45, 106, 79)
        for row in range(0, 30):
            for col in range(0, 25):
                self.ellipse(col * 9 + 2, row * 10 + 2, 1.5, 1.5, "F")

        # Rectángulo central
        self.set_fill_color(45, 106, 79)
        self.set_draw_color(82, 183, 136)
        self.set_line_width(0.5)
        self.rect(25, 70, 160, 130, "FD")

        # Ícono decorativo (rectángulo dorado)
        self.set_fill_color(233, 168, 0)
        self.rect(93, 82, 24, 5, "F")

        # Título
        self.set_font("Helvetica", "B", 26)
        self.set_text_color(255, 255, 255)
        self.set_xy(25, 100)
        self.cell(160, 14, "Contabilidad Arroceras", align="C", new_x=NX, new_y=NY)

        self.set_font("Helvetica", "", 14)
        self.set_text_color(244, 200, 66)
        self.set_x(25)
        self.cell(160, 10, "Design System", align="C", new_x=NX, new_y=NY)

        # Linea divisora
        self.set_draw_color(82, 183, 136)
        self.set_line_width(0.8)
        self.line(50, 126, 160, 126)

        self.set_font("Helvetica", "", 10)
        self.set_text_color(216, 243, 220)
        self.set_xy(25, 132)
        self.cell(160, 8, "Paleta de colores  -  Tipografia  -  Tokens CSS", align="C", new_x=NX, new_y=NY)

        self.set_xy(25, 148)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(82, 183, 136)
        self.cell(160, 6, "Proyecto academico 2026", align="C", new_x=NX, new_y=NY)

        # Footer de portada
        self.set_xy(0, 270)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(82, 183, 136)
        self.cell(210, 8, "Flask  -  HTML5  -  CSS3  -  MySQL  -  Font Awesome 6", align="C")


# ──────────────────────────────────────────
# Construcción del documento
# ──────────────────────────────────────────

pdf = DesignPDF()
pdf.set_margins(15, 24, 15)
pdf.set_auto_page_break(auto=True, margin=16)

# ── Portada ──
pdf.add_page()
pdf.cover()

# ── Página 2: Paleta de colores ──
pdf.add_page()
pdf.section_title("1. Paleta de Colores")
pdf.body_text(
    "Basada en tonos verdes forestales (produccion agricola) y dorados (cosecha y valor). "
    "Los tokens CSS estan definidos en static/css/style.css bajo :root {}."
)

SWATCH_W = 22
SWATCH_H = 14
COLS = 3
GAP_X = (180 - COLS * SWATCH_W) / (COLS - 1) + SWATCH_W  # ancho de celda

for i, (name, hex_val, rgb, usage) in enumerate(PALETTE):
    col = i % COLS
    if col == 0 and i > 0:
        pdf.ln(38)

    x = 15 + col * (180 // COLS)
    y = pdf.get_y()

    # Muestra de color
    r, g, b = rgb
    pdf.set_fill_color(r, g, b)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    pdf.rect(x, y, SWATCH_W, SWATCH_H, "FD")

    # Texto junto a la muestra
    pdf.set_xy(x + SWATCH_W + 2, y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(27, 45, 30)
    pdf.cell(180 // COLS - SWATCH_W - 4, 5, name[:28], new_x=NX, new_y=NY)

    pdf.set_x(x + SWATCH_W + 2)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 4, hex_val, new_x=NX, new_y=NY)

    pdf.set_x(x + SWATCH_W + 2)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(74, 107, 82)
    pdf.multi_cell(180 // COLS - SWATCH_W - 4, 3.8, usage)

    # Volver a la Y del inicio de esta fila si quedan más columnas
    if col < COLS - 1:
        pdf.set_y(y)

pdf.ln(12)

# ── Página 3: Tipografía ──
pdf.add_page()
pdf.section_title("2. Tipografia")
pdf.body_text("Dos fuentes complementarias: una serif elegante para titulos y una sans-serif "
              "moderna para el cuerpo. Ambas disponibles en Google Fonts.")

for font in FONTS:
    pdf.ln(4)
    # Cabecera del bloque
    pdf.set_fill_color(238, 247, 242)
    pdf.set_draw_color(200, 230, 200)
    pdf.set_line_width(0.3)
    pdf.rect(15, pdf.get_y(), 180, 52, "FD")

    y0 = pdf.get_y() + 3

    # Acento lateral dorado
    pdf.set_fill_color(233, 168, 0)
    pdf.rect(15, y0 - 3, 3, 52, "F")

    pdf.set_xy(22, y0)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(27, 67, 50)
    pdf.cell(0, 8, font["nombre"], new_x=NX, new_y=NY)

    pdf.set_x(22)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(64, 145, 108)
    pdf.cell(0, 5, font["tipo"], new_x=NX, new_y=NY)

    pdf.set_x(22)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(27, 45, 30)
    pdf.cell(30, 5, "Pesos:")
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(0, 5, font["pesos"], new_x=NX, new_y=NY)

    pdf.set_x(22)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(74, 107, 82)
    pdf.cell(30, 5, "Uso:")
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.multi_cell(150, 5, font["uso"])

    pdf.set_x(22)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(30, 4, "CSS var:")
    pdf.set_font("Courier", "", 7.5)
    pdf.set_text_color(45, 106, 79)
    pdf.cell(0, 4, font["css"], new_x=NX, new_y=NY)

    pdf.set_x(22)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 4, font["import"], new_x=NX, new_y=NY)

    pdf.ln(8)

# ── Página 4: Escala tipográfica ──
pdf.section_title("2.1  Escala Tipografica")
pdf.body_text("Escala de tamanios definidos como variables CSS (--fs-*).")

SCALE = [
    ("--fs-5xl / clamp(2.2-3.4rem)", "Hero H1",          16),
    ("--fs-4xl / 2.6rem",            "Section Title H2",  14),
    ("--fs-3xl / 2rem",              "Card H3 / Stats",   13),
    ("--fs-xl  / 1.25rem",           "Card H3 / Brand",   11),
    ("--fs-lg  / 1.125rem",          "Lead / Subtitle",   10),
    ("--fs-base / 1rem",             "Body / Buttons",     9),
    ("--fs-sm  / 0.875rem",          "Nav / Meta",         8),
    ("--fs-xs  / 0.75rem",           "Eyebrow / Caption",  7),
]

pdf.set_fill_color(238, 247, 242)
pdf.set_draw_color(200, 230, 200)
pdf.set_line_width(0.2)

for token, label, size in SCALE:
    y = pdf.get_y()
    pdf.rect(15, y, 180, 9, "FD")
    pdf.set_xy(18, y + 1.5)
    pdf.set_font("Courier", "", 7.5)
    pdf.set_text_color(45, 106, 79)
    pdf.cell(70, 6, token)
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(27, 45, 30)
    pdf.cell(0, 6, label, new_x=NX, new_y=NY)

pdf.ln(8)

# ── Página 5 (o continúa): Tokens CSS resumidos ──
pdf.section_title("3. Tokens CSS de Referencia")
pdf.body_text("Extracto de las variables definidas en :root{} dentro de static/css/style.css")

tokens = [
    ("COLOR",   "--clr-900",       "#1B4332"),
    ("COLOR",   "--clr-700",       "#2D6A4F"),
    ("COLOR",   "--clr-500",       "#40916C"),
    ("COLOR",   "--clr-300",       "#52B788"),
    ("COLOR",   "--clr-100",       "#D8F3DC"),
    ("COLOR",   "--clr-50",        "#EEF7F2"),
    ("COLOR",   "--gold-500",      "#E9A800"),
    ("COLOR",   "--gold-300",      "#F4C842"),
    ("COLOR",   "--bg",            "#F8F5EF"),
    ("COLOR",   "--surface",       "#FFFFFF"),
    ("COLOR",   "--txt",           "#1B2D1E"),
    ("COLOR",   "--txt-muted",     "#4A6B52"),
    ("FONT",    "--ff-heading",    "'Playfair Display', Georgia, serif"),
    ("FONT",    "--ff-body",       "'Nunito', system-ui, sans-serif"),
    ("RADIUS",  "--r-sm",          "6px"),
    ("RADIUS",  "--r-md",          "12px"),
    ("RADIUS",  "--r-lg",          "20px"),
    ("RADIUS",  "--r-full",        "9999px"),
    ("SHADOW",  "--sh-sm",         "0 1px 4px rgba(27,67,50,.08)"),
    ("SHADOW",  "--sh-md",         "0 4px 16px rgba(27,67,50,.12)"),
    ("SHADOW",  "--sh-lg",         "0 8px 32px rgba(27,67,50,.18)"),
    ("ICONS",    "Font Awesome 6",  "cdnjs.cloudflare.com - font-awesome/6.5.1"),
]

CAT_COLORS = {
    "COLOR":  (233, 168,  0),
    "FONT":   (82,  183, 136),
    "RADIUS": (64,  145, 108),
    "SHADOW": (45,  106,  79),
    "ICONS":  (27,   67,  50),
}

for cat, var, val in tokens:
    y = pdf.get_y()
    # badge categoría
    cr, cg, cb = CAT_COLORS.get(cat, (100, 100, 100))
    pdf.set_fill_color(cr, cg, cb)
    pdf.rect(15, y, 18, 6.5, "F")
    pdf.set_xy(15, y + 0.8)
    pdf.set_font("Helvetica", "B", 6)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(18, 5, cat, align="C")

    pdf.set_xy(35, y + 0.8)
    pdf.set_font("Courier", "B", 7.5)
    pdf.set_text_color(27, 67, 50)
    pdf.cell(55, 5, var)

    pdf.set_font("Courier", "", 7.5)
    pdf.set_text_color(74, 107, 82)
    pdf.cell(0, 5, val, new_x=NX, new_y=NY)

    pdf.ln(0.5)

# ── Guardar ──
output_path = os.path.join("tmp", "design-system.pdf")
pdf.output(output_path)
print(f"PDF generado correctamente: {output_path}")
