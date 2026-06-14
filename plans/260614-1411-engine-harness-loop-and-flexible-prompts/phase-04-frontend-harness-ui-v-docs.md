---
phase: 4
title: '[HOÃN — milestone riêng] Node trích vùng tổng quát'
status: completed
priority: P3
effort: 4-6h
dependencies: []
---

# Phase 4: [HOÃN sang milestone riêng] Node trích vùng tổng quát

> **Đã hoàn thành (session 2026-06-14, sau harness):** ban đầu hoãn (red-team Scope F8) vì không block harness; sau khi harness ship, user "tiếp" → đã implement. Node `extract_region` + `detect_region` (gemini/base/fake) + `crop_region` (PIL), test_extract_region.py 8/8, regression xanh. Áp đúng C2 (unpack tuple), C9 (gemini vision→JSON), padding=0.0 hợp lệ (không dùng `or`).

## Overview (cho milestone sau)

Node **"Trích vùng (AI)"**: input ảnh + mô tả đối tượng (text) → vision trả bbox 0..1 → crop PIL (giữ pixel gốc). Tổng quát (mặt/bò/chó/áo). Pre-process độ tin cậy cho ghép ảnh.

## Ghi chú kế thừa từ red-team (áp dụng khi build sau)
- **C2 — `resolve_model_config` trả TUPLE**: `provider, model = resolve_model_config(params["provider"])` rồi mới `provider.detect_region(...)`. KHÔNG bind cả tuple.
- **C9 — Gemini image-in→JSON-out**: `generate_content([Part.from_bytes(img), instruction], config=GenerateContentConfig(response_mime_type="application/json"))`, model vision text (`gemini-2.5-flash`; swap nếu model có "image" — `gemini.py:54`). Hiện `gemini.py` chỉ có image-modality hoặc text thuần → phải thêm path mới.
- **S7 — bỏ param `provider` select ở MVP**: chỉ Gemini hỗ trợ `detect_region` (base raise) → select 1 giá trị hợp lệ là footgun. Hardcode/ẩn select tới khi có provider vision thứ 2. Giữ `target`; cân nhắc `padding` cố định 0.08 thay vì param.
- Node registration theo pattern `backend/app/nodes/__init__.py` (đọc trước khi thêm).
- `detect_region` không tìm thấy → `{"found":false}` → node_error rõ (KHÔNG crop bừa, KHÔNG fallback ngầm).
- Test offline qua `fake.detect_region` (bbox cố định) + `run_node.py --fake`.

## Success Criteria (milestone sau)
- [ ] Node `extract_region` trong palette; form tự sinh; crop giữ pixel gốc.
- [ ] Test crop/padding/clamp/bbox-lỗi/provider-không-hỗ-trợ.
- [ ] (Manual) Gemini trích đúng ≥2 loại đối tượng theo mô tả.

## Next
- Khi sẵn sàng: `/ck:plan` mới với stub này làm nguồn (hoặc `/ck:brainstorm` nếu cần bàn thêm cơ chế bbox).
