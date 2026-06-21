"""Test lịch sử thực thi: create → finish → list (paging) → detail → delete →
clear + prune giữ đúng 50 bản ghi/workflow. Test db trực tiếp + API qua TestClient.

Chạy: backend\\.venv\\Scripts\\python.exe -m pytest backend/test_execution_history.py -q
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def env(tmp_path, monkeypatch):
    from app import config, db
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    monkeypatch.setattr(config, "WORKFLOWS_DIR", wf_dir)
    db.init_db()
    from app.main import app
    return db, TestClient(app)


def test_lifecycle_create_finish_detail_delete(env):
    db, _ = env
    eid = db.create_execution("wf-x", "full")
    detail = {"nodes": {"n1": "done", "n2": "error"},
              "output_refs": ["a" * 64]}
    db.finish_execution(eid, "success", "", detail, 1234)

    rec = db.get_execution(eid)
    assert rec["status"] == "success"
    assert rec["mode"] == "full"
    assert rec["duration_ms"] == 1234
    assert rec["detail"]["nodes"]["n1"] == "done"
    assert rec["detail"]["output_refs"] == ["a" * 64]

    assert db.delete_execution(eid) is True
    assert db.get_execution(eid) is None


def test_list_paging_and_clear_via_api(env):
    db, client = env
    for _ in range(15):
        eid = db.create_execution("wf-page", "full")
        db.finish_execution(eid, "success", "", {}, 10)

    r = client.get("/api/workflows/wf-page/executions?page=1&size=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 15
    assert len(body["items"]) == 10
    assert body["page"] == 1

    r2 = client.get("/api/workflows/wf-page/executions?page=2&size=10")
    assert len(r2.json()["items"]) == 5

    # mới nhất trước (id giảm dần)
    ids = [it["id"] for it in body["items"]]
    assert ids == sorted(ids, reverse=True)

    # clear hết
    r3 = client.delete("/api/workflows/wf-page/executions")
    assert r3.json()["cleared"] == 15
    assert client.get("/api/workflows/wf-page/executions").json()["total"] == 0


def test_prune_keeps_50(env):
    db, _ = env
    for _ in range(55):
        eid = db.create_execution("wf-prune", "full")
        db.finish_execution(eid, "success", "", {}, 10)
    _, total = db.list_executions("wf-prune", 100, 0)
    assert total == 50  # giữ đúng top-50 gần nhất, prune phần cũ hơn


def test_detail_api_and_404(env):
    db, client = env
    eid = db.create_execution("wf-d", "full")
    db.finish_execution(eid, "error", "boom", {"nodes": {"n1": "error"}}, 50)

    r = client.get(f"/api/executions/{eid}")
    assert r.status_code == 200
    assert r.json()["error"] == "boom"
    assert r.json()["detail"]["nodes"]["n1"] == "error"

    assert client.get("/api/executions/999999").status_code == 404
