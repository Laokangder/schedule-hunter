<template>
  <div class="app-shell min-h-screen text-white">
    <ScheduleIsland />

    <main class="relative z-10 mx-auto max-w-3xl px-5 pb-32 pt-8 sm:px-8 sm:pt-12">
      <header class="mb-12">
        <div>
          <p class="mb-2 text-xs font-semibold uppercase tracking-[0.28em] text-blue-400">Schedule Hunter</p>
          <h1 class="text-2xl font-semibold tracking-tight text-white sm:text-3xl">日程猎人</h1>
        </div>
      </header>

      <template v-if="activeView === 'today'">
      <section>
        <div class="hero-wash" aria-hidden="true"></div>
        <div class="relative">
          <p class="text-sm font-medium text-blue-400">{{ nextTaskLabel }}</p>
          <div class="mt-7 flex items-end justify-between gap-4">
            <div>
              <h2 class="text-4xl font-semibold tracking-tight text-white sm:text-5xl">{{ displayDate }}</h2>
              <p class="mt-3 text-base text-neutral-400 sm:text-lg">
                {{ greeting }}，今天还有 <span class="font-semibold text-blue-400">{{ unfinishedCount }}</span> 项日程
              </p>
            </div>
            <button type="button" class="hidden h-11 w-11 items-center justify-center rounded-full text-neutral-400 transition hover:bg-white/5 hover:text-white sm:flex" aria-label="刷新日程" @click="store.fetch_latest_tasks()">
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4 4v5h5M20 20v-5h-5M5.6 15.5A7.5 7.5 0 0118 7.2L20 9M4 15l2 1.8" />
              </svg>
            </button>
          </div>

          <button v-if="nextTask" type="button" class="next-task mt-9 w-full text-left" @click="openTask(nextTask)">
            <span class="timeline-pulse" aria-hidden="true"></span>
            <div class="min-w-0 pl-9">
              <div class="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <span class="text-2xl font-semibold tabular-nums text-white">{{ formatClock(nextTask.start_time) }}</span>
                <span class="truncate text-xl font-semibold text-white">{{ nextTask.title }}</span>
              </div>
              <p class="mt-2 flex items-center gap-1.5 text-sm text-neutral-400">
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 21s6-5.1 6-11a6 6 0 10-12 0c0 5.9 6 11 6 11z" />
                  <circle cx="12" cy="10" r="2" stroke-width="1.8" />
                </svg>
                {{ nextTask.location || '未设置地点' }}
              </p>
            </div>
          </button>
          <div v-else class="mt-9 border-l border-neutral-800 py-3 pl-8 text-sm text-neutral-500">今天暂时没有待完成日程</div>
        </div>
      </section>

      <section class="mt-12" aria-labelledby="ai-input-title">
        <h2 id="ai-input-title" class="sr-only">AI 智能创建日程</h2>
        <div class="ai-composer" :class="{ 'ai-composer--busy': store.is_loading }">
          <svg class="mt-1 h-5 w-5 flex-none text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 3l1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2L12 3zM5 14l.8 2.2L8 17l-2.2.8L5 20l-.8-2.2L2 17l2.2-.8L5 14z" />
          </svg>
          <textarea v-model="sniffText" rows="2" class="min-h-[56px] flex-1 resize-none bg-transparent text-base leading-7 text-white outline-none placeholder:text-neutral-500" placeholder="告诉我你接下来要做什么…" @keydown.enter.exact.prevent="handleSniff"></textarea>
          <button type="button" class="send-button" :disabled="!sniffText.trim() || store.is_loading" aria-label="智能解析" @click="handleSniff">
            <svg v-if="!store.is_loading" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h13m-5-5l5 5-5 5" /></svg>
            <svg v-else class="h-5 w-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8" stroke-width="2" stroke-dasharray="32" stroke-dashoffset="10" /></svg>
          </button>
        </div>
        <p class="mt-3 px-2 text-xs text-neutral-600">按 Enter 解析，Shift + Enter 换行</p>
        <p v-if="store.error_msg" class="mt-3 px-2 text-sm text-red-400" role="alert">{{ store.error_msg }}</p>
      </section>

      <section class="mt-14" aria-labelledby="schedule-title">
        <div class="mb-5 flex items-end justify-between">
          <div>
            <p class="mb-1 text-xs font-medium uppercase tracking-[0.22em] text-neutral-600">Timeline</p>
            <h2 id="schedule-title" class="text-2xl font-semibold tracking-tight">{{ pageTitle }}</h2>
          </div>
          <span class="text-sm text-neutral-500">{{ store.today_tasks.length }} 项</span>
        </div>
        <BountyList :tasks="store.today_tasks" :title="pageTitle" empty-text="这一天还没有日程" />
      </section>
      </template>

      <section v-else-if="activeView === 'calendar'" aria-labelledby="calendar-title">
        <div class="mb-8">
          <p class="mb-1 text-xs font-medium uppercase tracking-[0.22em] text-neutral-600">Calendar</p>
          <h2 id="calendar-title" class="text-3xl font-semibold tracking-tight">日历</h2>
          <p class="mt-2 text-sm text-neutral-500">选择日期查看当天的全部日程</p>
        </div>
        <CalendarGrid :marked-dates="store.marked_dates" />
        <div class="mt-12">
          <div class="mb-5 flex items-end justify-between">
            <div>
              <p class="mb-1 text-xs font-medium uppercase tracking-[0.22em] text-neutral-600">Selected date</p>
              <h3 class="text-2xl font-semibold tracking-tight">{{ displayDate }}</h3>
            </div>
            <span class="text-sm text-neutral-500">{{ store.today_tasks.length }} 项</span>
          </div>
          <BountyList :tasks="store.today_tasks" :title="pageTitle" empty-text="这一天还没有日程" />
        </div>
      </section>

      <section v-else-if="activeView === 'expired'" aria-labelledby="expired-title">
        <div class="mb-5 flex items-end justify-between gap-4">
          <div>
            <p class="mb-1 text-xs font-medium uppercase tracking-[0.22em] text-neutral-600">Archive</p>
            <h2 id="expired-title" class="text-3xl font-semibold tracking-tight">已过期日程</h2>
            <p class="mt-2 text-sm text-neutral-500">超过结束时间的日程会自动移动到这里</p>
          </div>
          <button type="button" class="text-sm font-medium text-red-400 transition hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-30" :disabled="store.expired_tasks.length === 0 || clearingExpired" @click="clearExpired">
            {{ clearingExpired ? '删除中…' : '清空全部' }}
          </button>
        </div>
        <BountyList :tasks="store.expired_tasks" title="已过期日程" empty-text="暂无已过期日程" />
      </section>

      <section v-else aria-labelledby="settings-title">
        <p class="mb-1 text-xs font-medium uppercase tracking-[0.22em] text-neutral-600">Preferences</p>
        <h2 id="settings-title" class="text-3xl font-semibold tracking-tight">设置</h2>
        <div class="mt-9 border-y border-white/[0.07] py-6">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="font-medium text-white">后端服务器地址</p>
              <p class="mt-1 text-sm leading-6 text-neutral-500">APK 请填写运行后端的电脑局域网地址，手机和电脑需要连接同一 Wi-Fi。</p>
            </div>
            <span class="rounded-full bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-400">{{ platformLabel }}</span>
          </div>
          <input
            v-model="backendAddress"
            type="url"
            inputmode="url"
            autocomplete="url"
            class="mt-5 w-full rounded-xl border border-white/10 bg-white/[0.035] px-4 py-3 text-sm text-white outline-none transition placeholder:text-neutral-600 focus:border-blue-500/70 focus:ring-4 focus:ring-blue-500/10"
            placeholder="例如：http://192.168.1.104:8000"
          />
          <div class="mt-4 flex items-center gap-4">
            <button type="button" class="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50" :disabled="testingBackend" @click="saveBackendAddress">
              {{ testingBackend ? '正在测试…' : '保存并测试连接' }}
            </button>
            <span v-if="backendStatus.message" class="text-sm" :class="backendStatus.success ? 'text-emerald-400' : 'text-red-400'">{{ backendStatus.message }}</span>
          </div>
          <p class="mt-4 text-xs leading-5 text-neutral-600">地址会保存在本机，重新打开 APK 后仍然有效。不要填写 localhost，因为它在手机上表示手机本身。</p>
        </div>
      </section>
    </main>

    <nav class="bottom-nav" aria-label="主导航">
      <button type="button" :class="{ active: activeView === 'today' }" @click="switchView('today')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 10.5L12 4l8 6.5V20H4v-9.5z" /><path d="M9 20v-6h6v6" /></svg><span>今天</span></button>
      <button type="button" :class="{ active: activeView === 'calendar' }" @click="switchView('calendar')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="4" y="5" width="16" height="15" rx="2" /><path d="M8 3v4M16 3v4M4 10h16" /></svg><span>日历</span></button>
      <button type="button" :class="{ active: activeView === 'expired' }" @click="switchView('expired')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="8" /><path d="M12 8v4l3 2" /></svg><span>过期</span></button>
      <button type="button" :class="{ active: activeView === 'settings' }" @click="switchView('settings')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="3" /><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6L7 7M17 17l1.4 1.4M18.4 5.6L17 7M7 17l-1.4 1.4" /></svg><span>设置</span></button>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useTaskStore } from '@/stores/useTaskStore'
