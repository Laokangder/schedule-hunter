import { Capacitor, registerPlugin } from '@capacitor/core'

const SystemNotificationListener = registerPlugin('SystemNotificationListener')

export function isSupported() {
  return Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android'
}

export async function getStatus() {
  if (!isSupported()) return { supported: false, granted: false, enabled: false }
  return SystemNotificationListener.checkPermission()
}

export async function openPermissionSettings() {
  if (!isSupported()) return false
  await SystemNotificationListener.openPermissionSettings()
  return true
}

export async function setEnabled(enabled) {
  if (!isSupported()) return { enabled: false }
  return SystemNotificationListener.setEnabled({ enabled })
}

export async function setBackendUrl(backendUrl) {
  if (!isSupported()) return { configured: false }
  return SystemNotificationListener.setBackendUrl({ backendUrl: backendUrl || '' })
}

export async function getPending() {
  if (!isSupported()) return []
  const result = await SystemNotificationListener.getPending()
  return Array.isArray(result?.notifications) ? result.notifications : []
}

export async function acknowledge(eventIds) {
  if (!isSupported() || !eventIds?.length) return { removed: 0 }
  return SystemNotificationListener.acknowledge({ eventIds })
}

export async function addCaptureListener(callback) {
  if (!isSupported()) return null
  return SystemNotificationListener.addListener('notificationCaptured', callback)
}
