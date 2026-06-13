---
phase: 2
title: "Engine nhãn theo ảnh và cache"
status: completed
priority: P1
effort: "4h"
dependencies: [1]
---

# Phase 2: Engine nhãn theo ảnh và cache

## Overview

Cho nhãn (mô tả ảnh) **đi theo ảnh** qua engine xuống node `Sửa ảnh`, và xử lý cache đúng: đổi mô tả KHÔNG sinh lại ảnh AI (node giữ nhãn cache-hit) nhưng LÀM node `Sửa ảnh` phía dưới chạy lại (prompt đổi). Đây là phase rủi ro nhất → test kỹ.

## Requirements

- Functional:
  - Engine set `instance.input_labels = {handle: [nhãn theo thứ tự cạnh]}` trước khi chạy node, lấy từ nhãn output của node cha (chỉ cho output ảnh).
  - Nhãn (param) KHÔNG vào `node_key` của node giữ nó → đổi nhãn không đổi `nk` → không sinh lại ảnh AI.
  - Nhãn nối vào `output_key` của ảnh → node con thấy `in_key` đổi → chạy lại.
  - Node con (Sửa ảnh) nhận nhãn đúng thứ tự ảnh, kể cả khi node nguồn cache-hit.
  - **Passthrough:** node `label_passthrough_from` (resize/filter/adjust) kế thừa nhãn từ ảnh vào → ảnh ra giữ nhãn; node không khai báo (edit_image) → output không nhãn.
- Non-functional: không đổi chữ ký `BaseNode.run(inputs, params)`; không hash lại bytes ảnh; logic tách helper PURE để test không cần chạy server.

## Architecture

**`engine_cache_key.py`** — thêm 3 helper pure:
```python
def label_params(cls) -> set[str]:
    """Tên các param đánh dấu is_image_label trên class node."""
    return {p.name for p in getattr(cls, "params", []) if getattr(p, "is_image_label", False)}

def key_params_excluding_labels(params: dict, label_names: set[str]) -> dict:
    """params dùng để tính node_key — đã bỏ param nhãn (đổi nhãn ≠ đổi key)."""
    return {k: v for k, v in params.items() if k not in label_names}

def label_out_key(base_out_key: str, label: str) -> str:
    """out_key của ảnh, nối hash nhãn → downstream chạy lại khi nhãn đổi."""
    if not (label or "").strip():
        return base_out_key
    h = hashlib.sha256(label.strip().encode("utf-8")).hexdigest()[:8]
    return f"{base_out_key}#{h}"
```
`node_key()` GIỮ NGUYÊN chữ ký — engine truyền `key_params_excluding_labels(...)` vào.

**`engine.py`** — trong vòng `for node_id in order` (thêm `labels: dict[(id,handle)]->str`):
1. **Gom nhãn input** SONG SONG với gom value: `gathered_labels[target_handle].append(labels.get(src, ""))` (cùng thứ tự cạnh với `gathered[target_handle]`). Trước `instance.run`: `instance.input_labels = dict(gathered_labels)`.
2. **Tính nhãn OUTPUT của node** (`out_label`):
   - `own = next((str(params[n]) for n in label_params(cls) if (params.get(n) or "").strip()), "")`.
   - Nếu `own` → `out_label = own` (node nguồn: load_image/generate).
   - Elif `cls.label_passthrough_from` và cổng đó có nhãn vào → `out_label = gathered_labels[cls.label_passthrough_from][-1]` (node Biến đổi kế thừa nhãn ảnh vào; lấy `[-1]` khớp `inputs[port]=values[-1]`).
   - Else `out_label = ""` (vd edit_image → composite, không nhãn).
3. **node_key BỎ param nhãn:** `nk = node_key(type, key_params_excluding_labels(params, label_params(cls)), in_keys, code)`. (Node Biến đổi: `label_params` rỗng → không bỏ gì; nhãn kế thừa vẫn lan qua `in_keys`.)
4. **out_key cho output ẢNH:** `out_keys[(id,handle)] = label_out_key(f"{nk}:{handle}", out_label)`; output text giữ `f"{nk}:{handle}"`.
5. **Ghi labels map:** `labels[(id,handle)] = out_label` cho output ảnh — ở CẢ nhánh cache-hit lẫn chạy thật (đọc từ `params`/`gathered_labels`, luôn có dù không thực thi).

> **Bất biến cache:** đổi nhãn ở node NGUỒN (param) → `nk` node nguồn KHÔNG đổi (param nhãn bị loại) → cache-hit, KHÔNG gọi provider (không tốn token); nhưng `out_key` đổi (kèm hash nhãn) → node con thấy `in_key` đổi → chạy lại với prompt mới.
>
> **Passthrough:** nhãn kế thừa lan qua `in_keys` (out_key nguồn đã kèm hash) → node Biến đổi `nk` ĐỔI → chạy lại (rẻ, không token) → out_key kèm nhãn kế thừa → edit phía dưới chạy lại + nhận đúng nhãn text qua `labels`. Chấp nhận node Biến đổi tính lại khi chỉ đổi nhãn (chi phí ~ms, không API).

## Related Code Files

