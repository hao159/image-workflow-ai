---
title: "Mô tả ảnh trên node nguồn rồi tự chèn vào prompt AI"
description: "Ô 'Mô tả ảnh' trên node Tải ảnh/Tạo ảnh: hiện làm phụ đề node + đi theo ảnh xuống node Sửa ảnh, engine tự chèn khối tham chiếu 'Ảnh 1/2' vào prompt. Cache: đổi mô tả không sinh lại ảnh AI. Nhãn passthrough qua node Biến đổi."
status: completed
priority: P2
branch: ""
tags: []
blockedBy: []
blocks: []
created: "2026-06-13T07:43:05.485Z"
createdBy: "ck:plan"
source: skill
---

# Mô tả ảnh trên node nguồn rồi tự chèn vào prompt AI

## Overview

Thêm ô **"Mô tả ảnh"** vào node nguồn (`Tải ảnh lên`, `Tạo ảnh`). Mô tả: (a) hiện làm phụ đề trên node (vai trò "đặt tên node"); (b) **đi theo ảnh** xuống node `Sửa ảnh`, engine tự ghép khối tham chiếu đánh số `Ảnh 1: …, Ảnh 2: …` trước prompt để AI biết ảnh nào là gì.

Nguồn brainstorm (đã chốt): `plans/reports/brainstorm-260613-1430-image-node-description-prompt-injection-report.md`.

**Mấu chốt kỹ thuật:** mô tả KHÔNG tính vào `node_key` của node giữ nó (đổi mô tả không sinh lại ảnh AI = không tốn token), NHƯNG nối vào `output_key` của ảnh → node `Sửa ảnh` phía dưới chạy lại đúng (prompt đổi).

**Mode:** `--tdd` — mỗi phase viết test khóa hành vi trước khi sửa code.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Backend param mô tả và chèn prompt](./phase-01-backend-param-m-t-v-ch-n-prompt.md) | ✅ Completed |
| 2 | [Engine nhãn theo ảnh và cache](./phase-02-engine-nh-n-theo-nh-v-cache.md) | ✅ Completed |
| 3 | [Frontend subtitle và tích hợp docs](./phase-03-frontend-subtitle-v-t-ch-h-p-docs.md) | ✅ Completed (code+docs; live Gemini verify còn chờ user) |

## Implementation Result (Session 2026-06-13)

- **Phase 1+2 backend:** done + tested. `test_nodes.py` 16/16 (8 mới), `test_engine_labels.py` 7/7 (mới), regression `test_engine_cache.py` 9/9, `test_codex.py` 19/19. `import app.nodes` OK.
- **Phase 3 frontend:** `.wf-node-subtitle` band dưới header, build sạch (201 modules).
- **Docs/memory:** README.md (bảng node + mục "Mô tả ảnh → Ảnh 1/Ảnh 2" + bullet cache), memory `image-workflow-project.md` cập nhật.
- **Code review:** DONE, 0 blocking (3 note Low/cosmetic, không sửa theo YAGNI). Cache invariant + label/value alignment verify đúng.
- **Git:** project CHƯA phải git repo → bỏ qua bước commit.

### Follow-up: interleave nhãn↔ảnh (sau verify Codex thật)

Verify thật trên Codex → tên đúng nhưng **mặt sai** (risk Phase 3 thành hiện thực). Tra log `logs/codex/260613-170152-ab964a.log`: app gửi khối + 7 ảnh đúng thứ tự → lỗi ở model, không phải app. Root cause: liệt kê text rời + ảnh trần → model không neo ảnh-nào-là-ai.
- **Fix:** Codex (`openai_codex.py`) + Gemini (`gemini.py`) xen caption `Ảnh N: <tên>` ngay trước từng ảnh (helper `numbered_image_caption` ở `providers/base.py`); `edit.py` truyền `image_labels` qua `**options`; OpenAI/ComfyUI/Fake bỏ qua (backward compat); `compose_edit_prompt` thêm `IMAGE_REF_INSTRUCTION` khi có nhãn.
- **Test:** test_codex.py 23/23 (+4), test_engine_labels.py 9/9 (+2), nodes 16/16, engine_cache 9/9.
- **Trần:** ghép nhiều mặt/1 lần gọi vẫn bấp bênh — caption tăng tỉ lệ đúng, không đảm bảo 100%. Giải pháp triệt để = ghép xác định PIL theo toạ độ slot (feature khác, ngoài scope).
- **Còn chờ user (manual):** re-verify thật trên Codex/Gemini với caption mới.

## Decisions (chốt từ brainstorm)

