import { createContext, useContext } from 'react'

// Cấp cho từng WorkflowNode khả năng "chạy tới node này" (▶ trên node) và biết
// trạng thái chạy hiện tại để disable nút khi đang bận.
export const RunContext = createContext({
  runNode: () => {},
  runningNodeId: null, // id node đang chạy riêng lẻ (null khi chạy tổng / rảnh)
  running: false,      // có đang chạy (tổng hoặc 1 node) hay không
})

export function useRun() {
  return useContext(RunContext)
}
