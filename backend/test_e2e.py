"""Test end-to-end: upload ảnh -> chạy workflow local (filter -> resize -> save) qua WebSocket."""
import asyncio
import io
import json

import httpx
import websockets
from PIL import Image

BASE = "http://127.0.0.1:8000"


async def main():
    # 1. Kiểm tra API node-types
    async with httpx.AsyncClient(base_url=BASE) as client:
        r = await client.get("/api/node-types")
        r.raise_for_status()
        types = [t["type"] for t in r.json()]
        print("node types:", types)
        assert "generate_image" in types and "edit_image" in types

        # 2. Upload một ảnh test
        img = Image.new("RGB", (640, 400), (200, 80, 40))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        r = await client.post("/api/upload", files={"file": ("test.png", buf.getvalue(), "image/png")})
        r.raise_for_status()
        file_id = r.json()["file_id"]
        print("uploaded:", file_id)

    # 3. Chạy workflow qua WebSocket
    workflow = {
        "name": "e2e-test",
        "nodes": [
            {"id": "n1", "type": "load_image", "params": {"file_id": file_id}},
            {"id": "n2", "type": "filter", "params": {"filter": "grayscale"}},
            {"id": "n3", "type": "resize", "params": {"width": 200, "height": 200, "keep_aspect": True}},
            {"id": "n4", "type": "save_image", "params": {"prefix": "e2e"}},
        ],
        "edges": [
            {"source": "n1", "sourceHandle": "image", "target": "n2", "targetHandle": "image"},
            {"source": "n2", "sourceHandle": "image", "target": "n3", "targetHandle": "image"},
            {"source": "n3", "sourceHandle": "image", "target": "n4", "targetHandle": "image"},
        ],
    }
    events = []
    async with websockets.connect("ws://127.0.0.1:8000/ws/run") as ws:
        await ws.send(json.dumps(workflow))
        async for msg in ws:
            ev = json.loads(msg)
            events.append(ev)
            print("event:", ev["type"], ev.get("node_id") or "", ev.get("message") or "",
                  "(có preview)" if ev.get("preview") else "")
            if ev["type"] in ("run_finished", "run_error"):
                break

    assert events[-1]["type"] == "run_finished", f"Run thất bại: {events[-1]}"
    finished = [e for e in events if e["type"] == "node_finished"]
    assert len(finished) == 4
    save_out = next(e for e in finished if e["node_id"] == "n4")
    path = save_out["outputs"]["path"]["value"]
    print("saved to:", path)

    # 4. Tải lại ảnh đã lưu, kiểm tra kích thước
    async with httpx.AsyncClient(base_url=BASE) as client:
        r = await client.get(path)
        r.raise_for_status()
        out = Image.open(io.BytesIO(r.content))
        print("output image:", out.size, out.mode)
        assert max(out.size) == 200

    print("\n=== E2E PASS ===")


asyncio.run(main())
