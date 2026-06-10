import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "portal.db"


def get_db_path() -> Path:
    env_path = os.environ.get("RAILWAY_DATABASE_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def init_db() -> None:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                name_client1 TEXT NOT NULL,
                name_client2 TEXT,
                dob_client1 TEXT NOT NULL,
                dob_client2 TEXT,
                ssn_last4_client1 TEXT,
                ssn_last4_client2 TEXT,
                monthly_salary REAL NOT NULL DEFAULT 0,
                monthly_expense_budget REAL NOT NULL DEFAULT 0,
                insurance_deductibles_total REAL NOT NULL DEFAULT 0,
                private_reserve_target_override REAL,
                is_married INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                owner TEXT NOT NULL CHECK(owner IN ('client1', 'client2', 'joint')),
                category TEXT NOT NULL CHECK(category IN ('retirement', 'non_retirement', 'trust', 'liability', 'sacs')),
                account_type TEXT NOT NULL,
                label TEXT NOT NULL,
                last_four TEXT,
                property_address TEXT,
                interest_rate REAL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                report_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'complete')),
                inflow_balance REAL,
                outflow_balance REAL,
                private_reserve_balance REAL,
                schwab_brokerage_balance REAL,
                excess REAL,
                private_reserve_target REAL,
                c1_retirement_total REAL,
                c2_retirement_total REAL,
                nr_total REAL,
                trust_value REAL,
                grand_total REAL,
                liabilities_total REAL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS report_balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                account_id INTEGER,
                balance REAL NOT NULL DEFAULT 0,
                cash_balance REAL,
                as_of_date TEXT,
                FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL
            );
            """
        )


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)
