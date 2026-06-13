---
phase: 1
title: Backend prompt bổ sung (metadata + helper + node AI)
status: completed
priority: P1
effort: 1.5h
dependencies: []
---

# Phase 1: Backend prompt bổ sung (metadata + helper + node AI)

## Overview
Đổi 3 node AI từ "input thắng, param bị bỏ qua" sang "ghép input + param". Thêm metadata để frontend biết param nào bổ sung cho cổng nào, và helper ghép dùng chung.

## Requirements
- Functional: prompt cuối = ghép `inputs.get(port)` + `params.get(param)` (lọc rỗng, dấu nối `", "`). Metadata `Param` xuất `supplement_for` (tên cổng) + `supplement_label` (nhãn khi nối).
- Non-functional: DRY (1 helper), giữ thông báo lỗi cũ khi cả 2 rỗng, không phá test hiện có.

## Architecture
`Param` (dataclass `base.py`) thêm 2 field optional → `to_dict()` xuất khi có. Helper `merge_prompt` ở module riêng `prompt_merge.py` (self-documenting, dùng chung 3 node). 3 node AI gọi helper trong `run()` + khai báo `supplement_for`/`supplement_label` trên param `prompt`.

Hành vi `merge_prompt(connected, supplement)`:
- Cả 2 có → `"<connected>, <supplement>"`.
- Chỉ connected (nối, ô rỗng) → `"<connected>"`.
- Chỉ supplement (không nối, gõ trực tiếp) → `"<supplement>"` (giữ y hành vi cũ).
- Cả 2 rỗng → `""` → node raise lỗi như cũ.

## Related Code Files
- Create: `backend/app/nodes/prompt_merge.py`
- Modify: `backend/app/nodes/base.py` (Param: 2 field + to_dict)
- Modify: `backend/app/nodes/enhance_prompt.py` (port `text` ↔ param `prompt`)
- Modify: `backend/app/nodes/generate.py` (port `prompt` ↔ param `prompt`)
- Modify: `backend/app/nodes/edit.py` (port `prompt` ↔ param `prompt`)

## Implementation Steps
1. `prompt_merge.py`:
   ```python
   def merge_prompt(connected: str | None, supplement: str | None, sep: str = ", ") -> str:
       """Ghép prompt từ cổng nối + prompt bổ sung gõ trong node.
       Lọc phần rỗng; nối vào trước, bổ sung sau."""
       return sep.join(p.strip() for p in (connected, supplement) if p and p.strip())
   ```
2. `base.py` — `Param` dataclass thêm:
   ```python
   supplement_for: str | None = None      # tên cổng input mà param này bổ sung
   supplement_label: str = ""             # nhãn hiển thị khi cổng đã nối
   ```
   Trong `to_dict()`, sau khối options:
   ```python
   if self.supplement_for:
       d["supplement_for"] = self.supplement_for
       d["supplement_label"] = self.supplement_label or self.label
   ```
3. `enhance_prompt.py`:
   - import `from .prompt_merge import merge_prompt`
   - param: `Param("prompt", "textarea", "Prompt gốc", default="", supplement_for="text", supplement_label="Prompt bổ sung")`
   - `run()`: `prompt = merge_prompt(inputs.get("text"), params.get("prompt"))` (bỏ `or`)
4. `generate.py`:
   - import helper; param `prompt` thêm `supplement_for="prompt", supplement_label="Prompt bổ sung"`
   - `run()`: `prompt = merge_prompt(inputs.get("prompt"), params.get("prompt"))`
5. `edit.py`:
   - import helper; param `prompt` thêm `supplement_for="prompt", supplement_label="Prompt bổ sung"`
   - `run()`: `prompt = merge_prompt(inputs.get("prompt"), params.get("prompt"))`
6. Compile check: `backend\.venv\Scripts\python -c "import app.nodes"` (cwd `backend/`) hoặc `... -m pytest backend/test_*.py -q` smoke.

## Success Criteria
- [ ] `merge_prompt` xử lý đúng 4 ca (cả 2 / chỉ nối / chỉ ô / rỗng).
- [ ] `/api/node-types` trả `supplement_for` + `supplement_label` cho param prompt của 3 node.
- [ ] 3 node AI import + chạy không lỗi cú pháp (compile check pass).
- [ ] Thông báo lỗi "cần prompt..." vẫn hoạt động khi cả 2 rỗng.

## Risk Assessment
- Đổi semantics `run()` có thể phá test cũ kỳ vọng "input thắng" → kiểm test_codex.py; merge giữ tương thích vì khi chỉ 1 nguồn kết quả y như cũ.
- `supplement_label` rỗng → fallback `self.label` (an toàn).
