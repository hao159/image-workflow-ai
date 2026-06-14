---
phase: 2
title: Engine harness loop opt-in (critic-refine)
status: completed
priority: P1
effort: 1.5-2d
dependencies:
  - 1
---

# Phase 2: Engine harness loop opt-in (critic-refine)

## Overview

Lõi harness: `run_workflow` thêm **outer bounded loop** opt-in — chạy DAG → AI critic chấm **ảnh sản phẩm cuối** vs goal → chưa đạt & còn lượt → **append feedback** vào prompt node sinh → re-run → lặp. Hết limit/đạt → xuất **best + report**. Thiếu `harness` config → đường hiện tại nguyên vẹn.

> Đây là phase rủi ro cao nhất. Toàn bộ fix red-team (C2–C13) gói trong đây.

## Requirements
- Functional:
  - `HarnessConfig{enabled:bool, max_iterations:int=3, criteria:str="", pass_score:float=8.0, critic_provider:str=""}`; `RunRequest.harness: Optional[HarnessConfig]`.
  - **Goal (C3)** = prompt **hiệu dụng đã merge** của node sinh terminal, tính tại iteration 0 bằng chính `merge_prompt(resolved_prompt_input, params["prompt"])` (import từ `nodes.prompt_merge`). KHÔNG đọc params thô (prompt có thể đến từ cổng nối, vd enhance_prompt).
  - **Critic (C4)** chấm **ảnh sản phẩm cuối** (ảnh chảy vào node `save_image` / ảnh terminal), KHÔNG phải output thô node sinh.
  - `provider.critique_image(image, goal, criteria) -> {score:0..10, passed:bool, feedback:str}`. `passed = score >= pass_score`.
  - **Critic provider (C8)**: resolve theo `critic_provider` nếu set; nếu trống → thử provider node sinh; nếu provider đó KHÔNG hỗ trợ vision → **lỗi RÕ TRƯỚC khi sinh** ("harness cần critic vision, cấu hình Gemini"). KHÔNG để chạy sinh xong mới chết.
  - Vòng lặp ≤ `max_iterations`. Mỗi vòng emit `harness_iteration` (iteration, score, passed, feedback). Đạt/hết lượt → emit `harness_report` + ảnh best là sản phẩm cuối.
  - **Feedback inject (C3)**: append feedback vào `params["prompt"]` node sinh (supplement) → `merge_prompt` đặt feedback SAU prompt cổng → đúng ngữ nghĩa "thêm chỉnh sửa", không thay/nhân đôi goal. Param đổi → `node_key` đổi → node sinh + downstream (transform, save) re-run; nhánh khác cache-hit. (KHÔNG đụng `engine_cache_key.py`.)
  - **Accumulate (C13)**: feedback tích lũy qua các vòng (cap ~3 chỉnh sửa / giới hạn ký tự), không reassign mất chỉnh cũ → tránh dao động.
- Non-functional:
  - **Backward-compat (C tuyệt đối)**: `harness` None/`enabled=false` → `run_workflow` chạy đúng hành vi + event sequence hiện tại; mọi test cũ xanh.
  - Token-aware: dừng sớm khi passed; cache lo phần không đổi; limit cứng.

## Architecture

