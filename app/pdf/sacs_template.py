from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _fmt_money(value: float | None) -> str:
    if value is None:
        return "$0"
    return f"${value:,.0f}" if float(value).is_integer() else f"${value:,.2f}"


def _draw_circle(c: canvas.Canvas, x: float, y: float, radius: float, fill_color, label: str, amount: str):
    c.setFillColor(fill_color)
    c.circle(x, y, radius, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.roundRect(x - 55, y - 12, 110, 24, 4, fill=1, stroke=0)
    c.setFillColor(fill_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(x, y - 5, amount)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(x, y + radius - 18, label)
    c.setFont("Helvetica", 9)
    c.drawCentredString(x, y - radius + 14, "$1,000 Floor")


def generate_sacs_pdf(client: dict, report: dict) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    inflow = client["monthly_salary"]
    outflow = client["monthly_expense_budget"]
    excess = report.get("excess") or (inflow - outflow)
    client1_salary = inflow / 2 if client.get("is_married") else inflow
    client2_salary = inflow / 2 if client.get("is_married") else 0

    # Page 1
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 0.75 * inch, "Simple Automated Cashflow System (SACS)")
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - inch, f"{client['display_name']} — {report['report_date']}")

    inflow_x, outflow_x, private_x = 1.6 * inch, width / 2, width - 1.6 * inch
    circle_y = height / 2 + 0.3 * inch
    radius = 0.85 * inch

    c.setFont("Helvetica", 10)
    c.drawString(0.6 * inch, circle_y + 1.3 * inch, f"${client1_salary:,.0f} - {client['name_client1']}")
    if client.get("is_married"):
        c.drawString(0.6 * inch, circle_y + 1.1 * inch, f"${client2_salary:,.0f} - {client['name_client2']}")

    _draw_circle(c, inflow_x, circle_y, radius, colors.HexColor("#2E7D32"), "INFLOW", _fmt_money(inflow))
    _draw_circle(c, outflow_x, circle_y, radius, colors.HexColor("#C62828"), "OUTFLOW", _fmt_money(outflow))
    _draw_circle(
        c,
        width / 2,
        circle_y - 2.2 * inch,
        radius,
        colors.HexColor("#1565C0"),
        "PRIVATE RESERVE",
        _fmt_money(excess) + "/mo*",
    )

    c.setStrokeColor(colors.HexColor("#C62828"))
    c.setLineWidth(3)
    c.line(inflow_x + radius + 5, circle_y, outflow_x - radius - 5, circle_y)
    c.setFillColor(colors.HexColor("#C62828"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, circle_y + 18, f"X = {_fmt_money(outflow)}/month*")
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, circle_y - 18, "Automated transfer on the 28th")

    c.setStrokeColor(colors.HexColor("#1565C0"))
    c.setLineWidth(2)
    c.line(inflow_x, circle_y - radius, width / 2, circle_y - 2.2 * inch + radius)
    c.setFillColor(colors.HexColor("#1565C0"))
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString((inflow_x + width / 2) / 2, circle_y - 1.2 * inch, f"{_fmt_money(excess)}/mo*")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 0.6 * inch, circle_y + 1.1 * inch, "X = Monthly Expenses")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, 0.8 * inch, "MONTHLY CASHFLOW")

    c.showPage()

    # Page 2
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 0.75 * inch, "Simple Automated Cashflow System (SACS)")
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - inch, f"{client['display_name']} — {report['report_date']}")

    box_y = height - 2.5 * inch
    sections = [
        ("Private Reserve Balance", report.get("private_reserve_balance")),
        ("Schwab Brokerage Balance", report.get("schwab_brokerage_balance")),
        ("Target Savings", report.get("private_reserve_target")),
    ]
    for title, value in sections:
        c.setFillColor(colors.HexColor("#E3F2FD"))
        c.roundRect(1 * inch, box_y, width - 2 * inch, 0.9 * inch, 8, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1.3 * inch, box_y + 0.5 * inch, title)
        c.setFont("Helvetica-Bold", 16)
        c.drawRightString(width - 1.3 * inch, box_y + 0.45 * inch, _fmt_money(value))
        box_y -= 1.2 * inch

    c.save()
    buffer.seek(0)
    return buffer.read()
