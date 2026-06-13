# Design: Per-node run + auto-cache (kiểu n8n) + fake provider

**Ngày:** 2026-06-13 | **Loại:** Brainstorm → design (đã user duyệt) | **Plan mode:** `/ck:plan --tdd`

## 1. Problem statement

Mỗi lần thêm/sửa node trên canvas → bấm "▶ Chạy" chạy lại CẢ workflow → gọi lại hết provider AI trả phí (gemini/openai/codex) ở thượng nguồn → tốn token vô ích. Muốn: test từng node kiểu n8n, tái dùng output đã có, chỉ chạy lại phần thật sự đổi.

## 2. Requirements (đã chốt với user)

- **A** — Chạy lại chỉ node đã đổi (+ downstream), tái dùng cache thượng nguồn. Bề mặt: **nút ▶ trên từng node card** (UI canvas). Cache **tự động theo (params + input)** — "đổi gì chạy lại nấy".
- **C** — Test code node mới ở backend khi viết/sửa node: **fake provider** trả ảnh mẫu (offline, không token) + **CLI `run-node`** chạy 1 node.
- Cache lưu **xuống đĩa** (sống qua restart/`--reload`).
- Nút ▶ trên node = **chạy TỚI node này** (node + upstream cần thiết), xem output node đó.
- KHÔNG làm: pinned-data thủ công, mock trong dropdown bắt buộc, auto-evict cache.

## 3. Cơ chế lõi — content-addressed memoization (Merkle / key-propagation)

`node_key = sha256(type + resolved_params + [output_key của node cha] + code_hash)`
- `output_key = (node_key, handle)` = danh tính 1 output. Không hash lại bytes ảnh (key cha đã đại diện).
- `code_hash = sha256(inspect.getsource(NodeClass))` → sửa code node là cache tự vô hiệu (cho kịch bản C dưới `--reload`).
- Đổi param/input bất kỳ ở thượng nguồn → key đổi lan xuống → node đó + downstream chạy lại; phần còn lại cache-hit (không gọi API).

**So sánh đã loại:** value-hash (hash bytes input mỗi run) — đúng nhưng tốn CPU hash ảnh MB; chọn key-propagation cho nhanh + chuẩn build-system.

## 4. Quy tắc nút

| Hành động | Ngữ nghĩa |
|---|---|
| **▶ trên 1 node** | force chạy node đó + cache-hit toàn bộ upstream. Vừa xem output, vừa ép sinh ảnh mới (AI bất định). Upstream AI KHÔNG gọi lại → không tốn token. |
| **▶ Chạy (tổng)** | cache-aware toàn bộ: chỉ node đổi (+ downstream) chạy lại. |
| **🗑 Xóa cache** | wipe để chạy tươi hoàn toàn. |

## 5. Components / files

**Backend**
- `backend/app/cache.py` *(mới ~90)* — disk store: `cache/nodes/{node_key}.json` (manifest: outputs + preview base64 inline) + `cache/blobs/{sha}.bin` (ảnh, dedupe content). API: `load(key)`, `save(key, outputs, preview)`, `clear()`.
- `backend/app/engine.py` *(sửa)* — thêm `target`/`force`, prune ancestors(target)∪{target}, tính node_key, hit/miss. Tách `engine_cache_key.py` nếu engine > 200 dòng.
- `backend/app/models.py` *(sửa)* — `RunEvent.cached: bool=False`; `RunRequest{workflow, target?, force[]}`.
- `backend/app/main.py` *(sửa)* — `/ws/run` parse `RunRequest` (vẫn nhận workflow thuần = full run, backward-compat); `POST /api/cache/clear`.
- `backend/app/providers/fake.py` *(mới)* — `FakeProvider`: `generate/edit` → PNG placeholder (PIL vẽ prompt lên nền màu), `generate_text` echo. Đăng ký `fake` + cờ `FORCE_FAKE` trong `providers/__init__.py`.
- `backend/run_node.py` *(mới ~80, CLI)* — `--type --param k=v --input handle=path --fake --out`; build inputs, `cls.resolve_params`, `cls().run()`, in meta + lưu ảnh.

**Frontend**
- `frontend/src/RunContext.jsx` *(mới nhỏ)* — expose `runNode(id)` cho node card.
- `frontend/src/App.jsx` *(sửa)* — `runNode(id)` gửi target+force; `run()` tổng cache-aware; nút 🗑 Xóa cache; xử lý event `cached`.
- `frontend/src/components/WorkflowNode.jsx` *(sửa)* — nút ▶ header + badge "đã dùng cache".
- `frontend/src/api.js` *(sửa)* — `openRunSocket` gửi envelope `{workflow, target, force}`; `clearCache()`.

**Tests**
- `backend/test_engine_cache.py` *(mới, offline + fake, có `__main__` runner như test_nodes.py)* — cache-hit lần 2; đổi param→re-run; đổi upstream→downstream re-run; target prune đúng; persistence qua instance mới; clear. Đếm số lần FakeProvider gọi để chứng minh "không gọi lại".
- Giữ nguyên `test_e2e.py` (full run vẫn chạy), `test_nodes.py`.

## 6. Phases

1. **Engine memoization + cache.py + key** (backend, offline) — TDD: viết `test_engine_cache.py` trước, chưa đụng UI.
2. **WS protocol** — target/force, `RunEvent.cached`, `/api/cache/clear`.
3. **Frontend** — ▶ per-node, badge cache, run tổng cache-aware, Xóa cache.
4. **Fake provider + run-node CLI** (kịch bản C).

## 7. Acceptance criteria

- `Prompt→Tạo ảnh(AI)→Resize`, chạy 1 lần (1 call). Thêm `Lưu ảnh`, ▶ trên nó → AI KHÔNG gọi lại (cache hit), chỉ node mới chạy.
- Đổi prompt node AI → nó + downstream chạy lại; đổi param Resize → AI cache-hit, chỉ Resize chạy.
- Restart backend (`--reload`) → cache vẫn còn (đĩa).
- `python run_node.py --type enhance_prompt --param text=... --fake` chạy offline, in output.
- `test_engine_cache.py` pass (FakeProvider call-count chứng minh không gọi lại).

## 8. Constraints

- Python/FastAPI backend, React + @xyflow/react frontend. File code < 200 dòng (modularize).
- KHÔNG phá: setup keepalive WS (`ws_ping_interval=None`), full-run hiện tại, test_e2e/test_nodes.
- pytest CHƯA cài trong venv → test chạy qua block `__main__` (như test_nodes.py/test_codex.py): `backend\.venv\Scripts\python.exe test_engine_cache.py`.
- `cache/` thêm vào `.gitignore`.

## 9. Risks & mitigations

- **AI bất định vs cache:** dùng lại ảnh cũ là cố ý (tiết kiệm token); muốn mới → ▶ force. Ghi rõ docs.
- **Cache stale khi sửa code node + `--reload`:** `code_hash` trong key + ▶ force + Xóa cache.
- **Cache phình đĩa:** chưa auto-evict (YAGNI); Xóa cache thủ công.
- **Đổi model sau lưng 1 config-name không invalidate** (node lưu *tên* config): minor; ghi chú; có thể nhét provider+model resolved vào key sau.
- **WS backward-compat:** parse cả envelope lẫn workflow thuần.

## 10. Unresolved questions

1. Cache có cần auto-evict/giới hạn dung lượng ngay không? (đề xuất: chưa)
2. `code_hash` chỉ hash source class node (không bắt đổi ở helper import như `prompt_merge.py`) — chấp nhận? (đề xuất: chấp nhận, ▶ force bù)
