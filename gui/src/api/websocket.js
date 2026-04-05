let socket = null
let messageHandlers = []

export function wsConnect() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.hostname
  const port = window.location.port || '8000'
  const wsUrl = `${protocol}//${host}:${port}/ws`

  socket = new WebSocket(wsUrl)

  socket.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data)
      messageHandlers.forEach(handler => handler(message))
    } catch (e) {
      console.error('Error parsing WebSocket message:', e)
    }
  }

  socket.onerror = (error) => {
    console.error('WebSocket error:', error)
  }

  return socket
}

export function wsSend(command) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(command))
  } else {
    console.error('WebSocket not connected')
  }
}

export function wsOnMessage(handler) {
  messageHandlers.push(handler)
  return () => {
    messageHandlers = messageHandlers.filter(h => h !== handler)
  }
}

export function wsClose() {
  if (socket) {
    socket.close()
    socket = null
  }
}

// API calls
const API_BASE = '/api'

export async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return response.json()
}

export async function apiPost(path, data) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return response.json()
}

export async function apiPut(path, data) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return response.json()
}

// Convenience functions
export const startSystem = () => apiPost('/start')
export const stopSystem = () => apiPost('/stop')
export const getStatus = () => apiGet('/status')
export const getConfig = () => apiGet('/config')
export const setConfig = (path, value) => apiPut(`/config/${path}`, { value })
export const getPlugins = () => apiGet('/plugins')
export const getMotors = () => apiGet('/motors')
export const setMotorAngle = (id, angle) => apiPost(`/motors/${id}/angle`, { angle })
export const testMotor = (id) => apiPost(`/motors/${id}/test`)
export const setHardwarePlugin = (pluginId) => apiPost(`/hardware/${pluginId}`)
export const setAudioSource = (pluginId) => apiPost(`/audio/${pluginId}`)
export const getDiagnostics = () => apiGet('/diagnostics')
export const exportConfig = () => apiPost('/config/export')
export const importConfig = (data) => apiPost('/config/import', data)
export const resetConfig = () => apiPost('/config/reset')