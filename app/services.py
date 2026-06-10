from __future__ import annotations

from datetime import date

from app.calculations import calculate_age, compute_report_totals, money
from app.database import get_connection, row_to_dict
from app.schemas import AccountIn, BalanceIn, ClientIn, ReportIn


def _fetch_accounts(conn, client_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM accounts WHERE client_id = ? ORDER BY sort_order, id",
        (client_id,),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def list_clients() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.*,
                   (
                       SELECT MAX(r.report_date)
                       FROM reports r
                       WHERE r.client_id = c.id AND r.status = 'complete'
                   ) AS last_report_date
            FROM clients c
            ORDER BY c.display_name
            """
        ).fetchall()
        clients = []
        for row in rows:
            client = row_to_dict(row)
            client["age_client1"] = calculate_age(client["dob_client1"])
            if client.get("dob_client2"):
                client["age_client2"] = calculate_age(client["dob_client2"])
            clients.append(client)
        return clients


def get_client(client_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        if not row:
            return None
        client = row_to_dict(row)
        client["age_client1"] = calculate_age(client["dob_client1"])
        if client.get("dob_client2"):
            client["age_client2"] = calculate_age(client["dob_client2"])
        client["accounts"] = _fetch_accounts(conn, client_id)
        return client


def _save_accounts(conn, client_id: int, accounts: list[AccountIn]) -> None:
    conn.execute("DELETE FROM accounts WHERE client_id = ?", (client_id,))
    for idx, account in enumerate(accounts):
        conn.execute(
            """
            INSERT INTO accounts (
                client_id, owner, category, account_type, label,
                last_four, property_address, interest_rate, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                account.owner,
                account.category,
                account.account_type,
                account.label,
                account.last_four,
                account.property_address,
                account.interest_rate,
                account.sort_order if account.sort_order else idx,
            ),
        )


def create_client(payload: ClientIn) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO clients (
                display_name, name_client1, name_client2,
                dob_client1, dob_client2,
                ssn_last4_client1, ssn_last4_client2,
                monthly_salary, monthly_expense_budget,
                insurance_deductibles_total, private_reserve_target_override,
                is_married
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.display_name,
                payload.name_client1,
                payload.name_client2,
                payload.dob_client1,
                payload.dob_client2,
                payload.ssn_last4_client1,
                payload.ssn_last4_client2,
                payload.monthly_salary,
                payload.monthly_expense_budget,
                payload.insurance_deductibles_total,
                payload.private_reserve_target_override,
                1 if payload.is_married else 0,
            ),
        )
        client_id = cursor.lastrowid
        _save_accounts(conn, client_id, payload.accounts)
        return client_id


def update_client(client_id: int, payload: ClientIn) -> bool:
    with get_connection() as conn:
        result = conn.execute(
            """
            UPDATE clients SET
                display_name = ?, name_client1 = ?, name_client2 = ?,
                dob_client1 = ?, dob_client2 = ?,
                ssn_last4_client1 = ?, ssn_last4_client2 = ?,
                monthly_salary = ?, monthly_expense_budget = ?,
                insurance_deductibles_total = ?, private_reserve_target_override = ?,
                is_married = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                payload.display_name,
                payload.name_client1,
                payload.name_client2,
                payload.dob_client1,
                payload.dob_client2,
                payload.ssn_last4_client1,
                payload.ssn_last4_client2,
                payload.monthly_salary,
                payload.monthly_expense_budget,
                payload.insurance_deductibles_total,
                payload.private_reserve_target_override,
                1 if payload.is_married else 0,
                client_id,
            ),
        )
        if result.rowcount == 0:
            return False
        _save_accounts(conn, client_id, payload.accounts)
        return True


def delete_client(client_id: int) -> bool:
    with get_connection() as conn:
        result = conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        return result.rowcount > 0


def _group_balances(client: dict, balances: list[BalanceIn]) -> dict:
    balance_map = {b.account_id: b for b in balances if b.account_id is not None}
    c1_ret, c2_ret, nr, liab = [], [], [], []
    trust_balance = 0.0

    for account in client["accounts"]:
        bal = balance_map.get(account["id"])
        value = bal.balance if bal else 0.0
        if account["category"] == "retirement":
            if account["owner"] == "client1":
                c1_ret.append(value)
            elif account["owner"] == "client2":
                c2_ret.append(value)
        elif account["category"] == "non_retirement":
            nr.append(value)
        elif account["category"] == "trust":
            trust_balance = value
        elif account["category"] == "liability":
            liab.append(value)

    return {
        "c1_retirement_balances": c1_ret,
        "c2_retirement_balances": c2_ret,
        "non_retirement_balances": nr,
        "trust_balance": trust_balance,
        "liability_balances": liab,
    }


def _compute_and_store_totals(conn, client: dict, report_id: int, payload: ReportIn) -> dict:
    grouped = _group_balances(client, payload.balances)
    totals = compute_report_totals(
        monthly_salary=client["monthly_salary"],
        monthly_expense_budget=client["monthly_expense_budget"],
        insurance_deductibles_total=client["insurance_deductibles_total"],
        private_reserve_target_override=client["private_reserve_target_override"],
        inflow_balance=payload.inflow_balance,
        outflow_balance=payload.outflow_balance,
        private_reserve_balance=payload.private_reserve_balance,
        **grouped,
    )

    conn.execute(
        """
        UPDATE reports SET
            report_date = ?, status = ?,
            inflow_balance = ?, outflow_balance = ?,
            private_reserve_balance = ?, schwab_brokerage_balance = ?,
            excess = ?, private_reserve_target = ?,
            c1_retirement_total = ?, c2_retirement_total = ?,
            nr_total = ?, trust_value = ?, grand_total = ?, liabilities_total = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            payload.report_date,
            payload.status,
            float(totals["inflow_balance"]),
            float(totals["outflow_balance"]),
            float(totals["private_reserve_balance"]),
            float(payload.schwab_brokerage_balance or 0),
            float(totals["excess"]),
            float(totals["private_reserve_target"]),
            float(totals["c1_retirement_total"]),
            float(totals["c2_retirement_total"]),
            float(totals["nr_total"]),
            float(totals["trust_value"]),
            float(totals["grand_total"]),
            float(totals["liabilities_total"]),
            report_id,
        ),
    )
    return {k: float(v) for k, v in totals.items()}