import ScheduleIsland from './Island/ScheduleIsland.vue'
import CalendarGrid from './CalendarGrid.vue'
import BountyList from './BountyList.vue'
import { localDateKey } from '@/utils/date'
import * as apiService from '@/services/apiService'

const store = useTaskStore()
const sniffText = ref('')
const clearingExpired = ref(false)
const activeView = ref('today')
const now = ref(Date.now())
const backendAddress = ref('')
const testingBackend = ref(false)
const backendStatus = ref({ success: false, message: '' })
let clockTimer = null

const platformLabel = apiService.is_native_app() ? 'APK' : 'Web'

const unfinishedTasks = computed(() => (store.today_tasks || []).filter(task => !['completed', 'expired'].includes(task.status)))
const unfinishedCount = computed(() => unfinishedTasks.value.length)
const nextTask = computed(() => unfinishedTasks.value.filter(task => new Date(task.end_time || task.start_time).getTime() >= now.value).slice().sort((a, b) => new Date(a.start_time) - new Date(b.start_time))[0] || null)

const displayDate = computed(() => {
  const date = new Date(`${store.selected_date}T12:00:00`)
  const weekday = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'][date.getDay()]
  return `${date.getMonth() + 1}月${date.getDate()}日 ${weekday}`
})

const greeting = computed(() => {
  const hour = new Date(now.value).getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '上午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const nextTaskLabel = computed(() => {
  if (!nextTask.value) return '接下来 · 暂无安排'
  const diff = new Date(nextTask.value.start_time).getTime() - now.value
  if (diff <= 0) return '当前日程 · 正在进行'
  const minutes = Math.ceil(diff / 60000)
  if (minutes < 60) return `下一日程 · ${minutes}分钟后`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return `下一日程 · ${hours}小时${rest ? `${rest}分钟` : ''}后`
})

