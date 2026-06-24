import { useEffect, useState } from 'react'
import { listProviderModels } from '../api.js'
import { useT } from '../i18n/use-t.js'

// Sentinel cho option "Nhập tay" trong <select> (gõ tên model tự do).
const MANUAL = '__manual__'

const dedupe = (...lists) => [...new Set(lists.flat().filter(Boolean))]

// Gợi ý năng lực model cho dropdown (hiển thị-only, không đổi value lưu).
// codex = host tool gen ảnh; tên chứa image/dall/imagen = model ảnh; còn lại coi
// là text/vision. Heuristic — chỉ để nhìn phát biết.
// Returns a catalog key so callers can translate at render time.
function capabilityTagKey(provider, model) {
  if (!model) return ''
  if (provider === 'codex') return 'model.capabilityImage'
  const m = model.toLowerCase()
  if (m.includes('image') || m.includes('dall') || m.includes('imagen')) return 'model.capabilityImage'
  return 'model.capabilityText'
}

/**
 * Dropdown model hybrid: list static curated + model live (nút Tải từ API) + Nhập tay.
 * `value` (chuỗi model) là nguồn sự thật duy nhất; component báo lên qua onChange.
 */
export default function ModelField({ provider, configId, apiKey, baseUrl, value, onChange, placeholder }) {
  const [options, setOptions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [manual, setManual] = useState(false)
  // lang drives re-render so capability tags switch language live
  const { t, lang } = useT()

  const optionLabel = (prov, model) => {
    const tagKey = capabilityTagKey(prov, model)
    return tagKey ? `${model} (${t(tagKey)})` : model
  }

  // Đổi provider → nạp static (không chạm mạng). value lạ → rơi vào Nhập tay.
  useEffect(() => {
    let cancelled = false
    setError('')
    listProviderModels(provider, { refresh: false })
      .then((res) => {
        if (cancelled) return
        const opts = dedupe(res.static, res.live)
        setOptions(opts)
        setManual(!!value && !opts.includes(value))
      })
      .catch(() => {
        if (cancelled) return
        setOptions([])
        setManual(!!value)
      })
    return () => { cancelled = true }
    // value cố tình KHÔNG nằm trong deps: chỉ reset list khi đổi provider.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider])

  const refresh = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await listProviderModels(provider, { refresh: true, configId, apiKey, baseUrl })
      setOptions(dedupe(res.static, res.live))
      if (res.error) setError(res.error)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const onSelect = (v) => {
    if (v === MANUAL) {
      setManual(true)
      return
    }
    setManual(false)
    onChange(v)
  }

  const selectValue = manual ? MANUAL : (value && options.includes(value) ? value : '')

  return (
    <label>
      <span>{t('model.fieldModel')}</span>
      <div className="model-field">
        <select value={selectValue} onChange={(e) => onSelect(e.target.value)}>
          <option value="">{placeholder || t('model.fieldModelDefault')}</option>
          {options.map((m) => (
            <option key={m} value={m}>{optionLabel(provider, m)}</option>
          ))}
          <option value={MANUAL}>{t('model.manualEntry')}</option>
        </select>
        <button type="button" className="btn ghost" disabled={loading} onClick={refresh}
                title={t('model.loadModelsTitle')}>
          {loading ? '…' : '⟳'}
        </button>
      </div>
      {manual && (
        <input
          type="text"
          placeholder={placeholder || t('model.fieldModelPlaceholderManual')}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
      {error && <div className="model-field-error">{error}</div>}
    </label>
  )
}
