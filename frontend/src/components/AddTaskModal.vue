<template>
  <div
    v-if="show"
    class="fixed inset-0 z-[100] flex items-center justify-center p-4"
    @click.self="close"
  >
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm"></div>

    <div class="relative w-full max-w-sm bg-neutral-900 rounded-2xl border border-white/10 overflow-hidden">
      <div class="p-4 border-b border-white/5">
        <h3 class="text-lg font-semibold text-white">添加新日程</h3>
      </div>

      <div class="p-4 space-y-4" v-if="!submitting">
        <div>
          <label class="block text-xs text-neutral-500 mb-1.5">任务标题</label>
          <input
            v-model="form.title"
            type="text"
            placeholder="输入任务标题"
            class="w-full bg-neutral-800 text-white rounded-lg px-3 py-2.5 text-sm border border-white/10 focus:border-green-500/50 outline-none"
          />
        </div>

        <div>
          <label class="block text-xs text-neutral-500 mb-1.5">开始时间</label>
          <input
            v-model="form.start_time"
            type="datetime-local"
            class="w-full bg-neutral-800 text-white rounded-lg px-3 py-2.5 text-sm border border-white/10 focus:border-green-500/50 outline-none"
          />
        </div>

        <div>
          <label class="block text-xs text-neutral-500 mb-1.5">结束时间</label>
          <input
            v-model="form.end_time"
            type="datetime-local"
            class="w-full bg-neutral-800 text-white rounded-lg px-3 py-2.5 text-sm border border-white/10 focus:border-green-500/50 outline-none"
          />
        </div>

        <div>
          <label class="block text-xs text-neutral-500 mb-1.5">地点</label>
          <input
            v-model="form.location"
            type="text"
            placeholder="输入地点（可选）"
            class="w-full bg-neutral-800 text-white rounded-lg px-3 py-2.5 text-sm border border-white/10 focus:border-green-500/50 outline-none"
          />
        </div>
      </div>

      <div v-if="submitting" class="p-8 flex flex-col items-center gap-3">
        <div class="w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-neutral-400 text-sm">正在创建日程...</p>
      </div>

      <div v-if="error_msg" class="px-4 pb-2">
        <p class="text-red-400 text-xs">{{ error_msg }}</p>
      </div>

      <div class="p-4 border-t border-white/5 flex gap-3" v-if="!submitting">
        <button
          @click="close"
          class="flex-1 px-4 py-2.5 rounded-xl bg-neutral-800 text-neutral-400 font-medium text-sm hover:bg-neutral-700 transition-colors"
        >
          取消
        </button>
        <button
          @click="handleAdd"
          :disabled="!form.title.trim() || !form.start_time || !form.end_time"
          class="flex-1 px-4 py-2.5 rounded-xl bg-green-600 text-white font-medium text-sm hover:bg-green-500 disabled:bg-neutral-700 disabled:text-neutral-500 disabled:cursor-not-allowed transition-colors"
        >
          添加
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useTaskStore } from '@/stores/useTaskStore'
import { create_task } from '@/services/apiService'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'added'])

const store = useTaskStore()

const form = ref({
  title: '',
  start_time: '',
  end_time: '',
  location: ''
})

const submitting = ref(false)
const error_msg = ref('')

function to_local_datetime_string(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

function to_iso_with_timezone(date) {
  const offset = -date.getTimezoneOffset()
  const sign = offset >= 0 ? '+' : '-'
  const abs_offset = Math.abs(offset)
  const tz_hours = String(Math.floor(abs_offset / 60)).padStart(2, '0')
  const tz_minutes = String(abs_offset % 60).padStart(2, '0')
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}${sign}${tz_hours}:${tz_minutes}`
}

watch(() => props.show, (val) => {
  if (val) {
    const now = new Date()
    now.setMinutes(0)
    now.setSeconds(0)
    now.setMilliseconds(0)
    const end = new Date(now.getTime() + 3600000)
    form.value = {
      title: '',
      start_time: to_local_datetime_string(now),
      end_time: to_local_datetime_string(end),
      location: ''
    }
    error_msg.value = ''
  }
})

function close() {
  if (submitting.value) return
  emit('close')
}

async function handleAdd() {
  if (!form.value.title.trim() || !form.value.start_time || !form.value.end_time) return

  const start_date = new Date(form.value.start_time)
  const end_date = new Date(form.value.end_time)

  if (end_date <= start_date) {
    error_msg.value = '结束时间必须晚于开始时间'
    return
  }

  const parsed = {
    title: form.value.title.trim(),
    start_time: to_iso_with_timezone(start_date),
    end_time: to_iso_with_timezone(end_date),
    location: form.value.location.trim() || null,
    participants: [],
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
  }

  const task_data = {
    source_text: parsed.title,
    parsed: parsed,
    priority: 'normal',
    reminder_policy: {
      enabled: true,
      offset_minutes: [30, 10, 5]
    },
    meta: {
      input_type: 'manual',
      language: 'zh-CN',
      client_timestamp: new Date().toISOString()
    }
  }

  submitting.value = true
  error_msg.value = ''

  try {
    const result = await create_task(task_data)

    if (result.success && result.data) {
      const response_data = result.data.data || result.data

      if (result.data.code === 0 || response_data.task_id) {
        const task = {
          id: response_data.task_id || `task_${Date.now()}`,
          task_id: response_data.task_id,
          title: parsed.title,
          start_time: parsed.start_time,
          end_time: parsed.end_time,
          location: parsed.location,
          participants: [],
          is_conflict: false,
          has_warning: false,
          status: response_data.status || 'scheduled'
        }

        store.tasks.push(task)
        store.setActiveTask(task)
        store.island_state = 'tracking'

        emit('added', task)
        close()
      } else {
        error_msg.value = result.data.message || '创建失败，请重试'
      }
    } else {
      error_msg.value = result.error || '网络错误，请重试'
    }
  } catch (error) {
    error_msg.value = error.message || '创建失败，请重试'
  } finally {
    submitting.value = false
  }
}
</script>
