import { Capacitor } from '@capacitor/core'
import { LocalNotifications } from '@capacitor/local-notifications'

const OWNER = 'schedule-hunter'
const DEFAULT_OFFSETS = [30, 10, 5, 0]
const REGISTRY_KEY = 'schedule_hunter_local_notification_registry_v1'

function taskIdOf(taskOrId) {
  if (typeof taskOrId === 'string' || typeof taskOrId === 'number') return String(taskOrId)
  return String(taskOrId?.task_id || taskOrId?.id || '')
}

function notificationId(taskId, offset) {
  const value = `${OWNER}:${taskId}:${offset}`
  let hash = 2166136261
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  const result = hash & 0x7fffffff
  return result || 1
}

function candidateNotificationId(candidateId) {
  return notificationId(`candidate:${candidateId}`, 0)
}

function readRegistry() {
  try {
    return JSON.parse(localStorage.getItem(REGISTRY_KEY) || '{}')
  } catch {
    return {}
  }
}

function writeRegistry(registry) {
  localStorage.setItem(REGISTRY_KEY, JSON.stringify(registry))
}

function configuredOffsets(task) {
  const policy = task?.reminder_policy
  if (policy?.enabled === false) return []
  const configured = Array.isArray(policy?.offset_minutes) ? policy.offset_minutes : DEFAULT_OFFSETS
  return [...new Set([...configured, 0].map(Number).filter(value => Number.isInteger(value) && value >= 0))]
}

function makeNotifications(task, exactAlarmGranted) {
  const taskId = taskIdOf(task)
  const startTime = new Date(task?.start_time).getTime()
  if (!taskId || !Number.isFinite(startTime) || !['scheduled', 'pending'].includes(task?.status || 'scheduled')) return []

  const now = Date.now()
  return configuredOffsets(task).map(offset => {
    const triggerAt = startTime - offset * 60_000
    if (triggerAt <= now + 1_000) return null
    const location = task.location ? ` · ${task.location}` : ''
    return {
      id: notificationId(taskId, offset),
      title: offset === 0 ? `日程开始：${task.title}` : `${offset} 分钟后：${task.title}`,
      body: `${new Date(startTime).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}${location}`,
      schedule: { at: new Date(triggerAt), allowWhileIdle: true },
      foreground: true,
      isExactNotification: exactAlarmGranted,
      isExactMandatory: false,
      extra: { owner: OWNER, type: 'task', task_id: taskId, offset_minutes: offset }
    }
  }).filter(Boolean)
}

export function isSupported() {
  return Capacitor.isNativePlatform()
}

export async function getPermissionState() {
  if (!isSupported()) return { supported: false, display: 'unavailable', exact_alarm: 'unavailable' }
  const [permission, exactSetting] = await Promise.all([
    LocalNotifications.checkPermissions(),
    LocalNotifications.checkExactNotificationSetting().catch(() => ({ exact_alarm: 'denied' }))
  ])
  return { supported: true, display: permission.display, exact_alarm: exactSetting.exact_alarm }
}

export async function requestPermission() {
  if (!isSupported()) return getPermissionState()
  await LocalNotifications.requestPermissions()
  return getPermissionState()
}

export async function requestExactAlarmPermission() {
  if (!isSupported()) return getPermissionState()
  await LocalNotifications.changeExactNotificationSetting()
  return getPermissionState()
}

async function cancelDescriptors(descriptors) {
  const unique = [...new Set(descriptors.map(item => Number(item.id)).filter(Number.isInteger))]
  if (unique.length > 0) await LocalNotifications.cancel({ notifications: unique.map(id => ({ id })) })
}