```
run_workflow(workflow, emit, *, target, force_ids, harness=None):
  order = topo(...); prune nếu target
  if not (harness and harness.enabled):
      await _execute_pass(workflow, emit, order, ...)   # nhánh thường — 1 pass, hành vi cũ
      return
  # --- harness branch ---
  product_node, gen_node, sink_nodes = locate_product(workflow, order)   # C4,C6,C7
  validate_or_error(...)                                  # C7: 0 node sinh / nhập nhằng → run_error rõ
  critic = resolve_critic(harness, gen_node) ; ensure_vision_or_error()  # C8 — TRƯỚC khi sinh
  goal = effective_prompt(gen_node, order)                # C3 — merge_prompt thật
  best = None ; feedbacks = []
  for it in range(harness.max_iterations):
      params_override = {gen_node.id: append_supplement(orig_prompt_param, feedbacks)}  # C3,C13
      try:
          results = await _execute_pass(workflow, emit, producers_only_order, ...,
                                        params_override=params_override, iteration=it)  # C6: chỉ producers
      except PassError as e:                              # C5
          if best: emit_final(best) + emit(harness_report, stopped_early=str(e)); return
          else: emit(run_error, e); return
      product_img = results[product_node]                 # ảnh sản phẩm cuối (trước sink)
      verdict = critic.critique_image(product_img, goal, harness.criteria)  # C2: critic đã unpack (provider,model)
      emit(harness_iteration: it, verdict.score, verdict.passed, verdict.feedback)
      if best is None or verdict.score > best.score: best = (score, product_img)
      if verdict.passed: break
      feedbacks.append(verdict.feedback)
  # C6: chạy sink (save/output) MỘT LẦN trên ảnh best, rồi report
  await run_sinks_once(sink_nodes, best.image, emit)
  emit(harness_report: best_iteration, best_score, history)
```

- **`_execute_pass` (refactor tối thiểu, KHÔNG override-dict tổng quát — Scope F4 + Failure F3/F7):** rút thân vòng `for node_id in order` hiện tại (`engine.py:117-199`) thành coroutine nhận `emit`, **state tươi mỗi lần gọi** (`results/out_keys/labels` mới), tham số `params_override: dict[node_id, dict] = {}` (chỉ ghi đè params của node sinh), `iteration`. Nhánh thường gọi đúng 1 lần, KHÔNG override → hành vi y cũ. Trả `results` (map (node_id,handle)->bytes) để harness lấy ảnh sản phẩm.
- **locate_product (C4,C6,C7):**
  - `sink_nodes` = node không có cạnh ra tiêu thụ ảnh (vd `save_image`) — chạy MỘT LẦN sau loop.
  - `product_node` = ảnh đầu vào của sink (hoặc ảnh terminal cuối topo nếu không có sink).
  - `gen_node` = node `generate_image`/`edit_image` gần nhất (truy ngược từ product qua transform).
  - **Edge cases:** 0 node sinh → `run_error` "harness cần ít nhất 1 node Tạo/Sửa ảnh". Nhiều sink/branch → MVP: `run_error` "harness chưa hỗ trợ nhiều nhánh đầu ra; chạy 1 nhánh" (KHÔNG đoán theo node-id sort — `engine.py:39`).
- **effective_prompt (C3):** engine resolve inputs node sinh (đã có `gathered`), gọi `merge_prompt(inputs.get("prompt"), params.get("prompt"))` y node làm.
- **resolve_critic + critique_image (C2,C8,C9):** `provider, model = resolve_model_config(critic_sel)` (UNPACK tuple). `base.critique_image` default raise. `gemini.critique_image`: `generate_content(contents=[Part.from_bytes(img), instruction(goal,criteria)], config=GenerateContentConfig(response_mime_type="application/json"))`, model vision text (`gemini-2.5-flash`; nếu model có "image" → swap như `gemini.py:54`); parse JSON `{score,passed,feedback}` robust.
- `models.py`: `HarnessConfig`; `RunRequest.harness`; `RunEvent` thêm `iteration:Optional[int]`, `score:Optional[float]`, `report:Optional[dict]`; type `harness_iteration`/`harness_report`. (Giữ report gọn, typed-ish — không nhồi dict lớn.)
- `main.py`: envelope đọc `harness` → truyền `run_workflow(..., harness=req.harness)`. Guard `emit` khi WS đóng giữa loop (C12): bắt exception emit → dừng gọn.
- **C12 (document):** disconnect giữa loop mất best RAM + feedback non-deterministic → KHÔNG resume ở MVP; ghi rõ giới hạn, không claim token-safe xuyên phiên.

