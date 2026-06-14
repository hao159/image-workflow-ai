export async function fetchNodeTypes() {
  const res = await fetch('/api/node-types')
  if (!res.ok) throw new Error('Không tải được danh sách node từ backend.')
  return res.json()
}

export async function uploadImage(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/upload', { method: 'POST', body: form })
  if (!res.ok) throw new Error('Upload ảnh thất bại.')
  return res.json()
}

export async function saveWorkflow(workflow) {
  const res = await fetch('/api/workflows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(workflow),
  })
  if (!res.ok) throw new Error('Lưu workflow thất bại.')
  return res.json()
}

export async function listWorkflows() {
  const res = await fetch('/api/workflows')
  return res.json()
}

export async function loadWorkflow(name) {
  const res = await fetch(`/api/workflows/${encodeURIComponent(name)}`)
  if (!res.ok) throw new Error('Không tải được workflow.')
  return res.json()
}

export async function deleteWorkflow(name) {
  const res = await fetch(`/api/workflows/${encodeURIComponent(name)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Xóa workflow thất bại.')
  return res.json()
}

export async function listModelConfigs() {
  const res = await fetch('/api/model-configs')
  if (!res.ok) throw new Error('Không tải được danh sách cấu hình model.')
  return res.json()
}

export async function saveModelConfig(cfg) {
  const res = await fetch('/api/model-configs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cfg),
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.error || 'Lưu cấu hình thất bại.')
  return body
}

export async function deleteModelConfig(id) {
  const res = await fetch(`/api/model-configs/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Xóa cấu hình thất bại.')
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
  if (!res.ok) throw new Error(data.error || 'Không tải được danh sách model.')
  return data
}

export function openRunSocket() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return new WebSocket(`${proto}://${location.host}/ws/run`)
}

export async function clearCache() {
  const res = await fetch('/api/cache/clear', { method: 'POST' })
  if (!res.ok) throw new Error('Xóa cache thất bại.')
  return res.json()
}

// ---------- OpenAI (Codex OAuth) ----------

export async function getOpenAIOAuthStatus() {
  const res = await fetch('/api/oauth/openai/status')
  if (!res.ok) throw new Error('Không lấy được trạng thái đăng nhập OpenAI.')
  return res.json()
}

export async function startOpenAIOAuth() {
  // Backend mở trình duyệt và chờ tới khi đăng nhập xong (có thể mất tới ~3 phút).
  const res = await fetch('/api/oauth/openai/start', { method: 'POST' })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.error || 'Đăng nhập OpenAI thất bại.')
  return body
}
