import { Capacitor } from '@capacitor/core'

const API_BASE_STORAGE_KEY = 'schedule_hunter_api_base_url'

function normalize_base_url(value) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  const with_protocol = /^https?:\/\//i.test(raw) ? raw : `http://${raw}`
  return with_protocol.replace(/\/+$/, '')
}

function get_build_time_api_url() {
  if (Capacitor.isNativePlatform()) {
    return import.meta.env.VITE_NATIVE_API_BASE_URL || import.meta.env.VITE_API_BASE_URL || ''
  }
  return import.meta.env.VITE_API_BASE_URL || ''
}

export function get_api_base_url() {
  const saved = window.localStorage.getItem(API_BASE_STORAGE_KEY)
  return normalize_base_url(saved || get_build_time_api_url())
}

export function set_api_base_url(value) {
  const normalized = normalize_base_url(value)
  if (normalized) window.localStorage.setItem(API_BASE_STORAGE_KEY, normalized)
  else window.localStorage.removeItem(API_BASE_STORAGE_KEY)
  return normalized
}

export function is_native_app() {
  return Capacitor.isNativePlatform()
}

function generate_request_id() {
  const now = new Date()
  const date_str = now.toISOString().slice(0, 10).replace(/-/g, '')
  const random = Math.random().toString(36).substr(2, 6)
  return `req_${date_str}_${random}`
}

function generate_trace_id() {
  const now = new Date()
  const date_str = now.toISOString().slice(0, 10).replace(/-/g, '')
  const random = Math.random().toString(36).substr(2, 6)
  return `trace_${date_str}_${random}`
}

let toastContainer = null

