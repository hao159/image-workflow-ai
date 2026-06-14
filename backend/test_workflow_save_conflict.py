"""Test save-conflict 409: lưu tên mới → 200; trùng tên chưa overwrite → 409;
overwrite=true → 200 ghi đè. Dùng DB tạm (override config.DB_PATH) + TestClient,
KHÔNG cần backend chạy sẵn.

Chạy: backend\\.venv\\Scripts\\python.exe -m pytest backend/test_workflow_save_conflict.py -q
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app import config, db
    # DB + thư mục workflows tạm → không đụng dữ liệu thật, không migrate file cũ.
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    monkeypatch.setattr(config, "WORKFLOWS_DIR", wf_dir)
    db.init_db()  # tạo bảng trong DB tạm; _connect() đọc DB_PATH động nên mọi query trúng tạm
    from app.main import app
    return TestClient(app)


def _wf(name):
    return {"name": name, "nodes": [], "edges": []}


def test_save_new_then_conflict_then_overwrite(client):
    # 1. Lưu tên mới → 200
    r = client.post("/api/workflows", json=_wf("wf-a"))
    assert r.status_code == 200
    assert r.json()["saved"] == "wf-a"

    # 2. Lưu lại trùng tên, không overwrite → 409 {"error":"exists"}
    r = client.post("/api/workflows", json=_wf("wf-a"))
    assert r.status_code == 409
    assert r.json()["error"] == "exists"
    assert r.json()["name"] == "wf-a"

    # 3. overwrite=true → 200 ghi đè
    r = client.post("/api/workflows?overwrite=true", json=_wf("wf-a"))
    assert r.status_code == 200
    assert r.json()["saved"] == "wf-a"


def test_different_names_no_conflict(client):
    assert client.post("/api/workflows", json=_wf("wf-1")).status_code == 200
    assert client.post("/api/workflows", json=_wf("wf-2")).status_code == 200
