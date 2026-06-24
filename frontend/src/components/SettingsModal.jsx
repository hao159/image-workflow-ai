import { useState } from 'react'
import { GearIcon, XIcon } from './icons.jsx'
import SettingsAppearanceTab from './settings-appearance-tab.jsx'
import SettingsModelTab from './settings-model-tab.jsx'
import { useT } from '../i18n/use-t.js'

// Tab values; labels resolved via t() at render time so they switch language live.
const TAB_VALUES = ['appearance', 'model']

// Khung modal Cài đặt: thanh tab Giao diện | Model. Mặc định mở tab Model (khớp
// hành vi cũ "mở ra thấy bảng cấu hình"). Cả 2 tab giữ mount (display toggle) để
// đổi tab không mất dữ liệu form đang nhập ở tab Model.
export default function SettingsModal({ onClose, onChanged }) {
  const [activeTab, setActiveTab] = useState('model')
  const { t } = useT()

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title"><GearIcon size={16} /> {t('settings.title')}</span>
          <button className="btn ghost" onClick={onClose}><XIcon size={15} /></button>
        </div>

        <div className="settings-tabs" role="tablist">
          {TAB_VALUES.map((value) => (
            <button
              key={value}
              className={`settings-tab-btn${activeTab === value ? ' active' : ''}`}
              onClick={() => setActiveTab(value)}
            >
              {t(`settings.tab.${value}`)}
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
