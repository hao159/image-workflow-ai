"""Unit test cho model_catalog + endpoint danh sách model (mock mạng, không key thật).

Chạy: backend\\.venv\\Scripts\\python.exe -m pytest test_model_catalog.py
"""
import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.providers import model_catalog


# ---------- STATIC ----------

def test_static_has_known_providers():
    for p in ("gemini", "openai", "codex"):
        assert p in model_catalog.STATIC
    assert "gemini-2.5-flash-image" in model_catalog.STATIC["gemini"]
    assert "gpt-5.5" in model_catalog.STATIC["codex"]


# ---------- fetch_live ----------

def test_fetch_live_gemini_requires_key():
    with pytest.raises(ValueError):
        model_catalog.fetch_live("gemini", api_key="")


def test_fetch_live_openai_parses_and_filters(monkeypatch):
    class _Resp:
        def raise_for_status(self): pass
        def json(self):
            return {"data": [{"id": "gpt-4o"}, {"id": "gpt-image-1"},
                             {"id": "whisper-1"}, {"id": "text-embedding-3"}]}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp())
    out = model_catalog.fetch_live("openai", api_key="sk-test")
    assert "gpt-4o" in out and "gpt-image-1" in out
    assert "whisper-1" not in out  # lọc về model gpt/image/dall


def test_fetch_live_codex_returns_empty():
    assert model_catalog.fetch_live("codex") == []


# ---------- Endpoint ----------

client = TestClient(main.app)


def test_endpoint_invalid_provider():
    r = client.post("/api/providers/nope/models", json={})
    assert r.status_code == 400


def test_endpoint_static_only_no_network(monkeypatch):
    # refresh mặc định False → KHÔNG gọi fetch_live.
    def _boom(*a, **k):
        raise AssertionError("fetch_live không được gọi khi refresh=False")
    monkeypatch.setattr(model_catalog, "fetch_live", _boom)
    r = client.post("/api/providers/gemini/models", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["static"] == model_catalog.STATIC["gemini"]
    assert body["live"] == [] and body["error"] is None


def test_endpoint_refresh_soft_fails(monkeypatch):
    monkeypatch.setattr(model_catalog, "fetch_live",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("key sai")))
    r = client.post("/api/providers/openai/models",
                    json={"refresh": True, "api_key": "bad"})
    assert r.status_code == 200  # fail mềm
    body = r.json()
    assert body["static"] == model_catalog.STATIC["openai"]
    assert body["live"] == [] and "key sai" in body["error"]


def test_endpoint_refresh_success(monkeypatch):
    monkeypatch.setattr(model_catalog, "fetch_live",
                        lambda *a, **k: ["gpt-4o", "gpt-image-1"])
    r = client.post("/api/providers/openai/models",
                    json={"refresh": True, "api_key": "sk"})
    body = r.json()
    assert body["error"] is None and body["live"] == ["gpt-4o", "gpt-image-1"]
