---
phase: 1
title: 'Prompt override đè (inline, không module)'
status: completed
priority: P1
effort: 1-2h
dependencies: []
---

# Phase 1: Prompt override đè (inline)

## Overview

Cho **override đè** chỉ thị identity cứng (`IMAGE_REF_INSTRUCTION`) trong khối tham chiếu node Sửa ảnh, **giữ auto-default**. Làm **inline** — thêm tham số `instruction_override` vào `compose_edit_prompt` + 1 param trên node. KHÔNG tạo module `adaptive_prompt.py` (YAGNI — chỉ là `override or default`), KHÔNG đụng `enhance_prompt`.

> **Red-team đã sửa:** bỏ module + test riêng (over-abstraction over 2 hằng + 1 ternary); bỏ "nền cho critic Phase 2" (critic tự dựng chỉ thị riêng theo goal, không tái dùng cái này); giữ logic TRONG class node để `code_hash` (hash source class — `engine_cache_key.py:17-33`) vẫn vô hiệu cache đúng khi đổi.

## Requirements
- Functional: node `Sửa ảnh` có param **"Chỉ thị hệ thống (tùy chọn)"** (textarea, default rỗng). Có giá trị → **thay** chỉ thị identity mặc định trong khối tham chiếu; trống → giữ mặc định khi có nhãn (như hiện tại).
- Non-functional: pure function, test không cần server. **Backward-compat tuyệt đối**: override rỗng/None → output Y HỆT hiện tại.

## Architecture
- `nodes/image_label_block.py` (file thật ở `backend/app/nodes/`, KHÔNG ở app root):
  - `compose_edit_prompt(labels, prompt, instruction_override=None)`: block dựng như cũ; `instr = (instruction_override or "").strip() or IMAGE_REF_INSTRUCTION`; có block → `f"{block}\n{instr}\n\n{prompt}"`. `instruction_override` None/rỗng + có nhãn → output cũ y nguyên. Không nhãn → prompt nguyên.
  - Giữ `IMAGE_REF_INSTRUCTION` tại chỗ (chỉ `test_engine_labels.py:147` tham chiếu — verified).
- `nodes/edit.py`: thêm `Param("instruction", "textarea", "Chỉ thị hệ thống (tùy chọn)", default="")`; `compose_edit_prompt(labels, prompt, instruction_override=params.get("instruction"))`.
- **Cache key**: `instruction` là param thường (vào node_key). Để tránh invalidate diện rộng workflow cũ: param rỗng đã có sẵn trong payload (giá trị "") → key đổi 1 lần khi thêm param. **Quyết:** chấp nhận re-run 1 lần (đơn giản, KISS) — KHÔNG thêm cơ chế loại param rỗng (over-engineer).

## Related Code Files
- Modify: `backend/app/nodes/image_label_block.py` (thêm tham số `instruction_override`)
- Modify: `backend/app/nodes/edit.py` (param + truyền override)
- Modify: `backend/test_nodes.py` (test override)
- **KHÔNG tạo** `adaptive_prompt.py`; **KHÔNG sửa** `enhance_prompt.py`.

## Implementation Steps (TDD)
1. **Test trước** (`test_nodes.py`, pure):
   - `compose_edit_prompt(["áo","người"], "ghép")` == output hiện tại (khối + `IMAGE_REF_INSTRUCTION` + prompt) — **khóa backward compat**.
   - `compose_edit_prompt([...], "ghép", instruction_override="Chỉ đổi nền")` → chứa "Chỉ đổi nền", KHÔNG chứa câu "không tráo mặt".
   - `instruction_override="  "` → dùng default. `[]`/nhãn rỗng → prompt nguyên.
   - Đỏ.
2. Sửa `image_label_block.py` thêm tham số.
3. Sửa `edit.py` thêm param + truyền.
4. Test node-level (stub provider): assert prompt gửi provider có/không có chỉ thị theo override.
5. Xanh + regression: `test_nodes.py`, `test_engine_labels.py`, `test_codex.py`, `test_engine_cache.py`. `import app.nodes` OK.

## Success Criteria
- [ ] Backward-compat test (override rỗng) khẳng định output không đổi.
- [ ] Node Sửa ảnh có ô override; nhập → đè; trống → mặc định.
- [ ] KHÔNG có file `adaptive_prompt.py`; `enhance_prompt.py` không đổi.
- [ ] Test cũ xanh; `import app.nodes` OK.

## Risk Assessment
- **Invalidate cache 1 lần** do thêm param → chấp nhận (chỉ edit node, re-run 1 lần).
- **Vỡ `test_engine_labels.py`** nếu lỡ đổi `IMAGE_REF_INSTRUCTION` → giữ hằng tại chỗ.
