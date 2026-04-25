import { defineStore } from 'pinia'
import * as apiService from '@/services/apiService'

export const useTaskStore = defineStore('task', {
  state: () => ({
    is_mock_mode: false,
    active_task: null,
    pending_task: null,
    is_conflict: false,
    conflict_detail: '',
    conflict_type: null,
    conflict_level: null,
    conflict_task_id: null,
    conflict_suggestions: [],
    needs_confirmation: false,
    ambiguities: [],
    captured_text: '',
    island_state: 'idle',
    last_response: null,
    trace_id: null,
    tasks: [],
    ws: null,
    is_loading: false,
    error: null,
    reminder_threshold: 30 * 60 * 1000,
    _timer_id: null,
    _disconnected: false,
    _native_handlers: [],
    selected_date: new Date().toISOString().split('T')[0]
  }),

  getters: {
    is_idle: (state) => state.island_state === 'idle',
    is_tracking: (state) => state.island_state === 'tracking',
    is_reminder: (state) => state.island_state === 'reminder',
    is_warning: (state) => state.island_state === 'warning',
    is_ambiguous: (state) => state.needs_confirmation && state.island_state === 'idle',
    current_task: (state) => state.active_task,
    warning_severity: (state) => {
      if (state.conflict_level === 'high') return 'critical'
      if (state.conflict_level === 'medium') return 'warning'
      return 'info'
    },
    today_tasks: (state) => {
      const tasks = state.tasks || []
      const selected = state.selected_date || new Date().toISOString().split('T')[0]
      return tasks.filter(task => {
        const task_date = task.start_time?.split('T')[0]
        return task_date === selected
      })
    },
    marked_dates: (state) => {
      const tasks = state.tasks || []
      const dates = tasks.map(task => task.start_time?.split('T')[0])
      return [...new Set(dates.filter(Boolean))]
    }
  },

  actions: {
    toggle_mock_mode() {
      this.is_mock_mode = !this.is_mock_mode
    },

    _start_reminder_timer() {
      if (this._timer_id) {
        clearInterval(this._timer_id)
      }
      this._timer_id = setInterval(() => {
        this._check_reminders()
      }, 30000)
    },

    _stop_reminder_timer() {
      if (this._timer_id) {
        clearInterval(this._timer_id)
        this._timer_id = null
      }
    },

    _check_reminders() {
      if (!this.pending_task) return

      const now = Date.now()
      const start = new Date(this.pending_task.start_time).getTime()
      const diff = start - now

      if (diff <= 0) {
        this.active_task = this.pending_task
        this.pending_task = null
        this.island_state = 'reminder'
        this._stop_reminder_timer()
      } else if (diff <= this.reminder_threshold) {
        this.active_task = this.pending_task
        this.pending_task = null
        if (this.is_conflict) {
          this.island_state = 'warning'
        } else {
          this.island_state = 'tracking'
        }
        this._stop_reminder_timer()
      }
    },

    setSelectedDate(date) {
      this.selected_date = date
      this.fetch_latest_tasks()
    },

    async fetch_latest_tasks() {
      this.is_loading = true
      this.error = null

      try {
        const result = await apiService.fetch_tasks(this.selected_date)

        if (result.success && result.data) {
          const response_data = result.data.data || result.data
          this.tasks = response_data.task_list || response_data.tasks || []
        } else {
          this.error = result.error
        }
      } catch (error) {
        this.error = error.message
      } finally {
        this.is_loading = false
      }
    },

    async sniffing_handler(raw_text, input_type = 'manual') {
      this.captured_text = raw_text

      try {
        const context = {
          recent_tasks: this.tasks.slice(0, 5).map(t => ({
            task_id: t.task_id || t.id,
            title: t.title,
            start_time: t.start_time,
            end_time: t.end_time
          })),
          user_preferences: {
            default_duration_minutes: 60,
            timezone: 'Asia/Shanghai'
          }
        }
        const meta = {
          input_type: input_type,
          app_version: '1.0.0'
        }
        const result = await apiService.parse_task(raw_text, context, meta)

        this.last_response = result

        if (result.success && result.data) {
          const response_data = result.data.data || result.data
          this.trace_id = response_data.trace_id || result.data.trace_id

          if (response_data.code === 0) {
            const parsed = response_data.parsed || {}
            const conflict = response_data.conflict
            const suggestions = response_data.suggestions || []
            this.needs_confirmation = response_data.needs_confirmation || false
            this.ambiguities = response_data.ambiguities || []

            this.is_conflict = response_data.is_conflict || false

            if (conflict) {
              this.conflict_detail = conflict.detail || ''
              this.conflict_type = conflict.conflict_type || null
              this.conflict_level = conflict.conflict_level || 'medium'
              this.conflict_task_id = conflict.conflicting_task_id || null
            } else {
              this.conflict_detail = ''
              this.conflict_type = null
              this.conflict_level = null
              this.conflict_task_id = null
            }

            this.conflict_suggestions = suggestions.map(s => ({
              action: s.action,
              description: s.description,
              suggested_time: s.suggested_time,
              suggested_duration_minutes: s.suggested_duration_minutes
            }))

            const task = {
              id: `task_${Date.now()}`,
              task_id: `task_${Date.now()}`,
              title: parsed.title,
              start_time: parsed.start_time,
              end_time: parsed.end_time,
              location: parsed.location,
              participants: parsed.participants || [],
              timezone: parsed.timezone || 'Asia/Shanghai',
              confidence: parsed.confidence || 0,
              source_text: raw_text,
              is_conflict: this.is_conflict,
              conflict_detail: this.conflict_detail,
              conflict_type: this.conflict_type,
              conflict_level: this.conflict_level,
              suggestions: this.conflict_suggestions,
              needs_confirmation: this.needs_confirmation,
              ambiguities: this.ambiguities
            }

            if (this.is_conflict) {
              this.island_state = 'warning'
              this.pending_task = task
            } else if (this.needs_confirmation) {
              this.island_state = 'idle'
              this.pending_task = task
            } else {
              this._schedule_reminder(task)
              this.island_state = 'idle'
            }

            return { success: true, data: response_data }
          } else {
            this.error = response_data.message || 'Parse failed'
            return { success: false, error: this.error }
          }
        } else {
          this.error = result.error
          return { success: false, error: result.error }
        }
      } catch (error) {
        this.error = error.message
        return { success: false, error: error.message }
      }
    },

    _schedule_reminder(task) {
      if (!task.start_time) return

      const now = Date.now()
      const start = new Date(task.start_time).getTime()
      const diff = start - now

      if (diff <= 0) {
        this.active_task = task
        this.pending_task = null
        this.island_state = 'reminder'
      } else if (diff <= this.reminder_threshold) {
        this.pending_task = task
        this.active_task = null
        this.island_state = 'tracking'
        this._start_reminder_timer()
      } else {
        this.pending_task = task
        this.active_task = null
        this.island_state = 'idle'
        this._start_reminder_timer()
      }
    },

    register_native_handler(callback) {
      this._native_handlers.push(callback)
    },

    unregister_native_handler(callback) {
      const index = this._native_handlers.indexOf(callback)
      if (index > -1) {
        this._native_handlers.splice(index, 1)
      }
    },

    async handle_native_sniff(source_text, input_type = 'manual') {
      if (!source_text || !source_text.trim()) return
      this.captured_text = source_text
      this.is_loading = true
      this.error = null

      try {
        const meta = {
          input_type: input_type,
          app_version: '1.0.0'
        }
        const result = await apiService.parse_task(source_text, {}, meta)

        if (result.success && result.data) {
          if (result.data.code === 0) {
            console.log('🔥 [DEBUG] 准备激活灵动岛，数据:', result.data)

            const raw_data = result.data.data?.parsed || result.data.data || result.data

            this.active_task = raw_data
            this.is_conflict = !!raw_data.is_conflict
            this.island_state = 'reminder'

            if (raw_data.is_conflict) {
              this.island_state = 'warning'
              if (raw_data.conflict) {
                this.conflict_detail = raw_data.conflict.detail || ''
                this.conflict_type = raw_data.conflict.conflict_type || null
                this.conflict_level = raw_data.conflict.conflict_level || 'medium'
              }
            }

            return { success: true, data: raw_data }
          } else {
            this.error = result.data.message || 'Parse failed'
            return { success: false, error: this.error }
          }
        } else {
          console.error('❌ [STORE ERROR]:', result.error)
          this.error = result.error
          return { success: false, error: result.error }
        }
      } catch (error) {
        console.error('❌ [STORE ERROR]:', error)
        this.error = error.message
        return { success: false, error: error.message }
      } finally {
        this.is_loading = false
      }
    },

    set_active_task(task) {
      this.active_task = task
      if (task?.is_conflict) {
        this.is_conflict = true
        this.conflict_detail = task.conflict_detail || ''
        this.conflict_type = task.conflict_type || null
        this.conflict_level = task.conflict_level || 'medium'
        this.conflict_suggestions = task.suggestions || []
        this.island_state = 'warning'
      } else {
        this.is_conflict = false
        this.conflict_detail = ''
        this.conflict_type = null
        this.conflict_level = null
        this.conflict_suggestions = []
        this.island_state = 'tracking'
      }
      this._schedule_reminder(task)
    },

    clear_active_task() {
      this.active_task = null
      this.pending_task = null
      this.is_conflict = false
      this.conflict_detail = ''
      this.conflict_type = null
      this.conflict_level = null
      this.conflict_task_id = null
      this.conflict_suggestions = []
      this.needs_confirmation = false
      this.ambiguities = []
      this.island_state = 'idle'
      this._stop_reminder_timer()
    },

    clearActiveTask() {
      this.clear_active_task()
    },

    setActiveTask(task) {
      this.set_active_task(task)
    },

    apply_suggestion(suggestion) {
      if (!suggestion || !this.pending_task) return

      const task = { ...this.pending_task }

      if (suggestion.action === 'reschedule' && suggestion.suggested_time) {
        const duration = new Date(task.end_time).getTime() - new Date(task.start_time).getTime()
        task.start_time = suggestion.suggested_time
        task.end_time = new Date(new Date(suggestion.suggested_time).getTime() + duration).toISOString()
      } else if (suggestion.action === 'shorten' && suggestion.suggested_duration_minutes) {
        task.end_time = new Date(new Date(task.start_time).getTime() + suggestion.suggested_duration_minutes * 60000).toISOString()
      } else if (suggestion.action === 'dismiss') {
        this.clear_active_task()
        return
      }

      task.is_conflict = false
      task.conflict_detail = ''
      task.conflict_type = null
      task.conflict_level = null
      this.is_conflict = false
      this.conflict_detail = ''
      this.conflict_type = null
      this.conflict_level = null

      this._schedule_reminder(task)
      this.island_state = 'idle'
    },

    dismiss_warning() {
      this.clear_active_task()
    },

    async check_task_conflict(task) {
      try {
        const result = await apiService.check_conflict(task.candidate || task, {})

        if (result.success && result.data) {
          const response_data = result.data.data || result.data
          if (response_data.has_conflict && response_data.conflicts?.length > 0) {
            const conflict = response_data.conflicts[0]
            this.is_conflict = true
            this.conflict_detail = conflict.detail || ''
            this.conflict_type = conflict.conflict_type || null
            this.conflict_level = conflict.conflict_level || 'medium'
            this.conflict_suggestions = conflict.suggestions?.map((s, i) => ({
              action: ['reschedule', 'shorten', 'dismiss'][i % 3],
              description: s
            })) || []
            this.island_state = 'warning'
            return true
          }
        }
        return false
      } catch (error) {
        this.error = error.message
        return false
      }
    },

    async create_task_from_active() {
      if (!this.active_task) return null

      const task_data = {
        source_text: this.captured_text || '',
        parsed: {
          title: this.active_task.title,
          start_time: this.active_task.start_time,
          end_time: this.active_task.end_time,
          location: this.active_task.location,
          participants: this.active_task.participants || [],
          timezone: this.active_task.timezone || 'Asia/Shanghai'
        },
        priority: 'normal',
        meta: {
          input_type: 'manual',
          language: 'zh-CN'
        }
      }

      try {
        const result = await apiService.create_task(task_data)

        if (result.success && result.data) {
          const response_data = result.data.data || result.data
          const created_task = {
            ...this.active_task,
            task_id: response_data.task_id,
            status: response_data.status || 'scheduled'
          }
          this.tasks.push(created_task)
          this.clear_active_task()
          this.fetch_latest_tasks()
          return created_task
        }
        return null
      } catch (error) {
        this.error = error.message
        return null
      }
    },

    async create_task_from_pending() {
      if (!this.pending_task) return null

      const task_data = {
        source_text: this.pending_task.source_text,
        parsed: {
          title: this.pending_task.title,
          start_time: this.pending_task.start_time,
          end_time: this.pending_task.end_time,
          location: this.pending_task.location,
          participants: this.pending_task.participants,
          timezone: this.pending_task.timezone
        },
        priority: 'normal',
        meta: {
          input_type: 'manual',
          language: 'zh-CN'
        }
      }

      try {
        const result = await apiService.create_task(task_data)

        if (result.success && result.data) {
          const response_data = result.data.data || result.data
          const created_task = {
            ...this.pending_task,
            task_id: response_data.task_id,
            status: response_data.status || 'scheduled'
          }
          this.tasks.push(created_task)
          this.clear_active_task()
          return created_task
        }
        return null
      } catch (error) {
        this.error = error.message
        return null
      }
    },

    add_local_task(task) {
      const new_task = {
        id: `task_${Date.now()}`,
        task_id: `task_${Date.now()}`,
        title: task.title,
        start_time: task.start_time,
        end_time: task.end_time,
        location: task.location || '',
        participants: task.participants || [],
        timezone: task.timezone || 'Asia/Shanghai',
        is_conflict: false,
        has_warning: false,
        ...task
      }
      this.tasks.push(new_task)
      this._schedule_reminder(new_task)
      return new_task
    },

    remove_task(task_id) {
      const index = this.tasks.findIndex(t => t.id === task_id || t.task_id === task_id)
      if (index > -1) {
        this.tasks.splice(index, 1)
        if (this.active_task?.id === task_id || this.active_task?.task_id === task_id ||
            this.pending_task?.id === task_id || this.pending_task?.task_id === task_id) {
          this.clear_active_task()
        }
      }
    },

    connect_web_socket() {
      if (this.ws) {
        this.ws.close()
      }

      try {
        this.ws = new WebSocket('ws://' + window.location.host + '/ws/tasks')

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'schedule_sniff' && data.text) {
              this.sniffing_handler(data.text, data.input_type || 'notification')
            } else if (data.type === 'reminder_triggered' && data.task_id) {
              const task = this.tasks.find(t => t.task_id === data.task_id)
              if (task) {
                this.active_task = task
                this.island_state = 'reminder'
              }
            } else if (data.type === 'conflict_detected' && data.task_id) {
              const task = this.tasks.find(t => t.task_id === data.task_id)
              if (task) {
                this.is_conflict = true
                this.conflict_detail = data.detail || ''
                this.conflict_type = data.conflict_type || 'time_overlap'
                this.conflict_level = data.conflict_level || 'medium'
                this.island_state = 'warning'
              }
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
            setTimeout(() => this.connect_web_socket(), 5000)
          }
        }
      } catch (error) {
        console.error('WebSocket connection error:', error)
      }
    },

    disconnect_web_socket() {
      this._disconnected = true
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
      this._stop_reminder_timer()
    }
  }
})
