<template>
  <div>
    <div v-if="store.pending_candidates.length === 0 && store.snoozed_candidates.length === 0" class="py-16 text-center text-sm text-neutral-500">
      还没有待确认的候选日程
    </div>

    <div class="space-y-4">
      <article v-for="candidate in store.pending_candidates" :key="candidate.candidate_id" class="candidate-card">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="candidate-kind" :class="kindClass(candidate.intent_type)">{{ kindLabel(candidate.intent_type) }}</span>
              <span v-if="candidate.is_conflict" class="candidate-kind bg-red-500/10 text-red-400">有冲突</span>
              <span v-if="candidate.seen_count > 1" class="text-xs text-neutral-500">合并 {{ candidate.seen_count }} 条</span>
            </div>
            <h3 class="mt-3 text-lg font-semibold text-white">{{ candidate.parsed?.title || '未命名日程' }}</h3>
            <p class="mt-2 text-sm text-neutral-400">{{ formatDateTime(candidate.parsed?.start_time) }}</p>
            <p v-if="candidate.parsed?.location" class="mt-1 text-sm text-neutral-500">{{ candidate.parsed.location }}</p>
          </div>
          <button type="button" class="text-xs text-neutral-500 hover:text-white" @click="store.select_candidate(candidate)">查看</button>
        </div>

        <div v-if="changeEntries(candidate).length" class="mt-4 rounded-xl bg-amber-500/[0.06] p-3 text-xs text-amber-200/80">
          <p v-for="(change, index) in changeEntries(candidate)" :key="index">
            {{ change.field || '字段' }}：{{ change.from || '未设置' }} → {{ change.to || change.value || '未设置' }}
          </p>
        </div>

        <div v-if="editingId === candidate.candidate_id" class="mt-4 grid gap-3 rounded-xl border border-white/[0.08] bg-black/20 p-4">
          <input v-model="draft.title" class="field" placeholder="日程标题" />
          <input v-model="draft.start_time" type="datetime-local" class="field" />
          <input v-model="draft.end_time" type="datetime-local" class="field" />
          <input v-model="draft.location" class="field" placeholder="地点" />
          <div class="flex gap-3">
            <button class="small-primary" type="button" @click="saveEdit(candidate)">保存修改</button>
            <button class="small-quiet" type="button" @click="editingId = null">取消</button>
          </div>
        </div>

        <div v-if="slotCandidateId === candidate.candidate_id && store.free_slot_suggestions.length" class="mt-4 space-y-2">
          <button v-for="(slot, index) in store.free_slot_suggestions" :key="index" type="button" class="slot-row" @click="applySlot(candidate, slot)">
            <span>{{ formatDateTime(slot.start_time) }} — {{ formatClock(slot.end_time) }}</span>
            <span class="text-neutral-500">{{ slot.reason || '可用时间' }}</span>
          </button>
        </div>

        <p class="mt-4 line-clamp-2 text-xs leading-5 text-neutral-600">{{ candidate.source_text }}</p>
        <div class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-neutral-600">
          <span>{{ candidate.source_app_name || '未知来源' }}</span>
          <span v-if="candidate.confidence">置信度 {{ Math.round(candidate.confidence * 100) }}%</span>
        </div>

        <div class="mt-5 flex flex-wrap gap-2">
          <button type="button" class="small-primary" @click="confirmCandidate(candidate)">{{ confirmingId === candidate.candidate_id ? '处理中…' : '确认' }}</button>
          <button type="button" class="small-quiet" @click="beginEdit(candidate)">修改</button>
          <button v-if="candidate.is_conflict" type="button" class="small-quiet" @click="findSlots(candidate)">找空档</button>
          <button type="button" class="small-quiet" @click="store.snooze_local_candidate(candidate.candidate_id, 10)">10分钟后</button>
          <button type="button" class="small-quiet" @click="store.snooze_local_candidate(candidate.candidate_id, 60)">1小时后</button>
          <button type="button" class="small-danger" @click="store.ignore_candidate(candidate.candidate_id)">忽略</button>
        </div>
      </article>
    </div>

    <div v-if="store.snoozed_candidates.length" class="mt-10">
      <p class="mb-3 text-xs font-semibold uppercase tracking-[.2em] text-neutral-600">稍后提醒</p>
      <button v-for="candidate in store.snoozed_candidates" :key="candidate.candidate_id" type="button" class="mb-2 flex w-full items-center justify-between rounded-xl border border-white/[0.06] px-4 py-3 text-left" @click="store.select_candidate(candidate)">
        <span class="truncate text-sm text-neutral-300">{{ candidate.parsed?.title }}</span>
        <span class="ml-4 flex-none text-xs text-neutral-600">{{ formatSnoozed(candidate.snoozed_until) }}</span>
      </button>
    </div>

    <p v-if="store.candidate_error" class="mt-5 text-sm text-red-400">{{ store.candidate_error }}</p>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useTaskStore } from '@/stores/useTaskStore'

