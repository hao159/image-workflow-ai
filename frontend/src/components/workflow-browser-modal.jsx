import { useEffect, useMemo, useState } from 'react'
import { FolderIcon, TrashIcon, XIcon } from './icons.jsx'
import ExecutionHistoryPanel from './execution-history-panel.jsx'
import { useT } from '../i18n/use-t.js'

const PAGE_SIZE = 8 // number of workflows per page (client-side paging)

// Full-screen modal replacing the old Workflows dropdown: 2 tabs
//  - List: saved workflows (with paging) + Load/Delete per row.
//  - History: run history for the selected workflow (n8n-style) — Phase 3.
export default function WorkflowBrowserModal({ workflows, onLoad, onDelete, onClose }) {
  const { t } = useT()
  const [tab, setTab] = useState('list') // 'list' | 'history'
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState(null) // workflow name for viewing history

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
          <span className="modal-title"><FolderIcon size={16} /> {t('workflowBrowser.title')}</span>
          <button className="btn ghost" onClick={onClose}><XIcon size={15} /></button>
        </div>

        <div className="wf-browser-tabs" role="tablist">
          <button
            className={`wf-tab${tab === 'list' ? ' active' : ''}`}
            onClick={() => setTab('list')}
          >
            {t('workflowBrowser.tabList')}
          </button>
          <button
            className={`wf-tab${tab === 'history' ? ' active' : ''}`}
            onClick={() => setTab('history')}
            disabled={!selected}
            title={selected ? '' : t('workflowBrowser.tabHistoryDisabledTitle')}
          >
            {selected
              ? t('workflowBrowser.tabHistorySelected', undefined, { name: selected })
              : t('workflowBrowser.tabHistory')}
          </button>
        </div>

        {tab === 'list' ? (
          <div className="wf-browser-body">
            {workflows.length === 0 && (
              <div className="wf-browser-empty">{t('workflowBrowser.empty')}</div>
            )}
            {rows.map((wf) => (
              <div
                className={`wf-row${selected === wf.name ? ' selected' : ''}`}
                key={wf.name}
                onClick={() => setSelected(wf.name)}
              >
                <button
                  className="wf-row-main"
                  title={t('workflowBrowser.loadTitle')}
                  onClick={(e) => { e.stopPropagation(); onLoad(wf.name); onClose() }}
                >
                  <span className="wf-row-name">{wf.name}</span>
                  <span className="wf-row-date">{wf.updated_at}</span>
                </button>
                <button
                  className="btn ghost"
                  title={t('workflowBrowser.historyTitle')}
                  onClick={(e) => { e.stopPropagation(); openHistory(wf.name) }}
                >
                  🕘
                </button>
                <button
                  className="btn ghost danger"
                  title={t('workflowBrowser.deleteTitle')}
                  onClick={(e) => { e.stopPropagation(); onDelete(wf.name) }}
                >
                  <TrashIcon size={14} />
                </button>
              </div>
            ))}
            {pageCount > 1 && (
              <div className="wf-pager">
                <button className="btn ghost" disabled={safePage === 0}
                  onClick={() => setPage(safePage - 1)}>{t('workflowBrowser.prev')}</button>
                <span className="wf-pager-info">{t('workflowBrowser.page', undefined, { p: safePage + 1, n: pageCount })}</span>
                <button className="btn ghost" disabled={safePage >= pageCount - 1}
                  onClick={() => setPage(safePage + 1)}>{t('workflowBrowser.next')}</button>
              </div>
            )}
          </div>
        ) : (
          <div className="wf-browser-body">
            {selected
              ? <ExecutionHistoryPanel workflowName={selected} />
              : <div className="wf-browser-empty">{t('workflowBrowser.emptyHistory')}</div>}
          </div>
        )}
      </div>
    </div>
  )
}
