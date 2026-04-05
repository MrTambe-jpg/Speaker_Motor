import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'

// WebSocket connection state
export const useStore = create(
  subscribeWithSelector((set, get) => ({
    // Connection state
    connected: false,
    ws: null,

    // System state
    isRunning: false,
    systemInfo: {},

    // Config
    config: {},
    configLoading: true,

    // Plugins
    plugins: {
      hardware: [],
      audio_source: [],
      processor: [],
      visualizer: []
    },
    pluginsLoading: true,

    // Active components
    activeHardware: null,
    activeAudioSource: null,
    activeProcessors: [],

    // Motor state
    motors: [],

    // Audio state
    audioData: null,
    fftData: null,
    beatData: null,

    // Track info
    trackInfo: {
      title: '',
      artist: '',
      album: '',
      artUrl: ''
    },

    // UI state
    currentPage: 'dashboard',
    sidebarOpen: true,

    // Actions
    connect: () => {
      const ws = new WebSocket(`ws://${window.location.host}/ws`)

      ws.onopen = () => {
        set({ connected: true, ws })
        // Request initial state
        ws.send(JSON.stringify({ cmd: 'get_status' }))
      }

      ws.onclose = () => {
        set({ connected: false, ws: null })
        // Attempt reconnection
        setTimeout(() => get().connect(), 3000)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          get().handleMessage(data)
        } catch (e) {
          console.error('Failed to parse message:', e)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      set({ ws })
    },

    disconnect: () => {
      const { ws } = get()
      if (ws) {
        ws.close()
      }
      set({ connected: false, ws: null })
    },

    handleMessage: (data) => {
      if (data.event) {
        // Handle event from server
        switch (data.event) {
          case 'motor_state':
            if (data.data.motors) {
              set({ motors: data.data.motors })
            }
            break
          case 'audio_data':
            set({ audioData: data.data })
            break
          case 'fft_data':
            set({ fftData: data.data })
            break
          case 'beat':
            set({ beatData: data.data })
            break
          case 'track_changed':
            set({ trackInfo: data.data })
            break
          case 'config_changed':
            // Refresh config
            get().fetchConfig()
            break
          default:
            break
        }
      }
    },

    sendCommand: (command) => {
      const { ws, connected } = get()
      if (ws && connected) {
        ws.send(JSON.stringify(command))
      }
    },

    // API calls
    fetchConfig: async () => {
      try {
        const response = await fetch('/api/config')
        const config = await response.json()
        set({ config, configLoading: false })
      } catch (error) {
        console.error('Failed to fetch config:', error)
        set({ configLoading: false })
      }
    },

    fetchPlugins: async () => {
      try {
        const response = await fetch('/api/plugins')
        const plugins = await response.json()
        set({ plugins, pluginsLoading: false })
      } catch (error) {
        console.error('Failed to fetch plugins:', error)
        set({ pluginsLoading: false })
      }
    },

    fetchSystemInfo: async () => {
      try {
        const response = await fetch('/api/system')
        const systemInfo = await response.json()
        set({ systemInfo })
      } catch (error) {
        console.error('Failed to fetch system info:', error)
      }
    },

    fetchMotors: async () => {
      try {
        const response = await fetch('/api/motors')
        const motors = await response.json()
        set({ motors })
      } catch (error) {
        console.error('Failed to fetch motors:', error)
      }
    },

    // Control actions
    start: async () => {
      try {
        await fetch('/api/start', { method: 'POST' })
        set({ isRunning: true })
      } catch (error) {
        console.error('Failed to start:', error)
      }
    },

    stop: async () => {
      try {
        await fetch('/api/stop', { method: 'POST' })
        set({ isRunning: false })
      } catch (error) {
        console.error('Failed to stop:', error)
      }
    },

    setHardware: async (pluginId) => {
      try {
        await fetch(`/api/hardware/${pluginId}`, { method: 'POST' })
        set({ activeHardware: pluginId })
      } catch (error) {
        console.error('Failed to set hardware:', error)
      }
    },

    setAudioSource: async (pluginId) => {
      try {
        await fetch(`/api/audio/${pluginId}`, { method: 'POST' })
        set({ activeAudioSource: pluginId })
      } catch (error) {
        console.error('Failed to set audio source:', error)
      }
    },

    setMotorAngle: async (motorId, angle) => {
      try {
        await fetch(`/api/motors/${motorId}/angle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ angle })
        })
      } catch (error) {
        console.error('Failed to set motor angle:', error)
      }
    },

    testMotor: async (motorId) => {
      try {
        await fetch(`/api/motors/${motorId}/test`, { method: 'POST' })
      } catch (error) {
        console.error('Failed to test motor:', error)
      }
    },

    updateConfig: async (keyPath, value) => {
      try {
        await fetch(`/api/config/${keyPath}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(value)
        })
        get().fetchConfig()
      } catch (error) {
        console.error('Failed to update config:', error)
      }
    },

    // Navigation
    setCurrentPage: (page) => set({ currentPage: page }),
    toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

    // Initialize
    initialize: async () => {
      await Promise.all([
        get().fetchConfig(),
        get().fetchPlugins(),
        get().fetchSystemInfo(),
        get().fetchMotors()
      ])
      get().connect()
    }
  }))
)

export default useStore