- Mô tả gõ trên node nguồn (`load_image` + `generate_image`); KHÔNG làm đổi tên cho mọi loại node (YAGNI).
- AI phân biệt ảnh bằng đánh số tự động `Ảnh 1/2/3` + chèn mô tả.
- Đánh số: ảnh gốc = `Ảnh 1`, rồi cổng `images` theo thứ tự cạnh nối.
- Ảnh nối nhưng trống mô tả → vẫn liệt kê `Ảnh N: (không mô tả)` (số không nhảy).
- Không ảnh nào có mô tả → prompt giữ NGUYÊN như cũ (backward compat).
- Param type `text` (1 dòng); khối tham chiếu tiếng Việt (`Ảnh đầu vào:`), đổi sang tiếng Anh nếu test thấy AI lệch.
- **[Validate] Khối tham chiếu đặt TRƯỚC prompt, CHỈ liệt kê (không thêm câu hướng dẫn).**
- **[Validate] Nhãn CHẢY QUA node "Biến đổi"** (`resize`/`filter`/`adjust`): ảnh vào có nhãn → ảnh ra giữ nhãn đó (passthrough). Node `edit_image` (AI ghép) KHÔNG passthrough — output là ảnh composite, không nhãn.

## Dependencies

- Build lên 2 plan đã `completed`: `260613-1100-prompt-supplement-and-combine-overhaul` (merge_prompt, supplement param) + `260613-1205-per-node-run-cache` (engine_cache_key, node_key). Không block — chỉ kế thừa cơ chế.

## Key files

- `backend/app/nodes/base.py` — `Param.is_image_label`
- `backend/app/nodes/inputs.py`, `generate.py` — thêm param mô tả
- `backend/app/nodes/transform.py` — `label_passthrough_from="image"` cho resize/filter/adjust
- `backend/app/nodes/edit.py` — đọc `self.input_labels`, chèn khối tham chiếu
- `backend/app/nodes/image_label_block.py` (mới) — helper dựng khối + compose prompt (pure)
- `backend/app/engine.py` — nhãn đi theo ảnh, set `instance.input_labels`, out_key kèm nhãn
- `backend/app/engine_cache_key.py` — tách nhãn khỏi node_key + helper out_key
- `frontend/src/components/WorkflowNode.jsx` — phụ đề mô tả trên header
- `backend/test_nodes.py`, `backend/test_engine_labels.py` (mới) — test

## Validation Log

### Session 1 (2026-06-13)

**Verification Results**
- Tier: Standard (3 phases). Claims checked: ~14 across phases.
- Verified: 14 | Failed: 0 | Unverified: 0
- Đối chiếu code thật: `Param`/`BaseNode.run(inputs,params)`/`instance=cls()` (base.py, engine.py); `node_key()` + `out_keys=f"{nk}:{handle}"` + `cache.load/save(nk)` (engine_cache_key.py, engine.py); `NodeParamField` default-case render text input; `edit.py images=[image,*images,image2]`+`merge_prompt`; `test_nodes.py` thuần + `__main__` runner; transform nodes (resize/filter/adjust) đều 1 cổng `image`→`image`.
- **Refinement (không phải failure):** test Phase 2 monkeypatch `app.nodes.edit.resolve_model_config` và `app.nodes.generate.resolve_model_config` (tên bind vào module node qua `from ..providers import`), KHÔNG patch ở `app.providers`.

**Decisions confirmed (3 câu hỏi)**
1. Nhãn ảnh dẫn xuất → **cho nhãn chảy qua node "Biến đổi"** (passthrough). → mở rộng Phase 2: BaseNode `label_passthrough_from`; engine kế thừa nhãn từ cổng input khi node không có nhãn riêng. Node `edit_image` KHÔNG passthrough.
2. Vị trí khối tham chiếu → **trước prompt, chỉ liệt kê** (không câu hướng dẫn). Khớp thiết kế Phase 1 sẵn có — không đổi.
3. Kiểu ô mô tả → **text 1 dòng**. Khớp thiết kế — không đổi.

**Recommendation:** proceed — đã propagate quyết định #1 vào Phase 1+2 và sweep nhất quán.

### Whole-Plan Consistency Sweep
- Đọc lại plan.md + 3 phase. Sửa mâu thuẫn: Phase 2 "2 helper" → "3 helper" (khớp danh sách hàm + Related Files + step 2); thuật ngữ `label_val` → `out_label`; "FakeProvider" → "stub provider" (test dùng stub tự định nghĩa, không phải FakeProvider thật).
- Đối chiếu xuôi: transform.py khai báo `label_passthrough_from` (Phase 1) ↔ engine đọc (Phase 2) ↔ Key files (plan.md) — nhất quán.
- **0 mâu thuẫn còn lại.** Plan sẵn sàng implement.
