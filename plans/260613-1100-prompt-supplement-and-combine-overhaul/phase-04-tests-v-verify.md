---
phase: 4
title: Tests và verify
status: completed
priority: P2
effort: 1h
dependencies:
  - 1
  - 2
  - 3
---

# Phase 4: Tests và verify

## Overview
Unit test logic ghép prompt + combine_text, compile check 2 đầu, và verify chạy thật end-to-end.

## Requirements
- Functional: test phủ `merge_prompt` (4 ca) + `CombineTextNode` (multi-input, thứ tự, shim a/b, lọc rỗng).
- Non-functional: không mock giả để qua build; test chạy không cần token (logic thuần, không gọi provider).

## Architecture
Tạo `backend/test_nodes.py` — test thuần Python, không cần backend chạy / không cần API token (khác `test_e2e.py`). Test gọi trực tiếp `merge_prompt` và `CombineTextNode().run()`. Node AI (`enhance/generate/edit`) gọi provider → không unit test ở đây; phủ qua `merge_prompt` + verify thủ công.

## Related Code Files
- Create: `backend/test_nodes.py`

## Implementation Steps
1. `test_nodes.py`:
   ```python
   from app.nodes.prompt_merge import merge_prompt
   from app.nodes.inputs import CombineTextNode

   def test_merge_both():      assert merge_prompt("mèo", "sơn dầu") == "mèo, sơn dầu"
   def test_merge_connected():  assert merge_prompt("mèo", "") == "mèo"
   def test_merge_supplement(): assert merge_prompt(None, "mèo") == "mèo"
   def test_merge_empty():      assert merge_prompt("", None) == ""

   def test_combine_multi_order():
       out = CombineTextNode().run({"texts": ["a", "b", "c"]}, {})
       assert out["text"] == "a\nb\nc"
   def test_combine_filters_empty():
       out = CombineTextNode().run({"texts": ["a", "  ", "", "b"]}, {})
       assert out["text"] == "a\nb"
   def test_combine_legacy_ab():
       out = CombineTextNode().run({"a": "x", "b": "y"}, {})
       assert out["text"] == "x\ny"
   def test_combine_empty():
       assert CombineTextNode().run({}, {})["text"] == ""
   ```
2. Chạy: `cd backend && .venv\Scripts\python -m pytest test_nodes.py -q`. Sửa tới khi pass (không bỏ qua test fail).
3. Smoke test bộ test hiện có: `.venv\Scripts\python -m pytest -q` (đảm bảo Phase 1 không phá `test_codex.py`).
4. Frontend build: `npm run build --prefix frontend` → 0 lỗi.
5. Verify thủ công (theo README "Chạy"):
   - Backend `backend\.venv\Scripts\python backend\run_server.py --reload`; frontend `npm run dev --prefix frontend`.
   - Dựng flow Prompt("mèo phi hành gia") → Enhance (gõ thêm "phong cách tranh sơn dầu") → Tạo ảnh. Bấm ▶ Chạy.
   - Xác nhận: cổng Enhance hiện "✓ đã nối"; ô đổi "Prompt bổ sung"; prompt đưa vào AI = "mèo phi hành gia, phong cách tranh sơn dầu" (soi `logs/codex/*.log` nếu cần với `CODEX_DEBUG=1`).
   - Nếu có workflow `combine_text` cũ trong `workflows/` → 📂 Mở → Chạy → không lỗi.

## Success Criteria
- [ ] `pytest test_nodes.py` pass 8/8.
- [ ] `pytest -q` (toàn bộ) pass — `test_codex.py` không hồi quy.
- [ ] `npm run build` pass.
- [ ] Verify thủ công: badge + relabel + prompt ghép đúng; workflow cũ chạy được.

## Risk Assessment
- Test cũ phụ thuộc "input thắng" có thể đỏ → đọc kỹ, sửa kỳ vọng theo hành vi ghép mới (không nới lỏng test để qua).
- Verify thủ công cần provider thật (codex/gemini) — nếu không có quota, dừng ở kiểm prompt ghép qua log thay vì ép ra ảnh.
