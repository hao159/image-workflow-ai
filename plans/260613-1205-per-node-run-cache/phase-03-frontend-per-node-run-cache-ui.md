---
phase: 3
title: "Frontend per-node run + cache UI"
status: completed
priority: P2
effort: "0.5d"
dependencies: [2]
---

# Phase 3: Frontend per-node run + cache UI

## Overview

Thêm nút ▶ trên mỗi node card (chạy tới node đó), badge "đã dùng cache" khi node cache-hit, nút 🗑 Xóa cache trên toolbar, và làm nút "▶ Chạy" tổng hiểu cache (chỉ tô lại node thật sự chạy). Không có JS test runner trong project → verify thủ công + qua `test_ws_cache.py` (Phase 2).

## Requirements

- Functional:
  - Nút ▶ trên header node card → `runNode(id)` gửi `{workflow, target: id, force: [id]}` qua WS.
  - Node nhận `node_finished` có `cached=true` → hiển thị badge nhỏ "⚡ cache".
  - Toolbar có nút 🗑 "Xóa cache" → `clearCache()` (`POST /api/cache/clear`) → báo status.
  - "▶ Chạy" tổng gửi envelope `{workflow, target: null, force: []}`; chỉ reset/tô node theo event nhận (giữ preview node cache-hit).
  - Đang chạy (1 node hoặc tổng) → disable các nút chạy khác; nút Dừng vẫn hoạt động.
- Non-functional: tái dùng vòng đời WS hiện có trong `App.jsx` (`openRunSocket`, `wsRef`, onmessage/onclose); KHÔNG trùng lặp logic → tách handler dùng chung cho run tổng + run-node.

## Architecture

- `RunContext.jsx`: `createContext` cấp `{ runNode, runningNodeId }`. Provider bọc `<ReactFlow>` trong `App`. `WorkflowNode` dùng `useContext` để gọi `runNode(id)` + biết node nào đang chạy.
- `App.jsx`:
  - Tách logic mở socket thành `startRun({ target, force })` (gói phần `run` hiện tại): set running, reset trạng thái **chỉ** các node sẽ chạy (target+ancestors khi có target; toàn bộ khi full), gắn onmessage/onclose như cũ + xử lý `ev.cached`.
  - `run()` = `startRun({ target: null, force: [] })`.
  - `runNode(id)` = `startRun({ target: id, force: [id] })`.
  - `clearCache()` từ `api.js` + nút toolbar 🗑.
  - onmessage `node_finished`: `updateNodeData(ev.node_id, { status:'done', preview, outputs, cached: ev.cached })`.
- `WorkflowNode.jsx`: thêm nút ▶ trong `.wf-node-header` (cạnh nút X), `onClick={() => runNode(id)}`, disable khi đang chạy; badge `data.cached` cạnh status-dot ("⚡ cache").
- `api.js`: `openRunSocket` giữ nguyên; thêm `clearCache()`; cách gửi payload đổi ở `App` (gửi envelope thay vì workflow thuần).

## Related Code Files

- Create: `frontend/src/RunContext.jsx`
- Modify: `frontend/src/App.jsx` (startRun, runNode, clearCache, nút toolbar, provider)
- Modify: `frontend/src/components/WorkflowNode.jsx` (nút ▶ + badge cache)
- Modify: `frontend/src/api.js` (clearCache; payload envelope)
- Modify: `frontend/src/components/icons.jsx` (icon ▶ nhỏ nếu chưa có — đã có PlayIcon, dùng lại size nhỏ)
- Read for context: `frontend/src/node-category-styles.js`, `frontend/src/ui-settings.js`

## Implementation Steps

1. `api.js`: thêm `export async function clearCache()` → `POST /api/cache/clear`.
2. `RunContext.jsx`: context + hook `useRun()`.
3. `App.jsx`:
   - Refactor `run` → `startRun({target, force})`; `run = () => startRun({target:null, force:[]})`.
   - `buildPayload()` giữ nguyên; khi gửi: `ws.send(JSON.stringify({ workflow: buildPayload(), target, force }))`.
   - Reset trạng thái có chọn lọc: nếu `target` → chỉ reset node target (ancestors để engine quyết cache, UI để nguyên preview cũ, cập nhật khi nhận event); nếu full → reset hết (như cũ).
   - onmessage thêm `cached` vào updateNodeData.
   - Thêm `runningNodeId` state (id khi chạy 1 node, null khi full) → cấp qua context.
   - Toolbar: nút 🗑 "Xóa cache" gọi `clearCache()` + set status "Đã xóa cache".
   - Bọc `<RunContext.Provider value={{runNode, runningNodeId}}>`.
4. `WorkflowNode.jsx`: `const { runNode, runningNodeId } = useRun()`; nút ▶ (title "Chạy tới node này") trong header, `disabled={!!runningNodeId || running}` (lấy running qua context hoặc prop); badge "⚡ cache" khi `data.cached`.
5. **Verify thủ công** (acceptance Phase): chạy backend + frontend; dựng `Prompt→Tạo ảnh(fake config)→Resize`; chạy tổng 1 lần; ▶ trên Resize → Tạo ảnh hiện badge ⚡ cache, không gọi lại; đổi prompt → chạy tổng → Tạo ảnh chạy lại. (Dùng fake provider của Phase 4 để khỏi tốn token khi demo; nếu Phase 4 chưa xong, test bằng node local resize/filter.)

## Success Criteria

- [x] Nút ▶ trên node chạy tới đúng node đó; upstream AI không bị gọi lại (badge ⚡ cache xuất hiện).
- [x] Nút 🗑 Xóa cache hoạt động → lần chạy kế tất cả chạy lại.
- [x] "▶ Chạy" tổng chỉ chạy lại node đã đổi + downstream; node khác giữ preview + badge cache.
- [x] Không vỡ luồng Dừng / mất-kết-nối hiện có; không disable nhầm.
- [x] Không trùng lặp code mở-socket (1 `startRun` dùng chung).

## Risk Assessment

- **Reset trạng thái khi run-node**: nếu reset hết node sẽ mất preview cache cũ → chỉ reset node sắp chạy. Mitigation: target → chỉ set node target 'running' khi nhận node_started; node cache-hit tự cập nhật qua event.
- **runningNodeId vs running (full)**: dùng 1 cờ `running` chung để disable; `runningNodeId` chỉ để biết node nào (UX). Tránh 2 nguồn sự thật → derive disable từ `running`.
- **Không có frontend test** → rủi ro regression; bù bằng verify thủ công theo checklist + `test_ws_cache.py` chứng minh backend đúng.
