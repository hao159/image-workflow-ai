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
import { useT } from '../i18n/use-t.js'

const PROVIDERS = [
  { value: 'gemini', label: 'Google Gemini', defaultModel: 'gemini-2.5-flash-image' },
  { value: 'openai', label: 'OpenAI (API key)', defaultModel: 'gpt-image-1' },
  // label for codex is localized at render time via t('model.providerCodex')
  { value: 'codex', labelKey: 'model.providerCodex', defaultModel: 'gpt-5.5' },
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
  const { t } = useT()

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

  // Resolve provider label: static label or translated labelKey
  const providerLabel = (p) => p.labelKey ? t(p.labelKey) : p.label

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
    if (!confirm(t('model.deleteConfirm', undefined, { name: cfg.name }))) return
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
        {t('model.hint')}
      </p>

      <div className="config-section-head">
        <span className="settings-section-title">{t('model.sectionTitle')}</span>
        <button className="btn primary" type="button" onClick={openAdd}>
          <PlusIcon size={13} /> {t('model.addConfig')}
        </button>
      </div>

      {configs.length > 0 ? (
        <table className="config-table">
          <thead>
            <tr>
              <th>{t('model.tableColName')}</th>
              <th>{t('model.tableColProvider')}</th>
              <th>{t('model.tableColModel')}</th>
              <th>{t('model.tableColApiKey')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {configs.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{providerLabel(PROVIDERS.find((p) => p.value === c.provider) || { label: c.provider })}</td>
                <td>{c.model || <span className="dim">{t('model.defaultValue')}</span>}</td>
                <td>{c.api_key_preview || <span className="dim">—</span>}</td>
                <td className="config-actions">
                  <button className="btn ghost" onClick={() => openEdit(c)}>{t('model.editBtn')}</button>
                  <button className="btn ghost danger" onClick={() => remove(c)}>{t('model.deleteBtn')}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="config-empty">{t('model.empty')}</p>
      )}

      {formOpen && (
      <div className="modal-backdrop config-modal-backdrop" onClick={closeForm}>
      <div className="modal config-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">
            {editing
              ? t('model.formTitleEdit', undefined, { name: form.name })
              : t('model.formTitleAdd')}
          </span>
          <button className="btn ghost" type="button" onClick={closeForm}><XIcon size={15} /></button>
        </div>
        <form className="config-form in-modal" onSubmit={submit}>
        <label>
          <span>{t('model.fieldName')}</span>
          <input
            type="text"
            required
            placeholder={t('model.fieldNamePlaceholder')}
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
          />
        </label>
        <label>
          <span>{t('model.fieldProvider')}</span>
          <select value={form.provider} onChange={(e) => set('provider', e.target.value)}>
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>{providerLabel(p)}</option>
            ))}
          </select>
        </label>
        {form.provider !== 'codex' && (
          <label>
            <span>{t('model.fieldApiKey')}</span>
            <input
              type="password"
              placeholder={editing
                ? t('model.fieldApiKeyPlaceholderEdit')
                : t('model.fieldApiKeyPlaceholderNew')}
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
                {t('model.oauthLoggedIn')}
                {oauthStatus.account_id && (
                  <span className="dim"> {t('model.oauthAccount', undefined, { id: oauthStatus.account_id.slice(0, 8) })}</span>
                )}
                {oauthStatus.expired && (
                  <div className="oauth-hint">{t('model.oauthExpired')}</div>
                )}
              </div>
            ) : (
              <div className="oauth-status">{t('model.oauthNotLoggedIn')}</div>
            )}
            <button type="button" className="btn" disabled={loggingIn} onClick={login}>
              {loggingIn ? t('model.oauthLoggingIn') : t('model.oauthLoginBtn')}
            </button>
            <p className="oauth-hint">
              {t('model.oauthHint')}
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
          placeholder={`${t('model.fieldModelDefault')} = ${providerMeta?.defaultModel}`}
        />
        {errorMsg && <div className="config-error">{errorMsg}</div>}
        <div className="config-form-actions">
          <button className="btn primary" type="submit" disabled={saving}>
            {editing ? <SaveIcon size={13} /> : <PlusIcon size={13} />}
            {editing ? t('model.submitUpdate') : t('model.submitAdd')}
          </button>
          <button className="btn" type="button" onClick={closeForm}>
            {t('model.cancelBtn')}
          </button>
        </div>
        </form>
      </div>
      </div>
      )}
    </>
  )
}
