---
phase: 2
title: Backend đại tu Ghép prompt (multi-input + shim)
status: completed
priority: P2
effort: 0.5h
dependencies: []
---

# Phase 2: Backend đại tu Ghép prompt (multi-input + shim)

## Overview
`combine_text` từ 2 cổng cố định `a`/`b` + param separator → 1 cổng `texts` nhận nhiều dây, nối bằng xuống dòng, bỏ separator. Tương thích workflow cũ.

## Requirements
- Functional: cổng `texts` (multiple) nhận N prompt theo thứ tự nối; output = các phần cách nhau `\n`; lọc phần rỗng. Bỏ param `separator`.
- Non-functional: workflow đã lưu (edges nối vào `a`/`b`) vẫn chạy không lỗi.

## Architecture
Engine (`engine.py:80-84`) tự gom cổng `multiple=True` thành list theo thứ tự nối → không đổi engine. Cổng cũ `a`/`b` (single) vẫn vào `inputs` dict nếu workflow cũ còn nối → shim gom thêm. Param `separator` cũ còn trong workflow lưu sẽ bị `run()` bỏ qua (vô hại).

## Related Code Files
- Modify: `backend/app/nodes/inputs.py` (`CombineTextNode`)

## Implementation Steps
1. Thay `CombineTextNode`:
   ```python
   @register_node
   class CombineTextNode(BaseNode):
       type_name = "combine_text"
       title = "Ghép prompt"
       category = "Đầu vào"
       description = "Ghép nhiều đoạn text thành một (mỗi đoạn một dòng). Nối bao nhiêu dây cũng được."
       inputs = [Port("texts", "text", "Các prompt", required=False, multiple=True)]
       outputs = [Port("text", "text", "Text")]
       params = []

       def run(self, inputs, params):
           parts = list(inputs.get("texts") or [])
           # Tương thích workflow lưu trước khi gộp cổng: cổng cũ "a"/"b"
           for legacy in ("a", "b"):
               if inputs.get(legacy):
                   parts.append(inputs[legacy])
           return {"text": "\n".join(p.strip() for p in parts if p and p.strip())}
   ```
2. Compile check như Phase 1.

## Success Criteria
- [ ] Nối 3 dây vào `texts` → output = 3 dòng đúng thứ tự nối.
- [ ] Phần rỗng bị lọc; không có dây → output `""`.
- [ ] Workflow cũ (edges `a`/`b` + param separator) load + chạy không lỗi, ghép đúng nội dung.
- [ ] `/api/node-types` cho `combine_text` không còn param `separator`, cổng = 1 (`texts`, multiple).

## Risk Assessment
- Output đổi dấu nối `", "` → `\n` cho workflow cũ: chủ ý (user yêu cầu mặc định xuống dòng). Ghi nhận, không cản.
- Nếu frontend cache metadata cũ (port a/b) → hiện 2 cổng cho tới khi `refreshNodeTypes`; reload trang là hết. Không cản (cổng mới vẫn nối được).
