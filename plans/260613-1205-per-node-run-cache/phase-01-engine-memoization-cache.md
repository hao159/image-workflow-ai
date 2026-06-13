---
phase: 1
title: "Engine memoization + cache"
status: completed
priority: P1
effort: "0.5d"
dependencies: []
---

# Phase 1: Engine memoization + cache

## Overview

Thêm tầng cache địa chỉ-nội-dung vào `run_workflow`: mỗi node tính `node_key`, key trùng cache đĩa → dùng lại output, KHÔNG thực thi. Hỗ trợ `target` (chạy tới 1 node = node + ancestors) và `force_ids` (ép chạy lại). Backend-only, offline, TDD.

## Requirements

- Functional:
  - `node_key = sha256(type + resolved_params + parent_output_keys + code_hash)`; `output_key = f"{node_key}:{handle}"`.
  - Cache HIT (key có trên đĩa & node ∉ force_ids) → load outputs+preview, set vào `results`, emit `node_finished(cached=True)`, bỏ qua `instance.run`.
  - Cache MISS → chạy như cũ → `cache.save(key, outputs, preview)` → emit `node_finished(cached=False)`.
  - `target` set → prune order về `ancestors(target) ∪ {target}` (giữ thứ tự topo).
  - `force_ids` → các node trong set luôn chạy thật (kể cả có cache).
  - Đổi param/input/code → key đổi → node + downstream chạy lại; nhánh không đổi cache-hit.
- Non-functional: engine giữ < 200 dòng (tách `engine_cache_key.py`); không phá full-run hiện tại; cache key deterministic (json `sort_keys`).

## Architecture

**Cache key (`engine_cache_key.py`):**
```python
def code_hash(cls) -> str:          # sha256(inspect.getsource(cls))[:16], cache theo cls
def node_key(node_type, params, inputs_out_keys, code) -> str:
    payload = {"type": node_type, "params": params,
               "inputs": inputs_out_keys, "code": code}   # inputs_out_keys: {handle: [parent output_key,...]}
    return sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str))[:32]
def prune_to_ancestors(order, target, edges) -> list[str]:  # BFS ngược theo edges, giữ thứ tự topo gốc
```

**Cache store (`cache.py`):**
```python
CACHE_DIR = config.CACHE_DIR        # ROOT_DIR/cache ; NODES=.../nodes ; BLOBS=.../blobs
@dataclass CachedResult: outputs: dict[str, bytes|str]; preview: str|None
def load(key) -> CachedResult|None  # đọc nodes/{key}.json; image → đọc blobs/{blob}.bin
def save(key, outputs, preview)     # image → blob=sha256(bytes), ghi blobs/{blob}.bin nếu thiếu; text inline; manifest json; rồi _evict_if_needed()
def clear()                         # rmtree CACHE_DIR rồi tạo lại nodes/ blobs/
def _evict_if_needed(max_bytes=config.CACHE_MAX_BYTES):  # tổng size blobs/*.bin > max → xóa file cũ nhất theo st_mtime tới khi <= max; touch mtime blob khi load (LRU thô)
```
**Auto-trim (Validation Q3):** `save()` gọi `_evict_if_needed()` sau khi ghi. Ngưỡng `CACHE_MAX_BYTES` mặc định 500MB (env override). Evict theo `mtime` blob (cũ nhất trước). `load()` `os.utime` blob được đọc → blob đang dùng "trẻ lại" (xấp xỉ LRU). KHÔNG xóa manifest trỏ blob vừa xóa ngay (manifest mồ côi → `load` thấy blob thiếu thì trả `None` = cache miss, an toàn).
Manifest: `{"outputs": {handle: {"dtype":"image","blob":sha} | {"dtype":"text","value":str}}, "preview": base64|null}`.
Tests override đường dẫn bằng gán `cache.CACHE_DIR = <tmp>` (đọc động trong từng hàm, KHÔNG bind hằng lúc import).

**Engine (`engine.py` sửa `run_workflow`):**
```
run_workflow(workflow, emit, *, target=None, force_ids=frozenset()):
    emit run_started; order = _topo_order(...)            # giữ nguyên
    if target: order = prune_to_ancestors(order, target, workflow.edges)
    out_keys: dict[(node_id,handle), str] = {}
    for node_id in order:
        ... resolve cls, gather inputs (giữ nguyên) ...
        # incoming_out_keys: theo từng target_handle, list out_keys[(src,src_handle)] đã có
        key = node_key(node_def.type, params, incoming_out_keys, code_hash(cls))
        emit node_started
        cached = None if node_id in force_ids else cache.load(key)
        if cached:
            for h, v in cached.outputs.items():
                results[(node_id,h)] = v; out_keys[(node_id,h)] = f"{key}:{h}"
            emit node_finished(preview=cached.preview, outputs=_meta(cached.outputs), cached=True); continue
        outputs = await to_thread(instance.run, ...)        # giữ nguyên + try/except cũ
        preview, _ = _build_preview_and_meta(outputs)       # tách helper từ vòng lặp hiện tại
        for h, v in outputs.items(): results[(node_id,h)] = v; out_keys[(node_id,h)] = f"{key}:{h}"
        cache.save(key, outputs, preview)
        emit node_finished(preview=preview, outputs=_meta(outputs), cached=False)
    emit run_finished
```
`_meta(outputs)` = vòng lặp build `out_meta` hiện tại (image→{dtype,size}, text→{dtype,value}) tách thành helper để DRY giữa hit/miss.

## Related Code Files

