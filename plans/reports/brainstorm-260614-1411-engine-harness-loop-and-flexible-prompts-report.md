# Brainstorm — Biến app thành Harness: engine critic-refine loop + prompt linh hoạt

**Ngày:** 2026-06-14 · **Trạng thái:** Đã chốt thiết kế, chờ lập plan
**Yêu cầu gốc (user):** Bug case cũ — ảnh mặt mờ nhưng cần tách mặt ghép khung khác; workflow ghép nhiều ảnh / phức tạp bị AI sai label. Nghi do system prompt **ràng cứng theo case test đã báo bug**. Muốn: (1) yếu tố *harness* — node tự dùng AI trích/crop đối tượng trước rồi mới ghép; (2) system prompt **linh hoạt theo ý đồ workflow** thay vì hard-code.

---

## 1. Problem statement

Gốc rễ (verified qua scout):
- **Chỉ thị cứng**: `image_label_block.py:12` `IMAGE_REF_INSTRUCTION` ("giữ nguyên nhận dạng, KHÔNG tráo mặt") **auto-chèn mỗi khi có nhãn ảnh** → tối ưu cho case test cũ, phá ý đồ workflow khác. `enhance_prompt.py:8` `SYSTEM_INSTRUCTION` cũng cố định.
- **Thiếu pre-process độ tin cậy**: ảnh đối tượng ít pixel → AI trích không đủ → ghép sai. README:104 chỉ có **mẹo thủ công** "crop sát trước khi upload". Không có node tự động.
- **Một-pass, không tự kiểm**: workflow chạy 1 lượt topo, không có bước AI tự chấm output so mục tiêu rồi refine → kết quả không "product ready" thì user phải tự sửa tay.

App hiện là **DAG một-pass**. User muốn nó **vận hành như một harness**: lặp có giới hạn, tự chấm, refine tới khi đạt product-ready.

## 2. Quyết định đã chốt (user xác nhận)

| Vấn đề | Lựa chọn |
|---|---|
| Kiến trúc | **Engine-level harness loop** (hướng A) — cách hoạt động cốt lõi, KHÔNG chỉ "thêm 1 node" |
| Rollout | **Opt-in toggle trước** (`▶ Chạy (harness)`) → mặc định bật sau khi đo chất lượng ổn |
| Critic chấm | **AI vision tự chấm** theo goal + **ô tiêu chí tùy chọn** (trống → chấm theo user prompt) |
| Hết limit chưa đạt | **Xuất iteration điểm cao nhất + report** (điểm + lý do); KHÔNG giết workflow |
| Chỉ thị cứng "không tráo mặt" | **Giữ auto-default nhưng cho override đè** → builder theo intent, bỏ hard-code theo case |
| Node trích | **TỔNG QUÁT** — mô tả gì tách nấy (mặt/bò/chó/người/áo), KHÔNG đặc trị "mặt" |
| Nguồn goal | **Tự động từ prompt của node sinh ảnh terminal** (bật harness là chạy, không bắt nhập thêm) |

## 3. Hướng đã chọn: A — Engine harness loop (opt-in trước)

### Loại 2 hướng khác
- **B. Chỉ thêm node Harness** — engine không đổi, KISS, nhưng chỉ là "thêm node" → user nói rõ muốn *đổi cách app hoạt động*, không khớp.
- **A mặc-định-ngay (không toggle)** — đúng tinh thần nhất nhưng đổi engine nhiều + rủi ro phá workflow cũ ngay → chọn opt-in trước cho an toàn, đo rồi mới mặc định.

### Cơ chế lõi (critic-refine loop)

```
▶ Chạy (harness)  ──► [topo pass: DAG chạy như cũ, cache-aware]
                            │
                            ▼
                output cuối + goal (auto = prompt node sinh cuối) + tiêu chí tùy chọn
                            │
                            ▼
                     AI CRITIC (vision) chấm điểm + pass/fail + feedback
                            │
              ┌──── đạt? ───┴─── chưa & còn lượt ───┐
              ▼ yes                                  ▼
        XUẤT best + report          inject feedback → re-run node sinh
                                    (cache lo node không đổi) ─► lặp tới limit
                                    hết limit → XUẤT best + report
```

- DAG **vẫn acyclic** (engine.py:49 vẫn chặn cycle) — loop ở **tầng run-orchestration**, không phải dây nối.
- **Adaptive system prompt** dùng chung cho critic + refiner: suy intent từ goal, không hard-code case. Auto-default giữ, override đè.
- **Backward-compat**: `▶ Chạy` thường = y hệt hiện tại; harness là đường riêng opt-in → workflow JSON cũ không vỡ (đúng tinh thần codebase).

