<template>
  <div>
    <div v-if="tasks.length === 0" class="empty-state">
      <span class="empty-line"></span>
      <p>{{ emptyText }}</p>
    </div>

    <div v-else class="timeline-list">
      <article
        v-for="task in sortedTasks"
        :key="task.task_id || task.id"
        class="timeline-row group"
        :class="{ 'timeline-row--muted': isCompleted(task) || isExpired(task) }"
      >
        <button
          type="button"
          class="timeline-content"
          :disabled="isExpired(task)"
          @click="!isExpired(task) && trackTask(task)"
        >
          <span class="timeline-dot" :class="dotClass(task)"></span>
          <time class="timeline-time">{{ formatTime(task.start_time) }}</time>
          <span class="min-w-0 flex-1">
            <span class="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span class="task-title" :class="{ 'line-through': isCompleted(task) }">{{ task.title }}</span>
              <span v-if="isExpired(task)" class="status-text text-red-400">已过期</span>
              <span v-else-if="isCompleted(task)" class="status-text text-emerald-400">已完成</span>
              <span v-else-if="task.is_conflict" class="status-text text-red-400">有冲突</span>
              <span v-else-if="isStartingSoon(task)" class="status-text text-amber-400">即将开始</span>
            </span>
            <span class="task-meta">
              <svg v-if="task.location" class="h-3.5 w-3.5 flex-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 21s6-5.1 6-11a6 6 0 10-12 0c0 5.9 6 11 6 11z" />
                <circle cx="12" cy="10" r="2" stroke-width="1.8" />
              </svg>
              {{ task.location || formatDuration(task) }}
            </span>
          </span>
        </button>

        <div class="row-actions">
          <button
            v-if="!isExpired(task)"
            type="button"
            class="row-action hover:text-blue-400"
            aria-label="编辑日程"
            title="编辑日程"
            @click="store.open_task_editor(task)"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4 20h4l11-11-4-4L4 16v4zM13.5 6.5l4 4" /></svg>
          </button>
          <button
            v-if="!isExpired(task)"
            type="button"
            class="row-action hover:text-emerald-400"
            :aria-label="isCompleted(task) ? '恢复日程' : '标记完成'"
            :title="isCompleted(task) ? '恢复日程' : '标记完成'"
            @click="toggleStatus(task)"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="8" stroke-width="1.8" />
              <path d="M8.5 12l2.3 2.3 4.8-5" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" />
            </svg>
          </button>
          <button type="button" class="row-action hover:text-red-400" aria-label="删除日程" title="删除日程" @click="deleteTask(task)">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M5 7h14M9 7V4h6v3m2 0l-1 13H8L7 7m3 4v5m4-5v5" />
            </svg>
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useTaskStore } from '@/stores/useTaskStore'

const props = defineProps({
  tasks: { type: Array, default: () => [] },
  title: { type: String, default: '日程' },
  emptyText: { type: String, default: '暂无日程' }
})

const store = useTaskStore()
const sortedTasks = computed(() => props.tasks.slice().sort((a, b) => new Date(a.start_time) - new Date(b.start_time)))

function formatTime(value) {
  if (!value) return '--:--'
  const date = new Date(value)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function formatDuration(task) {
  if (!task.start_time || !task.end_time) return '未设置地点'
  const minutes = Math.max(0, Math.round((new Date(task.end_time) - new Date(task.start_time)) / 60000))
  if (minutes < 60) return `${minutes} 分钟`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return `${hours} 小时${rest ? ` ${rest} 分钟` : ''}`
}

function isCompleted(task) { return task.status === 'completed' }

function isExpired(task) {
  if (task.status === 'expired') return true
  if (!task.start_time) return false
  const end = new Date(task.end_time || task.start_time).getTime()
  return Number.isFinite(end) && end < Date.now() && !isCompleted(task)
}

function isStartingSoon(task) {
  const diff = new Date(task.start_time).getTime() - Date.now()
  return diff > 0 && diff <= 30 * 60 * 1000
}

function dotClass(task) {
  if (isExpired(task)) return 'bg-red-500/70'
  if (isCompleted(task)) return 'bg-emerald-400'
  if (task.is_conflict) return 'bg-red-500 shadow-red-500/40'
  if (isStartingSoon(task)) return 'bg-amber-400 shadow-amber-400/40'
  return 'bg-blue-500 shadow-blue-500/40'
}

function trackTask(task) {
  store.active_task = task
  store.island_state = 'detail'
}

async function toggleStatus(task) { await store.toggleTaskStatus(task) }

async function deleteTask(task) {
  if (!confirm(`确定要删除日程“${task.title}”吗？`)) return
  await store.delete_task(task.task_id || task.id)
}
</script>

<style scoped>
.empty-state { display: flex; align-items: center; gap: 1rem; min-height: 5rem; color: #666b76; font-size: .875rem; }
.empty-line { width: 1px; height: 3rem; background: linear-gradient(to bottom, rgba(59,130,246,.6), transparent); }
.timeline-list { position: relative; }
.timeline-list::before { position: absolute; top: 1.75rem; bottom: 1.75rem; left: .28rem; width: 1px; content: ''; background: linear-gradient(to bottom, rgba(82,124,230,.44), rgba(255,255,255,.06)); }
.timeline-row { position: relative; display: flex; align-items: stretch; border-bottom: 1px solid rgba(255,255,255,.065); transition: background .2s; }
.timeline-row:last-child { border-bottom: 0; }
.timeline-row:hover { background: linear-gradient(90deg, transparent, rgba(255,255,255,.018), transparent); }
.timeline-row--muted { opacity: .58; }
.timeline-content { display: grid; min-width: 0; flex: 1; grid-template-columns: 1.25rem 4.8rem minmax(0,1fr); align-items: start; padding: 1.35rem 0; text-align: left; }
.timeline-content:disabled { cursor: default; }
.timeline-dot { z-index: 1; width: .58rem; height: .58rem; margin-top: .5rem; border-radius: 999px; box-shadow: 0 0 18px currentColor; }
.timeline-time { color: #f5f5f5; font-size: 1rem; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.55rem; }
.task-title { color: #f5f5f5; font-size: 1rem; font-weight: 600; line-height: 1.55rem; }
.status-text { font-size: .68rem; font-weight: 600; letter-spacing: .04em; }
.task-meta { display: flex; align-items: center; gap: .35rem; margin-top: .35rem; color: #777c87; font-size: .8rem; }
.row-actions { display: flex; align-items: center; gap: .1rem; padding-left: .45rem; }
.row-action { display: flex; width: 2rem; height: 2rem; align-items: center; justify-content: center; border-radius: 999px; color: #555b66; transition: color .2s, background .2s; }
.row-action:hover { background: rgba(255,255,255,.045); }
@media (max-width: 480px) {
  .timeline-content { grid-template-columns: 1.1rem 4rem minmax(0,1fr); }
  .timeline-time, .task-title { font-size: .92rem; }
  .row-actions { flex-direction: column; justify-content: center; padding-left: .2rem; }
}
</style>
