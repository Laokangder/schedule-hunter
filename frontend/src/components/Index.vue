<template>
  <div class="min-h-screen bg-neutral-950">
    <div class="fixed top-0 left-0 right-0 z-50 flex justify-center pt-3 pointer-events-none">
      <ScheduleIsland class="pointer-events-auto" />
    </div>

    <main class="max-w-2xl mx-auto px-6 pt-28 pb-8">
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-3xl font-bold text-white">日程猎人</h1>
          <p class="text-neutral-500 text-sm mt-1">Schedule Hunter</p>
        </div>
        <button
          @click="toggleMode"
          class="px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all"
          :class="store.is_mock_mode ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'"
        >
          {{ store.mode_label }}
        </button>
      </div>

      <div class="mb-8">
        <div class="bg-gradient-to-b from-neutral-900/80 to-neutral-950/80 rounded-3xl border border-neutral-800/60 p-6 shadow-2xl shadow-black/40">
          <div class="flex items-center gap-2 mb-4">
            <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            <span class="text-blue-400 text-sm font-semibold tracking-wide">AI 智能嗅探</span>
          </div>
          <textarea
            v-model="sniffText"
            @keyup.enter="handleSniff"
            placeholder="输入一段大白话，例如：明天下午3点去望京SOHO找张总谈合作"
            class="w-full bg-neutral-800/40 border border-neutral-700/60 rounded-2xl px-5 py-4 text-white text-base placeholder-neutral-500 resize-none focus:outline-none focus:border-blue-500/60 focus:ring-1 focus:ring-blue-500/20 transition-all"
            rows="4"
          ></textarea>
          <div class="flex items-center gap-3 mt-4">
            <button
              @click="handleSniff"
              class="flex-1 py-3 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 rounded-xl text-white text-sm font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-blue-600/20"
              :disabled="!sniffText.trim() || store.is_loading"
            >
              <svg v-if="!store.is_loading" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              <svg v-else class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>{{ store.is_loading ? '解析中...' : '智能解析' }}</span>
            </button>
          </div>
        </div>
      </div>

      <div class="mb-6">
        <CalendarGrid
          :marked-dates="store.marked_dates"
        />
      </div>

      <div>
        <div class="flex items-center gap-2 mb-4">
          <h2 class="text-lg font-bold text-white">{{ pageTitle }}</h2>
          <span class="text-xs text-neutral-500 font-mono">{{ store.selected_date }}</span>
        </div>
        <BountyList :tasks="store.today_tasks" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useTaskStore } from '@/stores/useTaskStore'
import ScheduleIsland from './Island/ScheduleIsland.vue'
import CalendarGrid from './CalendarGrid.vue'
import BountyList from './BountyList.vue'

const store = useTaskStore()
const sniffText = ref('')

function toggleMode() {
  store.toggle_mock_mode()
}

const pageTitle = computed(() => {
  const today = new Date().toISOString().split('T')[0]
  return store.selected_date === today ? '今日悬赏' : `${store.selected_date} 悬赏`
})

async function handleSniff() {
  if (!sniffText.value.trim()) return
  console.log('🚀 [INPUT] 用户输入已发出:', sniffText.value)
  await store.handle_native_sniff(sniffText.value)
  sniffText.value = ''
}

function handleNativeSniff(sourceText, inputType = 'manual') {
  return store.handle_native_sniff(sourceText, inputType)
}

onMounted(() => {
  window.handleNativeSniff = handleNativeSniff
  store.fetch_latest_tasks()
})

onUnmounted(() => {
  if (window.handleNativeSniff === handleNativeSniff) {
    delete window.handleNativeSniff
  }
})
</script>

<style scoped>
</style>
