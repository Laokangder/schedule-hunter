<template>
  <div class="bg-neutral-900/50 rounded-2xl p-4 border border-white/5">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-white font-semibold">今日悬赏</h3>
      <span class="text-xs text-neutral-500 font-mono">{{ tasks.length }} TASKS</span>
    </div>

    <div v-if="tasks.length === 0" class="text-center py-8">
      <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-neutral-800/50 flex items-center justify-center">
        <span class="text-2xl">🎯</span>
      </div>
      <p class="text-neutral-500 text-sm">暂无任务</p>
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="task in tasks"
        :key="task.id"
        @click="!isExpired(task) && trackTask(task)"
        class="bg-neutral-800/50 rounded-xl p-3 border border-white/5 hover:border-green-500/30 transition-all cursor-pointer group"
        :class="{ 'opacity-50': isCompleted(task) }"
      >
        <div class="flex items-start gap-3">
          <input
            type="checkbox"
            :checked="isCompleted(task)"
            :disabled="isExpired(task)"
            @click.stop="toggleStatus(task)"
            class="w-5 h-5 rounded border-neutral-600 bg-neutral-700 text-green-500 focus:ring-green-500 focus:ring-offset-0 cursor-pointer mt-1"
          />

          <div
            class="w-10 h-10 rounded-lg flex items-center justify-center font-mono text-xs flex-shrink-0"
            :class="getTimeSlotClass(task)"
          >
            {{ formatRelativeTime(task.start_time) }}
          </div>

          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <h4
                class="text-white font-medium text-sm truncate"
                :class="{ 'line-through text-neutral-500': isCompleted(task) }"
              >
                {{ task.title }}
              </h4>
              <span
                v-if="isExpired(task)"
                class="px-1.5 py-0.5 rounded text-xs font-medium flex-shrink-0 bg-red-500/20 text-red-400"
              >
                已过期
              </span>
              <span
                v-else
                class="px-1.5 py-0.5 rounded text-xs font-medium flex-shrink-0"
                :class="getDifficultyClass(task)"
              >
                {{ getDifficultyLabel(task) }}
              </span>
            </div>

            <div v-if="task.location" class="flex items-center gap-1 text-xs text-neutral-500">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span class="truncate">{{ task.location }}</span>
            </div>
          </div>

          <div class="w-6 h-6 rounded-full bg-green-500/10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <svg class="w-3 h-3 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>

          <button
            @click.stop="deleteTask(task)"
            class="w-6 h-6 rounded-full bg-red-500/10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500/30"
            title="删除任务"
          >
            <svg class="w-3 h-3 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v1M8 5h8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useTaskStore } from '@/stores/useTaskStore'

const props = defineProps({
  tasks: {
    type: Array,
    default: () => []
  }
})

const store = useTaskStore()

function formatRelativeTime(isoString) {
  if (!isoString) return '--:--'
  const now = new Date()
  const date = new Date(isoString)
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const tomorrow = new Date(today.getTime() + 86400000)
  const taskDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())

  if (taskDate.getTime() === today.getTime()) {
    return `今天${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  } else if (taskDate.getTime() === tomorrow.getTime()) {
    return `明天${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  } else {
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    const dayLabel = weekdays[date.getDay()]
    return `${dayLabel}${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }
}

function getTimeSlotClass(task) {
  const hour = new Date(task.start_time).getHours()
  if (hour < 12) {
    return 'bg-amber-500/10 text-amber-400'
  } else if (hour < 18) {
    return 'bg-blue-500/10 text-blue-400'
  } else {
    return 'bg-purple-500/10 text-purple-400'
  }
}

function getDifficultyClass(task) {
  if (task.is_conflict) {
    return 'bg-red-500/20 text-red-400'
  }
  if (task.has_warning) {
    return 'bg-yellow-500/20 text-yellow-400'
  }
  return 'bg-green-500/20 text-green-400'
}

function getDifficultyLabel(task) {
  if (task.is_conflict) {
    return '冲突'
  }
  if (task.has_warning) {
    return '警告'
  }
  return '正常'
}

function isCompleted(task) {
  return task.status === 'completed'
}

function isExpired(task) {
  if (task.status === 'expired') return true
  if (!task.start_time) return false
  const now = Date.now()
  const startTime = new Date(task.start_time).getTime()
  const endTime = task.end_time ? new Date(task.end_time).getTime() : startTime + 3600000
  return endTime < now
}

function trackTask(task) {
  store.active_task = task
  store.island_state = 'detail'
}

async function toggleStatus(task) {
  await store.toggleTaskStatus(task)
}

async function deleteTask(task) {
  if (!confirm(`确定要删除任务"${task.title}"吗？`)) {
    return
  }
  try {
    const result = await store.delete_task(task.task_id || task.id)
    if (result) {
      console.log('✅ 任务删除成功')
    }
  } catch (error) {
    console.error('❌ 删除失败:', error)
  }
}
</script>