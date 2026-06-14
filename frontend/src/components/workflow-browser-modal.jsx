import { useEffect, useMemo, useState } from 'react'
import { FolderIcon, TrashIcon, XIcon } from './icons.jsx'
import ExecutionHistoryPanel from './execution-history-panel.jsx'

const PAGE_SIZE = 8 // số workflow mỗi trang (paging client-side)

// Modal giữa màn hình thay cho dropdown Workflows cũ: 2 tab
//  - Danh sách: workflow đã lưu (có paging) + Tải/Xóa từng dòng.
//  - Lịch sử: các lần chạy của workflow đang chọn (kiểu n8n) — Phase 3.
export default function WorkflowBrowserModal({ workflows, onLoad, onDelete, onClose }) {
  const [tab, setTab] = useState('list') // 'list' | 'history'
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState(null) // tên workflow để xem lịch sử

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const pageCount = Math.max(1, Math.ceil(workflows.length / PAGE_SIZE))
  const safePage = Math.min(page, pageCount - 1)
  const rows = useMemo(
    () => workflows.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE),
    [workflows, safePage],
  )

  const openHistory = (name) => { setSelected(name); setTab('history') }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal wf-browser" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title"><FolderIcon size={16} /> Mở workflow</span>
          <button className="btn ghost" onClick={onClose}><XIcon size={15} /></button>
        </div>

        <div className="wf-browser-tabs" role="tablist">
          <button
            className={`wf-tab${tab === 'list' ? ' active' : ''}`}
            onClick={() => setTab('list')}
          >
            Danh sách
          </button>
          <button
            className={`wf-tab${tab === 'history' ? ' active' : ''}`}
            onClick={() => setTab('history')}
            disabled={!selected}
            title={selected ? '' : 'Chọn 1 workflow ở tab Danh sách trước'}
          >
            Lịch sử{selected ? `: ${selected}` : ''}
          </button>
        </div>

        {tab === 'list' ? (
          <div className="wf-browser-body">
            {workflows.length === 0 && (
              <div className="wf-browser-empty">Chưa có workflow nào.</div>
            )}
            {rows.map((wf) => (
              <div
                className={`wf-row${selected === wf.name ? ' selected' : ''}`}
                key={wf.name}
                onClick={() => setSelected(wf.name)}
              >
                <button
                  className="wf-row-main"
                  title="Tải workflow vào canvas"
                  onClick={(e) => { e.stopPropagation(); onLoad(wf.name); onClose() }}
                >
                  <span className="wf-row-name">{wf.name}</span>
                  <span className="wf-row-date">{wf.updated_at}</span>
                </button>
                <button
                  className="btn ghost"
                  title="Xem lịch sử chạy"
                  onClick={(e) => { e.stopPropagation(); openHistory(wf.name) }}
                >
                  🕘
                </button>
                <button
                  className="btn ghost danger"
                  title="Xóa workflow"
                  onClick={(e) => { e.stopPropagation(); onDelete(wf.name) }}
                >
                  <TrashIcon size={14} />
                </button>
              </div>
            ))}
            {pageCount > 1 && (
              <div className="wf-pager">
                <button className="btn ghost" disabled={safePage === 0}
                  onClick={() => setPage(safePage - 1)}>‹ Trước</button>
                <span className="wf-pager-info">Trang {safePage + 1}/{pageCount}</span>
                <button className="btn ghost" disabled={safePage >= pageCount - 1}
                  onClick={() => setPage(safePage + 1)}>Sau ›</button>
              </div>
            )}
          </div>
        ) : (
          <div className="wf-browser-body">
            {selected
              ? <ExecutionHistoryPanel workflowName={selected} />
              : <div className="wf-browser-empty">Chọn 1 workflow để xem lịch sử.</div>}
          </div>
        )}
      </div>
    </div>
  )
}
