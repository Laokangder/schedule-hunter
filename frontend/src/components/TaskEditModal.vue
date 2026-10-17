<template>
  <div v-if="store.editing_task" class="modal-backdrop" @click.self="store.close_task_editor()">
    <form class="modal-card" @submit.prevent="save">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[.2em] text-blue-400">Edit schedule</p>
          <h2 class="mt-1 text-xl font-semibold text-white">编辑日程</h2>
        </div>
        <button type="button" class="text-neutral-500 hover:text-white" @click="store.close_task_editor()">关闭</button>
      </div>
      <div class="mt-6 grid gap-4">
        <label class="label">标题<input v-model="form.title" required class="field" /></label>
        <label class="label">开始时间<input v-model="form.start_time" required type="datetime-local" class="field" /></label>
        <label class="label">结束时间<input v-model="form.end_time" required type="datetime-local" class="field" /></label>
        <label class="label">地点<input v-model="form.location" class="field" /></label>
      </div>
      <p v-if="error" class="mt-4 text-sm text-red-400">{{ error }}</p>
      <div class="mt-6 flex justify-end gap-3">
        <button type="button" class="rounded-xl px-4 py-2.5 text-sm text-neutral-400" @click="store.close_task_editor()">取消</button>
        <button type="submit" class="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50" :disabled="saving">{{ saving ? '保存中…' : '保存并重建提醒' }}</button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useTaskStore } from '@/stores/useTaskStore'

const store = useTaskStore()
const saving = ref(false)
const error = ref('')
const form = reactive({ title: '', start_time: '', end_time: '', location: '' })

function localInput(value) {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

watch(() => store.editing_task, task => {
  if (!task) return
  form.title = task.title || ''
  form.start_time = localInput(task.start_time)
  form.end_time = localInput(task.end_time || (task.start_time ? new Date(task.start_time).getTime() + 60 * 60_000 : ''))
  form.location = task.location || ''
  error.value = ''
}, { immediate: true })

async function save() {
  const start = new Date(form.start_time)
  const end = new Date(form.end_time)
  if (!(end > start)) {
    error.value = '结束时间必须晚于开始时间'
    return
  }
  saving.value = true
  error.value = ''
  const taskId = store.editing_task.task_id || store.editing_task.id
  const updated = await store.update_task_details(taskId, {
    title: form.title.trim(),
    start_time: start.toISOString(),
    end_time: end.toISOString(),
    location: form.location.trim()
  })
  if (!updated) error.value = store.error_msg || '保存失败'
  saving.value = false
}
</script>

<style scoped>
.modal-backdrop { position: fixed; z-index: 100; inset: 0; display: flex; align-items: center; justify-content: center; padding: 1.25rem; background: rgba(0,0,0,.72); backdrop-filter: blur(12px); }
.modal-card { width: min(100%, 32rem); border: 1px solid rgba(255,255,255,.1); border-radius: 1.5rem; padding: 1.4rem; background: #111318; box-shadow: 0 28px 90px rgba(0,0,0,.55); }
.label { display: grid; gap: .5rem; color: #a3a3a3; font-size: .78rem; }
.field { width: 100%; border: 1px solid rgba(255,255,255,.09); border-radius: .85rem; padding: .8rem .9rem; color: white; background: rgba(255,255,255,.035); outline: none; }
.field:focus { border-color: rgba(59,130,246,.75); }
</style>
