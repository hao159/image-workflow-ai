import json
import re
import time
import traceback
import uuid
from typing import Optional

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from . import cache, config, db
from .engine import run_workflow
from .image_normalize import normalize_image
from .models import RunEvent, RunRequest, Workflow
from .nodes import node_type_metadata
from .oauth_routes import router as oauth_router
from .providers import PROVIDER_NAMES, model_catalog
from .update_check import check_for_update

db.init_db()

app = FastAPI(title="Image Workflow")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(oauth_router)


@app.get("/api/version")
def get_version():
    return {"version": config.APP_VERSION}


@app.get("/api/update-check")
async def get_update_check(force: bool = False):
    """So version đang chạy với release GitHub mới nhất. Notify-only (không tự cập nhật)."""
    return await check_for_update(force=force)


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
        return JSONResponse({"error": "Tên cấu hình không được để trống.",
                             "code": "config_name_empty"}, status_code=400)
    if cfg.provider not in PROVIDER_NAMES:
        return JSONResponse({"error": f"Provider không hợp lệ: {cfg.provider}",
                             "code": "config_provider_invalid"}, status_code=400)
    existing = db.get_model_config(name)
    if existing and existing["id"] != cfg.id:
        return JSONResponse({"error": f"Đã có cấu hình tên '{name}'.",
                             "code": "config_name_exists"}, status_code=400)
    config_id = db.save_model_config(
        name, cfg.provider, cfg.api_key.strip(), cfg.model.strip(),
        cfg.base_url.strip(), config_id=cfg.id)
    if config_id is None:
        return JSONResponse({"error": "Không tìm thấy cấu hình cần cập nhật.",
                             "code": "config_not_found"}, status_code=404)
    return {"id": config_id, "name": name}


@app.delete("/api/model-configs/{config_id}")
def delete_model_config(config_id: int):
    if not db.delete_model_config(config_id):
        return JSONResponse({"error": "Không tìm thấy cấu hình.",
                             "code": "config_not_found"}, status_code=404)
    return {"deleted": config_id}


# ---------- Danh sách model cho dropdown (static curated + fetch live) ----------

class ProviderModelsIn(BaseModel):
    # refresh=False → chỉ trả static (đổi provider, không chạm mạng).
    # refresh=True  → fetch live thật (nút "⟳ Tải từ API").
    # config_id: dùng key/base_url đã lưu (lúc sửa, key form để trống).
    # api_key/base_url: dùng trực tiếp (lúc tạo mới, key gõ trong form chưa lưu).
    refresh: bool = False
    config_id: Optional[int] = None
    api_key: str = ""
    base_url: str = ""


@app.post("/api/providers/{provider}/models")
def list_provider_models(provider: str, body: ProviderModelsIn):
    """Trả {static, live, error}. Fetch live luôn fail mềm → static vẫn về, HTTP 200."""
    if provider not in model_catalog.STATIC:
        return JSONResponse({"error": f"Provider không hợp lệ: {provider}",
                             "code": "config_provider_invalid"}, status_code=400)

    static = model_catalog.STATIC[provider]
    if not body.refresh:
        return {"static": static, "live": [], "error": None}

    api_key, base_url = body.api_key.strip(), body.base_url.strip()
    if body.config_id is not None:
        cfg = db.get_model_config_by_id(body.config_id)
        if cfg:  # key/base_url đã lưu thắng giá trị body rỗng
            api_key = api_key or cfg["api_key"]
            base_url = base_url or cfg["base_url"]

    live: list[str] = []
    error = None
    try:
        live = model_catalog.fetch_live(provider, api_key, base_url)
    except Exception as e:  # noqa: BLE001 — fail mềm, giữ static
        error = str(e)
    return {"static": static, "live": live, "error": error}


@app.post("/api/upload")
async def upload_image(file: UploadFile):
    ext = (file.filename or "img.png").rsplit(".", 1)[-1].lower()
    if ext not in ("png", "jpg", "jpeg", "webp", "gif", "bmp"):
        return JSONResponse({"error": "Định dạng ảnh không hỗ trợ.",
                             "code": "upload_format_unsupported"}, status_code=400)
    data = await file.read()
    # Chuẩn hóa: thu nhỏ ≤ 2048px + nén (chặn upload vài chục MB, base64 nhẹ hơn).
    try:
        data, out_ext = normalize_image(data)
    except ValueError as e:
        msg = str(e)
        # Distinguish size-guard vs. decode failure for i18n
        if "quá lớn" in msg:
            code = "upload_too_large"
        else:
            code = "upload_invalid"
        return JSONResponse({"error": msg, "code": code}, status_code=400)
    file_id = f"{uuid.uuid4().hex}.{out_ext}"
    (config.UPLOADS_DIR / file_id).write_bytes(data)
    return {"file_id": file_id, "url": f"/api/uploads/{file_id}"}


