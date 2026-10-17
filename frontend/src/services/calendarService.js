import { Capacitor, registerPlugin } from '@capacitor/core'

const DeviceCalendar = registerPlugin('DeviceCalendar')
const ENABLED_KEY = 'schedule_hunter_calendar_sync_enabled'
const EVENT_MAP_KEY = 'schedule_hunter_calendar_event_map_v1'

function readMap() {
  try { return JSON.parse(localStorage.getItem(EVENT_MAP_KEY) || '{}') } catch { return {} }
}

function writeMap(value) {
  localStorage.setItem(EVENT_MAP_KEY, JSON.stringify(value))
}

function taskIdOf(task) {
  return String(task?.task_id || task?.id || '')
}

export function isSupported() {
  return Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android'
}

export function isEnabled() {
  return localStorage.getItem(ENABLED_KEY) === 'true'
}

export function setEnabled(enabled) {
  localStorage.setItem(ENABLED_KEY, enabled ? 'true' : 'false')
}

export async function getPermissionState() {
  if (!isSupported()) return { supported: false, granted: false }
  return DeviceCalendar.checkCalendarPermission()
}

export async function requestPermission() {
  if (!isSupported()) return { supported: false, granted: false }
  return DeviceCalendar.requestCalendarPermission()
}

export async function upsertTask(task) {
  if (!isSupported() || !isEnabled()) return { supported: isSupported(), synced: false }
  const taskId = taskIdOf(task)
  if (!taskId) return { supported: true, synced: false }
  const eventMap = readMap()
  const result = await DeviceCalendar.upsertEvent({
    eventId: eventMap[taskId] || '',
    title: task.title || '日程',
    startTime: task.start_time,
    endTime: task.end_time || task.start_time,
    location: task.location || '',
    description: '由日程猎人同步'
  })
  if (result?.eventId) {
    eventMap[taskId] = String(result.eventId)
    writeMap(eventMap)
  }
  return { supported: true, synced: !!result?.eventId, ...result }
}

export async function deleteTask(taskOrId) {
  if (!isSupported()) return { supported: false, deleted: false }
  const taskId = typeof taskOrId === 'object' ? taskIdOf(taskOrId) : String(taskOrId || '')
  const eventMap = readMap()
  const eventId = eventMap[taskId]
  if (!eventId) return { supported: true, deleted: false }
  const result = await DeviceCalendar.deleteEvent({ eventId })
  delete eventMap[taskId]
  writeMap(eventMap)
  return { supported: true, ...result }
}
