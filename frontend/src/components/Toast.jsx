import { AlertIcon, CheckIcon, XIcon } from './icons.jsx'

// Icon theo loại toast: success = dấu tích; error/warn/info = cảnh báo (tái dùng
// icon đã có, không thêm asset). Màu do CSS đặt theo class toast-<kind>.
function ToastIcon({ kind }) {
  return kind === 'success' ? <CheckIcon size={15} /> : <AlertIcon size={15} />
}

// Ngăn xếp toast (góc trên-giữa). Mỗi toast tự ẩn theo timer trong ToastContext;
// bấm ✕ để đóng sớm. Không render gì khi rỗng (giữ DOM sạch).
export default function ToastStack({ toasts, onDismiss }) {
  if (!toasts.length) return null
  return (
    <div className="toast-stack" role="region" aria-label="Thông báo">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`} role="status">
          <span className="toast-icon"><ToastIcon kind={t.kind} /></span>
          <span className="toast-msg">{t.msg}</span>
          <button className="toast-close" onClick={() => onDismiss(t.id)} aria-label="Đóng">
            <XIcon size={13} />
          </button>
        </div>
      ))}
    </div>
  )
}
