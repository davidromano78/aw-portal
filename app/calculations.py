from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def to_decimal(value: float | int | str | Decimal | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def money(value: float | int | str | Decimal | None) -> Decimal:
    return to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_age(dob_str: str, as_of: date | None = None) -> int:
    as_of = as_of or date.today()
    dob = date.fromisoformat(dob_str)
    age = as_of.year - dob.year
    if (as_of.month, as_of.day) < (dob.month, dob.day):
        age -= 1
    return age


def sacs_excess(inflow: float | Decimal, outflow: float | Decimal) -> Decimal:
    return money(to_decimal(inflow) - to_decimal(outflow))


def private_reserve_target(
    monthly_expenses: float | Decimal,
    deductibles: float | Decimal,
    override: float | Decimal | None = None,
) -> Decimal:
    if override is not None:
        return money(override)
    return money(to_decimal(monthly_expenses) * 6 + to_decimal(deductibles))


def sum_balances(balances: list[float | Decimal | None]) -> Decimal:
    total = Decimal("0")
    for balance in balances:
        total += to_decimal(balance)
    return money(total)


def retirement_total(balances: list[float | Decimal | None]) -> Decimal:
    return sum_balances(balances)


def non_retirement_total(balances: list[float | Decimal | None]) -> Decimal:
    return sum_balances(balances)


def liabilities_total(balances: list[float | Decimal | None]) -> Decimal:
    return sum_balances(balances)


def grand_total(
    c1_retirement: float | Decimal,
    c2_retirement: float | Decimal,
    non_retirement: float | Decimal,
    trust: float | Decimal,
) -> Decimal:
    return money(
        to_decimal(c1_retirement)
        + to_decimal(c2_retirement)
        + to_decimal(non_retirement)
        + to_decimal(trust)
    )


def compute_report_totals(
    *,
    monthly_salary: float,
    monthly_expense_budget: float,
    insurance_deductibles_total: float,
    private_reserve_target_override: float | None,
    inflow_balance: float | None,
    outflow_balance: float | None,
    private_reserve_balance: float | None,
    c1_retirement_balances: list[float],
    c2_retirement_balances: list[float],
    non_retirement_balances: list[float],
    trust_balance: float,
    liability_balances: list[float],
) -> dict[str, Decimal]:
    inflow = money(monthly_salary)
    outflow = money(monthly_expense_budget)
    excess = sacs_excess(inflow, outflow)
    target = private_reserve_target(
        monthly_expense_budget,
        insurance_deductibles_total,
        private_reserve_target_override,
    )
    c1_total = retirement_total(c1_retirement_balances)
    c2_total = retirement_total(c2_retirement_balances)
    nr_total = non_retirement_total(non_retirement_balances)
    trust_val = money(trust_balance)
    liab_total = liabilities_total(liability_balances)
    grand = grand_total(c1_total, c2_total, nr_total, trust_val)

    return {
        "inflow": inflow,
        "outflow": outflow,
        "excess": excess,
        "private_reserve_target": target,
        "inflow_balance": money(inflow_balance),
        "outflow_balance": money(outflow_balance),
        "private_reserve_balance": money(private_reserve_balance),
        "c1_retirement_total": c1_total,
        "c2_retirement_total": c2_total,
        "nr_total": nr_total,
        "trust_value": trust_val,
        "grand_total": grand,
        "liabilities_total": liab_total,
    }
