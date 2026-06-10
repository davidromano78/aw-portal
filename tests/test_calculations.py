from decimal import Decimal

from app.calculations import (
    calculate_age,
    grand_total,
    private_reserve_target,
    sacs_excess,
    sum_balances,
    compute_report_totals,
)


def test_sacs_excess():
    assert sacs_excess(15000, 12000) == Decimal("3000.00")


def test_private_reserve_target():
    assert private_reserve_target(12000, 5000) == Decimal("77000.00")
    assert private_reserve_target(12000, 5000, override=80000) == Decimal("80000.00")


def test_grand_total_excludes_liabilities():
    total = grand_total(11162.47, 126160.38, 189308.04, 0)
    assert total == Decimal("326630.89")


def test_sum_balances():
    assert sum_balances([11162.47, 0]) == Decimal("11162.47")


def test_compute_report_totals():
    totals = compute_report_totals(
        monthly_salary=15000,
        monthly_expense_budget=12000,
        insurance_deductibles_total=5000,
        private_reserve_target_override=None,
        inflow_balance=990,
        outflow_balance=12990,
        private_reserve_balance=86788,
        c1_retirement_balances=[11162.47, 0],
        c2_retirement_balances=[37232.46, 70042, 18885.92],
        non_retirement_balances=[448.26, 44024, 44067.78, 0, 990, 12990, 86788],
        trust_balance=0,
        liability_balances=[224218.24, 107587.31, 11152],
    )
    assert totals["excess"] == Decimal("3000.00")
    assert totals["c1_retirement_total"] == Decimal("11162.47")
    assert totals["c2_retirement_total"] == Decimal("126160.38")
    assert totals["nr_total"] == Decimal("189308.04")
    assert totals["grand_total"] == Decimal("326630.89")
    assert totals["liabilities_total"] == Decimal("342957.55")


def test_calculate_age():
    age = calculate_age("1970-01-15")
    assert age >= 50
