import { useEffect } from 'react'

// Popup xác nhận dùng chung (thay window.confirm). Esc / backdrop / Hủy = hủy.
export default function ConfirmDialog({
  message,
  confirmLabel = 'Xóa',
  danger = true,
  onConfirm,
  onCancel,
}) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onCancel() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel])

  return (
    <div className="modal-backdrop confirm-backdrop" onClick={onCancel}>
      <div
        className="confirm-dialog"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="confirm-msg">{message}</div>
        <div className="confirm-actions">
          <button className="btn ghost" onClick={onCancel}>Hủy</button>
          <button className={`btn${danger ? ' danger' : ''}`} onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
