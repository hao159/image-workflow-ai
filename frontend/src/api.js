import { t, translateError } from './i18n/index.js'

export async function fetchNodeTypes() {
  const res = await fetch('/api/node-types')
  if (!res.ok) throw new Error(t('error.node_list_failed'))
  return res.json()
}

export async function uploadImage(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/upload', { method: 'POST', body: form })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(translateError(body.code, body.error || t('error.upload_failed')))
  }
  return res.json()
}

export async function saveWorkflow(workflow, { overwrite = false } = {}) {
  const res = await fetch(`/api/workflows?overwrite=${overwrite}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(workflow),
  })
  if (res.status === 409) {
    // Tên đã tồn tại — App bắt .code === 'exists' để hỏi xác nhận ghi đè.
    const err = new Error(t('error.workflow_exists'))
    err.code = 'exists'
    throw err
  }
  if (!res.ok) throw new Error(t('error.workflow_save_failed'))
  return res.json()
}

export async function listWorkflows() {
  const res = await fetch('/api/workflows')
  return res.json()
}

export async function loadWorkflow(name) {
  const res = await fetch(`/api/workflows/${encodeURIComponent(name)}`)
  if (!res.ok) throw new Error(t('error.workflow_load_failed'))
  return res.json()
}

export async function deleteWorkflow(name) {
  const res = await fetch(`/api/workflows/${encodeURIComponent(name)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(t('error.workflow_delete_failed'))
  return res.json()
}

export async function listModelConfigs() {
  const res = await fetch('/api/model-configs')
  if (!res.ok) throw new Error(t('error.model_configs_failed'))
  return res.json()
}

export async function saveModelConfig(cfg) {
  const res = await fetch('/api/model-configs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cfg),
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(translateError(body.code, body.error || t('error.save_model_config_failed')))
  return body
}

export async function deleteModelConfig(id) {
  const res = await fetch(`/api/model-configs/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(t('error.delete_model_config_failed'))
  return res.json()
}

export async function listProviderModels(provider, { refresh = false, configId, apiKey, baseUrl } = {}) {
  const body = { refresh }
  if (configId != null) body.config_id = configId
  if (apiKey) body.api_key = apiKey
  if (baseUrl) body.base_url = baseUrl
  const res = await fetch(`/api/providers/${encodeURIComponent(provider)}/models`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(translateError(data.code, data.error || t('error.model_list_failed')))
  return data
}

// ---------- Lịch sử thực thi (exec history) ----------

export async function listExecutions(name, { page = 1, size = 10 } = {}) {
  const res = await fetch(
    `/api/workflows/${encodeURIComponent(name)}/executions?page=${page}&size=${size}`)
  if (!res.ok) throw new Error(t('error.execution_list_failed'))
  return res.json()
}

export async function getExecution(id) {
  const res = await fetch(`/api/executions/${id}`)
  if (!res.ok) throw new Error(t('error.execution_get_failed'))
  return res.json()
}

export async function deleteExecution(id) {
  const res = await fetch(`/api/executions/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(t('error.execution_delete_failed'))
  return res.json()
}

export async function clearExecutions(name) {
  const res = await fetch(
    `/api/workflows/${encodeURIComponent(name)}/executions`, { method: 'DELETE' })
  if (!res.ok) throw new Error(t('error.execution_clear_failed'))
  return res.json()
}

// Kiểm tra bản mới (notify-only). Fail mềm: lỗi/offline → backend vẫn trả 200 với
// error != null, App bỏ qua im lặng nên không làm phiền người dùng.
export async function checkForUpdate() {
  const res = await fetch('/api/update-check')
  if (!res.ok) throw new Error(t('error.update_check_failed'))
  return res.json()
}

export function openRunSocket() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return new WebSocket(`${proto}://${location.host}/ws/run`)
}

export async function clearCache() {
  const res = await fetch('/api/cache/clear', { method: 'POST' })
  if (!res.ok) throw new Error(t('error.cache_clear_failed'))
  return res.json()
}

// ---------- OpenAI (Codex OAuth) ----------

export async function getOpenAIOAuthStatus() {
  const res = await fetch('/api/oauth/openai/status')
  if (!res.ok) throw new Error(t('error.oauth_status_failed'))
  return res.json()
}

export async function startOpenAIOAuth() {
  // Backend mở trình duyệt và chờ tới khi đăng nhập xong (có thể mất tới ~3 phút).
  const res = await fetch('/api/oauth/openai/start', { method: 'POST' })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(translateError(body.code, body.error || t('error.oauth_login_failed')))
  return body
}

// ---------- Thư viện ảnh (uploads/outputs) ----------

export async function listUploads() {
  const res = await fetch('/api/uploads')
  if (!res.ok) throw new Error(t('error.uploads_list_failed'))
  return res.json()
}

export async function listOutputs() {
  const res = await fetch('/api/outputs')
  if (!res.ok) throw new Error(t('error.outputs_list_failed'))
  return res.json()
}

export async function deleteUpload(name) {
  const res = await fetch(`/api/uploads/${encodeURIComponent(name)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(t('error.image_delete_failed'))
  return res.json()
}

export async function deleteOutput(name) {
  const res = await fetch(`/api/outputs/${encodeURIComponent(name)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(t('error.image_delete_failed'))
  return res.json()
}
