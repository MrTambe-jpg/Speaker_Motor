import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import {
  Activity, Settings, Music, Sliders, History, Wrench,
  Menu, X, Wifi, WifiOff, Play, Square
} from 'lucide-react'
import useStore from './store'
import Dashboard from './pages/Dashboard'
import SettingsPage from './pages/Settings'
import AudioSources from './pages/AudioSources'
import MotorConfig from './pages/MotorConfig'
import Sequences from './pages/Sequences'
import Diagnostics from './pages/Diagnostics'

function App() {
  const {
    connected, isRunning, sidebarOpen, currentPage,
    toggleSidebar, start, stop, initialize
  } = useStore()

  useEffect(() => {
    initialize()
  }, [])

  const navItems = [
    { path: '/', icon: Activity, label: 'Dashboard' },
    { path: '/settings', icon: Settings, label: 'Settings' },
    { path: '/audio', icon: Music, label: 'Audio Sources' },
    { path: '/motors', icon: Sliders, label: 'Motor Config' },
    { path: '/sequences', icon: History, label: 'Sequences' },
    { path: '/diagnostics', icon: Wrench, label: 'Diagnostics' },
  ]

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-dark-950 flex">
        {/* Sidebar */}
        <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-dark-900 border-r border-dark-700
                          transform transition-transform duration-300 ease-in-out
                          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
          {/* Logo */}
          <div className="h-16 flex items-center justify-between px-4 border-b border-dark-700">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary-500 flex items-center justify-center">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">OMNISOUND</h1>
                <p className="text-xs text-dark-400">v1.0.0</p>
              </div>
            </div>
            <button onClick={toggleSidebar} className="lg:hidden p-2 hover:bg-dark-700 rounded">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="p-4 space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-lg transition-all
                   ${isActive
                     ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                     : 'text-dark-300 hover:bg-dark-700 hover:text-white'}`
                }
              >
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          {/* Status */}
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-dark-700">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-dark-400">Connection</span>
              <div className={`flex items-center gap-2 ${connected ? 'text-green-400' : 'text-red-400'}`}>
                {connected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
                <span className="text-sm">{connected ? 'Connected' : 'Disconnected'}</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className={`flex-1 transition-all duration-300 ${sidebarOpen ? 'lg:ml-64' : ''}`}>
          {/* Top bar */}
          <header className="h-16 bg-dark-900/80 backdrop-blur-sm border-b border-dark-700
                            sticky top-0 z-40 flex items-center px-4 gap-4">
            <button onClick={toggleSidebar} className="p-2 hover:bg-dark-700 rounded lg:hidden">
              <Menu className="w-5 h-5" />
            </button>

            <div className="flex-1" />

            {/* Play/Stop controls */}
            <div className="flex items-center gap-2">
              {isRunning ? (
                <button
                  onClick={stop}
                  className="flex items-center gap-2 px-4 py-2 bg-red-500/20 text-red-400
                           border border-red-500/30 rounded-lg hover:bg-red-500/30 transition"
                >
                  <Square className="w-4 h-4" />
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  onClick={start}
                  className="flex items-center gap-2 px-4 py-2 bg-green-500/20 text-green-400
                           border border-green-500/30 rounded-lg hover:bg-green-500/30 transition"
                >
                  <Play className="w-4 h-4" />
                  <span>Start</span>
                </button>
              )}
            </div>
          </header>

          {/* Page content */}
          <div className="p-6">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/audio" element={<AudioSources />} />
              <Route path="/motors" element={<MotorConfig />} />
              <Route path="/sequences" element={<Sequences />} />
              <Route path="/diagnostics" element={<Diagnostics />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App