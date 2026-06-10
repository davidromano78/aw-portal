from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.schemas import ClientIn
from app.services import create_client, delete_client, get_client, list_clients, update_client

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/clients", response_class=HTMLResponse)
def clients_page(request: Request):
    return templates.TemplateResponse(
        "clients.html",
        {"request": request, "clients": list_clients()},
    )


@router.get("/clients/new", response_class=HTMLResponse)
def new_client_page(request: Request):
    return templates.TemplateResponse(
        "client_form.html",
        {"request": request, "client": None, "mode": "create"},
    )


@router.get("/clients/{client_id}", response_class=HTMLResponse)
def edit_client_page(request: Request, client_id: int):
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return templates.TemplateResponse(
        "client_form.html",
        {"request": request, "client": client, "mode": "edit"},
    )


@router.post("/api/clients")
def api_create_client(payload: ClientIn):
    client_id = create_client(payload)
    return {"id": client_id}


@router.put("/api/clients/{client_id}")
def api_update_client(client_id: int, payload: ClientIn):
    if not update_client(client_id, payload):
        raise HTTPException(status_code=404, detail="Client not found")
    return {"ok": True}


@router.delete("/api/clients/{client_id}")
def api_delete_client(client_id: int):
    if not delete_client(client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    return {"ok": True}


@router.post("/clients")
async def create_client_form(request: Request):
    form = await request.form()
    payload = _client_from_form(form)
    client_id = create_client(payload)
    return RedirectResponse(url=f"/clients/{client_id}", status_code=303)


@router.post("/clients/{client_id}")
async def update_client_form(request: Request, client_id: int):
    form = await request.form()
    payload = _client_from_form(form)
    if not update_client(client_id, payload):
        raise HTTPException(status_code=404, detail="Client not found")
    return RedirectResponse(url=f"/clients/{client_id}", status_code=303)


def _client_from_form(form) -> ClientIn:
    from app.schemas import AccountIn

    accounts = []
    account_count = int(form.get("account_count") or 0)
    for i in range(account_count):
        if not form.get(f"account_label_{i}"):
            continue
        accounts.append(
            AccountIn(
                owner=form.get(f"account_owner_{i}"),
                category=form.get(f"account_category_{i}"),
                account_type=form.get(f"account_type_{i}") or "Account",
                label=form.get(f"account_label_{i}"),
                last_four=form.get(f"account_last_four_{i}") or None,
                property_address=form.get(f"account_property_{i}") or None,
                interest_rate=float(form.get(f"account_rate_{i}") or 0) or None,
                sort_order=i,
            )
        )

    return ClientIn(
        display_name=form.get("display_name"),
        name_client1=form.get("name_client1"),
        name_client2=form.get("name_client2") or None,
        dob_client1=form.get("dob_client1"),
        dob_client2=form.get("dob_client2") or None,
        ssn_last4_client1=form.get("ssn_last4_client1") or None,
        ssn_last4_client2=form.get("ssn_last4_client2") or None,
        monthly_salary=float(form.get("monthly_salary") or 0),
        monthly_expense_budget=float(form.get("monthly_expense_budget") or 0),
        insurance_deductibles_total=float(form.get("insurance_deductibles_total") or 0),
        private_reserve_target_override=float(form.get("private_reserve_target_override") or 0) or None,
        is_married=form.get("is_married") == "on",
        accounts=accounts,
    )