const pageTitle = computed(() => store.selected_date === localDateKey() ? '今日日程' : `${displayDate.value}日程`)

function formatClock(value) {
  if (!value) return '--:--'
  const date = new Date(value)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function openTask(task) { store.set_active_task(task); store.island_state = 'detail' }

async function handleSniff() {
  if (!sniffText.value.trim() || store.is_loading) return
  const result = await store.handle_native_sniff(sniffText.value)
  if (result?.success) sniffText.value = ''
}

async function clearExpired() {
  if (!confirm(`确定删除全部 ${store.expired_tasks.length} 条已过期日程吗？`)) return
  clearingExpired.value = true
  await store.delete_all_expired()
  clearingExpired.value = false
}

function switchView(view) {
  activeView.value = view
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function saveBackendAddress() {
  testingBackend.value = true
  backendStatus.value = { success: false, message: '' }
  const savedAddress = apiService.set_api_base_url(backendAddress.value)
  backendAddress.value = savedAddress || apiService.get_api_base_url()
  const result = await apiService.test_backend_connection(backendAddress.value)
  if (result.success) {
    backendStatus.value = { success: true, message: '连接成功' }
    store.disconnect_web_socket()
    store.connect_web_socket()
    store._start_poll()
    await store.fetch_latest_tasks()
  } else {
    backendStatus.value = { success: false, message: `连接失败：${result.error}` }
  }
  testingBackend.value = false
}

function handleNativeSniff(sourceText, inputType = 'manual') { return store.handle_native_sniff(sourceText, inputType) }

onMounted(() => {
  window.handleNativeSniff = handleNativeSniff
  backendAddress.value = apiService.get_api_base_url()
  clockTimer = window.setInterval(() => { now.value = Date.now() }, 30000)
  store.fetch_latest_tasks()
  store.connect_web_socket()
  store._start_poll()
})

onUnmounted(() => {
  if (window.handleNativeSniff === handleNativeSniff) delete window.handleNativeSniff
  if (clockTimer) window.clearInterval(clockTimer)
  store.disconnect_web_socket()
})
</script>

<style scoped>
.app-shell { position: relative; overflow-x: hidden; background: radial-gradient(circle at 88% 5%, rgba(47,107,255,.13), transparent 24rem), linear-gradient(180deg, #07090d 0%, #040506 58%, #07090c 100%); }
.app-shell::before { position: fixed; inset: 0; pointer-events: none; content: ''; opacity: .22; background-image: linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px); background-size: 48px 48px; mask-image: linear-gradient(to bottom, black, transparent 72%); }
.hero-wash { position: absolute; top: 7rem; right: -8rem; width: 24rem; height: 18rem; pointer-events: none; border-radius: 999px; background: radial-gradient(circle, rgba(57,112,255,.12), transparent 66%); filter: blur(12px); }
.next-task { position: relative; display: block; padding: 1rem 0 1.2rem; border-left: 1px solid rgba(82,124,230,.42); }
.timeline-pulse { position: absolute; top: 2rem; left: -5px; width: 9px; height: 9px; border-radius: 999px; background: #3b82f6; box-shadow: 0 0 0 5px rgba(59,130,246,.12), 0 0 22px rgba(59,130,246,.7); }
.ai-composer { display: flex; align-items: flex-start; gap: 1rem; padding: 1.15rem 1.1rem 1rem 1.25rem; border: 1px solid rgba(88,133,255,.48); border-radius: 1.7rem; background: linear-gradient(135deg, rgba(21,29,45,.88), rgba(13,15,22,.9)); box-shadow: 0 18px 55px rgba(0,0,0,.32), inset 0 1px rgba(255,255,255,.025); transition: border-color .2s, box-shadow .2s; }
.ai-composer:focus-within { border-color: rgba(96,144,255,.9); box-shadow: 0 18px 60px rgba(0,0,0,.4), 0 0 0 4px rgba(59,130,246,.08); }
.ai-composer--busy { opacity: .75; }
.send-button { display: flex; width: 2.9rem; height: 2.9rem; flex: none; align-items: center; justify-content: center; border-radius: 999px; color: white; background: linear-gradient(135deg, #2f6bff, #7957ff); box-shadow: 0 10px 28px rgba(56,91,255,.35); transition: transform .2s, opacity .2s; }
.send-button:hover:not(:disabled) { transform: translateY(-1px) scale(1.03); }
.send-button:disabled { opacity: .35; cursor: not-allowed; box-shadow: none; }
.bottom-nav { position: fixed; z-index: 60; left: 50%; bottom: max(1rem, env(safe-area-inset-bottom)); display: flex; width: min(calc(100% - 2rem), 30rem); transform: translateX(-50%); justify-content: space-around; padding: .65rem .7rem; border: 1px solid rgba(255,255,255,.08); border-radius: 1.45rem; background: rgba(10,12,17,.88); box-shadow: 0 20px 60px rgba(0,0,0,.52); backdrop-filter: blur(22px); }
.bottom-nav button { display: flex; min-width: 3.6rem; flex-direction: column; align-items: center; gap: .25rem; color: #737783; font-size: .68rem; transition: color .2s; }
.bottom-nav button:hover, .bottom-nav button.active { color: #4c8dff; }
.bottom-nav svg { width: 1.35rem; height: 1.35rem; stroke-width: 1.7; }
@media (min-width: 768px) { .bottom-nav { bottom: 1.5rem; } }
</style>
