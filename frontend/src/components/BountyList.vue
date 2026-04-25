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
        @click="trackTask(task)"
        class="bg-neutral-800/50 rounded-xl p-3 border border-white/5 hover:border-green-500/30 transition-all cursor-pointer group"
      >
        <div class="flex items-start gap-3">
          <div
            class="w-10 h-10 rounded-lg flex items-center justify-center font-mono text-sm flex-shrink-0"
            :class="getTimeSlotClass(task)"
          >
            {{ formatTime(task.start_time) }}
          </div>

          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <h4 class="text-white font-medium text-sm truncate">{{ task.title }}</h4>
              <span
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

function formatTime(isoString) {
  if (!isoString) return '--:--'
  const date = new Date(isoString)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
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

function trackTask(task) {
  store.setActiveTask(task)
  store.island_state = 'tracking'
}
</script>
