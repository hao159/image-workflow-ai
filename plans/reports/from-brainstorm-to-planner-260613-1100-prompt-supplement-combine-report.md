# Brainstorm → Planner: "Prompt bổ sung" + Đại tu node Ghép prompt

- Date: 2026-06-13 11:00 (Asia/Saigon)
- Status: Đã duyệt thiết kế (user approved 2026-06-13)
- Handoff: → `/ck:plan`

## Problem statement

Node-based image tool (FastAPI + React Flow). 3 node AI (`enhance_prompt`, `generate_image`, `edit_image`) đều dùng mẫu `inputs.get(x) or params.get(y)` → khi cổng prompt **đã nối dây**, ô prompt soạn-tay trong node **bị bỏ qua âm thầm** (gõ vô vô tác dụng). Node `Prompt` nối vô Enhance trông trùng lặp / "đơn độc". Đồng thời node `Ghép prompt` (`combine_text`) chỉ ghép được 2 input cố định (`a`/`b`) + param "ký tự nối".

## Requirements (chốt)

1. **Expected output**:
   - A. Khi cổng text đã nối, ô param prompt trùng → relabel "Prompt bổ sung" + cổng có badge "✓ đã nối"; backend GHÉP `nối_vào + ", " + bổ_sung`.
   - B. Node `Ghép prompt`: 1 cổng `texts` nhận nhiều dây, bỏ param separator, mặc định nối bằng `\n`.
2. **Acceptance criteria**:
   - Nối Prompt→Enhance + gõ thêm vào ô → prompt cuối = `<nối>, <bổ sung>` (verify qua test + chạy thật).
   - Chỉ nối, ô rỗng → prompt = `<nối>`. Chỉ gõ, không nối → prompt = ô (giữ hành vi cũ). Cả 2 rỗng → lỗi như cũ.
   - Ghép prompt nối 3+ dây → output = các prompt cách nhau xuống dòng, đúng thứ tự nối.
   - Workflow cũ (combine_text dùng `a`/`b`) vẫn chạy (shim).
3. **Scope boundary (OUT)**: không mirror read-only nội dung node nguồn (Q2 obviated bởi lựa chọn "bổ sung"); không áp cho cổng ảnh; không đổi engine.
4. **Constraints**: full-stack (backend + frontend), có backward-compat cho workflow đã lưu; UI tự sinh từ metadata — đổi metadata phải tổng quát; `@xyflow/react ^12.4.0`; tuân YAGNI/KISS/DRY, file < 200 LOC.
5. **Touchpoints (verified)**:
   - `backend/app/nodes/base.py` — thêm field `supplement_for`, `supplement_label` cho `Param` + export trong `to_dict()`.
   - `backend/app/nodes/enhance_prompt.py:37`, `generate.py:25`, `edit.py:30` — đổi sang helper ghép.
   - `backend/app/nodes/inputs.py:37-49` — đại tu `CombineTextNode`.
   - Helper ghép prompt dùng chung (mới, vd `nodes/_text.py` hoặc hàm trong `base.py`).
   - `frontend/src/components/WorkflowNode.jsx` — `useNodeConnections` → badge + relabel.
   - `frontend/src/styles/workflow-node.css` — style badge.
   - Tests: `backend/test_*`.

## Approaches đã cân nhắc (Tính năng A)

| # | Cách | Pros | Cons | Quyết định |
|---|------|------|------|-----------|
| 1 | Ẩn ô, mount nội dung nối vào (read-only, kiểu ComfyUI) | Một-nguồn-sự-thật, gọn | Mất khả năng thêm; cần mirror live/after-run (phức tạp) | Loại |
| 2 | **Đổi ô → "Prompt bổ sung", backend ghép** | Vẫn thêm được; backend đơn giản; bỏ được "input thắng âm thầm" | Đổi semantics run(); cần link param↔port | **CHỌN** |
| 3 | Kết hợp preview read-only + ô bổ sung riêng | Giàu nhất | Node cao, phức tạp nhất | Loại |

User chọn #2 (Q1). Phạm vi: mọi cổng text có param trùng (Q3).

## Final solution

### A. Mẫu "Prompt bổ sung"
- `Param` thêm `supplement_for` (tên port) + `supplement_label`.
- Helper dùng chung:
  ```python
  def merge_prompt(connected, supplement, sep=", "):
      return sep.join(p.strip() for p in (connected, supplement) if p and p.strip())
  ```
- `enhance_prompt`: port `text` ↔ param `prompt` (label nối: "Prompt bổ sung"); giữ nguyên param `style` ("Hướng dẫn thêm").
- `generate_image`, `edit_image`: port `prompt` ↔ param `prompt`.
- Frontend: `useNodeConnections({ id, handleType: 'target' })` → set handle đang nối (`in-<port>`). Cổng nối → badge "✓ đã nối"; param có `supplement_for` ứng cổng đang nối → label = `supplement_label`, ô vẫn soạn được.

### B. Đại tu Ghép prompt
- `inputs = [Port("texts", "text", "Các prompt", required=False, multiple=True)]`, bỏ param `separator`.
- `run()`: `"\n".join(p for p in (inputs.get("texts") or []) if p and p.strip())`.
- Shim tương thích: gom thêm `inputs.get("a")`, `inputs.get("b")` nếu workflow cũ còn nối vào.

## Validation
- Unit test: `merge_prompt` (4 ca: cả 2 / chỉ nối / chỉ ô / rỗng); combine nhiều input + thứ tự + shim a/b.
- Manual: chạy thật 1 workflow Prompt→Enhance→Tạo ảnh; mở 1 workflow combine_text đã lưu.

## Risks
- Đổi ports `combine_text` phá edge cũ → mitigated bằng shim; test bằng workflow đã lưu.
- `useNodeConnections` phải trong node context (đã đúng).
- Dấu nối prompt bổ sung `", "` (theo preview user duyệt) khác `\n` của Ghép prompt — chủ ý, không đồng bộ.

## Next steps
- `/ck:plan` chia phase: (1) base.py metadata + helper, (2) 3 node AI dùng helper, (3) combine_text + shim, (4) frontend badge/relabel + CSS, (5) tests.

## Open questions
- Không có. (Dấu nối ", " đã được duyệt; có thể đổi sang `\n` sau nếu muốn đồng bộ.)
