<template>
  <div class="min-h-screen bg-neutral-950">
    <div class="fixed top-0 left-0 right-0 z-50 flex justify-center pt-3 pointer-events-none">
      <ScheduleIsland class="pointer-events-auto" />
    </div>

    <main class="max-w-lg mx-auto px-4 pt-24 pb-8">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-white">日程猎人</h1>
          <p class="text-neutral-500 text-sm mt-1">Schedule Hunter</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="toggleMode"
            class="px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all"
            :class="store.isMockMode ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'"
          >
            {{ store.modeLabel }}
          </button>
          <button
            @click="showAddModal = true"
            class="w-10 h-10 rounded-xl bg-green-600 hover:bg-green-500 flex items-center justify-center transition-colors"
          >
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
      </div>

      <Transition name="mode-toast">
        <div
          v-if="showModeToast"
          class="mb-4 px-4 py-2 rounded-xl text-sm font-medium text-center"
          :class="store.isMockMode ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'"
        >
          {{ store.isMockMode ? 'MOCK 模式已启用' : 'API 模式已启用' }}
        </div>
      </Transition>

      <div class="mb-6">
        <CalendarGrid
          :marked-dates="store.markedDates"
          @select="handleDateSelect"
        />
      </div>

      <div>
        <BountyList :tasks="store.todayTasks" />
      </div>

      <div class="mt-8 pt-6 border-t border-white/5">
        <h3 class="text-neutral-500 text-xs font-medium uppercase tracking-wider mb-3">数据嗅探测试</h3>
        <div class="flex gap-2">
          <input
            v-model="sniffText"
            type="text"
            placeholder="输入日程文本测试解析..."
            class="flex-1 bg-neutral-900 text-white text-sm rounded-lg px-3 py-2.5 border border-white/10 focus:border-green-500/50 outline-none"
            @keyup.enter="handleSniff"
          />
          <button
            @click="handleSniff"
            class="px-4 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-white text-sm rounded-lg transition-colors"
          >
            解析
          </button>
        </div>
        <p v-if="store.capturedText" class="text-neutral-500 text-xs mt-2">
          最近捕获: {{ store.capturedText }}
        </p>
      </div>
    </main>

    <AddTaskModal
      :show="showAddModal"
      @close="showAddModal = false"
      @added="handleTaskAdded"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useTaskStore } from '@/stores/useTaskStore'
import ScheduleIsland from './Island/ScheduleIsland.vue'
import CalendarGrid from './CalendarGrid.vue'
import BountyList from './BountyList.vue'
import AddTaskModal from './AddTaskModal.vue'

const store = useTaskStore()
const showAddModal = ref(false)
const sniffText = ref('')
const showModeToast = ref(false)

function toggleMode() {
  store.toggleMockMode()
  showModeToast.value = true
  setTimeout(() => {
    showModeToast.value = false
  }, 2000)
}

function handleDateSelect(dateStr) {
  console.log('Selected date:', dateStr)
}

function handleTaskAdded(task) {
  console.log('Task added:', task)
}

async function handleSniff() {
  if (!sniffText.value.trim()) return
  await store.sniffingHandler(sniffText.value)
  sniffText.value = ''
}

onMounted(() => {
  store.fetchLatestTasks()
})
</script>

<style scoped>
.mode-toast-enter-active,
.mode-toast-leave-active {
  transition: all 0.3s ease;
}
.mode-toast-enter-from,
.mode-toast-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
