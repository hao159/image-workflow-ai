import { useEffect, useMemo, useRef, useState } from 'react'
import { categoryStyle } from '../node-category-styles.js'
import { SearchIcon } from './icons.jsx'

const CATEGORY_ORDER = ['Đầu vào', 'AI', 'Biến đổi', 'Đầu ra', 'Khác']
const PANEL_W = 264
const PANEL_MAX_H = 360

// Menu nổi khi user kéo dây thả ra khoảng trống: liệt kê các node TƯƠNG THÍCH
// (có cổng cùng dtype để nối được), chọn 1 node → tạo node + tự nối dây.
export default function ConnectNodeMenu({ screenX, screenY, items, onPick, onClose }) {
  const [filter, setFilter] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const q = filter.trim().toLowerCase()
  const byCategory = useMemo(() => {
    const groups = {}
    for (const meta of items) {
      const matched =
        !q ||
        meta.title.toLowerCase().includes(q) ||
        (meta.description || '').toLowerCase().includes(q)
      if (matched) (groups[meta.category] ??= []).push(meta)
    }
    return groups
  }, [items, q])
  const categories = CATEGORY_ORDER.filter((c) => byCategory[c])

  // Giữ menu trong khung nhìn (không tràn mép phải/dưới màn hình).
  const left = Math.min(screenX, window.innerWidth - PANEL_W - 8)
  const top = Math.min(screenY, window.innerHeight - PANEL_MAX_H - 8)

  return (
    <>
      <div className="connect-menu-overlay" onClick={onClose} onContextMenu={(e) => e.preventDefault()} />
      <div className="connect-menu" style={{ left: Math.max(8, left), top: Math.max(8, top) }}>
        <div className="connect-menu-search">
          <SearchIcon size={13} className="connect-menu-search-icon" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Tạo node nối tiếp..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <div className="connect-menu-scroll">
          {categories.length === 0 && (
            <div className="connect-menu-empty">Không có node tương thích.</div>
          )}
          {categories.map((cat) => {
            const { Icon, color } = categoryStyle(cat)
            return (
              <div key={cat} className="connect-menu-group" style={{ '--cat': color }}>
                <div className="connect-menu-group-title">{cat}</div>
                {byCategory[cat].map((meta) => (
                  <button
                    key={meta.type}
                    type="button"
                    className="connect-menu-item"
                    title={meta.description}
                    onClick={() => onPick(meta.type)}
                  >
                    <span className="connect-menu-item-icon"><Icon size={13} /></span>
                    <span className="connect-menu-item-name">{meta.title}</span>
                  </button>
                ))}
              </div>
            )
          })}
        </div>
      </div>
    </>
  )
}
