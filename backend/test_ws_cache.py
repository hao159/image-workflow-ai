"""Test WS cache protocol (Phase 2) — envelope target/force + cached flag + clear.

CẦN backend đang chạy (offline node, KHÔNG dùng AI → không tốn token):
  Terminal 1: backend\\.venv\\Scripts\\python backend\\run_server.py
  Terminal 2: backend\\.venv\\Scripts\\python.exe test_ws_cache.py

Workflow test: load_image → filter(grayscale) → resize → save_image (toàn node local).
"""
import asyncio
import io
import json

import httpx
import websockets
from PIL import Image

BASE = "http://127.0.0.1:8000"
WS = "ws://127.0.0.1:8000/ws/run"


def _wf(file_id):
    return {
        "name": "ws-cache-test",
        "nodes": [
            {"id": "n1", "type": "load_image", "params": {"file_id": file_id}},
            {"id": "n2", "type": "filter", "params": {"filter": "grayscale"}},
            {"id": "n3", "type": "resize",
             "params": {"width": 200, "height": 200, "keep_aspect": True}},
            {"id": "n4", "type": "save_image", "params": {"prefix": "wscache"}},
        ],
        "edges": [
            {"source": "n1", "sourceHandle": "image", "target": "n2", "targetHandle": "image"},
            {"source": "n2", "sourceHandle": "image", "target": "n3", "targetHandle": "image"},
            {"source": "n3", "sourceHandle": "image", "target": "n4", "targetHandle": "image"},
        ],
    }


async def _run(message: dict) -> dict:
    """Gửi 1 message WS, gom node_finished theo node_id. Raise nếu run_error."""
    finished = {}
    async with websockets.connect(WS) as ws:
        await ws.send(json.dumps(message))
        async for msg in ws:
            ev = json.loads(msg)
            if ev["type"] == "node_finished":
                finished[ev["node_id"]] = ev
            elif ev["type"] == "run_error":
                raise AssertionError(f"run_error: {ev.get('message')}")
            elif ev["type"] == "run_finished":
                break
    return finished


async def main():
    # 0. Upload ảnh test
    async with httpx.AsyncClient(base_url=BASE) as client:
        img = Image.new("RGB", (640, 400), (200, 80, 40))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        r = await client.post("/api/upload",
                              files={"file": ("t.png", buf.getvalue(), "image/png")})
        r.raise_for_status()
        file_id = r.json()["file_id"]

        # Bắt đầu sạch cache
        r = await client.post("/api/cache/clear")
        r.raise_for_status()
        assert r.json() == {"cleared": True}

    wf = _wf(file_id)

    # 1. Run đầu (envelope, target=null) → tất cả cached=false
    f1 = await _run({"workflow": wf, "target": None, "force": []})
    assert len(f1) == 4, f"phải có 4 node_finished, có {len(f1)}"
    assert all(not e["cached"] for e in f1.values()), "lần 1 phải toàn cached=false"

    # 2. Run lại y hệt → tất cả cached=true
    f2 = await _run({"workflow": wf, "target": None, "force": []})
    assert all(e["cached"] for e in f2.values()), f"lần 2 phải toàn cached=true: {f2}"

    # 3. target=resize(n3) + force=[n3] → n1/n2 cache-hit, n3 chạy lại, n4 bị prune
    f3 = await _run({"workflow": wf, "target": "n3", "force": ["n3"]})
    assert f3["n1"]["cached"] and f3["n2"]["cached"], "upstream phải cache-hit"
    assert not f3["n3"]["cached"], "n3 bị force → cached=false"
    assert "n4" not in f3, "target=n3 → n4 (downstream) không được chạy"

    # 4. Clear cache → run lại → tất cả cached=false
    async with httpx.AsyncClient(base_url=BASE) as client:
        r = await client.post("/api/cache/clear")
        r.raise_for_status()
    f4 = await _run({"workflow": wf, "target": None, "force": []})
    assert all(not e["cached"] for e in f4.values()), "sau clear phải toàn cached=false"

    # 5. Workflow thuần (không bọc envelope) → vẫn chạy (backward-compat)
    f5 = await _run(wf)
    assert len(f5) == 4, "workflow thuần phải chạy đủ 4 node"

    print("\n=== WS CACHE PASS ===")


asyncio.run(main())
