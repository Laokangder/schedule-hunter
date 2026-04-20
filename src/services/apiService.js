const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function request(url, options = {}) {
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json'
    }
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...defaultOptions,
    ...options
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

export async function parseText(rawText) {
  try {
    const data = await request('/api/v1/task/parse', {
      method: 'POST',
      body: JSON.stringify({ text: rawText })
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function syncCalendar(month) {
  try {
    const data = await request(`/api/v1/calendar/sync?month=${month}`)
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function fetchTasks() {
  try {
    const data = await request('/api/v1/tasks')
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function createTask(task) {
  try {
    const data = await request('/api/v1/tasks', {
      method: 'POST',
      body: JSON.stringify(task)
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function updateTask(taskId, task) {
  try {
    const data = await request(`/api/v1/tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify(task)
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function deleteTask(taskId) {
  try {
    const data = await request(`/api/v1/tasks/${taskId}`, {
      method: 'DELETE'
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export async function checkConflict(task) {
  try {
    const data = await request('/api/v1/tasks/conflict-check', {
      method: 'POST',
      body: JSON.stringify(task)
    })
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}
