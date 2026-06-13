---
phase: 1
title: "Backend param mô tả và chèn prompt"
status: completed
priority: P1
effort: "3h"
dependencies: []
---

# Phase 1: Backend param mô tả và chèn prompt

## Overview

Thêm cờ `Param.is_image_label`, ô "Mô tả ảnh" cho `load_image` + `generate_image`, và helper PURE dựng khối tham chiếu + ghép vào prompt node `Sửa ảnh`. Tất cả logic ở phase này thuần (không cần engine/provider/DB) → test thẳng trong `test_nodes.py`.

## Requirements

- Functional:
  - `load_image` + `generate_image` có param `image_label` (text, default `""`), đánh dấu `is_image_label=True`.
  - Helper dựng khối tham chiếu đánh số từ list nhãn; ảnh trống nhãn → `Ảnh N: (không mô tả)`.
  - Node `Sửa ảnh` ghép khối tham chiếu TRƯỚC prompt (sau khi `merge_prompt`).
  - Không nhãn nào → khối rỗng → prompt y như cũ.
- Non-functional: helper pure, không phụ thuộc engine; `Param.to_dict()` xuất `is_image_label` chỉ khi True (tránh phình metadata).

## Architecture

**`base.py`** — `Param` thêm field `is_image_label: bool = False`; `to_dict()` thêm `d["is_image_label"]=True` khi set (để frontend biết param nào là phụ đề). `BaseNode` thêm 2 class attr: `input_labels: dict = {}` (engine set ở Phase 2) + `label_passthrough_from: str | None = None` (tên cổng input mà output ảnh kế thừa nhãn — dùng cho node Biến đổi).

<!-- Updated: Validation Session 1 - passthrough nhãn qua node Biến đổi -->
**`transform.py`** — `ResizeNode`/`FilterNode`/`AdjustNode` thêm class attr `label_passthrough_from = "image"` (chỉ 1 dòng/class). Logic kế thừa nằm ở engine (Phase 2); ở đây chỉ KHAI BÁO. `edit_image`/`generate_image`/`load_image` KHÔNG đặt attr này (generate/load có nhãn riêng qua param; edit output composite không nhãn).

**`nodes/image_label_block.py`** (mới, pure):
```python
REFERENCE_HEADER = "Ảnh đầu vào:"
NO_LABEL = "(không mô tả)"

def build_reference_block(labels: list[str]) -> str:
    """labels theo đúng thứ tự ảnh (index 0 = Ảnh 1). Rỗng/khoảng trắng → '(không mô tả)'.
    Trả "" nếu KHÔNG nhãn nào có nội dung (giữ prompt cũ nguyên vẹn)."""
    if not any((l or "").strip() for l in labels):
        return ""
    lines = [f"- Ảnh {i+1}: {(l or '').strip() or NO_LABEL}" for i, l in enumerate(labels)]
    return REFERENCE_HEADER + "\n" + "\n".join(lines)

def compose_edit_prompt(labels: list[str], prompt: str) -> str:
    """Ghép khối tham chiếu (nếu có) trước prompt người dùng, cách 1 dòng trống."""
    block = build_reference_block(labels)
    return f"{block}\n\n{prompt}" if block else prompt
```

**`edit.py`** — sau `merge_prompt`, gọi `compose_edit_prompt(labels, prompt)` với `labels` lấy từ `self.input_labels` (class attr khai báo ở `base.py` trên; engine set giá trị thật ở Phase 2; mặc định `{}` → list rỗng → prompt cũ). Thứ tự nhãn = `[label("image")] + labels("images") + [label("image2") legacy]`, khớp đúng thứ tự `images = [image, *images, image2]` đang dựng.

> Lưu ý: nhãn THẬT chỉ chảy tới ở Phase 2. Phase 1 chỉ cần `self.input_labels` mặc định rỗng → `edit.py` chạy y như cũ, test backward-compat pass ngay.

## Related Code Files

- Create: `backend/app/nodes/image_label_block.py`
- Modify: `backend/app/nodes/base.py` (Param.is_image_label + BaseNode.input_labels + BaseNode.label_passthrough_from), `backend/app/nodes/inputs.py` (LoadImageNode param), `backend/app/nodes/generate.py` (GenerateImageNode param), `backend/app/nodes/transform.py` (label_passthrough_from="image" cho resize/filter/adjust), `backend/app/nodes/edit.py` (compose prompt)
- Modify (test): `backend/test_nodes.py`

## Implementation Steps (TDD — test trước)

1. **Viết test trước** trong `test_nodes.py` (import `build_reference_block`, `compose_edit_prompt`):
   - `build_reference_block(["cái áo","người mẫu"])` == `"Ảnh đầu vào:\n- Ảnh 1: cái áo\n- Ảnh 2: người mẫu"`.
   - Nhãn rỗng giữa: `build_reference_block(["cái áo","","nền"])` chứa `"- Ảnh 2: (không mô tả)"` và số không nhảy (`Ảnh 3: nền`).
   - Không nhãn: `build_reference_block(["",""])` == `""` và `build_reference_block([])` == `""`.
   - `compose_edit_prompt(["áo","người"], "mặc áo lên người")` bắt đầu bằng `"Ảnh đầu vào:"` và kết thúc bằng `"mặc áo lên người"`.
   - `compose_edit_prompt([], "x")` == `"x"` (backward compat).
   - Metadata: `LoadImageNode.metadata()["params"]` có param `image_label` với `is_image_label True`; tương tự `GenerateImageNode`.
   - Chạy `backend\.venv\Scripts\python.exe test_nodes.py` → các test mới FAIL (đỏ).
2. `base.py`: thêm `is_image_label: bool = False` vào `Param`; `to_dict()` xuất khi True. Thêm `input_labels: dict = {}` + `label_passthrough_from: str | None = None` vào `BaseNode`.
3. Tạo `nodes/image_label_block.py` theo Architecture.
4. `inputs.py`: `LoadImageNode.params` thêm `Param("image_label", "text", "Mô tả ảnh", default="", is_image_label=True)`.
5. `generate.py`: `GenerateImageNode.params` thêm param tương tự (cuối list).
5b. `transform.py`: thêm `label_passthrough_from = "image"` vào `ResizeNode`, `FilterNode`, `AdjustNode` (chỉ khai báo; engine dùng ở Phase 2).
6. `edit.py`: dựng `labels` từ `self.input_labels` đúng thứ tự ảnh; `prompt = compose_edit_prompt(labels, prompt)` ngay trước `provider.edit(...)`.
7. Chạy lại `test_nodes.py` → tất cả PASS (xanh).
8. Compile check: `backend\.venv\Scripts\python.exe -c "import app.nodes"` không lỗi import.

## Success Criteria

- [ ] Test mới trong `test_nodes.py` PASS, các test cũ vẫn PASS.
- [ ] `image_label` xuất hiện trong metadata 2 node với cờ `is_image_label`.
- [ ] `edit.py` với `input_labels` rỗng → prompt KHÔNG đổi (diff hành vi = 0).
- [ ] `import app.nodes` không lỗi.

## Risk Assessment

- **Param mô tả lọt vào `node_key` → đổi mô tả sinh lại ảnh.** Phase 1 CHƯA xử lý cache (mô tả vẫn là param thường); rủi ro token chỉ được khử ở Phase 2. KHÔNG verify cache ở phase này. Mitigation: ghi rõ ràng, Phase 2 là bắt buộc trước khi dùng thật.
- Thứ tự nhãn lệch thứ tự ảnh → AI map sai. Mitigation: dựng `labels` CÙNG biểu thức với `images` trong `edit.py` (cùng thứ tự `image, *images, image2`).