- Modify: `backend/app/engine_cache_key.py` (3 helper; `hashlib` đã import sẵn ở dòng 8), `backend/app/engine.py` (gom nhãn + set input_labels, tính out_label own/passthrough, nk loại param nhãn, out_key kèm nhãn, labels map cả nhánh cache-hit)
- Đọc (không sửa): `backend/app/nodes/transform.py` (`label_passthrough_from` — khai báo ở Phase 1)
- Create (test): `backend/test_engine_labels.py`

## Implementation Steps (TDD — test trước)

1. **Viết test trước** `backend/test_engine_labels.py` (có `__main__` runner như test_codex.py; dùng `asyncio.run`):
   - **Pure helper:** `key_params_excluding_labels({"prompt":"x","image_label":"áo"}, {"image_label"})` == `{"prompt":"x"}`. `label_out_key("k:image","áo") != label_out_key("k:image","người")`; `label_out_key("k:image","")` == `"k:image"`. `label_params(GenerateImageNode)` == `{"image_label"}`; `label_params(ResizeNode)` == `set()`.
   - **Integration** — dùng 1 stub provider tự định nghĩa trong test (object có `generate(prompt, **kw)→bytes PNG nhỏ` + `edit(images, prompt, **kw)→bytes`, ghi lại `prompt` nhận được + đếm số lần gọi). **Monkeypatch đúng tên đã bind vào module node:** `app.nodes.generate.resolve_model_config` và `app.nodes.edit.resolve_model_config` → trả `(stub, "")` (KHÔNG patch `app.providers`). Khôi phục trong `finally`.
     - **Đánh số + thứ tự:** workflow `gen1(image_label="cái áo") + gen2(image_label="người mẫu") → edit(image=gen1, images=[gen2])`. Chạy `run_workflow`. Assert prompt mà stub.edit nhận CHỨA `"Ảnh 1: cái áo"` và `"Ảnh 2: người mẫu"`.
     - **Cache (không tốn token):** chạy lần 1 (lưu cache); đổi `gen1.image_label` → "áo khoác"; chạy lần 2. Assert: `generate` call-count cho gen1 KHÔNG tăng (cache-hit); `edit` call-count TĂNG (chạy lại); prompt mới chứa `"áo khoác"`.
     - **Passthrough qua node Biến đổi:** workflow `gen1(image_label="cái áo") → resize → edit(image=resize_out)`. Assert prompt edit nhận CHỨA `"Ảnh 1: cái áo"` (nhãn sống sót qua Resize). `resize` dùng PIL thật trên bytes stub — OK.
     - **Backward compat:** workflow không nhãn → prompt edit KHÔNG có dòng `"Ảnh đầu vào:"`.
   - Chạy → FAIL.
2. `engine_cache_key.py`: thêm 3 helper (`label_params`, `key_params_excluding_labels`, `label_out_key`); `hashlib` đã import sẵn (dòng 8).
3. `engine.py`: sửa theo Architecture (bước 1–5). Cẩn thận: `labels` map điền ở CẢ nhánh cache-hit (sau `cache.load`) lẫn nhánh chạy thật. Nhãn output tính từ `params` (own) hoặc `gathered_labels` (passthrough) — luôn sẵn dù node không thực thi.
4. Chạy `backend\.venv\Scripts\python.exe test_engine_labels.py` → PASS; chạy lại `test_nodes.py` (Phase 1) vẫn PASS.
5. Smoke e2e thủ công (tùy chọn, cần backend chạy): 2 node Tải ảnh + Sửa ảnh với fake config → kiểm prompt log.

## Success Criteria

- [ ] `test_engine_labels.py` PASS (helper + đánh số/thứ tự + cache + passthrough + backward compat).
- [ ] Đổi mô tả node `Tạo ảnh` → KHÔNG gọi lại provider.generate (cache-hit) nhưng node `Sửa ảnh` chạy lại.
- [ ] Node `Sửa ảnh` nhận nhãn đúng thứ tự (Ảnh 1 = ảnh gốc, Ảnh 2.. = cổng images theo thứ tự nối).
- [ ] Nhãn sống sót qua node Biến đổi (load/gen → resize → edit vẫn thấy nhãn).
- [ ] Workflow không nhãn → prompt edit không đổi so với trước.
- [ ] `test_nodes.py` (Phase 1) vẫn PASS.

## Risk Assessment

- **Nhãn không điền ở nhánh cache-hit** → node con chạy lại nhưng `input_labels` rỗng → mất mô tả. Mitigation: test cache ở bước 1 bắt đúng case này (đổi nhãn gen1 vốn cache-hit).
- **`label_out_key` đổi nhưng `nk` cache-hit ghi đè out_key cũ** — kiểm: out_key tính lại mỗi run từ `nk` + `out_label` hiện tại, không đọc từ cache → luôn đúng.
- **Thứ tự cạnh không ổn định giữa 2 lần chạy** → đánh số nhảy. Engine gom theo thứ tự `workflow.edges` (đầu vào cố định theo file) → ổn định; ghi chú nếu sau này sort lại edges.
- **Stub provider / `resolve_model_config` trong test** cần monkeypatch sạch (teardown) để không rò sang test khác. Mitigation: patch trong từng test, khôi phục ở `finally`.
