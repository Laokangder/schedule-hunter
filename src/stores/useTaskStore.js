import { defineStore } from 'pinia'
import * as apiService from '@/services/apiService'
import * as mockProvider from '@/services/mockProvider'

export const useTaskStore = defineStore('task', {
  state: () => ({
    isMockMode: true,
    activeTask: null,
    pendingTask: null,
    isConflict: false,
    conflictDetail: '',
    conflictSuggestions: [],
    capturedText: '',
    islandState: 'idle',
    lastParseResult: null,
    tasks: [],
    ws: null,
    isLoading: false,
    error: null,
    _timerId: null,
    REMINDER_THRESHOLD: 30 * 60 * 1000
  }),

  getters: {
    isTracking: (state) => state.islandState === 'tracking',
    hasConflict: (state) => state.isConflict,
    currentTask: (state) => state.activeTask,
    todayTasks: (state) => {
      const today = new Date().toISOString().split('T')[0]
      return state.tasks.filter(task => {
        const taskDate = task.start_time?.split('T')[0]
        return taskDate === today
      })
    },
    markedDates: (state) => {
      const dates = state.tasks.map(task => task.start_time?.split('T')[0])
      return [...new Set(dates.filter(Boolean))]
    },
    modeLabel: (state) => state.isMockMode ? 'MOCK' : 'API'
  },

  actions: {
    toggleMockMode() {
      this.isMockMode = !this.isMockMode
    },

    _startReminderTimer() {
      if (this._timerId) {
        clearInterval(this._timerId)
      }
      this._timerId = setInterval(() => {
        this._checkReminders()
      }, 30000)
    },

    _stopReminderTimer() {
      if (this._timerId) {
        clearInterval(this._timerId)
        this._timerId = null
      }
    },

    _checkReminders() {
      if (!this.pendingTask) return

      const now = Date.now()
      const start = new Date(this.pendingTask.start_time).getTime()
      const diff = start - now

      if (diff <= this.REMINDER_THRESHOLD && diff > 0) {
        this.activeTask = this.pendingTask
        this.pendingTask = null
        if (this.isConflict) {
          this.islandState = 'warning'
        } else {
          this.islandState = 'tracking'
        }
        this._stopReminderTimer()
      } else if (diff <= 0) {
        this.activeTask = this.pendingTask
        this.pendingTask = null
        this.islandState = 'reminder'
        this._stopReminderTimer()
      }
    },

    async fetchLatestTasks() {
      this.isLoading = true
      this.error = null

      try {
        let result
        if (this.isMockMode) {
          result = await mockProvider.mockFetchTasks()
        } else {
          result = await apiService.fetchTasks()
        }

        if (result.success) {
          this.tasks = result.data || []
        } else {
          this.error = result.error
        }
      } catch (error) {
        this.error = error.message
      } finally {
        this.isLoading = false
      }
    },

    async sniffingHandler(rawText) {
      this.capturedText = rawText

      try {
        let result
        if (this.isMockMode) {
          result = await mockProvider.mockParseText(rawText)
        } else {
          result = await apiService.parseText(rawText)
        }

        this.lastParseResult = result

        if (result.success && result.data?.parsed) {
          const parsed = result.data.parsed
          const task = {
            id: parsed.id || `task_${Date.now()}`,
            title: parsed.title || '新任务',
            start_time: parsed.start_time,
            end_time: parsed.end_time,
            location: parsed.location || '',
            confidence: parsed.confidence || 0,
            is_conflict: result.data.is_conflict || false,
            has_warning: parsed.has_warning || false,
            ai_suggestion: parsed.ai_suggestion || ''
          }

          if (result.data.is_conflict) {
            this.isConflict = true
            this.conflictDetail = result.data.conflict?.detail || ''
            this.conflictSuggestions = result.data.conflict?.suggestions || []
            this.islandState = 'warning'
          } else {
            this.isConflict = false
            this.conflictDetail = ''
            this.conflictSuggestions = []
            this.islandState = 'idle'
          }

          const exists = this.tasks.some(
            t => t.title === task.title && t.start_time === task.start_time
          )

          if (!exists) {
            this.tasks.push(task)
          }

          this._scheduleReminder(task)
        }

        return result
      } catch (error) {
        this.error = error.message
        return { success: false, error: error.message }
      }
    },

    _scheduleReminder(task) {
      const now = Date.now()
      const start = new Date(task.start_time).getTime()
      const diff = start - now

      if (diff <= 0) {
        this.activeTask = task
        this.pendingTask = null
        this.islandState = 'reminder'
      } else if (diff <= this.REMINDER_THRESHOLD) {
        this.pendingTask = task
        this.activeTask = null
        this.islandState = 'tracking'
        this._startReminderTimer()
      } else {
        this.pendingTask = task
        this.activeTask = null
        this.islandState = 'idle'
        this._startReminderTimer()
      }
    },

    async pushSniffedText(text, source = 'clipboard') {
      return this.sniffingHandler(text)
    },

    setActiveTask(task) {
      this.activeTask = task
      if (task?.is_conflict) {
        this.isConflict = true
        this.conflictDetail = task.conflict_detail || ''
        this.conflictSuggestions = task.suggestions || []
        this.islandState = 'warning'
      } else {
        this.isConflict = false
        this.conflictDetail = ''
        this.conflictSuggestions = []
        this.islandState = 'tracking'
      }
      this._scheduleReminder(task)
    },

    clearActiveTask() {
      this.activeTask = null
      this.pendingTask = null
      this.isConflict = false
      this.conflictDetail = ''
      this.conflictSuggestions = []
      this.islandState = 'idle'
      this._stopReminderTimer()
    },

    async checkTaskConflict(task) {
      try {
        let result
        if (this.isMockMode) {
          result = await mockProvider.mockCheckConflict(task)
        } else {
          result = await apiService.checkConflict(task)
        }

        if (result.success && result.data?.conflict) {
          this.isConflict = true
          this.conflictDetail = result.data.conflict.detail
          this.conflictSuggestions = result.data.conflict.suggestions || []
          this.islandState = 'warning'
          return true
        }
        return false
      } catch (error) {
        this.error = error.message
        return false
      }
    },

    addLocalTask(task) {
      const newTask = {
        id: `task_${Date.now()}`,
        title: task.title,
        start_time: task.start_time,
        end_time: task.end_time,
        location: task.location || '',
        is_conflict: false,
        has_warning: false,
        ...task
      }
      this.tasks.push(newTask)
      this._scheduleReminder(newTask)
      return newTask
    },

    removeTask(taskId) {
      const index = this.tasks.findIndex(t => t.id === taskId)
      if (index > -1) {
        this.tasks.splice(index, 1)
        if (this.activeTask?.id === taskId || this.pendingTask?.id === taskId) {
          this.clearActiveTask()
        }
      }
    },

    connectWebSocket() {
      if (this.ws) {
        this.ws.close()
      }

      const apiHost = import.meta.env.VITE_API_HOST || '127.0.0.1:8000'
      const wsUrl = `ws://${apiHost}/ws/push`

      try {
        this.ws = new WebSocket(wsUrl)

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'schedule_sniff' && data.text) {
              this.sniffingHandler(data.text)
            }
          } catch (e) {
            console.error('WebSocket message parse error:', e)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
        }

        this.ws.onclose = () => {
          this.ws = null
          if (!this._disconnected) {
            setTimeout(() => this.connectWebSocket(), 5000)
          }
        }
      } catch (error) {
        console.error('WebSocket connection error:', error)
      }
    },

    disconnectWebSocket() {
      this._disconnected = true
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
      this._stopReminderTimer()
    }
  }
})