def _safe_file(directory, name: str):
    path = (directory / name).resolve()
    if not path.is_relative_to(directory) or not path.is_file():
        return None
    return path


_IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}


def _list_images(directory, url_prefix: str):
    # Liệt kê file ảnh trong thư mục → mới nhất trước (theo mtime). Bỏ file không phải ảnh.
    if not directory.is_dir():
        return []
    items = []
    for p in directory.iterdir():
        if not p.is_file() or p.suffix.lower().lstrip(".") not in _IMAGE_EXTS:
            continue
        st = p.stat()
        items.append({
            "name": p.name,
            "url": f"{url_prefix}/{p.name}",
            "size": st.st_size,
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)),
            "_mtime": st.st_mtime,
        })
    items.sort(key=lambda x: x["_mtime"], reverse=True)
    for it in items:
        del it["_mtime"]
    return items


# List routes registered before /{name} catch-alls so they match first.
@app.get("/api/uploads")
def list_uploads():
    return _list_images(config.UPLOADS_DIR, "/api/uploads")


@app.get("/api/outputs")
def list_outputs():
    return _list_images(config.OUTPUTS_DIR, "/api/outputs")


# Delete routes registered before GET /{name} so Starlette finds the right method
# when a path-traversal attempt (e.g. "../../x") is passed as {name}.
@app.delete("/api/uploads/{name:path}")
def delete_upload(name: str):
    # {name:path} captures encoded slashes (%2f) so path-traversal attempts reach this
    # handler and are rejected by _safe_file instead of leaking to the SPA catch-all.
    path = _safe_file(config.UPLOADS_DIR, name)
    if not path:
        return JSONResponse({"error": "Không tìm thấy file.", "code": "file_not_found"},
                            status_code=404)
    path.unlink(missing_ok=True)
    return {"deleted": name}


@app.delete("/api/outputs/{name:path}")
def delete_output(name: str):
    # Same rationale as delete_upload above.
    path = _safe_file(config.OUTPUTS_DIR, name)
    if not path:
        return JSONResponse({"error": "Không tìm thấy file.", "code": "file_not_found"},
                            status_code=404)
    path.unlink(missing_ok=True)
    return {"deleted": name}


@app.get("/api/uploads/{name}")
def get_upload(name: str):
    path = _safe_file(config.UPLOADS_DIR, name)
    if not path:
        return JSONResponse({"error": "Không tìm thấy file.", "code": "file_not_found"},
                            status_code=404)
    return FileResponse(path)


@app.get("/api/outputs/{name}")
def get_output(name: str):
    path = _safe_file(config.OUTPUTS_DIR, name)
    if not path:
        return JSONResponse({"error": "Không tìm thấy file.", "code": "file_not_found"},
                            status_code=404)
    return FileResponse(path)


@app.get("/api/cache-image/{sha}")
def get_cache_image(sha: str):
    # Ảnh GỐC full-res của node AI/biến đổi: phục vụ blob cache theo sha256
    # (frontend lấy sha từ output meta). sha hex 64 ký tự → chặn path traversal.
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        return JSONResponse({"error": "Mã ảnh không hợp lệ.", "code": "file_not_found"},
                            status_code=404)
    path = _safe_file(config.CACHE_DIR / "blobs", f"{sha}.bin")
    if not path:
        return JSONResponse(
            {"error": "Ảnh gốc không còn trong cache (đã bị dọn).",
             "code": "file_not_found"}, status_code=404)
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
        return JSONResponse({"error": "Không tìm thấy workflow.",
                             "code": "workflow_not_found"}, status_code=404)
    return data


@app.post("/api/workflows")
def save_workflow(workflow: Workflow, overwrite: bool = False):
    name = workflow.name.strip() or "untitled"
    # Trùng tên & chưa bật ghi đè → 409 để frontend hỏi xác nhận (tránh đè ngầm).
    if not overwrite and db.workflow_exists(name):
        return JSONResponse({"error": "exists", "name": name,
                             "code": "workflow_exists"}, status_code=409)
    db.save_workflow(name, workflow.model_dump())
    return {"saved": name}


