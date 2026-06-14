import { useEffect, useState } from 'react'
import {
  clearExecutions,
  deleteExecution,
  getExecution,
  listExecutions,
} from '../api.js'
import { useImageViewer } from '../ImageViewerContext.jsx'
import { TrashIcon } from './icons.jsx'

const PAGE_SIZE = 8 // số bản ghi exec mỗi trang (paging server-side)

const STATUS_LABEL = {
  success: '✓ Thành công',
  error: '✗ Lỗi',
  stopped: '⏹ Đã dừng',
  running: '… Đang chạy',
}

function fmtDuration(ms) {
  if (ms == null) return '—'
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

// Lịch sử thực thi kiểu n8n cho 1 workflow: list (paging) + master-detail.
export default function ExecutionHistoryPanel({ workflowName }) {
  const { openViewer } = useImageViewer()
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
    if (!confirm('Xóa lần chạy này?')) return
    await deleteExecution(id)
    if (selected?.id === id) setSelected(null)
    reload()
  }

  const clearAll = async () => {
    if (!confirm(`Xóa toàn bộ lịch sử của "${workflowName}"?`)) return
    await clearExecutions(workflowName)
    setSelected(null)
    setPage(1)
    reload()
  }

  const pageCount = Math.max(1, Math.ceil(data.total / PAGE_SIZE))

  return (
    <div>
      <div className="exec-history-head">
        <span className="exec-subtitle">Lịch sử chạy · {data.total} bản ghi</span>
        {data.total > 0 && (
          <button className="btn ghost danger" onClick={clearAll}>
            <TrashIcon size={13} /> Xóa hết
          </button>
        )}
      </div>

      {loading && <div className="wf-browser-empty">Đang tải…</div>}
      {!loading && data.items.length === 0 && (
        <div className="wf-browser-empty">Workflow này chưa có lần chạy nào được ghi.</div>
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
                  {STATUS_LABEL[ex.status] || ex.status}
                </span>
                <span className="exec-mode">{ex.mode}</span>
              </div>
              <span className="exec-row-sub">{ex.started_at} · {fmtDuration(ex.duration_ms)}</span>
            </div>
            <button className="btn ghost danger" title="Xóa lần chạy"
              onClick={(e) => removeOne(e, ex.id)}>
              <TrashIcon size={13} />
            </button>
          </div>
        ))}
      </div>

      {pageCount > 1 && (
        <div className="wf-pager">
          <button className="btn ghost" disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}>‹ Trước</button>
          <span className="wf-pager-info">Trang {page}/{pageCount}</span>
          <button className="btn ghost" disabled={page >= pageCount}
            onClick={() => setPage((p) => p + 1)}>Sau ›</button>
        </div>
      )}

      {selected && <ExecDetail exec={selected} openViewer={openViewer} />}
    </div>
  )
}

// Chi tiết 1 lần chạy: ảnh kết quả + vòng harness + trạng thái node + lỗi.
function ExecDetail({ exec, openViewer }) {
  const [broken, setBroken] = useState(() => new Set()) // sha ảnh đã bị dọn khỏi cache
  const detail = exec.detail || {}
  const refs = detail.output_refs || []
  const nodes = detail.nodes || {}
  const harness = detail.harness || {}
  const iterations = harness.iterations || []

  const markBroken = (sha) => setBroken((s) => new Set(s).add(sha))

  return (
    <div className="exec-detail">
      {exec.error && <div className="exec-error-box">{exec.error}</div>}

      <div>
        <div className="exec-subtitle">Ảnh kết quả</div>
        {refs.length === 0 ? (
          <div className="exec-row-sub">Không có ảnh.</div>
        ) : (
          <div className="exec-images">
            {refs.map((sha) => (broken.has(sha) ? (
              <div className="exec-thumb-missing" key={sha}>Ảnh đã bị dọn khỏi cache</div>
            ) : (
              <img
                key={sha}
                className="exec-thumb"
                src={`/api/cache-image/${sha}`}
                alt="kết quả"
                onClick={() => openViewer({
                  src: `/api/cache-image/${sha}`, filename: `${sha.slice(0, 12)}.png`,
                })}
                onError={() => markBroken(sha)}
              />
            )))}
          </div>
        )}
      </div>

      {iterations.length > 0 && (
        <div>
          <div className="exec-subtitle">
            Harness{harness.best_score != null
              ? ` · best vòng ${(harness.best_iteration ?? 0) + 1} (điểm ${harness.best_score})`
              : ''}
          </div>
          {iterations.map((it) => (
            <div key={it.iteration} className={`exec-harness-row${it.passed ? ' passed' : ''}`}>
              <b>Vòng {(it.iteration ?? 0) + 1}: {it.score}{it.passed ? ' ✓' : ''}</b>
              {it.feedback && <span className="exec-harness-fb"> — {it.feedback}</span>}
            </div>
          ))}
        </div>
      )}

      {Object.keys(nodes).length > 0 && (
        <div>
          <div className="exec-subtitle">Trạng thái node</div>
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