## Related Code Files
- Create: `backend/test_harness_loop.py`
- Modify: `backend/app/engine.py` (tách `_execute_pass`; harness branch; locate_product; effective_prompt; run_sinks_once)
- Modify: `backend/app/models.py` (HarnessConfig, RunRequest.harness, RunEvent fields/types)
- Modify: `backend/app/main.py` (truyền harness + guard emit)
- Modify: `backend/app/providers/base.py` (`critique_image` default raise)
- Modify: `backend/app/providers/gemini.py` (`critique_image` impl — vision text + JSON)
- Modify: `backend/app/providers/fake.py` (`critique_image` trả điểm tăng theo iteration để test loop)

## Implementation Steps (TDD)
1. **Test trước** (`test_harness_loop.py`, stub/fake — KHÔNG mạng):
   - **Backward-compat**: `run_workflow(harness=None)` → kết quả + event sequence Y HỆT baseline (đối chiếu `test_engine_*`). KHÓA.
   - **Dừng khi đạt**: critique passed iter0 → 1 vòng producers, harness_report best=0, sink chạy đúng 1 lần.
   - **Hết limit**: luôn fail, score [5,6,7] → 3 vòng, best=iter2.
   - **Best≠last (C6)**: score [6,9,4] → best=iter1; **sink chạy 1 lần trên ảnh iter1**; `outputs/` KHÔNG có file thừa iter2.
   - **Feedback append + accumulate (C3,C13)**: pass2 prompt node sinh chứa feedback (sau prompt cổng), pass3 chứa cả 2 chỉnh; node không liên quan cache-hit.
   - **Goal từ cổng nối (C3)**: workflow `enhance/prompt-port → generate` → goal = prompt merge thật (không phải param rỗng).
   - **Critic không vision (C8)**: provider không hỗ trợ → run_error TRƯỚC khi sinh.
   - **Fail giữa loop (C5)**: pass2 raise → emit best (iter0/1) + report stopped_early, KHÔNG mất best.
   - **0 node sinh / nhiều sink (C7)**: run_error rõ.
   - Đỏ.
2. **Refactor `_execute_pass`** (giữ logic cũ) → chạy regression `test_engine_*` XANH TRƯỚC khi thêm loop (rủi ro lớn nhất).
3. `models.py`: HarnessConfig + fields.
4. `base.py` + `fake.py`: `critique_image`.
5. `engine.py`: locate_product + effective_prompt + harness branch + run_sinks_once.
6. `main.py`: truyền harness + guard emit.
7. `gemini.py`: critique_image thật (vision text + JSON parse robust).
8. Xanh toàn bộ + regression. `import app` OK.
9. **(Manual, chờ user)** verify thật trên Gemini sau Phase 3 UI.

## Success Criteria
- [ ] `harness=None` → hành vi + event sequence KHÔNG đổi (test khóa xanh).
- [ ] Loop dừng khi passed / hết limit; xuất **best** (kể cả best≠last); sink chạy **1 lần** trên best (không file thừa).
- [ ] Goal lấy đúng prompt merge (cả khi prompt từ cổng nối).
- [ ] Feedback append + accumulate; node sinh+downstream re-run, nhánh khác cache-hit.
- [ ] Critic không vision → lỗi RÕ trước khi sinh. Fail giữa loop → giữ best + report.
- [ ] 0 node sinh / nhiều sink → run_error rõ.
- [ ] Test cũ (`test_engine_cache/labels/nodes/codex`) xanh.

## Risk Assessment
- **Refactor `_execute_pass` lệch hành vi** → tách thuần + regression NGAY bước 2.
- **Tách producers vs sink phức tạp** → định nghĩa sink = node không có con tiêu thụ ảnh; test 1-3 hình dạng graph.
- **Loop tốn token** → limit cứng + dừng sớm + cache.
- **Critic chấm lệch** → criteria cho user ghì + report hiện lý do (Phase 3).
- **Disconnect giữa loop** → MVP không resume; document.

## Open (chốt khi code)
- `max_iterations`=3, `pass_score`=8.0 (chỉnh ở toolbar Phase 3).
- Nhiều nhánh đầu ra: MVP báo lỗi; mở rộng sau.
