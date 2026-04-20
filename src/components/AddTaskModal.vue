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

      <div class="p-4 space-y-4">
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
          <label class="block text-xs text-neutral-500 mb-1.5">地点</label>
          <input
            v-model="form.location"
            type="text"
            placeholder="输入地点（可选）"
            class="w-full bg-neutral-800 text-white rounded-lg px-3 py-2.5 text-sm border border-white/10 focus:border-green-500/50 outline-none"
          />
        </div>
      </div>

      <div class="p-4 border-t border-white/5 flex gap-3">
        <button
          @click="close"
          class="flex-1 px-4 py-2.5 rounded-xl bg-neutral-800 text-neutral-400 font-medium text-sm hover:bg-neutral-700 transition-colors"
        >
          取消
        </button>
        <button
          @click="handleAdd"
          :disabled="!form.title.trim() || !form.start_time"
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
  location: ''
})

watch(() => props.show, (val) => {
  if (val) {
    const now = new Date()
    now.setHours(now.getHours() + 1)
    now.setMinutes(0)
    form.value = {
      title: '',
      start_time: now.toISOString().slice(0, 16),
      location: ''
    }
  }
})

function close() {
  emit('close')
}

function handleAdd() {
  if (!form.value.title.trim() || !form.value.start_time) return

  const startDate = new Date(form.value.start_time)
  const endDate = new Date(startDate.getTime() + 3600000)

  const task = {
    id: `task_${Date.now()}`,
    title: form.value.title.trim(),
    start_time: startDate.toISOString(),
    end_time: endDate.toISOString(),
    location: form.value.location.trim(),
    is_conflict: false,
    has_warning: false
  }

  store.tasks.push(task)
  store.setActiveTask(task)
  store.islandState = 'tracking'

  emit('added', task)
  close()
}
</script>