### Node trích vùng tổng quát (building block)
- Node mới **"Trích vùng (AI)"**: input ảnh + ô **mô tả đối tượng** (`"con bò"`, `"khuôn mặt người bên trái"`, `"cái áo"`) → vision trả **bbox** đúng đối tượng → backend **crop PIL** (giữ nguyên pixel gốc, không bịa, rẻ, deterministic).
- Một node tách mọi thứ → linh hoạt, tái dùng trong/ngoài harness. KHÔNG đặc trị "mặt".

## 4. Related code files (touchpoints — xác nhận khi lập plan)

**Sửa:**
- `backend/app/engine.py` — outer bounded loop + critic stage + chọn best + emit report; giữ nhánh chạy thường nguyên vẹn.
- `backend/app/image_label_block.py` — thay `IMAGE_REF_INSTRUCTION` auto-cứng → builder adaptive theo intent + hỗ trợ override.
- `backend/app/nodes/enhance_prompt.py` — `SYSTEM_INSTRUCTION` dùng builder chung, bỏ cố định.
- `backend/app/providers/base.py` + `gemini.py` — thêm capability: vision-bbox (cho node trích) + critic-score (chấm output vs goal). Provider không hỗ trợ vision → degrade rõ ràng.
- `backend/app/models.py` — `RunEvent` mang report/iteration/score.
- `backend/app/engine_cache_key.py` — feedback inject làm prompt hiệu dụng đổi → key lan xuống re-run node sinh; node khác cache-hit.
- `frontend/src/components/` (toolbar) — toggle `▶ Chạy (harness)` + ô tiêu chí tùy chọn + hiển thị report/điểm/iteration.

**Tạo:**
- `backend/app/nodes/extract_region.py` — node trích vùng tổng quát (vision bbox → crop PIL).
- (tùy chọn) `backend/app/adaptive_prompt.py` — builder system prompt theo intent (dùng chung critic/refiner/enhance).

**Test:** `backend/test_nodes.py` (node trích), `backend/test_engine_labels.py`/mới (harness loop: dừng khi đạt, dừng khi hết limit, best-selection, chạy thường không đổi).

## 5. Success criteria

- **Harness loop**: workflow + goal auto → chạy ≤ N iteration, critic chấm mỗi vòng, dừng khi pass hoặc hết limit, xuất **best + report**. Test thật trên Gemini.
- **Chạy thường (harness off)**: output **y hệt hiện tại** — workflow JSON đã lưu chạy không lỗi (backward-compat).
- **Node trích**: ảnh + `"con bò"` → output crop chứa con bò; đổi mô tả → tách đối tượng khác. Test thật.
- **Adaptive prompt**: chỉ thị "không tráo mặt" KHÔNG còn auto-chèn mù; theo intent; override hoạt động; flow nhãn cũ vẫn chạy khi không override.
- **Token-aware**: harness off không tốn thêm token; harness on tôn trọng limit (không loop vô hạn).

## 6. Rủi ro & giảm thiểu

- **Critic cần provider vision** (Gemini có; OpenAI/ComfyUI yếu) → degrade rõ: harness yêu cầu cấu hình provider vision, báo lỗi sớm thay vì chấm bậy.
- **Loop tốn token** → limit cứng + dừng sớm khi đạt + cache re-run chỉ node đổi.
- **Đổi engine = rủi ro phá run thường** → harness là nhánh opt-in riêng; nhánh thường giữ nguyên; test backward-compat bắt buộc.
- **Critic chấm lệch ý** → ô tiêu chí tùy chọn cho user ghì; report để user thấy lý do; mở rộng critic dần.
- **bbox vision sai/không thấy đối tượng** → node trích trả lỗi rõ + fallback trả ảnh gốc (không crash workflow).

## 7. Mở rộng dần (sau MVP, ngoài scope đợt này)

- Harness mode thành **mặc định** sau khi đo chất lượng.
- Critic đa tiêu chí / đa provider vote.
- Thêm building-block node tự kiểm (vd "Validate label" trước khi ghép).
- Stream tiến độ trong-loop lên UI (hiện engine chỉ emit node_started/finished).
- Loop bọc sub-workflow (hiện chỉ loop tầng run toàn DAG).

## 8. Unresolved questions

- **Limit mặc định** bao nhiêu vòng? (đề xuất 3, cho chỉnh ở toolbar) — chốt khi lập plan.
- **Critic chấm output nào** khi workflow có nhiều node Lưu/terminal ảnh? (đề xuất: ảnh ở (các) node terminal; nếu nhiều → chấm từng cái hay gộp?) — chốt khi lập plan.
- **Ngưỡng pass** của điểm critic (vd ≥ 8/10) cố định hay cho chỉnh? — đề xuất cho chỉnh, default hợp lý.
