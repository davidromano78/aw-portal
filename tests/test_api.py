import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RAILWAY_DATABASE_PATH", str(db_path))
    from app.database import init_db
    from app.main import app
    from app.services import seed_sample_client

    init_db()
    seed_sample_client()
    return TestClient(app)


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_clients_page(client):
    res = client.get("/clients")
    assert res.status_code == 200
    assert "Sample Client" in res.text


def test_pdf_downloads(client):
    from app.services import list_reports

    report_id = list_reports()[0]["id"]
    sacs = client.get(f"/reports/{report_id}/download/sacs")
    tcc = client.get(f"/reports/{report_id}/download/tcc")
    zip_all = client.get(f"/reports/{report_id}/download/all")
    assert sacs.status_code == 200
    assert tcc.status_code == 200
    assert zip_all.status_code == 200
    assert sacs.headers["content-type"] == "application/pdf"
    assert len(sacs.content) > 1000
