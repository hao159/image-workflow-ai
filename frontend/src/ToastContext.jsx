import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import ToastStack from './components/Toast.jsx'

// Toast thông báo dùng chung (góc trên-giữa). Tách vai trò khỏi status-chip toolbar:
// chip giữ trạng thái BỀN "đang chạy" (cập nhật tại chỗ), còn toast
// NỔI LÊN cho sự kiện rời rạc (xong / lỗi / đã lưu / đã xóa / mất kết nối) rồi tự ẩn.
// Cấp qua Context giống ImageViewerContext.jsx để component lồng sâu cũng gọi được.
const ToastContext = createContext({
  success: () => {}, error: () => {}, info: () => {}, warn: () => {},
})

export function useToast() {
  return useContext(ToastContext)
}

// Thời lượng tự ẩn theo loại (ms). Lỗi/cảnh báo đứng lâu hơn để kịp đọc.
const DURATION = { success: 3500, info: 3500, warn: 5000, error: 6000 }

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]) // [{ id, kind, msg }]
  const idRef = useRef(0)
  const timers = useRef(new Map())

  const dismiss = useCallback((id) => {
    setToasts((list) => list.filter((t) => t.id !== id))
    const tm = timers.current.get(id)
    if (tm) { clearTimeout(tm); timers.current.delete(id) }
  }, [])

  const push = useCallback((kind, msg) => {
    if (!msg) return
    const id = ++idRef.current
    setToasts((list) => [...list, { id, kind, msg: String(msg) }])
    timers.current.set(id, setTimeout(() => dismiss(id), DURATION[kind] || 4000))
  }, [dismiss])

  // API ổn định (push không đổi reference) → an toàn khi để trong dependency array.
  const api = useMemo(() => ({
    success: (m) => push('success', m),
    error: (m) => push('error', m),
    info: (m) => push('info', m),
    warn: (m) => push('warn', m),
  }), [push])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}
