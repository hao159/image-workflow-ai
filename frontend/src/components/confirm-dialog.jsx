import { useEffect } from 'react'
import { useT } from '../i18n/use-t.js'

// Popup xác nhận dùng chung (thay window.confirm). Esc / backdrop / Hủy = hủy.
export default function ConfirmDialog({
  message,
  confirmLabel,
  danger = true,
  onConfirm,
  onCancel,
}) {
  const { t } = useT()
  const label = confirmLabel ?? t('dialog.defaultConfirm')

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
          <button className="btn ghost" onClick={onCancel}>{t('dialog.cancel')}</button>
          <button className={`btn${danger ? ' danger' : ''}`} onClick={onConfirm}>
            {label}
          </button>
        </div>
      </div>
    </div>
  )
}