const store = useTaskStore()
const editingId = ref(null)
const confirmingId = ref(null)
const slotCandidateId = ref(null)
const draft = reactive({ title: '', start_time: '', end_time: '', location: '' })

function localInput(value) {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function beginEdit(candidate) {
  editingId.value = candidate.candidate_id
  draft.title = candidate.parsed?.title || ''
  draft.start_time = localInput(candidate.parsed?.start_time)
  draft.end_time = localInput(candidate.parsed?.end_time)
  draft.location = candidate.parsed?.location || ''
}

async function saveEdit(candidate) {
  const saved = await store.edit_candidate(candidate.candidate_id, {
    title: draft.title.trim(),
    start_time: draft.start_time ? new Date(draft.start_time).toISOString() : candidate.parsed?.start_time,
    end_time: draft.end_time ? new Date(draft.end_time).toISOString() : candidate.parsed?.end_time,
    location: draft.location.trim()
  })
  if (saved) editingId.value = null
}

async function confirmCandidate(candidate) {
  if (confirmingId.value) return
  confirmingId.value = candidate.candidate_id
  await store.confirm_local_candidate(candidate.candidate_id)
  confirmingId.value = null
}

async function findSlots(candidate) {
  slotCandidateId.value = candidate.candidate_id
  await store.request_free_slots(candidate.parsed)
}

async function applySlot(candidate, slot) {
  const saved = await store.edit_candidate(candidate.candidate_id, { start_time: slot.start_time, end_time: slot.end_time })
  if (saved) slotCandidateId.value = null
}

function changeEntries(candidate) {
  const changes = candidate?.changes
  if (Array.isArray(changes)) return changes
  return Object.entries(changes || {}).map(([field, value]) => {
    if (value && typeof value === 'object') return { field, ...value }
    return { field, to: value }
  })
}

function kindLabel(value) {
  if (value === 'update') return '变更'
  if (value === 'cancel') return '取消'
  return '新日程'
}

function kindClass(value) {
  if (value === 'update') return 'bg-amber-500/10 text-amber-400'
  if (value === 'cancel') return 'bg-red-500/10 text-red-400'
  return 'bg-blue-500/10 text-blue-400'
}

function formatDateTime(value) {
  if (!value) return '时间待确认'
  return new Date(value).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit' })
}

function formatClock(value) {
  if (!value) return '--:--'
  return new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function formatSnoozed(value) {
  return `${new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })} 再提醒`
}
</script>

<style scoped>
.candidate-card { border: 1px solid rgba(255,255,255,.075); border-radius: 1.35rem; padding: 1.15rem; background: rgba(255,255,255,.025); }
.candidate-kind { border-radius: 999px; padding: .25rem .55rem; font-size: .68rem; font-weight: 600; }
.field { width: 100%; border: 1px solid rgba(255,255,255,.09); border-radius: .8rem; padding: .7rem .85rem; color: white; background: rgba(255,255,255,.035); outline: none; }
.field:focus { border-color: rgba(59,130,246,.7); }
.small-primary, .small-quiet, .small-danger { border-radius: .75rem; padding: .55rem .8rem; font-size: .75rem; font-weight: 600; transition: background .2s, color .2s; }
.small-primary { color: white; background: #2563eb; }
.small-quiet { color: #a3a3a3; background: rgba(255,255,255,.05); }
.small-danger { color: #f87171; background: rgba(239,68,68,.07); }
.slot-row { display: flex; width: 100%; justify-content: space-between; gap: 1rem; border-radius: .75rem; padding: .65rem .75rem; color: #bfdbfe; background: rgba(59,130,246,.07); font-size: .75rem; text-align: left; }
</style>
