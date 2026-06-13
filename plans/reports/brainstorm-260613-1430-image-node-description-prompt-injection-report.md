# Brainstorm — Mô tả ảnh trên node nguồn → tự chèn vào prompt cho AI

**Ngày:** 2026-06-13 · **Trạng thái:** Đã chốt thiết kế, chờ lập plan
**Yêu cầu gốc (user):** "đặt tên cho từng node để mô tả node đó… node ảnh tôi muốn mô tả từng ảnh… để prompt mô tả chi tiết có thể trỏ cho AI biết"

## 1. Problem statement

Node `Sửa ảnh (AI)` nhận nhiều ảnh (`image` gốc + cổng `images` multiple) rồi gọi
`provider.edit([image, *images], prompt)`. AI chỉ nhận **một đống ảnh + prompt thô**,
KHÔNG có nhãn nào cho biết ảnh nào là gì → khó ghép kiểu "mặc áo (ảnh A) lên người (ảnh B)".

Cần: gắn mô tả cho từng ảnh nguồn, mô tả **đi theo ảnh** xuống node Sửa ảnh và
**tự chèn vào prompt** để AI phân biệt được.

## 2. Quyết định đã chốt (user xác nhận)

| Vấn đề | Lựa chọn |
|---|---|
| Mục tiêu | **Cả hai**: ô mô tả vừa làm tên hiển thị trên node, vừa báo cho AI |
| AI phân biệt ảnh kiểu gì | **Tự đánh số + chèn mô tả**: "Ảnh 1: …, Ảnh 2: …" ghép trước prompt |
| Mô tả gõ ở đâu | **Trên node nguồn**: `Tải ảnh lên` (`load_image`) + `Tạo ảnh` (`generate_image`) |
| Phạm vi đặt tên | **Chỉ node ảnh** — KHÔNG làm đổi tên cosmetic cho mọi loại node (YAGNI) |
| Ảnh nối nhưng trống mô tả | **Vẫn đánh số**, ghi "(không mô tả)" — giữ số thứ tự nhất quán |

## 3. Hướng đã chọn: ô "Mô tả ảnh" trên node nguồn (Hướng A)

Loại 2 hướng khác:
- **B. Node "Gán nhãn ảnh" riêng** — rườm rà, kéo thêm node+dây mỗi ảnh.
- **C. Mô tả ngay trên node Sửa ảnh** — cổng `images` là *multiple* (số ảnh không cố định) → UI khó, dễ lệch thứ tự.

## 4. Thiết kế

### 4.1 Giao diện
- `load_image` + `generate_image` thêm 1 param **"Mô tả ảnh"** (text/textarea, default rỗng).
- Có mô tả → hiện **phụ đề dưới tiêu đề node** trên canvas (vai trò "đặt tên node").

### 4.2 Tự chèn vào prompt (lõi)
Node `Sửa ảnh` dựng khối tham chiếu rồi ghép TRƯỚC prompt người dùng:
```
Ảnh đầu vào:
- Ảnh 1: cái áo sơ mi trắng
- Ảnh 2: người mẫu nữ tóc dài
- Ảnh 3: (không mô tả)

mặc áo ở Ảnh 1 lên người ở Ảnh 2
```
- Đánh số: **Ảnh gốc = Ảnh 1**, rồi các "Ảnh ghép thêm" theo thứ tự nối dây (edge order).
- Ảnh trống mô tả: vẫn liệt kê "(không mô tả)".
- **Không ảnh nào có mô tả → prompt GIỮ NGUYÊN như hiện tại** (không phá hành vi cũ, không phá workflow đã lưu).

### 4.3 Kiến trúc — nhãn "đi theo ảnh"
- `engine.py`: thêm map `labels[(node_id, handle)]` lấy từ ô mô tả node nguồn; khi gom
  input cho node Sửa ảnh, gom nhãn **cùng thứ tự** với ảnh, truyền vào `run()` qua khóa
  nội bộ (vd `inputs["__labels__"]`). Node khác bỏ qua → **KHÔNG đổi chữ ký `run`**,
  không phá node cũ.