function showToast(message, type = 'error') {
  if (!toastContainer) {
    toastContainer = document.createElement('div')
    toastContainer.id = 'api-toast-container'
    toastContainer.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 99999;
      display: flex;
      flex-direction: column;
      gap: 8px;
      pointer-events: none;
    `
    document.body.appendChild(toastContainer)
  }

  const toast = document.createElement('div')
  const bgColor = type === 'error' ? 'bg-red-600' : type === 'success' ? 'bg-green-600' : 'bg-blue-600'
  toast.className = `${bgColor} text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 animate-slide-in`
  toast.style.cssText = `
    pointer-events: auto;
    max-width: 320px;
    animation: slideInRight 0.3s ease-out;
  `

  const icon = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️'
  toast.innerHTML = `<span>${icon}</span><span class="text-sm">${message}</span>`

  toastContainer.appendChild(toast)

  setTimeout(() => {
    toast.style.opacity = '0'
    toast.style.transform = 'translateX(100%)'
    toast.style.transition = 'all 0.3s ease-in'
    setTimeout(() => toast.remove(), 300)
  }, 4000)
}

const style = document.createElement('style')
style.textContent = `
  @keyframes slideInRight {
    from { opacity: 0; transform: translateX(100%); }
    to { opacity: 1; transform: translateX(0); }
  }
`
document.head.appendChild(style)

export function get_websocket_url() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL
  const api_base_url = get_api_base_url()
  if (api_base_url) return `${api_base_url.replace(/^http/i, 'ws')}/ws/tasks`
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/tasks`
}

export async function test_backend_connection(value = get_api_base_url()) {
  const base_url = normalize_base_url(value)
  if (!base_url) {
    return { success: false, error: '请先填写后端地址' }
  }
  try {
    const response = await fetch(`${base_url}/`, { signal: AbortSignal.timeout(5000) })
    if (!response.ok) return { success: false, error: `HTTP ${response.status}` }
    const data = await response.json()
    return { success: true, data, base_url }
  } catch (error) {
    return { success: false, error: error.message || '无法连接后端' }
  }
}

async function request(url, options = {}) {
  const default_options = {
    headers: {
      'Content-Type': 'application/json'
    },
    signal: AbortSignal.timeout(15000)
  }

  console.log('📡 [NETWORK] 请求:', url, options.method || 'GET')
  try {
    const response = await fetch(`${get_api_base_url()}${url}`, {
      ...default_options,
      ...options
    })

    if (!response.ok) {
      const error_data = await response.json().catch(() => ({}))
      const errorMsg = error_data.message || error_data.detail || `HTTP ${response.status}`
      showToast(errorMsg, 'error')
      throw new Error(errorMsg)
    }

    const json = await response.json()

    if (json.code && json.code !== 0) {
      showToast(json.message || `错误码 ${json.code}`, 'error')
    }

    console.log('📡 [NETWORK] 响应:', url, response.status, json)
    return json
  } catch (error) {
    if (error.name === 'AbortError' || error.message.includes('timeout') || error.message.includes('aborted')) {
      showToast('请求超时，请检查网络连接', 'error')
    } else if (!error.message.includes('HTTP')) {
      showToast(error.message || '网络错误', 'error')
    }
    throw error
  }
}

export async function parse_task(source_text, context = {}, meta = {}) {
  const request_body = {
    request_id: generate_request_id(),
    source_text: source_text,
    context: {
      recent_tasks: context.recent_tasks || [],
      user_preferences: {
        default_duration_minutes: context.user_preferences?.default_duration_minutes || 60,
        timezone: context.user_preferences?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
      }
    },
    meta: {
      input_type: meta.input_type || 'manual',
      client_timestamp: new Date().toISOString(),
      app_version: meta.app_version || '1.0.0'
    }
  }

  try {
    const data = await request('/api/v1/task/parse', {
      method: 'POST',
      body: JSON.stringify(request_body)
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function fetch_tasks(date, status) {
  const params = new URLSearchParams()
  if (date) params.append('date', date)
  if (status) params.append('status', status)

  const query_string = params.toString()
  const url = `/api/v1/tasks${query_string ? '?' + query_string : ''}`

  try {
    const data = await request(url, {
      method: 'GET'
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function create_task(task_data) {
  const request_body = {
    request_id: generate_request_id(),
    source_text: task_data.source_text || task_data.parsed?.title || '',
    parsed: {
      title: task_data.parsed?.title || task_data.title,
      start_time: task_data.parsed?.start_time || task_data.start_time,
      end_time: task_data.parsed?.end_time || task_data.end_time,
      location: task_data.parsed?.location || task_data.location,
      participants: task_data.parsed?.participants || task_data.participants || [],
      timezone: task_data.parsed?.timezone || 'Asia/Shanghai'
    },
    priority: task_data.priority || 'normal',
    reminder_policy: {
      enabled: task_data.reminder_policy?.enabled !== false,
      offset_minutes: task_data.reminder_policy?.offset_minutes || [30, 10, 5]
    },
    meta: {
      input_type: task_data.meta?.input_type || 'manual',
      language: task_data.meta?.language || 'zh-CN',
      client_timestamp: new Date().toISOString()
    }
  }

  try {
    const data = await request('/api/v1/tasks', {
      method: 'POST',
      body: JSON.stringify(request_body)
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function update_task(task_id, task_data) {
  try {
    const data = await request(`/api/v1/tasks/${task_id}`, {
      method: 'PUT',
      body: JSON.stringify(task_data)
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function delete_task(task_id) {
  try {
    const data = await request(`/api/v1/tasks/${task_id}`, {
      method: 'DELETE'
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function delete_expired_tasks() {
  try {
    const data = await request('/api/v1/tasks/expired', { method: 'DELETE' })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function update_task_status(task_id, status) {
  try {
    const data = await request(`/api/v1/tasks/${task_id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function check_conflict(candidate, scope = {}) {
  const request_body = {
    request_id: generate_request_id(),
    candidate: {
      title: candidate.title,
      start_time: candidate.start_time,
      end_time: candidate.end_time,
      location: candidate.location
    },
    scope: {
      check_type: scope.check_type || 'time_overlap',
      include_travel_time: scope.include_travel_time !== false,
      travel_buffer_minutes: scope.travel_buffer_minutes || 20
    }
  }

  try {
    const data = await request('/api/v1/tasks/conflict-check', {
      method: 'POST',
      body: JSON.stringify(request_body)
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function sync_calendar(month) {
  try {
    const data = await request(`/api/v1/calendar/sync?month=${month}`)
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}
