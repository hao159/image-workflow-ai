import { useCallback, useEffect, useMemo, useState } from 'react'
import { ImageIcon, TrashIcon, XIcon } from './icons.jsx'
import { listUploads, listOutputs, deleteUpload, deleteOutput } from '../api.js'
import { useImageViewer } from '../ImageViewerContext.jsx'
import { useToast } from '../ToastContext.jsx'
import ConfirmDialog from './confirm-dialog.jsx'
import { useT } from '../i18n/use-t.js'

const PAGE_SIZE = 12 // số thumbnail mỗi trang (paging client-side)

// Cấu hình 2 tab: key + hàm list/delete tương ứng.
const TABS = {
  uploads: { list: listUploads, del: deleteUpload },
  outputs: { list: listOutputs, del: deleteOutput },
}

// Modal thư viện ảnh: 2 tab (uploads/outputs), lưới thumbnail có paging,
// click ảnh → lightbox dùng chung, xóa qua popup xác nhận (ConfirmDialog).
export default function ImageLibraryModal({ onClose }) {
  const { t } = useT()
  const [tab, setTab] = useState('uploads')
  const [items, setItems] = useState([])
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [pending, setPending] = useState(null) // { name } chờ xác nhận xóa
  const { openViewer } = useImageViewer()
  const toast = useToast()

  const refresh = useCallback(async (which) => {
    setLoading(true)
    try {
      setItems(await TABS[which].list())
    } catch (e) {
      toast.error(e.message)
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [toast])

  // Đổi tab → reset trang + nạp danh sách tab đó.
  useEffect(() => { setPage(0); refresh(tab) }, [tab, refresh])

  // Esc đóng modal (trừ khi đang mở popup xác nhận — Esc đó để hủy popup).
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape' && !pending) onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, pending])

  const pageCount = Math.max(1, Math.ceil(items.length / PAGE_SIZE))
  const safePage = Math.min(page, pageCount - 1)
  const rows = useMemo(
    () => items.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE),
    [items, safePage],
  )

  const doDelete = async () => {
    const name = pending.name
    setPending(null)
    try {
      await TABS[tab].del(name)
      toast.success(t('library.toastDeleted'))
      refresh(tab)
    } catch (e) {
      toast.error(e.message)
    }
  }

  const TAB_LABELS = {
    uploads: t('library.tabUploads'),
    outputs: t('library.tabOutputs'),
  }

  return (
    <>
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal img-library" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <span className="modal-title"><ImageIcon size={16} /> {t('library.title')}</span>
            <button className="btn ghost" onClick={onClose}><XIcon size={15} /></button>
          </div>

          <div className="wf-browser-tabs" role="tablist">
            {Object.keys(TABS).map((key) => (
              <button
                key={key}
                className={`wf-tab${tab === key ? ' active' : ''}`}
                onClick={() => setTab(key)}
              >
                {TAB_LABELS[key]}
              </button>
            ))}
          </div>

          {tab === 'uploads' && (
            <div className="img-library-note">
              {t('library.uploadNote')}
            </div>
          )}

          <div className="img-library-body">
            {loading ? (
              <div className="wf-browser-empty">{t('library.loading')}</div>
            ) : items.length === 0 ? (
              <div className="wf-browser-empty">{t('library.empty')}</div>
            ) : (
              <div className="img-grid">
                {rows.map((it) => (
                  <div className="img-card" key={it.name}>
                    <button
                      className="img-card-thumb"
                      title={t('library.viewTitle')}
                      onClick={() => openViewer({ src: it.url, filename: it.name })}
                    >
                      <img src={it.url} alt={it.name} loading="lazy" />
                    </button>
                    <div className="img-card-foot">
                      <span className="img-card-name" title={it.name}>{it.name}</span>
                      <button
                        className="btn ghost danger"
                        title={t('library.deleteTitle')}
                        onClick={() => setPending({ name: it.name })}
                      >
                        <TrashIcon size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {pageCount > 1 && (
              <div className="wf-pager">
                <button className="btn ghost" disabled={safePage === 0}
                  onClick={() => setPage(safePage - 1)}>{t('library.prevPage')}</button>
                <span className="wf-pager-info">{t('library.page', null, { p: safePage + 1, n: pageCount })}</span>
                <button className="btn ghost" disabled={safePage >= pageCount - 1}
                  onClick={() => setPage(safePage + 1)}>{t('library.nextPage')}</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {pending && (
        <ConfirmDialog
          message={t('library.confirmDelete', null, { name: pending.name })}
          onConfirm={doDelete}
          onCancel={() => setPending(null)}
        />
      )}
    </>
  )
}
