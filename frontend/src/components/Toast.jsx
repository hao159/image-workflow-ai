import { AlertIcon, CheckIcon, XIcon } from './icons.jsx'
import { useT } from '../i18n/use-t.js'

// Icon theo loại toast: success = dấu tích; error/warn/info = cảnh báo (tái dùng
// icon đã có, không thêm asset). Màu do CSS đặt theo class toast-<kind>.
function ToastIcon({ kind }) {
  return kind === 'success' ? <CheckIcon size={15} /> : <AlertIcon size={15} />
}

// Ngăn xếp toast (góc trên-giữa). Mỗi toast tự ẩn theo timer trong ToastContext;
// bấm ✕ để đóng sớm. Không render gì khi rỗng (giữ DOM sạch).
export default function ToastStack({ toasts, onDismiss }) {
  const { t } = useT()
  if (!toasts.length) return null
  return (
    <div className="toast-stack" role="region" aria-label={t('toast.regionLabel')}>
      {toasts.map((t0) => (
        <div key={t0.id} className={`toast toast-${t0.kind}`} role="status">
          <span className="toast-icon"><ToastIcon kind={t0.kind} /></span>
          <span className="toast-msg">{t0.msg}</span>
          <button className="toast-close" onClick={() => onDismiss(t0.id)} aria-label={t('toast.closeLabel')}>
            <XIcon size={13} />
          </button>
        </div>
      ))}
    </div>
  )
}
