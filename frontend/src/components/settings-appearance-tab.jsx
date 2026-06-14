import { useState } from 'react'
import {
  getRunEffect,
  setRunEffect,
  RUN_EFFECT_OPTIONS,
  getThemeSetting,
  setThemeSetting,
  THEME_OPTIONS,
} from '../ui-settings.js'

// Tab "Giao diện": chọn nền sáng/tối (áp ngay) + hiệu ứng node đang chạy.
export default function SettingsAppearanceTab() {
  const [runEffect, setRunEffectState] = useState(getRunEffect)
  const [theme, setThemeState] = useState(getThemeSetting)

  return (
    <div className="settings-section">
      <div className="settings-row">
        <span>Nền sáng/tối</span>
        <div className="theme-seg" role="group" aria-label="Chọn nền sáng/tối">
          {THEME_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              className={`theme-seg-btn${theme === o.value ? ' active' : ''}`}
              onClick={() => {
                setThemeSetting(o.value)
                setThemeState(o.value)
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>
      <label className="settings-row">
        <span>Hiệu ứng node đang chạy</span>
        <select
          value={runEffect}
          onChange={(e) => {
            setRunEffect(e.target.value)
            setRunEffectState(e.target.value)
          }}
        >
          {RUN_EFFECT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </label>
    </div>
  )
}
