import json
import re
import traceback
import uuid
from typing import Optional

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ValidationError

from . import cache, config, db
from .engine import run_workflow
from .image_normalize import normalize_image
from .models import RunEvent, RunRequest, Workflow
from .nodes import node_type_metadata
from .oauth_routes import router as oauth_router
from .providers import PROVIDER_NAMES

db.init_db()

app = FastAPI(title="Image Workflow")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(oauth_router)


@app.get("/api/node-types")
def get_node_types():
    return node_type_metadata()


@app.get("/api/providers")
def get_providers():
    return {
        "providers": PROVIDER_NAMES,
        "configured": {
            "gemini": bool(config.GEMINI_API_KEY),
            "openai": bool(config.OPENAI_API_KEY),
            "comfyui": config.COMFYUI_URL,
        },
    }


# ---------- Cấu hình model (API key đặt tên) ----------

class ModelConfigIn(BaseModel):
    id: Optional[int] = None
    name: str
    provider: str
    api_key: str = ""
    model: str = ""
    base_url: str = ""


def _mask_key(key: str) -> str:
    if not key:
        return ""
    return f"••••{key[-4:]}" if len(key) > 4 else "••••"


@app.get("/api/model-configs")
def list_model_configs():
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "provider": c["provider"],
            "model": c["model"],
            "base_url": c["base_url"],
            "api_key_preview": _mask_key(c["api_key"]),
        }
        for c in db.list_model_configs()
    ]


@app.post("/api/model-configs")
def save_model_config(cfg: ModelConfigIn):
    name = cfg.name.strip()
    if not name:
        return JSONResponse({"error": "Tên cấu hình không được để trống."}, status_code=400)
    if cfg.provider not in PROVIDER_NAMES:
        return JSONResponse({"error": f"Provider không hợp lệ: {cfg.provider}"}, status_code=400)
    existing = db.get_model_config(name)
    if existing and existing["id"] != cfg.id:
        return JSONResponse({"error": f"Đã có cấu hình tên '{name}'."}, status_code=400)
    config_id = db.save_model_config(
        name, cfg.provider, cfg.api_key.strip(), cfg.model.strip(),
        cfg.base_url.strip(), config_id=cfg.id)
    if config_id is None:
        return JSONResponse({"error": "Không tìm thấy cấu hình cần cập nhật."}, status_code=404)
    return {"id": config_id, "name": name}


@app.delete("/api/model-configs/{config_id}")
def delete_model_config(config_id: int):
    if not db.delete_model_config(config_id):
        return JSONResponse({"error": "Không tìm thấy cấu hình."}, status_code=404)
    return {"deleted": config_id}


@app.post("/api/upload")
async def upload_image(file: UploadFile):
    ext = (file.filename or "img.png").rsplit(".", 1)[-1].lower()
    if ext not in ("png", "jpg", "jpeg", "webp", "gif", "bmp"):
        return JSONResponse({"error": "Định dạng ảnh không hỗ trợ."}, status_code=400)
    data = await file.read()
    # Chuẩn hóa: thu nhỏ ≤ 2048px + nén (chặn upload vài chục MB, base64 nhẹ hơn).
    try:
        data, out_ext = normalize_image(data)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    file_id = f"{uuid.uuid4().hex}.{out_ext}"
    (config.UPLOADS_DIR / file_id).write_bytes(data)
    return {"file_id": file_id, "url": f"/api/uploads/{file_id}"}


def _safe_file(directory, name: str):
    path = (directory / name).resolve()
    if not path.is_relative_to(directory) or not path.is_file():
        return None
    return path


@app.get("/api/uploads/{name}")
def get_upload(name: str):
    path = _safe_file(config.UPLOADS_DIR, name)
    if not path:
        return JSONResponse({"error": "Không tìm thấy file."}, status_code=404)
    return FileResponse(path)


@app.get("/api/outputs/{name}")
def get_output(name: str):
    path = _safe_file(config.OUTPUTS_DIR, name)
    if not path:
        return JSONResponse({"error": "Không tìm thấy file."}, status_code=404)
    return FileResponse(path)


@app.get("/api/cache-image/{sha}")
def get_cache_image(sha: str):
    # Ảnh GỐC full-res của node AI/biến đổi: phục vụ blob cache theo sha256
    # (frontend lấy sha từ output meta). sha hex 64 ký tự → chặn path traversal.
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        return JSONResponse({"error": "Mã ảnh không hợp lệ."}, status_code=404)
    path = _safe_file(config.CACHE_DIR / "blobs", f"{sha}.bin")
    if not path:
        return JSONResponse(
            {"error": "Ảnh gốc không còn trong cache (đã bị dọn)."}, status_code=404)
    # Output ảnh của node AI/biến đổi luôn là PNG (chỉ các node này dùng endpoint
    # này; node Tải ảnh lên xem qua /api/uploads). Nếu sau route blob khác định
    # dạng qua đây thì cần sniff content-type.
    return FileResponse(path, media_type="image/png")


@app.get("/api/workflows")
def list_workflows():
    return db.list_workflows()


@app.get("/api/workflows/{name}")
def get_workflow(name: str):
    data = db.get_workflow(name)
    if data is None:
        return JSONResponse({"error": "Không tìm thấy workflow."}, status_code=404)
    return data


@app.post("/api/workflows")
def save_workflow(workflow: Workflow):
    name = workflow.name.strip() or "untitled"
    db.save_workflow(name, workflow.model_dump())
    return {"saved": name}


@app.delete("/api/workflows/{name}")
def delete_workflow(name: str):
    if not db.delete_workflow(name):
        return JSONResponse({"error": "Không tìm thấy workflow."}, status_code=404)
    return {"deleted": name}


@app.post("/api/cache/clear")
def clear_cache():
    cache.clear()
    return {"cleared": True}


@app.websocket("/ws/run")
async def ws_run(ws: WebSocket):
    """Client gửi JSON workflow, server stream event tiến độ về.

    Nhận 2 dạng message:
      - Envelope `{"workflow": {...}, "target": "id"|null, "force": ["id",...]}`
        → chạy tới `target`, ép chạy lại `force` (per-node run / chạy tới node).
      - Workflow thuần `{"name","nodes","edges"}` → full run (backward-compat).
    """
    await ws.accept()
    try:
        raw = await ws.receive_text()
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "workflow" in data:  # envelope
                req = RunRequest.model_validate(data)
                workflow, target, force = req.workflow, req.target, frozenset(req.force)
            else:                                               # workflow thuần
                workflow, target, force = Workflow.model_validate(data), None, frozenset()
        except (ValidationError, ValueError) as e:
            await ws.send_text(RunEvent(
                type="run_error", message=f"Workflow không hợp lệ: {e}").model_dump_json())
            return

        async def emit(event: RunEvent):
            await ws.send_text(event.model_dump_json(exclude_none=True))

        try:
            await run_workflow(workflow, emit, target=target, force_ids=force)
        except WebSocketDisconnect:
            raise
        except Exception as e:  # noqa: BLE001 — lỗi engine ngoài dự kiến phải về UI
            traceback.print_exc()
            await emit(RunEvent(type="run_error", message=f"Lỗi nội bộ server: {e}"))
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ws.close()
        except RuntimeError:
            pass
