from typing import Literal

from pydantic import BaseModel, Field


OwnerType = Literal["client1", "client2", "joint"]
CategoryType = Literal["retirement", "non_retirement", "trust", "liability", "sacs"]
ReportStatus = Literal["draft", "complete"]


class AccountIn(BaseModel):
    id: int | None = None
    owner: OwnerType
    category: CategoryType
    account_type: str
    label: str
    last_four: str | None = None
    property_address: str | None = None
    interest_rate: float | None = None
    sort_order: int = 0


class ClientIn(BaseModel):
    display_name: str
    name_client1: str
    name_client2: str | None = None
    dob_client1: str
    dob_client2: str | None = None
    ssn_last4_client1: str | None = None
    ssn_last4_client2: str | None = None
    monthly_salary: float = 0
    monthly_expense_budget: float = 0
    insurance_deductibles_total: float = 0
    private_reserve_target_override: float | None = None
    is_married: bool = False
    accounts: list[AccountIn] = Field(default_factory=list)


class BalanceIn(BaseModel):
    account_id: int | None = None
    balance: float = 0
    cash_balance: float | None = None
    as_of_date: str | None = None


class ReportIn(BaseModel):
    report_date: str
    status: ReportStatus = "draft"
    inflow_balance: float | None = None
    outflow_balance: float | None = None
    private_reserve_balance: float | None = None
    schwab_brokerage_balance: float | None = None
    balances: list[BalanceIn] = Field(default_factory=list)
