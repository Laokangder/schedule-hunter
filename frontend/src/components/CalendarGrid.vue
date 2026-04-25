<template>
  <div class="bg-neutral-900/50 rounded-2xl p-4 border border-white/5">
    <div class="flex items-center justify-between mb-4">
      <button
        @click="prevMonth"
        class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-neutral-800 text-neutral-400 hover:text-white transition-colors"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <div class="text-center">
        <h3 class="text-white font-semibold">{{ year }}.{{ String(month + 1).padStart(2, '0') }}</h3>
        <p class="text-xs text-neutral-500">{{ weekDays[locale]?.[new Date(year, month, 1).getDay()] || '' }}</p>
      </div>
      <button
        @click="nextMonth"
        class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-neutral-800 text-neutral-400 hover:text-white transition-colors"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>

    <div class="grid grid-cols-7 gap-1 mb-2">
      <div
        v-for="day in weekDays[locale]"
        :key="day"
        class="text-center text-xs text-neutral-500 py-2 font-mono"
      >
        {{ day }}
      </div>
    </div>

    <div class="grid grid-cols-7 gap-1">
      <div
        v-for="(day, index) in calendarDays"
        :key="index"
        class="relative aspect-square"
      >
        <button
          v-if="day"
          @click="selectDate(day)"
          class="w-full h-full flex flex-col items-center justify-center rounded-lg transition-all font-mono text-sm relative"
          :class="[
            isToday(day) ? 'text-green-400' : isSelected(day) ? 'text-white' : 'text-neutral-400',
            isSelected(day) ? 'bg-neutral-800 ring-1 ring-green-500' : 'hover:bg-neutral-800/50'
          ]"
        >
          <span>{{ day }}</span>
          <span
            v-if="hasTask(day)"
            class="absolute bottom-1 w-1 h-1 rounded-full bg-green-500"
          ></span>
        </button>
        <div v-else class="w-full h-full"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useTaskStore } from '@/stores/useTaskStore'

const store = useTaskStore()

const props = defineProps({
  markedDates: {
    type: Array,
    default: () => []
  }
})

const locale = 'zh'
const weekDays = {
  zh: ['日', '一', '二', '三', '四', '五', '六']
}

const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth())

const calendarDays = computed(() => {
  const firstDay = new Date(year.value, month.value, 1).getDay()
  const daysInMonth = new Date(year.value, month.value + 1, 0).getDate()
  const days = []

  for (let i = 0; i < firstDay; i++) {
    days.push(null)
  }

  for (let i = 1; i <= daysInMonth; i++) {
    days.push(i)
  }

  return days
})

function prevMonth() {
  if (month.value === 0) {
    month.value = 11
    year.value--
  } else {
    month.value--
  }
}

function nextMonth() {
  if (month.value === 11) {
    month.value = 0
    year.value++
  } else {
    month.value++
  }
}

function isToday(day) {
  return (
    day === today.getDate() &&
    month.value === today.getMonth() &&
    year.value === today.getFullYear()
  )
}

function isSelected(day) {
  const dateStr = `${year.value}-${String(month.value + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  return dateStr === store.selected_date
}

function hasTask(day) {
  const dateStr = `${year.value}-${String(month.value + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  return props.markedDates.includes(dateStr)
}

function selectDate(day) {
  const dateStr = `${year.value}-${String(month.value + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  store.setSelectedDate(dateStr)
}
</script>
