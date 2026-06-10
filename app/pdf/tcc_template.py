from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.calculations import calculate_age


def _fmt_money(value: float | None) -> str:
    if value is None:
        return "$0.00"
    return f"${value:,.2f}"


def _draw_account_bubble(c: canvas.Canvas, x: float, y: float, account: dict, balance: float, cash: float | None, as_of: str | None):
    c.setFillColor(colors.HexColor("#E8F5E9"))
    c.circle(x, y, 0.55 * inch, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x, y + 22, account["account_type"].upper())
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x, y + 6, _fmt_money(balance))
    if as_of:
        c.setFont("Helvetica", 7)
        c.drawCentredString(x, y - 8, f"as of {as_of}")
    if cash is not None:
        c.drawCentredString(x, y - 20, f"${cash:,.0f} Cash")


def _draw_client_info(c: canvas.Canvas, x: float, y: float, name: str, dob: str, ssn: str | None):
    c.setFillColor(colors.HexColor("#2E7D32"))
    c.ellipse(x - 70, y - 18, x + 70, y + 18, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x, y + 8, name)
    age = calculate_age(dob)
    c.setFont("Helvetica", 8)
    c.drawCentredString(x, y - 2, f"Age {age} | DOB {dob}")
    if ssn:
        c.drawCentredString(x, y - 12, f"SSN ...{ssn}")


def _positions(count: int, start_x: float, end_x: float, y: float) -> list[tuple[float, float]]:
    if count <= 0:
        return []
    if count == 1:
        return [((start_x + end_x) / 2, y)]
    step = (end_x - start_x) / (count - 1)
    return [(start_x + i * step, y) for i in range(count)]


