"""Test thư viện ảnh: list uploads/outputs (lọc ảnh, mới nhất trước) + delete an toàn.
Dùng thư mục tạm (monkeypatch config) + TestClient, KHÔNG cần backend chạy sẵn.

Chạy: backend\\.venv\\Scripts\\python.exe -m pytest backend/test_image_library.py -q
"""
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app import config
    up = tmp_path / "uploads"; up.mkdir()
    out = tmp_path / "outputs"; out.mkdir()
    monkeypatch.setattr(config, "UPLOADS_DIR", up)
    monkeypatch.setattr(config, "OUTPUTS_DIR", out)
    from app.main import app
    return TestClient(app)


def test_list_uploads_filters_and_sorts_newest_first(client):
    from app import config
    a = config.UPLOADS_DIR / "a.png"; a.write_bytes(b"x")
    b = config.UPLOADS_DIR / "b.jpg"; b.write_bytes(b"yy")
    (config.UPLOADS_DIR / "notes.txt").write_text("skip")  # không phải ảnh → bỏ
    os.utime(a, (1000, 1000))  # a cũ hơn
    os.utime(b, (2000, 2000))  # b mới hơn

    r = client.get("/api/uploads")
    assert r.status_code == 200
    data = r.json()
    assert [it["name"] for it in data] == ["b.jpg", "a.png"]  # mới nhất trước
    assert data[0]["url"] == "/api/uploads/b.jpg"
    assert data[0]["size"] == 2
    assert "modified" in data[0]


def test_delete_output_removes_file(client):
    from app import config
    f = config.OUTPUTS_DIR / "result.png"; f.write_bytes(b"z")
    r = client.delete("/api/outputs/result.png")
    assert r.status_code == 200
    assert r.json()["deleted"] == "result.png"
    assert not f.exists()


def test_delete_missing_returns_404(client):
    r = client.delete("/api/uploads/nope.png")
    assert r.status_code == 404


def test_delete_path_traversal_rejected(client):
    r = client.delete("/api/uploads/..%2f..%2fsecret.txt")
    assert r.status_code == 404