- `edit.py`: đọc nhãn → dựng khối tham chiếu → ghép trước prompt (tái dùng tinh thần
  `merge_prompt`). `provider.edit()` **không đổi** — chỉ làm giàu `prompt`.

### 4.4 Cache (điểm tinh tế)
Yêu cầu nghịch nhau:
- Đổi mô tả → node `Sửa ảnh` PHẢI chạy lại (prompt đổi).
- Đổi mô tả → `Tạo ảnh (AI)` KHÔNG được sinh lại (mô tả chỉ là nhãn, ảnh không đổi → tốn token vô ích).

Giải pháp: mô tả **không tính vào `node_key` của chính node giữ nó**, nhưng **nối vào
`output_key`** của ảnh đó → node Sửa ảnh phía dưới thấy input đổi → chạy lại; còn node
`Tạo ảnh` không sinh lại. (`load_image` chạy lại là miễn phí.) → đụng `engine_cache_key.py`.

## 5. Related code files

**Sửa:**
- `backend/app/nodes/inputs.py` — thêm param "Mô tả ảnh" cho `LoadImageNode`
- `backend/app/nodes/generate.py` — thêm param "Mô tả ảnh" cho `GenerateImageNode`
- `backend/app/nodes/edit.py` — đọc nhãn, dựng khối tham chiếu, ghép prompt
- `backend/app/engine.py` — theo dõi + truyền `labels` theo ảnh
- `backend/app/engine_cache_key.py` — mô tả nối vào out_key (không vào node_key của node giữ nó)
- `backend/app/nodes/base.py` — (có thể) thêm cờ Param đánh dấu "đây là mô tả ảnh" / cờ display-as-subtitle
- `frontend/src/components/WorkflowNode.jsx` — hiện phụ đề mô tả trên header
- `backend/test_nodes.py` — thêm test cho merge khối tham chiếu + thứ tự + ảnh trống mô tả

**Tạo:** (tùy chọn) helper `nodes/image_label.py` nếu logic dựng khối tham chiếu > vài dòng.

## 6. Success criteria
- Workflow 2× `Tải ảnh lên` (mô tả "cái áo", "người mẫu") → `Sửa ảnh` "mặc áo lên người":
  prompt gửi provider CHỨA khối "Ảnh 1: cái áo / Ảnh 2: người mẫu" đúng thứ tự; AI ghép đúng (test thật trên Gemini).
- Đổi 1 mô tả → node `Sửa ảnh` cache-miss chạy lại; node `Tạo ảnh` upstream vẫn cache-hit (không tốn token).
- Mọi ảnh trống mô tả → prompt y hệt hành vi cũ; workflow JSON đã lưu chạy không lỗi.
- Trống mô tả nhưng ảnh được nối → liệt kê "(không mô tả)", số thứ tự không nhảy.

## 7. Rủi ro & giảm thiểu
- **AI có tôn trọng "Ảnh 1/2" không?** Mạnh nhất với **Gemini (Nano Banana)**; `gpt-image`/`codex` yếu hơn → best-effort. → test thật 1 workflow 2 ảnh sau khi làm; nếu yếu, cân nhắc lặp lại số trong câu mô tả.
- **Thứ tự edge không hiển nhiên trên canvas.** Giảm thiểu: số đi kèm mô tả nên AI tự map; (về sau, ngoài scope) badge số tại cổng vào node Sửa ảnh.
- **Cache sai → tốn token.** Phải test riêng nhánh "đổi mô tả không sinh lại ảnh AI".

## 8. Unresolved questions
- Param "Mô tả ảnh" nên là `text` (1 dòng) hay `textarea` (nhiều dòng)? → đề xuất `text` cho gọn, nâng lên `textarea` nếu cần.
- Khối tham chiếu nên tiếng Việt ("Ảnh đầu vào:") hay tiếng Anh ("Input images:")? Provider/AI có thể "ăn" tiếng Anh tốt hơn — cần xác nhận khi lập plan (mặc định đề xuất: tiếng Việt theo UI, đổi nếu test thấy AI lệch).
