---
phase: 3
title: Frontend badge và relabel cổng đã nối
status: completed
priority: P2
effort: 1h
dependencies:
  - 1
---

# Phase 3: Frontend badge và relabel cổng đã nối

## Overview
`WorkflowNode` phát hiện cổng input nào đang được nối → gắn badge "✓ đã nối" vào label cổng, và relabel param có `supplement_for` ứng cổng đó sang `supplement_label`. Ô vẫn soạn được.

## Requirements
- Functional: cổng nối → badge; param bổ sung → đổi nhãn khi cổng nối, giữ nhãn gốc khi chưa nối.
- Non-functional: không thread `edges` xuống node (dùng hook React Flow); không đổi node khác.

## Architecture
`@xyflow/react ^12.4.0` có `useNodeConnections({ id, handleType })` → trả connections tới node hiện tại. Build `Set` các `targetHandle` đang nối. Handle id trong code = `in-${port.name}` (xem `WorkflowNode.jsx:67`). Gọi hook 1 lần ở đầu component (đúng rules-of-hooks). Metadata `supplement_for`/`supplement_label` đã có từ Phase 1.

## Related Code Files
- Modify: `frontend/src/components/WorkflowNode.jsx`
- Modify: `frontend/src/styles/workflow-node.css` (style badge)

## Implementation Steps
1. Import: `import { Handle, Position, useReactFlow, useNodeConnections } from '@xyflow/react'`.
2. Trong `WorkflowNode`, sau khi có `id`:
   ```jsx
   const connections = useNodeConnections({ id, handleType: 'target' })
   const connectedHandles = new Set(connections.map((c) => c.targetHandle))
   const isConnected = (portName) => connectedHandles.has(`in-${portName}`)
   ```
3. Label cổng input (khối `meta.inputs.map`): khi `isConnected(port.name)` → thêm badge:
   ```jsx
   <span className="wf-port-label">
     {port.label}
     {isConnected(port.name) && <span className="wf-port-badge">✓ đã nối</span>}
     {!isConnected(port.name) && (port.multiple ? ' (nhiều dây)' : port.required ? '' : ' (tùy chọn)')}
   </span>
   ```
   (Khi đã nối thì badge thay cho hậu tố "(tùy chọn)".)
4. Param label (khối `meta.params.map`): tính nhãn hiển thị:
   ```jsx
   const label =
     spec.supplement_for && isConnected(spec.supplement_for)
       ? spec.supplement_label || spec.label
       : spec.label
   ```
   Dùng `label` thay `spec.label` trong `<span className="wf-param-label">`.
5. CSS `workflow-node.css` — badge nhỏ màu accent/xanh:
   ```css
   .wf-port-badge {
     margin-left: 6px; padding: 0 6px; border-radius: 999px;
     font-size: 10px; font-weight: 600;
     background: rgba(52, 211, 153, 0.16); color: #34d399;
   }
   ```
6. Compile check: `npm run build --prefix frontend` (báo lỗi JSX/import nếu có).

## Success Criteria
- [ ] Nối Prompt → Enhance: cổng "Prompt gốc" hiện badge "✓ đã nối"; ô param đổi nhãn "Prompt bổ sung", vẫn gõ được.
- [ ] Gỡ dây → label cổng + param trở lại bình thường ("(tùy chọn)" / "Prompt gốc").
- [ ] Tương tự cho Tạo ảnh + Sửa ảnh (cổng `prompt`).
- [ ] `npm run build` không lỗi.

## Risk Assessment
- `useNodeConnections` API: nếu signature khác ở 12.4 → fallback `useHandleConnections({ type:'target', id:'in-<port>' })` (deprecated nhưng còn). Kiểm bằng docs context7 nếu build cảnh báo.
- Hook phải trong node context (đã đúng — node render trong `<ReactFlow>`).
