import { useState } from 'react'
import { categoryStyle } from '../node-category-styles.js'
import { PlusIcon, SearchIcon } from './icons.jsx'

const CATEGORY_ORDER = ['Đầu vào', 'AI', 'Biến đổi', 'Đầu ra', 'Khác']

export default function Palette({ nodeTypes, onAdd }) {
  const [filter, setFilter] = useState('')
  const q = filter.trim().toLowerCase()

  const byCategory = {}
  for (const meta of nodeTypes) {
    const matched =
      !q ||
      meta.title.toLowerCase().includes(q) ||
      (meta.description || '').toLowerCase().includes(q)
    if (matched) (byCategory[meta.category] ??= []).push(meta)
  }
  const categories = CATEGORY_ORDER.filter((c) => byCategory[c])

  return (
    <aside className="palette">
      <div className="palette-brand">
        <img className="palette-logo" src="/image-workflow-logo.svg" alt="Image Workflow" width="34" height="34" />
        <div>
          <h1 className="palette-title">Image Workflow</h1>
          <p className="palette-sub">Node-based AI editor</p>
        </div>
      </div>

      <div className="palette-search">
        <SearchIcon size={13} className="palette-search-icon" />
        <input
          type="text"
          placeholder="Tìm node..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>
      <p className="palette-hint">Bấm để nối tiếp vào flow, hoặc kéo thả vào vị trí tùy ý</p>

      <div className="palette-scroll">
        {categories.length === 0 && (
          <div className="palette-empty">
            {nodeTypes.length === 0 ? 'Đang chờ backend...' : 'Không tìm thấy node nào.'}
          </div>
        )}
        {categories.map((cat) => {
          const { Icon, color } = categoryStyle(cat)
          return (
            <div key={cat} className="palette-group" style={{ '--cat': color }}>
              <div className="palette-group-title">{cat}</div>
              {byCategory[cat].map((meta) => (
                <div
                  key={meta.type}
                  className="palette-item"
                  draggable
                  title={meta.description}
                  onClick={() => onAdd?.(meta.type)}
                  onDragStart={(e) => {
                    e.dataTransfer.setData('application/x-node-type', meta.type)
                    e.dataTransfer.effectAllowed = 'move'
                  }}
                >
                  <span className="palette-item-icon"><Icon size={13} /></span>
                  <span className="palette-item-name">{meta.title}</span>
                  <span className="palette-item-add"><PlusIcon size={13} /></span>
                </div>
              ))}
            </div>
          )
        })}
      </div>
    </aside>
  )
}
