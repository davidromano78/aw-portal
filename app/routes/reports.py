from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.schemas import BalanceIn, ReportIn
from app.services import (
    create_report,
    get_client,
    get_last_report_balances,
    get_report,
    list_reports,
    update_report,
    validate_report_complete,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/clients/{client_id}/reports/new", response_class=HTMLResponse)
def new_report_page(request: Request, client_id: int):
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    last_balances = get_last_report_balances(client_id)
    return templates.TemplateResponse(
        "report_entry.html",
        {
            "request": request,
            "client": client,
            "report": None,
            "last_balances": last_balances,
            "errors": [],
        },
    )


@router.get("/reports/{report_id}", response_class=HTMLResponse)
def edit_report_page(request: Request, report_id: int):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    last_balances = get_last_report_balances(report["client_id"])
    return templates.TemplateResponse(
        "report_entry.html",
        {
            "request": request,
            "client": report["client"],
            "report": report,
            "last_balances": last_balances,
            "errors": [],
        },
    )


@router.get("/reports", response_class=HTMLResponse)
def reports_history_page(request: Request, client_id: int | None = Query(default=None)):
    return templates.TemplateResponse(
        "report_history.html",
        {
            "request": request,
            "reports": list_reports(client_id),
            "client_id": client_id,
        },
    )


@router.post("/api/reports/preview")
async def preview_report(request: Request):
    body = await request.json()
    client = get_client(body["client_id"])
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    payload = ReportIn(**body["report"])
    from app.services import _group_balances
    from app.calculations import compute_report_totals

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
    return {k: float(v) for k, v in totals.items()}


@router.post("/clients/{client_id}/reports")
async def create_report_form(request: Request, client_id: int):
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    payload = await _report_from_form(request, client)
    errors = validate_report_complete(client, payload) if payload.status == "complete" else []
    if errors:
        return templates.TemplateResponse(
            "report_entry.html",
            {
                "request": request,
                "client": client,
                "report": payload.model_dump(),
                "last_balances": get_last_report_balances(client_id),
                "errors": errors,
            },
            status_code=400,
        )
    report_id = create_report(client_id, payload)
    return RedirectResponse(url=f"/reports/{report_id}", status_code=303)


@router.post("/reports/{report_id}")
async def update_report_form(request: Request, report_id: int):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    client = report["client"]
    payload = await _report_from_form(request, client)
    errors = validate_report_complete(client, payload) if payload.status == "complete" else []
    if errors:
        return templates.TemplateResponse(
            "report_entry.html",
            {
                "request": request,
                "client": client,
                "report": {**report, **payload.model_dump()},
                "last_balances": get_last_report_balances(client["id"]),
                "errors": errors,
            },
            status_code=400,
        )
    update_report(report_id, payload)
    return RedirectResponse(url=f"/reports/{report_id}", status_code=303)


async def _report_from_form(request: Request, client: dict) -> ReportIn:
    form = await request.form()
    balances = []
    for account in client["accounts"]:
        if account["category"] in ("retirement", "non_retirement", "trust", "liability"):
            bal_val = form.get(f"balance_{account['id']}")
            cash_val = form.get(f"cash_{account['id']}")
            as_of = form.get(f"as_of_{account['id']}")
            balances.append(
                BalanceIn(
                    account_id=account["id"],
                    balance=float(bal_val or 0),
                    cash_balance=float(cash_val) if cash_val else None,
                    as_of_date=as_of or None,
                )
            )

    return ReportIn(
        report_date=form.get("report_date"),
        status=form.get("status") or "draft",
        inflow_balance=float(form.get("inflow_balance") or 0) if form.get("inflow_balance") else None,
        outflow_balance=float(form.get("outflow_balance") or 0) if form.get("outflow_balance") else None,
        private_reserve_balance=float(form.get("private_reserve_balance") or 0) if form.get("private_reserve_balance") else None,
        schwab_brokerage_balance=float(form.get("schwab_brokerage_balance") or 0) if form.get("schwab_brokerage_balance") else None,
        balances=balances,
    )