export async function cancelTask(taskOrId) {
  if (!isSupported()) return { supported: false, cancelled: 0 }
  const taskId = taskIdOf(taskOrId)
  if (!taskId) return { supported: true, cancelled: 0 }

  const registry = readRegistry()
  const registeredIds = registry[taskId] || []
  const possibleIds = [...new Set([...DEFAULT_OFFSETS, ...configuredOffsets(taskOrId)].map(offset => notificationId(taskId, offset)))]
  const ids = [...new Set([...registeredIds, ...possibleIds])]
  await cancelDescriptors(ids.map(id => ({ id })))
  delete registry[taskId]
  writeRegistry(registry)
  return { supported: true, cancelled: ids.length }
}

export async function scheduleTask(task) {
  if (!isSupported()) return { supported: false, scheduled: 0 }
  const permission = await getPermissionState()
  if (permission.display !== 'granted') return { ...permission, scheduled: 0 }

  await cancelTask(task)
  const notifications = makeNotifications(task, permission.exact_alarm === 'granted')
  if (notifications.length > 0) await LocalNotifications.schedule({ notifications })

  const taskId = taskIdOf(task)
  const registry = readRegistry()
  if (notifications.length > 0) registry[taskId] = notifications.map(item => item.id)
  else delete registry[taskId]
  writeRegistry(registry)
  return { ...permission, scheduled: notifications.length }
}

export async function rebuildTask(task) {
  return scheduleTask(task)
}

export async function scheduleCandidateSnooze(candidate, minutes) {
  if (!isSupported()) return { supported: false, scheduled: 0 }
  const permission = await getPermissionState()
  if (permission.display !== 'granted') return { ...permission, scheduled: 0 }
  const candidateId = String(candidate?.candidate_id || '')
  if (!candidateId) return { ...permission, scheduled: 0 }
  const id = candidateNotificationId(candidateId)
  await LocalNotifications.cancel({ notifications: [{ id }] }).catch(() => {})
  await LocalNotifications.schedule({
    notifications: [{
      id,
      title: `候选日程：${candidate.parsed?.title || '待确认日程'}`,
      body: '稍后提醒时间已到，点击查看并确认',
      schedule: { at: new Date(Date.now() + Math.max(1, Number(minutes) || 10) * 60_000), allowWhileIdle: true },
      foreground: true,
      extra: { owner: OWNER, type: 'candidate_snooze', candidate_id: candidateId }
    }]
  })
  return { ...permission, scheduled: 1 }
}

export async function cancelCandidateSnooze(candidateId) {
  if (!isSupported() || !candidateId) return { supported: isSupported(), cancelled: 0 }
  await LocalNotifications.cancel({ notifications: [{ id: candidateNotificationId(String(candidateId)) }] }).catch(() => {})
  return { supported: true, cancelled: 1 }
}

export async function addActionListener(callback) {
  if (!isSupported()) return null
  return LocalNotifications.addListener('localNotificationActionPerformed', callback)
}

export async function reconcileTasks(tasks = []) {
  if (!isSupported()) return { supported: false, scheduled: 0, cancelled: 0 }
  const permission = await getPermissionState()
  if (permission.display !== 'granted') return { ...permission, scheduled: 0, cancelled: 0 }

  const pending = await LocalNotifications.getPending()
  const owned = (pending.notifications || []).filter(item => item.extra?.owner === OWNER && item.extra?.type !== 'candidate_snooze')
  await cancelDescriptors(owned)

  const byId = new Map()
  for (const task of tasks) {
    const taskId = taskIdOf(task)
    if (taskId && ['scheduled', 'pending'].includes(task.status || 'scheduled')) byId.set(taskId, task)
  }
  const notifications = [...byId.values()].flatMap(task => makeNotifications(task, permission.exact_alarm === 'granted'))
  const uniqueNotifications = [...new Map(notifications.map(item => [item.id, item])).values()]
  if (uniqueNotifications.length > 0) await LocalNotifications.schedule({ notifications: uniqueNotifications })

  const registry = {}
  for (const item of uniqueNotifications) {
    const taskId = String(item.extra.task_id)
    registry[taskId] = [...(registry[taskId] || []), item.id]
  }
  writeRegistry(registry)
  return { ...permission, scheduled: uniqueNotifications.length, cancelled: owned.length }
}