def _save_report_balances(conn, report_id: int, balances: list[BalanceIn]) -> None:
    conn.execute("DELETE FROM report_balances WHERE report_id = ?", (report_id,))
    for bal in balances:
        if bal.account_id is None:
            continue
        conn.execute(
            """
            INSERT INTO report_balances (report_id, account_id, balance, cash_balance, as_of_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (report_id, bal.account_id, bal.balance, bal.cash_balance, bal.as_of_date),
        )


def create_report(client_id: int, payload: ReportIn) -> int | None:
    client = get_client(client_id)
    if not client:
        return None

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reports (client_id, report_date, status)
            VALUES (?, ?, ?)
            """,
            (client_id, payload.report_date, payload.status),
        )
        report_id = cursor.lastrowid
        _save_report_balances(conn, report_id, payload.balances)
        _compute_and_store_totals(conn, client, report_id, payload)
        return report_id


def update_report(report_id: int, payload: ReportIn) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not row:
            return False
        client = get_client(row["client_id"])
        if not client:
            return False
        _save_report_balances(conn, report_id, payload.balances)
        _compute_and_store_totals(conn, client, report_id, payload)
        return True


def get_report(report_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not row:
            return None
        report = row_to_dict(row)
        client = get_client(report["client_id"])
        report["client"] = client
        balance_rows = conn.execute(
            "SELECT * FROM report_balances WHERE report_id = ?",
            (report_id,),
        ).fetchall()
        report["balances"] = [row_to_dict(r) for r in balance_rows]
        return report


def list_reports(client_id: int | None = None) -> list[dict]:
    with get_connection() as conn:
        if client_id:
            rows = conn.execute(
                """
                SELECT r.*, c.display_name
                FROM reports r
                JOIN clients c ON c.id = r.client_id
                WHERE r.client_id = ?
                ORDER BY r.report_date DESC, r.id DESC
                """,
                (client_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT r.*, c.display_name
                FROM reports r
                JOIN clients c ON c.id = r.client_id
                ORDER BY r.report_date DESC, r.id DESC
                """
            ).fetchall()
        return [row_to_dict(r) for r in rows]


def get_last_report_balances(client_id: int) -> dict[int, dict]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id FROM reports
            WHERE client_id = ? AND status = 'complete'
            ORDER BY report_date DESC, id DESC
            LIMIT 1
            """,
            (client_id,),
        ).fetchone()
        if not row:
            return {}
        balances = conn.execute(
            "SELECT * FROM report_balances WHERE report_id = ?",
            (row["id"],),
        ).fetchall()
        return {b["account_id"]: row_to_dict(b) for b in balances if b["account_id"]}


def validate_report_complete(client: dict, payload: ReportIn) -> list[str]:
    errors: list[str] = []
    if not payload.report_date:
        errors.append("Report date is required.")

    required_sacs = [
        ("inflow_balance", "Inflow balance"),
        ("outflow_balance", "Outflow balance"),
        ("private_reserve_balance", "Private Reserve balance"),
        ("schwab_brokerage_balance", "Schwab brokerage balance"),
    ]
    for field, label in required_sacs:
        value = getattr(payload, field)
        if value is None:
            errors.append(f"{label} is required.")

    balance_map = {b.account_id: b for b in payload.balances if b.account_id}
    for account in client["accounts"]:
        if account["category"] in ("retirement", "non_retirement", "trust", "liability"):
            bal = balance_map.get(account["id"])
            if not bal or bal.balance is None:
                errors.append(f"Balance required for {account['label']}.")

    return errors


def seed_sample_client() -> int | None:
    existing = list_clients()
    if any(c["display_name"] == "Sample Client" for c in existing):
        return next(c["id"] for c in existing if c["display_name"] == "Sample Client")

    sample = ClientIn(
        display_name="Sample Client",
        name_client1="Client 1",
        name_client2="Client 2",
        dob_client1="1970-01-15",
        dob_client2="1972-06-20",
        ssn_last4_client1="1234",
        ssn_last4_client2="5678",
        monthly_salary=15000,
        monthly_expense_budget=12000,
        insurance_deductibles_total=5000,
        is_married=True,
        accounts=[
            AccountIn(owner="client1", category="retirement", account_type="Roth IRA", label="Roth IRA", sort_order=0),
            AccountIn(owner="client1", category="retirement", account_type="IRA", label="IRA", sort_order=1),
            AccountIn(owner="client2", category="retirement", account_type="IRA", label="IRA", sort_order=2),
            AccountIn(owner="client2", category="retirement", account_type="401K", label="401K", sort_order=3),
            AccountIn(owner="client2", category="retirement", account_type="Roth IRA", label="Roth IRA", sort_order=4),
            AccountIn(owner="joint", category="non_retirement", account_type="Checking", label="Wells Fargo Main Checking", sort_order=5),
            AccountIn(owner="joint", category="non_retirement", account_type="Savings", label="Wells Fargo Savings", sort_order=6),
            AccountIn(owner="joint", category="non_retirement", account_type="FICA", label="StoneCastle FICA", sort_order=7),
            AccountIn(owner="joint", category="non_retirement", account_type="Brokerage", label="Schwab JT TEN", sort_order=8),
            AccountIn(owner="joint", category="non_retirement", account_type="Checking", label="Pinnacle Inflow", sort_order=9),
            AccountIn(owner="joint", category="non_retirement", account_type="Checking", label="Pinnacle Outflow", sort_order=10),
            AccountIn(owner="joint", category="non_retirement", account_type="Savings", label="Pinnacle Private Reserve", sort_order=11),
            AccountIn(owner="joint", category="trust", account_type="Family Trust", label="Client 1 and Client 2 Family Trust", property_address="123 Main St", sort_order=12),
            AccountIn(owner="joint", category="liability", account_type="Mortgage", label="P Mortg", interest_rate=3.5, sort_order=13),
            AccountIn(owner="joint", category="liability", account_type="Mortgage", label="S Mortg", interest_rate=4.0, sort_order=14),
            AccountIn(owner="joint", category="liability", account_type="Auto Loan", label="Mercedes", interest_rate=5.9, sort_order=15),
        ],
    )
    client_id = create_client(sample)
    client = get_client(client_id)

    balance_values = {
        "Roth IRA": (11162.47, 316),
        "IRA": (0, None),
        "401K": (70042, None),
        "Wells Fargo Main Checking": (448.26, None),
        "Wells Fargo Savings": (44024, None),
        "StoneCastle FICA": (44067.78, None),
        "Schwab JT TEN": (0, None),
        "Pinnacle Inflow": (990, None),
        "Pinnacle Outflow": (12990, None),
        "Pinnacle Private Reserve": (86788, None),
        "Client 1 and Client 2 Family Trust": (0, None),
        "P Mortg": (224218.24, None),
        "S Mortg": (107587.31, None),
        "Mercedes": (11152, None),
    }
    balances = []
    for acct in client["accounts"]:
        val, cash = balance_values.get(acct["label"], (0, None))
        if acct["label"] == "IRA" and acct["owner"] == "client2":
            val, cash = 37232.46, 914
        if acct["label"] == "Roth IRA" and acct["owner"] == "client2":
            val, cash = 18885.92, 508
        balances.append(
            BalanceIn(account_id=acct["id"], balance=val, cash_balance=cash, as_of_date="2023-07-25")
        )

    report_payload = ReportIn(
        report_date=date.today().isoformat(),
        status="complete",
        inflow_balance=990,
        outflow_balance=12990,
        private_reserve_balance=86788,
        schwab_brokerage_balance=0,
        balances=balances,
    )
    create_report(client_id, report_payload)
    return client_id