- Create: `backend/app/cache.py`
- Create: `backend/app/engine_cache_key.py`
- Create: `backend/test_engine_cache.py`
- Modify: `backend/app/engine.py` (thêm target/force, hit/miss; tách `_meta`)
- Modify: `backend/app/config.py` (thêm `CACHE_DIR = ROOT_DIR / "cache"` + mkdir nodes/blobs; `CACHE_MAX_BYTES = int(os.getenv("CACHE_MAX_BYTES", 500*1024*1024))`)
- Modify: `.gitignore` (thêm `cache/`)
- Read for context: `backend/app/models.py` (RunEvent — phase 2 thêm `cached`; phase 1 có thể bỏ qua field, emit không kèm), `backend/app/nodes/base.py`

> Lưu ý liên-phase: `RunEvent.cached` được THÊM ở Phase 2. Phase 1 có thể emit `cached` qua kwargs bị pydantic loại (an toàn) HOẶC làm Phase 2 model trước. Để TDD Phase 1 độc lập, test Phase 1 KHÔNG assert field `cached` trên `RunEvent` mà assert qua **call-count node** (xem dưới). Engine truyền `cached=...` chỉ khi field tồn tại.

## Implementation Steps

1. **Test trước** (`test_engine_cache.py`, offline, có `__main__` runner như `test_nodes.py`):
   - Định nghĩa `_CountNode(BaseNode)` trong test: `type_name="_count"`, 1 input text `in` (required=False), 1 output text `out`, param `tag`; `run` tăng `_CountNode.calls[tag]` rồi trả `{"out": tag}`. Đăng ký tay vào `NODE_REGISTRY` (cleanup cuối).
   - Set `cache.CACHE_DIR` = thư mục tạm; `cache.clear()` đầu mỗi test.
   - Helper `run(wf, **kw)`: `asyncio.run(run_workflow(wf, collect_emit, **kw))` → trả list event.
   - Cases:
     - `test_hit_second_run`: [a→b]; run1 → calls a=1,b=1; run2 (same) → calls không tăng; (nếu có field) event b cached=True.
     - `test_param_change_reruns_self_and_downstream`: đổi param b → run2: a giữ, b tăng.
     - `test_upstream_change_invalidates_downstream`: đổi param a → run2: a+b đều tăng.
     - `test_unrelated_branch_cached`: [a→c],[b→c?] hoặc 2 nhánh rời; đổi 1 leaf → chỉ nhánh đó tăng.
     - `test_target_prune`: [a→b→c]; run(target=b) → c.calls==0, a&b chạy.
     - `test_force_reruns_target_only`: cache [a→b]; run(target=b, force_ids={b}) → b tăng, a giữ.
     - `test_disk_persistence`: sau run, `cache.load(key_b) is not None`.
     - `test_clear`: sau `cache.clear()`, run lại → calls tăng.
     - `test_evict_over_limit`: gán `cache.CACHE_MAX_BYTES` nhỏ (vd 1KB), `save` nhiều blob ảnh > ngưỡng → blob cũ nhất bị xóa, tổng size <= ngưỡng; `load` key trỏ blob đã xóa → trả `None` (miss, không crash).
2. `config.py`: thêm `CACHE_DIR` + `CACHE_MAX_BYTES`, đưa `CACHE_DIR/"nodes"`, `CACHE_DIR/"blobs"` vào vòng mkdir.
3. `.gitignore`: thêm dòng `cache/`.
4. Viết `engine_cache_key.py` (`code_hash`, `node_key`, `prune_to_ancestors`).
5. Viết `cache.py` (`load`/`save`/`clear`, `CachedResult`, `_evict_if_needed`). `load` trả `None` nếu blob tham chiếu đã bị evict (an toàn, = miss).
6. Sửa `engine.py`: tách `_meta`/preview helper, chèn key + hit/miss + target/force. Giữ try/except node cũ.
7. Chạy `backend\.venv\Scripts\python.exe test_engine_cache.py` → all pass. Chạy lại `test_nodes.py` (không vỡ).

## Success Criteria

- [x] `test_engine_cache.py`: 9/9 pass (call-count chứng minh cache-hit không thực thi lại; có test evict).
- [x] Auto-trim: tổng `blobs/*.bin` không vượt `CACHE_MAX_BYTES`; blob cũ nhất bị xóa trước; `load` blob đã evict → miss (không crash).
- [x] Full-run cũ không đổi hành vi: `test_nodes.py` pass; engine vẫn emit đủ run_started/node_*/run_finished.
- [x] `engine.py` < 200 dòng; logic key/prune nằm ở `engine_cache_key.py`.
- [x] Cache ghi ra `cache/nodes/*.json` + `cache/blobs/*.bin`; `cache.clear()` xóa sạch.
- [x] `target` chỉ chạy ancestors+target; `force_ids` ép chạy lại.

## Risk Assessment

- **`cached` field chưa có ở Phase 1** → engine chỉ truyền khi field tồn tại (getattr/try) hoặc Phase 1 thêm luôn field vào RunEvent (đơn giản hơn — cân nhắc gộp). Mitigation: test Phase 1 dựa call-count, không phụ thuộc field.
- **Hash params có giá trị non-JSON** (params chỉ là text/number/select/checkbox/file_id → JSON-safe); dùng `default=str` phòng hờ.
- **Ảnh nhét đầy đĩa**: dedupe theo content-sha + auto-trim theo mtime khi vượt `CACHE_MAX_BYTES` (mặc định 500MB) — đã implement trong `save()` (Validation Q3). Manifest mồ côi (blob bị evict) → `load` trả None = miss an toàn.
- **`inspect.getsource` lỗi với class định nghĩa động trong test**: dùng `try/except OSError → code=""`.
