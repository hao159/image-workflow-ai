import { useEffect, useState } from 'react'
import {
  deleteModelConfig,
  getOpenAIOAuthStatus,
  listModelConfigs,
  saveModelConfig,
  startOpenAIOAuth,
} from '../api.js'
import { PlusIcon, SaveIcon, XIcon } from './icons.jsx'
import ModelField from './model-field.jsx'

const PROVIDERS = [
  { value: 'gemini', label: 'Google Gemini', defaultModel: 'gemini-2.5-flash-image' },
  { value: 'openai', label: 'OpenAI (API key)', defaultModel: 'gpt-image-1' },
  { value: 'codex', label: 'OpenAI (đăng nhập ChatGPT)', defaultModel: 'gpt-5.5' },
]

const EMPTY_FORM = { id: null, name: '', provider: 'gemini', api_key: '', model: '', base_url: '' }

// Tab "Model": bảng cấu hình + form thêm/sửa + khối đăng nhập OpenAI (codex).
export default function SettingsModelTab({ onChanged }) {
  const [configs, setConfigs] = useState([])
  const [form, setForm] = useState(EMPTY_FORM)
  const [formOpen, setFormOpen] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [saving, setSaving] = useState(false)
  // Trạng thái đăng nhập OpenAI (Codex OAuth)
  const [oauthStatus, setOauthStatus] = useState(null)
  const [loggingIn, setLoggingIn] = useState(false)

  const refresh = () => listModelConfigs().then(setConfigs).catch((e) => setErrorMsg(e.message))
  const refreshOauth = () => getOpenAIOAuthStatus().then(setOauthStatus).catch(() => setOauthStatus(null))

  useEffect(() => {
    refresh()
    refreshOauth()
  }, [])

  const login = async () => {
    setErrorMsg('')
    setLoggingIn(true)
    try {
      const st = await startOpenAIOAuth()
      setOauthStatus(st)
    } catch (err) {
      setErrorMsg(err.message)
    } finally {
      setLoggingIn(false)
    }
  }

  const set = (name, value) => setForm((f) => ({ ...f, [name]: value }))
  const editing = form.id !== null
  const providerMeta = PROVIDERS.find((p) => p.value === form.provider)

  // Mở popup thêm mới (form trống) / sửa (đổ dữ liệu config, ẩn api_key cũ).
  const openAdd = () => {
    setForm(EMPTY_FORM)
    setErrorMsg('')
    setFormOpen(true)
  }
  const openEdit = (cfg) => {
    setForm({ ...cfg, api_key: '' })
    setErrorMsg('')
    setFormOpen(true)
  }
  const closeForm = () => {
    setForm(EMPTY_FORM)
    setErrorMsg('')
    setFormOpen(false)
  }

  const submit = async (e) => {
    e.preventDefault()
    setErrorMsg('')
    setSaving(true)
    try {
      await saveModelConfig(form)
      setForm(EMPTY_FORM)
      setFormOpen(false)
      await refresh()
      onChanged?.()
    } catch (err) {
      setErrorMsg(err.message)
    } finally {
      setSaving(false)
    }
  }

  const remove = async (cfg) => {
    if (!confirm(`Xóa cấu hình "${cfg.name}"?`)) return
    try {
      await deleteModelConfig(cfg.id)
      if (form.id === cfg.id) closeForm()
      await refresh()
      onChanged?.()
    } catch (err) {
      setErrorMsg(err.message)
    }
  }

  return (
    <>
      <p className="modal-hint">
        Tạo nhiều cấu hình với tên riêng (vd "Google - Gemini 2", "Google - Gemini 3")
        rồi chọn theo tên trong node Tạo/Sửa ảnh.
      </p>

      <div className="config-section-head">
        <span className="settings-section-title">Cấu hình model</span>
        <button className="btn primary" type="button" onClick={openAdd}>
          <PlusIcon size={13} /> Thêm cấu hình
        </button>
      </div>

      {configs.length > 0 ? (
        <table className="config-table">
          <thead>
            <tr><th>Tên</th><th>Provider</th><th>Model</th><th>API key</th><th></th></tr>
          </thead>
          <tbody>
            {configs.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{PROVIDERS.find((p) => p.value === c.provider)?.label || c.provider}</td>
                <td>{c.model || <span className="dim">mặc định</span>}</td>
                <td>{c.api_key_preview || <span className="dim">—</span>}</td>
                <td className="config-actions">
                  <button className="btn ghost" onClick={() => openEdit(c)}>Sửa</button>
                  <button className="btn ghost danger" onClick={() => remove(c)}>Xóa</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="config-empty">Chưa có cấu hình nào. Bấm "Thêm cấu hình" để tạo mới.</p>
      )}

      {formOpen && (
      <div className="modal-backdrop config-modal-backdrop" onClick={closeForm}>
      <div className="modal config-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">{editing ? `Sửa "${form.name}"` : 'Thêm cấu hình mới'}</span>
          <button className="btn ghost" type="button" onClick={closeForm}><XIcon size={15} /></button>
        </div>
        <form className="config-form in-modal" onSubmit={submit}>
        <label>
          <span>Tên cấu hình</span>
          <input
            type="text"
            required
            placeholder="vd: Google - Gemini 3"
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
          />
        </label>
        <label>
          <span>Provider</span>
          <select value={form.provider} onChange={(e) => set('provider', e.target.value)}>
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </label>
        {form.provider !== 'codex' && (
          <label>
            <span>API key</span>
            <input
              type="password"
              placeholder={editing ? 'để trống = giữ key hiện tại' : 'dán API key vào đây'}
              required={!editing}
              value={form.api_key}
              onChange={(e) => set('api_key', e.target.value)}
            />
          </label>
        )}
        {form.provider === 'codex' && (
          <div className="oauth-box">
            {oauthStatus?.logged_in ? (
              <div className="oauth-status ok">
                ✓ Đã đăng nhập ChatGPT
                {oauthStatus.account_id && <span className="dim"> (tài khoản {oauthStatus.account_id.slice(0, 8)}…)</span>}
                {oauthStatus.expired && <div className="oauth-hint">Phiên đã hết hạn — sẽ tự làm mới, hoặc đăng nhập lại nếu lỗi.</div>}
              </div>
            ) : (
              <div className="oauth-status">Chưa đăng nhập ChatGPT.</div>
            )}
            <button type="button" className="btn" disabled={loggingIn} onClick={login}>
              {loggingIn ? 'Đang chờ đăng nhập trên trình duyệt…' : '🔑 Đăng nhập OpenAI (ChatGPT)'}
            </button>
            <p className="oauth-hint">
              Dùng quota gói ChatGPT, không cần API key. Token chia sẻ với Codex CLI
              (~/.codex/auth.json).
            </p>
          </div>
        )}
        <ModelField
          provider={form.provider}
          configId={form.id}
          apiKey={form.api_key}
          baseUrl={form.base_url}
          value={form.model}
          onChange={(v) => set('model', v)}
          placeholder={`mặc định = ${providerMeta?.defaultModel}`}
        />
        {errorMsg && <div className="config-error">{errorMsg}</div>}
        <div className="config-form-actions">
          <button className="btn primary" type="submit" disabled={saving}>
            {editing ? <SaveIcon size={13} /> : <PlusIcon size={13} />}
            {editing ? 'Cập nhật' : 'Thêm'}
          </button>
          <button className="btn" type="button" onClick={closeForm}>
            Hủy
          </button>
        </div>
        </form>
      </div>
      </div>
      )}
    </>
  )
}
