import { useEffect, useState } from 'react'
import {
  clearExecutions,
  deleteExecution,
  getExecution,
  listExecutions,
} from '../api.js'
import { useImageViewer } from '../ImageViewerContext.jsx'
import { useT } from '../i18n/use-t.js'
import { TrashIcon } from './icons.jsx'

const PAGE_SIZE = 8 // số bản ghi exec mỗi trang (paging server-side)

function fmtDuration(ms) {
  if (ms == null) return '—'
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

// Lịch sử thực thi kiểu n8n cho 1 workflow: list (paging) + master-detail.
export default function ExecutionHistoryPanel({ workflowName }) {
  const { openViewer } = useImageViewer()
  const { t } = useT()
  const [page, setPage] = useState(1)
  const [data, setData] = useState({ items: [], total: 0 })
  const [selected, setSelected] = useState(null) // bản ghi exec đầy đủ (detail)
  const [loading, setLoading] = useState(false)

  const reload = () => {
    setLoading(true)
    listExecutions(workflowName, { page, size: PAGE_SIZE })
      .then(setData)
      .catch(() => setData({ items: [], total: 0 }))
      .finally(() => setLoading(false))
  }

  // Lazy: chỉ fetch khi panel này được render (mở tab Lịch sử) / đổi trang / đổi workflow.
  useEffect(() => {
    setSelected(null)
    reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowName, page])

  const openDetail = async (id) => {
    try { setSelected(await getExecution(id)) } catch { /* bỏ qua lỗi tải detail */ }
  }

  const removeOne = async (e, id) => {
    e.stopPropagation()
    if (!confirm(t('history.confirmDeleteOne'))) return
    await deleteExecution(id)
    if (selected?.id === id) setSelected(null)
    reload()
  }

  const clearAll = async () => {
    if (!confirm(t('history.confirmClearAll', undefined, { name: workflowName }))) return
    await clearExecutions(workflowName)
    setSelected(null)
    setPage(1)
    reload()
  }

  const pageCount = Math.max(1, Math.ceil(data.total / PAGE_SIZE))

  return (
    <div>
      <div className="exec-history-head">
        <span className="exec-subtitle">{t('history.title', undefined, { total: data.total })}</span>
        {data.total > 0 && (
          <button className="btn ghost danger" onClick={clearAll}>
            <TrashIcon size={13} /> {t('history.clearAll')}
          </button>
        )}
      </div>

      {loading && <div className="wf-browser-empty">{t('history.loading')}</div>}
      {!loading && data.items.length === 0 && (
        <div className="wf-browser-empty">{t('history.empty')}</div>
      )}

      <div className="exec-list">
        {data.items.map((ex) => (
          <div
            key={ex.id}
            className={`exec-row${selected?.id === ex.id ? ' selected' : ''}`}
            onClick={() => openDetail(ex.id)}
          >
            <div className="exec-row-info">
              <div className="exec-row-top">
                <span className={`exec-badge ${ex.status}`}>
                  {t('history.status.' + ex.status, ex.status)}
                </span>
                <span className="exec-mode">{ex.mode}</span>
              </div>
              <span className="exec-row-sub">{ex.started_at} · {fmtDuration(ex.duration_ms)}</span>
            </div>
            <button className="btn ghost danger" title={t('history.deleteRowTitle')}
              onClick={(e) => removeOne(e, ex.id)}>
              <TrashIcon size={13} />
            </button>
          </div>
        ))}
      </div>

      {pageCount > 1 && (
        <div className="wf-pager">
          <button className="btn ghost" disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}>{t('history.prev')}</button>
          <span className="wf-pager-info">{t('history.page', undefined, { page, pageCount })}</span>
          <button className="btn ghost" disabled={page >= pageCount}
            onClick={() => setPage((p) => p + 1)}>{t('history.next')}</button>
        </div>
      )}

      {selected && <ExecDetail exec={selected} openViewer={openViewer} />}
    </div>
  )
}

// Chi tiết 1 lần chạy: ảnh kết quả + trạng thái node + lỗi.
function ExecDetail({ exec, openViewer }) {
  const { t } = useT()
  const [broken, setBroken] = useState(() => new Set()) // sha ảnh đã bị dọn khỏi cache
  const detail = exec.detail || {}
  const refs = detail.output_refs || []
  const nodes = detail.nodes || {}

  const markBroken = (sha) => setBroken((s) => new Set(s).add(sha))

  return (
    <div className="exec-detail">
      {exec.error && <div className="exec-error-box">{exec.error}</div>}

      <div>
        <div className="exec-subtitle">{t('history.detail.imagesTitle')}</div>
        {refs.length === 0 ? (
          <div className="exec-row-sub">{t('history.detail.noImages')}</div>
        ) : (
          <div className="exec-images">
            {refs.map((sha) => (broken.has(sha) ? (
              <div className="exec-thumb-missing" key={sha}>{t('history.detail.imageMissing')}</div>
            ) : (
              <img
                key={sha}
                className="exec-thumb"
                src={`/api/cache-image/${sha}`}
                alt={t('history.detail.imageAlt')}
                onClick={() => openViewer({
                  src: `/api/cache-image/${sha}`, filename: `${sha.slice(0, 12)}.png`,
                })}
                onError={() => markBroken(sha)}
              />
            )))}
          </div>
        )}
      </div>

      {Object.keys(nodes).length > 0 && (
        <div>
          <div className="exec-subtitle">{t('history.detail.nodesTitle')}</div>
          <div className="exec-nodes">
            {Object.entries(nodes).map(([id, st]) => (
              <div className="exec-node-row" key={id}>
                <span className={`exec-node-dot ${st}`} />
                <span className="exec-node-id">{id}</span>
                <span>{st}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
