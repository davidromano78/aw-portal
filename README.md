# AW Client Report Portal

Internal portal for Educated Freedom to manage client profiles, enter quarterly financial balances, auto-calculate SACS/TCC totals, and generate PDF reports.

## Features

- Client profile management (lightweight CRM)
- Account structure builder (retirement, non-retirement, trust, liabilities)
- Quarterly report data entry with live calculation preview
- SACS and TCC PDF generation (ReportLab)
- Report history with PDF/ZIP download

## Local Development

```bash
cd aw-portal
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

A sample client is seeded on first startup.

## Tests

```bash
pytest
```

## Railway Deployment

1. Create a new Railway project and connect this repo/folder.
2. Add a persistent volume and set `RAILWAY_DATABASE_PATH` to a path on that volume (e.g. `/data/portal.db`).
3. Railway uses `railway.toml` / `Procfile` to start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Health check: `GET /health`

**Note:** Do not add a custom `nixpacks.toml` with manual `pip install` — it breaks Railway's Python auto-detection. Let Nixpacks detect Python from `requirements.txt`.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `RAILWAY_DATABASE_PATH` | SQLite file path on persistent volume (production) |
| `PORT` | HTTP port (set by Railway) |

## Business Rules

- Excess = Inflow − Outflow
- Private Reserve Target = (6 × monthly expenses) + insurance deductibles
- Liabilities are shown separately and **not** subtracted from net worth
- Trust is **not** included in non-retirement total
