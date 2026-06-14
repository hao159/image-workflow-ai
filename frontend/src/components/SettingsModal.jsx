import { useState } from 'react'
import { GearIcon, XIcon } from './icons.jsx'
import SettingsAppearanceTab from './settings-appearance-tab.jsx'
import SettingsModelTab from './settings-model-tab.jsx'

const TABS = [
  { value: 'appearance', label: 'Giao diện' },
  { value: 'model', label: 'Model' },
]

// Khung modal Cài đặt: thanh tab Giao diện | Model. Mặc định mở tab Model (khớp
// hành vi cũ "mở ra thấy bảng cấu hình"). Cả 2 tab giữ mount (display toggle) để
// đổi tab không mất dữ liệu form đang nhập ở tab Model.
export default function SettingsModal({ onClose, onChanged }) {
  const [activeTab, setActiveTab] = useState('model')

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title"><GearIcon size={16} /> Cài đặt</span>
          <button className="btn ghost" onClick={onClose}><XIcon size={15} /></button>
        </div>

        <div className="settings-tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.value}
              className={`settings-tab-btn${activeTab === t.value ? ' active' : ''}`}
              onClick={() => setActiveTab(t.value)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div style={{ display: activeTab === 'appearance' ? 'block' : 'none' }}>
          <SettingsAppearanceTab />
        </div>
        <div style={{ display: activeTab === 'model' ? 'block' : 'none' }}>
          <SettingsModelTab onChanged={onChanged} />
        </div>
      </div>
    </div>
  )
}
