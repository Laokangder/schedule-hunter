import { defineStore } from 'pinia'
import * as apiService from '@/services/apiService'
import * as notificationService from '@/services/notificationService'
import * as systemNotificationService from '@/services/systemNotificationService'
import { localDateKey } from '@/utils/date'

const processedSystemNotificationIds = new Set()
let systemNotificationProcessingChain = Promise.resolve()

// 错误码到中文消息的映射
const ERROR_MESSAGES = {
  1001: '解析文本为空，请输入日程内容',
  1002: '无法识别时间，请补充具体时间',
  1003: 'AI 不太确定，请核对信息',
  2001: '任务时间无效，请检查时间是否合理',
  2002: '冲突检测失败，已为您忽略冲突',
  2003: '日程冲突严重，请调整时间或取消',
  3001: '任务创建失败，请稍后重试',
  4001: '任务不存在或已删除',
  5000: '服务暂不可用，请稍后重试'
}

export const useTaskStore = defineStore('task', {
  state: () => ({
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
    expired_tasks: [],
    ws: null,
    is_loading: false,
    error: null,
    error_msg: '',
    notification_supported: notificationService.isSupported(),
    notification_permission: notificationService.isSupported() ? 'prompt' : 'unavailable',
    notification_exact_alarm: notificationService.isSupported() ? 'prompt' : 'unavailable',
    notification_error: '',
    _notifications_initialized: false,
    system_notification_supported: systemNotificationService.isSupported(),
    system_notification_permission: false,
    system_notification_enabled: false,
    system_notification_error: '',
    _system_notification_listener_handle: null,
    _system_notifications_initialized: false,
    reminder_threshold: 30 * 60 * 1000,
    _timer_id: null,
    _poll_interval_id: null,
    _expiration_timer_id: null,
    _disconnected: false,
    _native_handlers: [],
    selected_date: localDateKey()
  }),

  getters: {
    is_idle: (state) => state.island_state === 'idle',
    is_tracking: (state) => state.island_state === 'tracking',
    is_candidate: (state) => state.island_state === 'candidate',
    is_reminder: (state) => state.island_state === 'reminder',
    is_warning: (state) => state.island_state === 'warning',
    is_detail: (state) => state.island_state === 'detail',
    is_ambiguous: (state) => state.needs_confirmation && state.island_state === 'idle',
    current_task: (state) => state.active_task,
    warning_severity: (state) => {
      if (state.conflict_level === 'high') return 'critical'
      if (state.conflict_level === 'medium') return 'warning'
      return 'info'
    },
    today_tasks: (state) => {
      const tasks = state.tasks || []
      const selected = state.selected_date || localDateKey()
      return tasks.filter(task => {
        const task_date = task.start_time?.split('T')[0]
        return task_date === selected && task.status !== 'expired'
      })
    },
    marked_dates: (state) => {
      const tasks = state.tasks || []
      const dates = tasks.map(task => task.start_time?.split('T')[0])
      return [...new Set(dates.filter(Boolean))]
    },
    // 获取当前错误的中文消息
    errorMessage: (state) => {
      if (!state.error) return ''
      const code = parseInt(state.error)
      if (ERROR_MESSAGES[code]) {
        return ERROR_MESSAGES[code]
      }
      return state.error
    }
  },

  actions: {
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

    _start_poll() {
      if (!this._poll_interval_id) {
        this._poll_interval_id = setInterval(() => {
          this.fetch_latest_tasks()
        }, 30000)
      }
      if (!this._expiration_timer_id) {
        this._expiration_timer_id = setInterval(() => {
          this._sync_local_expiration()
        }, 1000)
      }
    },

    _stop_poll() {
      if (this._poll_interval_id) {
        clearInterval(this._poll_interval_id)
        this._poll_interval_id = null
      }
      if (this._expiration_timer_id) {
        clearInterval(this._expiration_timer_id)
        this._expiration_timer_id = null
      }
    },

    _sync_local_expiration() {
      const now = Date.now()
      const newlyExpired = []
      this.tasks = (this.tasks || []).filter(task => {
        if (!['scheduled', 'pending'].includes(task.status)) return true
        const endTime = new Date(task.end_time || task.start_time).getTime()
        if (!Number.isFinite(endTime) || endTime > now) return true
        newlyExpired.push({ ...task, status: 'expired' })
        return false
      })
      for (const task of newlyExpired) {
        const taskId = task.task_id || task.id
        const existingIndex = this.expired_tasks.findIndex(item => (item.task_id || item.id) === taskId)
        if (existingIndex >= 0) {
          this.expired_tasks[existingIndex] = task
        } else {
          this.expired_tasks.unshift(task)
        }
        void notificationService.cancelTask(task).catch(error => {
          console.error('Cancel expired task notification failed:', error)
        })
      }
    },

    async initialize_local_notifications() {
      if (this._notifications_initialized || !this.notification_supported) return
      this._notifications_initialized = true
      try {
        const permission = await notificationService.getPermissionState()
        this.notification_permission = permission.display
        this.notification_exact_alarm = permission.exact_alarm
        if (permission.display !== 'granted') return

        const result = await apiService.fetch_tasks()
        if (result.success) {
          const response = result.data?.data || result.data || {}
          await notificationService.reconcileTasks(response.task_list || response.tasks || [])
        }
        this.notification_error = ''
      } catch (error) {
        this.notification_error = error.message || '通知初始化失败'
        console.error('Initialize local notifications failed:', error)
      }
    },

    async request_notification_permission() {
      if (!this.notification_supported) return false
      try {
        const permission = await notificationService.requestPermission()
        this.notification_permission = permission.display
        this.notification_exact_alarm = permission.exact_alarm
        if (permission.display === 'granted') {
          const result = await apiService.fetch_tasks()
          if (result.success) {
            const response = result.data?.data || result.data || {}
            await notificationService.reconcileTasks(response.task_list || response.tasks || [])
          } else {
            await Promise.all(this.tasks.map(task => notificationService.scheduleTask(task)))
          }
          this.notification_error = ''
          return true
        }
        this.notification_error = '通知权限未开启，请在系统设置中允许通知'
        return false
      } catch (error) {
        this.notification_error = error.message || '通知授权失败'
        return false
      }
    },

    async request_exact_alarm_permission() {
      if (!this.notification_supported) return false
      try {
        const permission = await notificationService.requestExactAlarmPermission()
        this.notification_exact_alarm = permission.exact_alarm
        if (permission.exact_alarm === 'granted') {
          this._notifications_initialized = false
          await this.initialize_local_notifications()
          this.notification_error = ''
          return true
        }
        this.notification_error = '请在系统的“闹钟和提醒”设置中允许此应用'
        return false
      } catch (error) {
        this.notification_error = error.message || '精确提醒授权失败'
        return false
      }
    },

    async refresh_notification_permission_state() {
      if (!this.notification_supported) return
      try {
        const previousDisplay = this.notification_permission
        const previousExact = this.notification_exact_alarm
        const permission = await notificationService.getPermissionState()
        this.notification_permission = permission.display
        this.notification_exact_alarm = permission.exact_alarm
        if (permission.display === 'granted' && (previousDisplay !== 'granted' || previousExact !== permission.exact_alarm)) {
          this._notifications_initialized = false
          await this.initialize_local_notifications()
        }
      } catch (error) {
        console.error('Refresh notification permission failed:', error)
      }
    },

    async initialize_system_notification_listener() {
      if (!this.system_notification_supported) return
      try {
        await systemNotificationService.setBackendUrl(apiService.get_api_base_url())
        const status = await systemNotificationService.getStatus()
        this.system_notification_permission = !!status.granted
        this.system_notification_enabled = !!status.enabled

        if (!this._system_notification_listener_handle) {
          this._system_notification_listener_handle = await systemNotificationService.addCaptureListener(event => {
            this.handle_system_notification_event(event)
          })
        }

        this._system_notifications_initialized = true
        this.system_notification_error = ''
        if (this.system_notification_permission && this.system_notification_enabled) {
          await this.drain_system_notification_queue()
        }
      } catch (error) {
        this.system_notification_error = error.message || '系统通知监听初始化失败'
        console.error('Initialize system notification listener failed:', error)
      }
    },

    async refresh_system_notification_permission_state() {
      if (!this.system_notification_supported) return
      try {
        const status = await systemNotificationService.getStatus()
        this.system_notification_permission = !!status.granted
        this.system_notification_enabled = !!status.enabled
        if (this.system_notification_permission && this.system_notification_enabled) {
          await this.drain_system_notification_queue()
        }
      } catch (error) {
        this.system_notification_error = error.message || '无法读取系统通知监听状态'
      }
    },

    async open_system_notification_settings() {
      try {
        await systemNotificationService.openPermissionSettings()
        return true
      } catch (error) {
        this.system_notification_error = error.message || '无法打开通知使用权设置'
        return false
      }
    },

    async set_system_notification_enabled(enabled) {
      if (!this.system_notification_supported) return false
      try {
        const result = await systemNotificationService.setEnabled(enabled)
        this.system_notification_enabled = !!result.enabled
        if (this.system_notification_enabled && this.system_notification_permission) {
          await this.drain_system_notification_queue()
        }
        this.system_notification_error = ''
        return true
      } catch (error) {
        this.system_notification_error = error.message || '系统通知监听切换失败'
        return false
      }
    },

    async configure_system_notification_backend(backendUrl) {
      if (!this.system_notification_supported) return false
      try {
        const result = await systemNotificationService.setBackendUrl(backendUrl)
        return !!result.configured
      } catch (error) {
        this.system_notification_error = error.message || '后台解析地址配置失败'
        return false
      }
    },

    handle_system_notification_event(event) {
      systemNotificationProcessingChain = systemNotificationProcessingChain
        .then(() => this._process_system_notification_event(event))
        .catch(error => {
          this.system_notification_error = error.message || '系统通知处理失败'
          console.error('Process system notification failed:', error)
        })
      return systemNotificationProcessingChain
    },

    async _process_system_notification_event(event) {
      const eventId = event?.event_id
      const sourceText = event?.source_text?.trim()
      if (!eventId || !sourceText || processedSystemNotificationIds.has(eventId)) return false
      if (this.active_task || this.pending_task) return false

      processedSystemNotificationIds.add(eventId)
      if (processedSystemNotificationIds.size > 200) {
        const oldest = processedSystemNotificationIds.values().next().value
        processedSystemNotificationIds.delete(oldest)
      }

      const result = event.parsed_response
        ? this.apply_parse_response(event.parsed_response, sourceText)
        : await this.sniffing_handler(sourceText, 'notification')
      if (result?.success) {
        await systemNotificationService.acknowledge([eventId])
        this.system_notification_error = ''
        return true
      }

      if (result?.retryable === false) {
        await systemNotificationService.acknowledge([eventId])
        this.system_notification_error = ''
        return false
      }

      processedSystemNotificationIds.delete(eventId)
      this.system_notification_error = result?.error || '后端暂时不可用，通知已保留等待重试'
      return false
    },

    async drain_system_notification_queue() {
      if (!this.system_notification_permission || !this.system_notification_enabled) return 0
      if (this.active_task || this.pending_task) return 0
      const notifications = await systemNotificationService.getPending()
      for (const event of notifications) {
        const createdCandidate = await this.handle_system_notification_event(event)
        if (createdCandidate || this.active_task || this.pending_task || this.system_notification_error) break
      }
      return notifications.length
    },

    async dispose_system_notification_listener() {
      if (this._system_notification_listener_handle) {
        await this._system_notification_listener_handle.remove()
        this._system_notification_listener_handle = null
      }
      this._system_notifications_initialized = false
    },

    async register_task_notifications(task) {
      try {
        const result = await notificationService.scheduleTask(task)
        if (result.display) this.notification_permission = result.display
        if (result.exact_alarm) this.notification_exact_alarm = result.exact_alarm
        return result
      } catch (error) {
        this.notification_error = error.message || '通知注册失败'
        console.error('Register task notifications failed:', error)
        return null
      }
    },

    async rebuild_task_notifications(task) {
      try {
        return await notificationService.rebuildTask(task)
      } catch (error) {
        this.notification_error = error.message || '通知改期重建失败'
        return null
      }
    },

    setSelectedDate(date) {
      this.selected_date = date
      this.fetch_latest_tasks()
      this._start_poll()
    },

    async fetch_latest_tasks() {
      this.is_loading = true
      this.error = null
      this.error_msg = ''

      try {
        const [result, expiredResult] = await Promise.all([
          apiService.fetch_tasks(this.selected_date),
          apiService.fetch_tasks(null, 'expired')
        ])

        if (result.success && result.data) {
          const response_data = result.data.data || result.data
          if (response_data.code && response_data.code !== 0) {
            this.error = String(response_data.code)
            this.error_msg = ERROR_MESSAGES[response_data.code] || response_data.message || '请求失败'
          } else {
            this.tasks = response_data.task_list || response_data.tasks || []
          }
        } else {
          this.error = result.error
          this.error_msg = ERROR_MESSAGES[parseInt(result.error)] || result.error
        }
        if (expiredResult.success && expiredResult.data) {
          const expired_data = expiredResult.data.data || expiredResult.data
          this.expired_tasks = expired_data.task_list || expired_data.tasks || []
        }
      } catch (error) {
        this.error = error.message
        this.error_msg = ERROR_MESSAGES[parseInt(error.message)] || error.message
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

        if (result.success && result.data) {
          return this.apply_parse_response(result.data, raw_text)
        } else {
          this.error = result.error
          this.error_msg = ERROR_MESSAGES[parseInt(result.error)] || result.error
          return { success: false, error: this.error_msg, retryable: true }
        }
      } catch (error) {
        this.error = error.message
        this.error_msg = ERROR_MESSAGES[parseInt(error.message)] || error.message
        return { success: false, error: this.error_msg, retryable: true }
      }
    },

    apply_parse_response(response_envelope, raw_text) {
      this.last_response = { success: true, data: response_envelope }
      const response_data = response_envelope?.data || {}
      this.trace_id = response_envelope?.trace_id || response_data.trace_id

      if (response_envelope?.code !== 0) {
        this.error = String(response_envelope?.code)
        this.error_msg = ERROR_MESSAGES[response_envelope?.code] || response_envelope?.message || '解析失败'
        return { success: false, error: this.error_msg, code: response_envelope?.code, retryable: false }
      }

      const parsed = response_data.parsed || {}
      const conflict = response_data.conflict
      const suggestions = response_data.suggestions || []
      this.needs_confirmation = response_data.needs_confirmation || false
      this.ambiguities = response_data.ambiguities || []
      this.error = null
      this.error_msg = ''
      this.is_conflict = response_data.is_conflict || false

      if (conflict) {
        this.conflict_detail = conflict.detail || ''
        this.conflict_type = conflict.conflict_type || null
        this.conflict_level = conflict.conflict_level || 'medium'
        this.conflict_task_id = conflict.conflicting_task_id || conflict.task_id || null
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

      const temporaryId = `task_${Date.now()}`
      const task = {
        id: temporaryId,
        task_id: temporaryId,
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
        this.active_task = task
        this.pending_task = task
        this.island_state = 'warning'
      } else {
        this.active_task = task
        this.pending_task = task
        this.island_state = 'candidate'
      }

      return { success: true, data: response_data }
    },

    _schedule_reminder(task) {
      if (!task?.start_time) return

      const now = Date.now()
      const start = new Date(task.start_time).getTime()
      const diff = start - now

      if (diff <= 0) {
        this.active_task = task
        this.pending_task = null
        this.island_state = 'reminder'
      } else if (diff <= this.reminder_threshold) {
        this.active_task = task
        this.pending_task = null
        this.island_state = 'tracking'
      } else {
        this.active_task = task
        this.pending_task = task
        this.island_state = 'tracking'
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

            this.active_task = {
              ...raw_data,
              source_text
            }
            this.is_conflict = !!raw_data.is_conflict
            this.island_state = 'candidate'

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
      if (this.system_notification_permission && this.system_notification_enabled) {
        Promise.resolve().then(() => this.drain_system_notification_queue())
      }
    },

    clearActiveTask() {
      this.clear_active_task()
    },

    acknowledge_reminder() {
      if (this.island_state !== 'reminder') return
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
          await this.register_task_notifications(created_task)
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
          await this.register_task_notifications(created_task)
          this.clear_active_task()
          return created_task
        }
        return null
      } catch (error) {
        this.error = error.message
        return null
      }
    },

    async confirm_conflicting_task() {
      const conflict_task = this.pending_task || this.active_task
      if (!conflict_task) {
        this.error = '没有可创建的冲突日程'
        this.error_msg = this.error
        return null
      }

      const task_data = {
        source_text: conflict_task.source_text || this.captured_text || '',
        parsed: {
          title: conflict_task.title,
          start_time: conflict_task.start_time,
          end_time: conflict_task.end_time,
          location: conflict_task.location,
          participants: conflict_task.participants || [],
          timezone: conflict_task.timezone || 'Asia/Shanghai'
        },
        priority: conflict_task.priority || 'normal',
        reminder_policy: conflict_task.reminder_policy,
        meta: {
          input_type: conflict_task.input_type || 'manual',
          language: 'zh-CN'
        }
      }

      try {
        const result = await apiService.create_task(task_data)
        const response = result.data || {}
        const response_data = response.data || {}

        if (!result.success || response.code !== 0 || !response_data.task_id) {
          this.error = String(response.code || result.error || '3001')
          this.error_msg = response.message || result.error || '任务创建失败，请重试'
          return null
        }

        const created_task = {
          ...conflict_task,
          task_id: response_data.task_id,
          status: response_data.status || 'scheduled',
          is_conflict: false,
          conflict_detail: '',
          conflict_type: null,
          conflict_level: null,
          suggestions: []
        }

        this.tasks.push(created_task)
        await this.register_task_notifications(created_task)
        this.error = null
        this.error_msg = ''
        this.clear_active_task()
        await this.fetch_latest_tasks()
        return created_task
      } catch (error) {
        this.error = error.message
        this.error_msg = error.message || '任务创建失败，请重试'
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
      void this.register_task_notifications(new_task)
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
      const expiredIndex = this.expired_tasks.findIndex(t => t.id === task_id || t.task_id === task_id)
      if (expiredIndex > -1) this.expired_tasks.splice(expiredIndex, 1)
      void notificationService.cancelTask(task_id)
    },

    connect_web_socket() {
      if (this.ws) {
        this.ws.close()
      }

      try {
        this._disconnected = false
        this.ws = new WebSocket(apiService.get_websocket_url())

        this.ws.onmessage = async (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'REMINDER') {
              const task = this.tasks.find(t => t.task_id === data.task_id)
              if (task) {
                this.active_task = task
                this.island_state = 'reminder'
                this._show_reminder_toast(data.title)
              } else {
                this.active_task = { title: data.title, task_id: data.task_id }
                this.island_state = 'reminder'
              }
              this.fetch_latest_tasks()
            } else if (data.type === 'TASK_UPDATED') {
              await this.fetch_latest_tasks()
              this._notifications_initialized = false
              await this.initialize_local_notifications()
            } else if (data.type === 'schedule_sniff' && data.text) {
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

    _show_reminder_toast(title) {
      if (typeof window !== 'undefined' && window.showToast) {
        window.showToast(`任务提醒: ${title}`)
      }
    },

    disconnect_web_socket() {
      this._disconnected = true
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
      this._stop_reminder_timer()
      this._stop_poll()
    },

    async delete_task(task_id) {
      try {
        const result = await apiService.delete_task(task_id)
        if (result.success && result.data) {
          const response = result.data
          if (response.code === 0) {
            const idx = this.tasks.findIndex(t => t.task_id === task_id)
            if (idx > -1) this.tasks.splice(idx, 1)
            const expiredIdx = this.expired_tasks.findIndex(t => t.task_id === task_id)
            if (expiredIdx > -1) this.expired_tasks.splice(expiredIdx, 1)
            await notificationService.cancelTask(task_id)
            this.error = null
            this.error_msg = ''
            return true
          }
          this.error = String(response.code)
          this.error_msg = ERROR_MESSAGES[response.code] || response.message || '删除失败'
          return false
        }
        this.error = result.error
        this.error_msg = ERROR_MESSAGES[parseInt(result.error)] || result.error
        return false
      } catch (error) {
        this.error = error.message
        this.error_msg = ERROR_MESSAGES[parseInt(error.message)] || error.message
        return false
      }
    },

    async delete_all_expired() {
      const expiredTaskIds = this.expired_tasks.map(task => task.task_id || task.id).filter(Boolean)
      const result = await apiService.delete_expired_tasks()
      if (result.success && result.data?.code === 0) {
        const deletedCount = result.data.data?.deleted_count || 0
        await Promise.all(expiredTaskIds.map(taskId => notificationService.cancelTask(taskId)))
        this.expired_tasks = []
        this.error = null
        this.error_msg = ''
        return deletedCount
      }
      this.error = result.data?.code ? String(result.data.code) : result.error
      this.error_msg = result.data?.message || result.error || '清空过期日程失败'
      return null
    },

    async toggleTaskStatus(task) {
      const task_id = task.task_id || task.id
      const currentStatus = task.status || 'pending'
      if (currentStatus === 'expired') return false

      const newStatus = currentStatus === 'completed' ? 'scheduled' : 'completed'

      const idx = this.tasks.findIndex(t => (t.task_id || t.id) === task_id)
      if (idx > -1) {
        this.tasks[idx] = { ...this.tasks[idx], status: newStatus }
      }

      try {
        const result = await apiService.update_task_status(task_id, newStatus)
        if (result.success && result.data) {
          const response = result.data
          if (response.code === 0) {
            const updatedTask = idx > -1 ? this.tasks[idx] : { ...task, status: newStatus }
            if (newStatus === 'completed') {
              await notificationService.cancelTask(task_id)
            } else {
              await this.rebuild_task_notifications(updatedTask)
            }
            this.error = null
            this.error_msg = ''
            return true
          }
          if (idx > -1) {
            this.tasks[idx] = { ...this.tasks[idx], status: currentStatus }
          }
          this.error = String(response.code)
          this.error_msg = ERROR_MESSAGES[response.code] || response.message || '状态更新失败'
          return false
        }
        if (idx > -1) {
          this.tasks[idx] = { ...this.tasks[idx], status: currentStatus }
        }
        this.error = result.error
        this.error_msg = ERROR_MESSAGES[parseInt(result.error)] || result.error
        return false
      } catch (error) {
        if (idx > -1) {
          this.tasks[idx] = { ...this.tasks[idx], status: currentStatus }
        }
        this.error = error.message
        this.error_msg = ERROR_MESSAGES[parseInt(error.message)] || error.message
        return false
      }
    }
  }
})
