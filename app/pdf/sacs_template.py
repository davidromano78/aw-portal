import math
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

COLOR_INFLOW = colors.HexColor("#2E7D32")
COLOR_OUTFLOW = colors.HexColor("#C62828")
COLOR_PRIVATE = colors.HexColor("#1565C0")
COLOR_WHITE = colors.HexColor("#FFFFFF")
COLOR_BLACK = colors.HexColor("#000000")
COLOR_ARROW_BLUE = colors.HexColor("#1565C0")
COLOR_ARROW_RED = colors.HexColor("#C62828")
COLOR_ARROW_GREEN = colors.HexColor("#2E7D32")

FLOOR_AMOUNT = "$1,000 Floor"
TRANSFER_DAY = 28


def _fmt_money(value: float | None) -> str:
    if value is None:
        return "$0"
    return f"${value:,.0f}" if float(value).is_integer() else f"${value:,.2f}"


def _circle_chord_x(cx: float, cy: float, radius: float, line_y: float) -> tuple[float, float]:
    dy = line_y - cy
    if abs(dy) >= radius:
        return cx - radius, cx + radius
    half = math.sqrt(radius * radius - dy * dy)
    return cx - half, cx + half


def _draw_arrow_line(
    c: canvas.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color,
    width: float = 2,
    head_size: float = 10,
):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)

    angle = math.atan2(y2 - y1, x2 - x1)
    left = angle + math.pi * 0.82
    right = angle - math.pi * 0.82
    p1 = (x2, y2)
    p2 = (x2 + head_size * math.cos(left), y2 + head_size * math.sin(left))
    p3 = (x2 + head_size * math.cos(right), y2 + head_size * math.sin(right))
    path = c.beginPath()
    path.moveTo(*p1)
    path.lineTo(*p2)
    path.lineTo(*p3)
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def _label_on_line(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float, text: str, color, font_size: int = 10, offset: float = 12):
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", font_size)
    c.drawCentredString(mx, my + offset, text)


def _draw_flow_circle(
    c: canvas.Canvas,
    cx: float,
    cy: float,
    radius: float,
    fill_color,
    label: str,
    amount: str,
):
    c.setFillColor(fill_color)
    c.setStrokeColor(COLOR_BLACK)
    c.setLineWidth(1.5)
    c.circle(cx, cy, radius, fill=1, stroke=1)

    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(cx, cy + radius - 22, label)

    c.setFillColor(colors.white)
    c.roundRect(cx - 55, cy + 2, 110, 26, 4, fill=1, stroke=0)
    c.setFillColor(fill_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(cx, cy + 12, amount)

    floor_y = cy - radius * 0.35
    x_left, x_right = _circle_chord_x(cx, cy, radius, floor_y)
    c.setStrokeColor(COLOR_BLACK)
    c.setLineWidth(1)
    c.line(x_left, floor_y, x_right, floor_y)

    c.setFillColor(COLOR_BLACK)
    c.setFont("Helvetica", 9)
    c.drawCentredString(cx, cy - radius + 16, FLOOR_AMOUNT)


def _draw_private_reserve_circle(c: canvas.Canvas, cx: float, cy: float, radius: float):
    c.setFillColor(COLOR_PRIVATE)
    c.setStrokeColor(COLOR_BLACK)
    c.setLineWidth(1.5)
    c.circle(cx, cy, radius, fill=1, stroke=1)

    lines = ["PRIVATE", "RESERVE"]
    font_size = 11
    line_height = font_size + 2
    while font_size >= 8:
        total_h = line_height * len(lines)
        if total_h <= radius * 1.4:
            break
        font_size -= 1
        line_height = font_size + 2

    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", font_size)
    start_y = cy + (line_height * (len(lines) - 1)) / 2
    for i, line in enumerate(lines):
        c.drawCentredString(cx, start_y - i * line_height, line)


def _draw_page_header(c: canvas.Canvas, width: float, height: float, client: dict, report: dict):
    c.setFillColor(COLOR_BLACK)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 0.65 * inch, "Simple Automated Cashflow System (SACS)")
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 0.95 * inch, "Client Example")
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, height - 1.2 * inch, f"{client['display_name']} — {report['report_date']}")