@app.delete("/api/workflows/{name}")
def delete_workflow(name: str):
    if not db.delete_workflow(name):
        return JSONResponse({"error": "Không tìm thấy workflow.",
                             "code": "workflow_not_found"}, status_code=404)
    return {"deleted": name}


# ---------- Lịch sử thực thi (exec history) ----------

@app.get("/api/workflows/{name}/executions")
def list_workflow_executions(name: str, page: int = 1, size: int = 10):
    page = max(1, page)
    size = max(1, min(size, 100))
    rows, total = db.list_executions(name, size, (page - 1) * size)
    return {"items": rows, "total": total, "page": page, "size": size}


@app.get("/api/executions/{exec_id}")
def get_workflow_execution(exec_id: int):
    rec = db.get_execution(exec_id)
    if rec is None:
        return JSONResponse({"error": "Không tìm thấy bản ghi thực thi.",
                             "code": "execution_not_found"}, status_code=404)
    return rec


@app.delete("/api/executions/{exec_id}")
def delete_workflow_execution(exec_id: int):
    if not db.delete_execution(exec_id):
        return JSONResponse({"error": "Không tìm thấy bản ghi thực thi.",
                             "code": "execution_not_found"}, status_code=404)
    return {"deleted": exec_id}


@app.delete("/api/workflows/{name}/executions")
def clear_workflow_executions(name: str):
    return {"cleared": db.clear_executions(name)}


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
                type="run_error", message=f"Workflow không hợp lệ: {e}",
                code="workflow_invalid").model_dump_json())
            return

        # Chỉ ghi lịch sử cho ▶ Chạy (full) — KHÔNG ghi chạy 1 node lẻ
        # (target≠None) để lịch sử sạch.
        record_mode = "full" if target is None else None

        # Gom dữ liệu run để lưu DB: trạng thái từng node, sha ảnh kết quả.
        nodes_status: dict[str, str] = {}
        output_refs: list[str] = []
        outcome = {"status": "running", "error": ""}  # cập nhật khi run_finished/run_error

        def _record(event: RunEvent):
            if event.type == "node_started" and event.node_id:
                nodes_status[event.node_id] = "running"
            elif event.type == "node_finished" and event.node_id:
                nodes_status[event.node_id] = "done"
                for meta in (event.outputs or {}).values():
                    if isinstance(meta, dict) and meta.get("dtype") == "image" \
                            and meta.get("sha") and meta["sha"] not in output_refs:
                        output_refs.append(meta["sha"])
            elif event.type == "node_error" and event.node_id:
                nodes_status[event.node_id] = "error"
            elif event.type == "run_finished":
                outcome["status"] = "success"
            elif event.type == "run_error":
                outcome["status"] = "error"
                outcome["error"] = event.message or ""

        async def emit(event: RunEvent):
            if record_mode:
                _record(event)
            await ws.send_text(event.model_dump_json(exclude_none=True))

        exec_id = db.create_execution(
            workflow.name.strip() or "untitled", record_mode) if record_mode else None
        started = time.monotonic()
        try:
            try:
                await run_workflow(workflow, emit, target=target, force_ids=force)
            except WebSocketDisconnect:
                raise
            except Exception as e:  # noqa: BLE001 — lỗi engine ngoài dự kiến phải về UI
                traceback.print_exc()
                outcome["status"], outcome["error"] = "error", str(e)
                await emit(RunEvent(type="run_error", message=f"Lỗi nội bộ server: {e}",
                                    code="internal_error"))
        finally:
            # Chốt bản ghi kể cả khi client ngắt giữa chừng (status còn 'running' → 'stopped').
            if exec_id is not None:
                if outcome["status"] == "running":
                    outcome["status"] = "stopped"
                detail = {"nodes": nodes_status, "output_refs": output_refs}
                db.finish_execution(exec_id, outcome["status"], outcome["error"],
                                    detail, int((time.monotonic() - started) * 1000))
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ws.close()
        except RuntimeError:
            pass


# ---------- Phục vụ SPA (frontend build) cùng origin ----------
# Mount Ở CUỐI: Starlette khớp route theo thứ tự đăng ký → mọi /api/* và /ws/run
# ở trên thắng; phần còn lại do StaticFiles xử lý (html=True trả index.html tại /).
# Frontend không có client-side router (chỉ React Flow) nên không cần history-fallback.
# Chỉ mount khi có thư mục build (chạy dev với Vite proxy thì SPA_DIR vắng → bỏ qua).
if config.SPA_DIR.is_dir():
    app.mount("/", StaticFiles(directory=config.SPA_DIR, html=True), name="spa")
