import { useEffect } from 'react'
import { DownloadIcon, ExternalLinkIcon, XIcon } from './icons.jsx'
import { useT } from '../i18n/use-t.js'

// Lightbox xem ảnh full-res: click nền / Esc / nút X để đóng; tải ảnh gốc; mở tab mới.
// `view` = { src, filename }. src luôn là URL ảnh GỐC (không phải thumbnail preview).
export default function ImageViewerModal({ view, onClose }) {
  const { t } = useT()
  const { src, filename } = view

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden' // khóa scroll nền khi mở
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [onClose])

  return (
    <div className="img-viewer-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="img-viewer-actions" onClick={(e) => e.stopPropagation()}>
        <a
          className="img-viewer-btn"
          href={src}
          download={filename || ''}
          title={t('imageViewer.downloadTitle')}
        >
          <DownloadIcon size={15} /> {t('imageViewer.downloadLabel')}
        </a>
        <button
          type="button"
          className="img-viewer-btn icon-only"
          title={t('imageViewer.openTabTitle')}
          onClick={() => window.open(src, '_blank', 'noopener')}
        >
          <ExternalLinkIcon size={15} />
        </button>
        <button type="button" className="img-viewer-btn icon-only" title={t('imageViewer.closeTitle')} onClick={onClose}>
          <XIcon size={17} />
        </button>
      </div>
      <img
        className="img-viewer-img"
        src={src}
        alt={t('imageViewer.imgAlt')}
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  )
}
