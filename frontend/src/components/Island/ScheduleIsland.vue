<template>
  <div class="fixed top-4 left-1/2 -translate-x-1/2 z-[9999] flex items-center justify-center">
    <Transition
      name="island"
      mode="out-in"
      enter-active-class="transition-all duration-500 ease-out"
      leave-active-class="transition-all duration-300 ease-in"
    >
      <div
        v-if="isIdle"
        key="idle"
        class="h-8 px-4 bg-black/80 backdrop-blur-xl rounded-full flex items-center justify-center border border-white/10 cursor-pointer hover:bg-black/70 transition-colors"
        style="min-width: 48px;"
      >
        <div class="w-2 h-2 bg-neutral-500 rounded-full"></div>
      </div>

      <div
        v-else-if="isTracking"
        key="tracking"
        class="px-5 py-3 bg-black/90 backdrop-blur-2xl rounded-2xl flex items-center gap-4 border border-white/10 shadow-2xl shadow-black/50 cursor-pointer"
        style="min-width: 220px;"
        @click="handleTrackingClick"
      >
        <div class="w-10 h-10 bg-neutral-800 rounded-xl flex items-center justify-center flex-shrink-0">
          <span class="text-base">{{ taskIcon }}</span>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-white text-sm font-medium truncate">{{ activeTask?.title }}</p>
          <p class="text-neutral-400 text-xs font-mono mt-0.5">{{ countdownText }}</p>
        </div>
        <div
          class="w-2 h-2 rounded-full flex-shrink-0"
          :class="urgencyClass"
        ></div>
      </div>

      <div
        v-else-if="isWarning"
        key="warning"
        class="px-5 py-4 bg-red-950/90 backdrop-blur-2xl rounded-2xl border border-red-500/30 shadow-2xl shadow-red-500/10"
        style="min-width: 320px;"
        :class="{ 'animate-pulse': true }"
      >
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-red-900/50 rounded-xl flex items-center justify-center">
            <span class="text-lg">⚠️</span>
          </div>
          <div>
            <p class="text-red-400 text-xs font-medium uppercase tracking-wider">Conflict Alert</p>
            <p class="text-white text-sm font-semibold mt-0.5">日程冲突</p>
          </div>
        </div>
        <p class="text-red-300/80 text-sm leading-relaxed">{{ conflictMessage }}</p>
        <div class="flex gap-2 mt-3">
          <button
            class="flex-1 px-3 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-lg text-red-300 text-xs font-medium transition-colors"
            @click="handleDismiss"
          >
            忽略
          </button>
          <button
            class="flex-1 px-3 py-2 bg-white/10 hover:bg-white/20 border border-white/10 rounded-lg text-white text-xs font-medium transition-colors"
            @click="handleReschedule"
          >
            调整时间
          </button>
          <button
            class="flex-1 px-3 py-2 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-lg text-blue-300 text-xs font-medium transition-colors"
            @click="handleConfirmAnyway"
          >
            确认创建
          </button>
        </div>
      </div>

      <div
        v-else-if="isReminder"
        key="reminder"
        class="px-6 py-4 bg-gradient-to-b from-neutral-900 to-neutral-950 backdrop-blur-2xl rounded-2xl border border-white/20 shadow-2xl"
        style="min-width: 340px;"
      >
        <div class="flex items-center gap-4 mb-4">
          <div class="w-12 h-12 bg-blue-600/30 rounded-xl flex items-center justify-center">
            <span class="text-2xl">🔔</span>
          </div>
          <div>
            <p class="text-blue-400 text-xs font-medium uppercase tracking-wider">Reminder</p>
            <p class="text-white text-lg font-semibold mt-0.5">{{ activeTask?.title }}</p>
          </div>
        </div>
        <div class="bg-white/5 rounded-xl p-3 mb-4">
          <p class="text-neutral-300 text-sm">{{ activeTask?.location || '未设置地点' }}</p>
          <p class="text-neutral-500 text-xs mt-1 font-mono">{{ formatTime(activeTask?.start_time) }}</p>
        </div>
        <div class="flex gap-3">
          <button
            class="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-500 rounded-xl text-white text-sm font-semibold transition-colors"
            @click="handleCancel"
          >
            取消
          </button>
          <button
            class="flex-1 px-4 py-2.5 bg-neutral-700 hover:bg-neutral-600 rounded-xl text-white text-sm font-semibold transition-colors"
            @click="handlePostpone"
          >
            推迟
          </button>
          <button
            class="flex-1 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-white text-sm font-semibold transition-colors"
            @click="handleConfirm"
          >
            确认
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useTaskStore } from '@/stores/useTaskStore'

const store = useTaskStore()

const isIdle = computed(() => store.island_state === 'idle')
const isTracking = computed(() => store.island_state === 'tracking')
const isWarning = computed(() => store.island_state === 'warning')
const isReminder = computed(() => store.island_state === 'reminder')
const activeTask = computed(() => store.active_task)

const taskIcon = computed(() => {
  if (!activeTask.value) return '📅'
  const icons = ['📅', '📝', '🎯', '💼', '🏠', '✈️', '🎨', '📞']
  const title = activeTask.value.title || ''
  const index = title.charCodeAt(0) % icons.length
  return icons[index]
})

const countdownText = computed(() => {
  if (!activeTask.value?.start_time) return '--:--'
  const now = Date.now()
  const start = new Date(activeTask.value.start_time).getTime()
  const diff = start - now
  if (diff <= 0) return '即将开始'
  const hours = Math.floor(diff / 3600000)
  const minutes = Math.floor((diff % 3600000) / 60000)
  if (hours > 0) {
    return `${hours}小时${minutes}分`
  }
  return `${minutes}分钟`
})

const urgencyClass = computed(() => {
  if (!activeTask.value?.start_time) return 'bg-green-500'
  const now = Date.now()
  const start = new Date(activeTask.value.start_time).getTime()
  const diff = start - now
  const minute = 60000
  if (diff <= 0) return 'bg-red-500 animate-pulse'
  if (diff <= 10 * minute) return 'bg-red-500 animate-pulse'
  if (diff <= 30 * minute) return 'bg-orange-500 animate-pulse'
  return 'bg-green-500'
})

const conflictMessage = computed(() => {
  return store.conflict_detail || '检测到日程冲突，请确认是否继续'
})

const formatTime = (isoString) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const handleTrackingClick = () => {
  store.clearActiveTask()
}

const handleDismiss = () => {
  store.clearActiveTask()
}

const handleReschedule = () => {
  store.clearActiveTask()
}

const handleConfirmAnyway = () => {
  store.is_conflict = false
  store.island_state = 'tracking'
}

const handleCancel = () => {
  store.clearActiveTask()
}

const handlePostpone = () => {
  if (activeTask.value?.start_time) {
    const newStart = new Date(new Date(activeTask.value.start_time).getTime() + 15 * 60000)
    const newEnd = new Date(new Date(activeTask.value.end_time).getTime() + 15 * 60000)
    store.setActiveTask({
      ...activeTask.value,
      start_time: newStart.toISOString(),
      end_time: newEnd.toISOString()
    })
  }
}

const handleConfirm = async () => {
  await store.create_task_from_active()
}
</script>

<style scoped>
.island-enter-from {
  opacity: 0;
  transform: scale(0.8) translateX(-50%);
}
.island-leave-to {
  opacity: 0;
  transform: scale(0.9) translateX(-50%);
}
</style>