def generate_tcc_pdf(client: dict, report: dict) -> bytes:
    buffer = BytesIO()
    page_size = landscape(letter)
    c = canvas.Canvas(buffer, pagesize=page_size)
    width, height = page_size

    balance_map = {b["account_id"]: b for b in report.get("balances", []) if b.get("account_id")}

    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.5 * inch, height - 0.5 * inch, client["display_name"])
    c.setFont("Helvetica", 11)
    c.drawString(0.5 * inch, height - 0.75 * inch, f"Date: {report['report_date']}")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 0.5 * inch, height - 0.5 * inch, f"GRAND TOTAL: {_fmt_money(report.get('grand_total'))}")
    c.drawRightString(width - 0.5 * inch, height - 0.75 * inch, f"Total Liabilities: {_fmt_money(report.get('liabilities_total'))}")

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 1.1 * inch, "RETIREMENT")
    c.line(0.5 * inch, height - 1.25 * inch, width - 0.5 * inch, height - 1.25 * inch)
    c.drawCentredString(width / 2, height / 2 - 0.15 * inch, "NON RETIREMENT")

    _draw_client_info(c, 1.5 * inch, height - 1.6 * inch, client["name_client1"], client["dob_client1"], client.get("ssn_last4_client1"))
    if client.get("is_married") and client.get("dob_client2"):
        _draw_client_info(c, width - 1.5 * inch, height - 1.6 * inch, client["name_client2"], client["dob_client2"], client.get("ssn_last4_client2"))

    c1_accounts = [a for a in client["accounts"] if a["category"] == "retirement" and a["owner"] == "client1"]
    c2_accounts = [a for a in client["accounts"] if a["category"] == "retirement" and a["owner"] == "client2"]
    nr_accounts = [a for a in client["accounts"] if a["category"] == "non_retirement"]
    trust_accounts = [a for a in client["accounts"] if a["category"] == "trust"]
    liability_accounts = [a for a in client["accounts"] if a["category"] == "liability"]

    ret_y = height - 2.4 * inch
    for (acct, pos) in zip(c1_accounts, _positions(len(c1_accounts), 0.8 * inch, width / 2 - 0.4 * inch, ret_y)):
        bal = balance_map.get(acct["id"], {})
        _draw_account_bubble(c, pos[0], pos[1], acct, bal.get("balance", 0), bal.get("cash_balance"), bal.get("as_of_date"))

    for (acct, pos) in zip(c2_accounts, _positions(len(c2_accounts), width / 2 + 0.4 * inch, width - 0.8 * inch, ret_y)):
        bal = balance_map.get(acct["id"], {})
        _draw_account_bubble(c, pos[0], pos[1], acct, bal.get("balance", 0), bal.get("cash_balance"), bal.get("as_of_date"))

    c.setFillColor(colors.HexColor("#EEEEEE"))
    c.roundRect(0.7 * inch, ret_y - 0.95 * inch, 1.8 * inch, 0.45 * inch, 4, fill=1, stroke=0)
    c.roundRect(width - 2.5 * inch, ret_y - 0.95 * inch, 1.8 * inch, 0.45 * inch, 4, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(1.6 * inch, ret_y - 0.78 * inch, f"C1 Retirement: {_fmt_money(report.get('c1_retirement_total'))}")
    c.drawCentredString(width - 1.6 * inch, ret_y - 0.78 * inch, f"C2 Retirement: {_fmt_money(report.get('c2_retirement_total'))}")

    nr_y = height / 2 - 0.9 * inch
    left_nr = [a for a in nr_accounts if a["sort_order"] < (nr_accounts[-1]["sort_order"] if nr_accounts else 0) or len(nr_accounts) <= 6]
    mid = max(1, len(nr_accounts) // 2)
    left_nr = nr_accounts[:mid]
    right_nr = nr_accounts[mid:]

    for (acct, pos) in zip(left_nr, _positions(len(left_nr), 0.8 * inch, width / 2 - 1.2 * inch, nr_y)):
        bal = balance_map.get(acct["id"], {})
        _draw_account_bubble(c, pos[0], pos[1], acct, bal.get("balance", 0), bal.get("cash_balance"), bal.get("as_of_date"))

    for (acct, pos) in zip(right_nr, _positions(len(right_nr), width / 2 + 1.2 * inch, width - 0.8 * inch, nr_y)):
        bal = balance_map.get(acct["id"], {})
        _draw_account_bubble(c, pos[0], pos[1], acct, bal.get("balance", 0), bal.get("cash_balance"), bal.get("as_of_date"))

    if trust_accounts:
        trust = trust_accounts[0]
        bal = balance_map.get(trust["id"], {})
        c.setFillColor(colors.HexColor("#E3F2FD"))
        c.circle(width / 2, nr_y, 0.65 * inch, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(width / 2, nr_y + 18, trust["label"])
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width / 2, nr_y, _fmt_money(bal.get("balance", 0)))
        if trust.get("property_address"):
            c.setFont("Helvetica", 7)
            c.drawCentredString(width / 2, nr_y - 18, trust["property_address"])

    c.setFillColor(colors.HexColor("#EEEEEE"))
    c.roundRect(width / 2 - 1.4 * inch, nr_y - 1.5 * inch, 2.8 * inch, 0.45 * inch, 4, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2, nr_y - 1.32 * inch, f"Non-Retirement Total: {_fmt_money(report.get('nr_total'))}")

    if liability_accounts:
        table_x = width / 2 - 1.6 * inch
        table_y = nr_y - 2.0 * inch
        c.setFillColor(colors.HexColor("#BDBDBD"))
        c.rect(table_x, table_y - 0.15 * inch - 0.22 * inch * len(liability_accounts), 3.2 * inch, 0.22 * inch * len(liability_accounts) + 0.3 * inch, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(table_x + 0.1 * inch, table_y, "Liabilities")
        row_y = table_y - 0.2 * inch
        for acct in liability_accounts:
            bal = balance_map.get(acct["id"], {})
            rate = f"{acct['interest_rate']}%" if acct.get("interest_rate") is not None else ""
            c.setFont("Helvetica", 8)
            c.drawString(table_x + 0.1 * inch, row_y, acct["label"])
            c.drawString(table_x + 1.2 * inch, row_y, rate)
            c.drawRightString(table_x + 3.0 * inch, row_y, _fmt_money(bal.get("balance", 0)))
            row_y -= 0.22 * inch

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#C62828"))
    c.drawRightString(width - 0.5 * inch, 0.4 * inch, "* Indicates we do not have up to date information")

    c.save()
    buffer.seek(0)
    return buffer.read()
