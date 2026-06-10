from app.pdf.sacs_template import generate_sacs_pdf


def _sample_client():
    return {
        "display_name": "Sample Client",
        "name_client1": "Client 1",
        "name_client2": "Client 2",
        "is_married": True,
        "monthly_salary": 15000,
        "monthly_expense_budget": 12000,
    }


def _sample_report():
    return {
        "report_date": "2026-06-10",
        "excess": 3000,
        "private_reserve_balance": 86788,
        "schwab_brokerage_balance": 0,
        "private_reserve_target": 77000,
    }


def test_sacs_pdf_generates_successfully():
    pdf = generate_sacs_pdf(_sample_client(), _sample_report())
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 2000


def test_sacs_pdf_uses_landscape_pages():
    pdf = generate_sacs_pdf(_sample_client(), _sample_report())
    # Landscape letter MediaBox: 792 x 612 points
    assert b"/MediaBox" in pdf
    assert b"792" in pdf
    assert b"612" in pdf