def _draw_page1_diagram(c: canvas.Canvas, width: float, height: float, client: dict, report: dict):
    inflow = client["monthly_salary"]
    outflow = client["monthly_expense_budget"]
    excess = report.get("excess") or (inflow - outflow)

    center_x = width / 2
    radius = 0.85 * inch
    horizontal_offset = 2.8 * inch

    private_cx = center_x
    private_cy = 2.0 * inch
    inflow_cx = center_x - horizontal_offset
    outflow_cx = center_x + horizontal_offset
    flow_cy = height * 0.58

    _draw_flow_circle(c, inflow_cx, flow_cy, radius, COLOR_INFLOW, "INFLOW", _fmt_money(inflow))
    _draw_flow_circle(c, outflow_cx, flow_cy, radius, COLOR_OUTFLOW, "OUTFLOW", _fmt_money(outflow))
    _draw_private_reserve_circle(c, private_cx, private_cy, radius)

    # Arrow 2: Inflow -> Outflow (red)
    inflow_edge_x = inflow_cx + radius + 4
    outflow_edge_x = outflow_cx - radius - 4
    _draw_arrow_line(c, inflow_edge_x, flow_cy, outflow_edge_x, flow_cy, COLOR_ARROW_RED, width=3, head_size=12)
    c.setFillColor(COLOR_ARROW_RED)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(center_x, flow_cy + 20, f"X = {_fmt_money(outflow)}/month")
    c.setFont("Helvetica", 9)
    c.setFillColor(COLOR_BLACK)
    c.drawCentredString(center_x, flow_cy - 22, f"Automated transfer on the {TRANSFER_DAY}th")

    # Arrow 1: Inflow -> Private Reserve (blue, L-shaped path)
    mid_x = (inflow_cx + private_cx) / 2
    bend_y = (flow_cy - radius + private_cy + radius) / 2
    c.setStrokeColor(COLOR_ARROW_BLUE)
    c.setFillColor(COLOR_ARROW_BLUE)
    c.setLineWidth(2)
    c.line(inflow_cx, flow_cy - radius, inflow_cx, bend_y)
    c.line(inflow_cx, bend_y, private_cx - radius * 0.3, bend_y)
    _draw_arrow_line(c, private_cx - radius * 0.3, bend_y, private_cx - radius * 0.15, private_cy + radius * 0.5, COLOR_ARROW_BLUE, width=2, head_size=10)
    _label_on_line(c, inflow_cx, bend_y, private_cx - radius * 0.3, bend_y, f"{_fmt_money(excess)}/mo", COLOR_ARROW_BLUE, font_size=10, offset=10)

    # Arrow 4: Client contributions -> Inflow (green)
    contrib_x = 0.7 * inch
    contrib_top_y = flow_cy + 1.5 * inch
    client1_salary = inflow / 2 if client.get("is_married") else inflow
    client2_salary = inflow / 2 if client.get("is_married") else 0

    c.setFillColor(COLOR_ARROW_GREEN)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(contrib_x, contrib_top_y, "$")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(contrib_x + 0.35 * inch, contrib_top_y + 4, f"{_fmt_money(client1_salary)} - {client['name_client1']}")
    arrow_start_y = contrib_top_y - 8
    if client.get("is_married") and client.get("name_client2"):
        c.drawString(contrib_x + 0.35 * inch, contrib_top_y - 14, f"{_fmt_money(client2_salary)} - {client['name_client2']}")
        arrow_start_y = contrib_top_y - 28

    arrow_start_x = contrib_x + 0.9 * inch
    arrow_end_x = inflow_cx - radius - 6
    arrow_end_y = flow_cy + radius * 0.2
    _draw_arrow_line(c, arrow_start_x, arrow_start_y, arrow_end_x, arrow_end_y, COLOR_ARROW_GREEN, width=2.5, head_size=11)

    # Arrow 3: Monthly Expenses -> Outflow (black)
    expenses_x = width - 1.4 * inch
    expenses_y = flow_cy + 1.35 * inch
    c.setFillColor(COLOR_BLACK)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 0.7 * inch, expenses_y, "X = Monthly Expenses")
    expenses_arrow_start_x = width - 1.1 * inch
    expenses_arrow_start_y = expenses_y - 18
    expenses_arrow_end_x = outflow_cx + radius * 0.15
    expenses_arrow_end_y = flow_cy + radius * 0.35
    _draw_arrow_line(
        c,
        expenses_arrow_start_x,
        expenses_arrow_start_y,
        expenses_arrow_end_x,
        expenses_arrow_end_y,
        COLOR_BLACK,
        width=1.5,
        head_size=9,
    )

    # Monthly Cashflow below Private Reserve
    c.setFillColor(COLOR_BLACK)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(private_cx, private_cy - radius - 0.35 * inch, "MONTHLY CASHFLOW")


def _draw_page2_balances(c: canvas.Canvas, width: float, height: float, client: dict, report: dict):
    _draw_page_header(c, width, height, client, report)

    box_y = height - 2.2 * inch
    sections = [
        ("Private Reserve Balance", report.get("private_reserve_balance")),
        ("Schwab Brokerage Balance", report.get("schwab_brokerage_balance")),
        ("Target Savings", report.get("private_reserve_target")),
    ]
    for title, value in sections:
        c.setFillColor(colors.HexColor("#E3F2FD"))
        c.roundRect(1 * inch, box_y, width - 2 * inch, 0.9 * inch, 8, fill=1, stroke=0)
        c.setFillColor(COLOR_BLACK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1.3 * inch, box_y + 0.5 * inch, title)
        c.setFont("Helvetica-Bold", 16)
        c.drawRightString(width - 1.3 * inch, box_y + 0.45 * inch, _fmt_money(value))
        box_y -= 1.2 * inch


def generate_sacs_pdf(client: dict, report: dict) -> bytes:
    buffer = BytesIO()
    page_size = landscape(letter)
    c = canvas.Canvas(buffer, pagesize=page_size)
    width, height = page_size

    _draw_page_header(c, width, height, client, report)
    _draw_page1_diagram(c, width, height, client, report)
    c.showPage()

    _draw_page2_balances(c, width, height, client, report)
    c.save()
    buffer.seek(0)
    return buffer.read()
