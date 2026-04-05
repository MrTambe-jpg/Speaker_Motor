import { useState, useEffect } from 'react'
import { Wrench, Cpu, Wifi, Activity, Terminal, RefreshCw } from 'lucide-react'
import useStore from '../store'

function Diagnostics() {
  const { systemInfo, connected, plugins, motors, fetchSystemInfo, fetchPlugins } = useStore()
  const [logs, setLogs] = useState([])
  const [isRunning, setIsRunning] = useState(false)

  const runDiagnostics = async () => {
    setIsRunning(true)
    await Promise.all([fetchSystemInfo(), fetchPlugins()])
    setIsRunning(false)
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wrench className="w-6 h-6 text-primary-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Diagnostics</h1>
            <p className="text-dark-400 mt-1">System information and troubleshooting</p>
          </div>
        </div>
        <button
          onClick={runDiagnostics}
          disabled={isRunning}
          className="btn btn-primary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${isRunning ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Connection Status */}
      <div className="card">
        <h3 className="font-medium text-white mb-4 flex items-center gap-2">
          <Wifi className="w-5 h-5" />
          Connection Status
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-dark-700 rounded-lg p-4">
            <div className="text-sm text-dark-400">WebSocket</div>
            <div className="flex items-center gap-2 mt-1">
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className={connected ? 'text-green-400' : 'text-red-400'}>
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
          <div className="bg-dark-700 rounded-lg p-4">
            <div className="text-sm text-dark-400">Hardware</div>
            <div className="flex items-center gap-2 mt-1">
              <div className={`w-2 h-2 rounded-full ${config?.hardware?.active_plugin ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className={config?.hardware?.active_plugin ? 'text-green-400' : 'text-red-400'}>
                {config?.hardware?.active_plugin || 'None'}
              </span>
            </div>
          </div>
          <div className="bg-dark-700 rounded-lg p-4">
            <div className="text-sm text-dark-400">Audio Source</div>
            <div className="flex items-center gap-2 mt-1">
              <div className={`w-2 h-2 rounded-full ${config?.audio?.active_source ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className={config?.audio?.active_source ? 'text-green-400' : 'text-red-400'}>
                {config?.audio?.active_source || 'None'}
              </span>
            </div>
          </div>
          <div className="bg-dark-700 rounded-lg p-4">
            <div className="text-sm text-dark-400">Motors</div>
            <div className="flex items-center gap-2 mt-1">
              <div className={`w-2 h-2 rounded-full ${motors?.length > 0 ? 'bg-green-500' : 'bg-yellow-500'}`} />
              <span className={motors?.length > 0 ? 'text-green-400' : 'text-yellow-400'}>
                {motors?.length || 0} Active
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* System Information */}
      <div className="card">
        <h3 className="font-medium text-white mb-4 flex items-center gap-2">
          <Cpu className="w-5 h-5" />
          System Information
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-dark-400">Platform</div>
            <div className="text-white">{systemInfo?.platform || 'Unknown'}</div>
          </div>
          <div>
            <div className="text-dark-400">Architecture</div>
            <div className="text-white">{systemInfo?.architecture || 'Unknown'}</div>
          </div>
          <div>
            <div className="text-dark-400">Python Version</div>
            <div className="text-white">{systemInfo?.python_version?.split(' ')[0] || 'Unknown'}</div>
          </div>
          <div>
            <div className="text-dark-400">CPU Cores</div>
            <div className="text-white">{systemInfo?.cpu_count || 'Unknown'}</div>
          </div>
          <div>
            <div className="text-dark-400">Hostname</div>
            <div className="text-white">{systemInfo?.hostname || 'Unknown'}</div>
          </div>
          <div>
            <div className="text-dark-400">Version</div>
            <div className="text-white">{systemInfo?.omnisound_version || '1.0.0'}</div>
          </div>
        </div>
      </div>

      {/* Plugin Status */}
      <div className="card">
        <h3 className="font-medium text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Plugin Status
        </h3>
        <div className="space-y-4">
          {['hardware', 'audio_source', 'processor'].map((type) => (
            <div key={type}>
              <div className="text-sm text-dark-400 mb-2 capitalize">{type.replace('_', ' ')}</div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {plugins?.[type]?.map((plugin) => (
                  <div key={plugin.id} className="bg-dark-700 rounded p-2 flex items-center justify-between">
                    <span className="text-sm text-white">{plugin.name}</span>
                    <div className={`w-2 h-2 rounded-full ${plugin.available ? 'bg-green-500' : 'bg-red-500'}`} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Log Viewer */}
      <div className="card">
        <h3 className="font-medium text-white mb-4 flex items-center gap-2">
          <Terminal className="w-5 h-5" />
          System Logs
        </h3>
        <div className="bg-dark-900 rounded-lg p-4 h-64 overflow-y-auto font-mono text-sm">
          {logs.length > 0 ? (
            logs.map((log, index) => (
              <div key={index} className={`mb-1 ${log.level === 'error' ? 'text-red-400' : log.level === 'warning' ? 'text-yellow-400' : 'text-dark-300'}`}>
                <span className="text-dark-500">[{log.time}]</span> {log.message}
              </div>
            ))
          ) : (
            <div className="text-dark-500">No logs available. Start the system to see logs.</div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h3 className="font-medium text-white mb-4">Quick Actions</h3>
        <div className="flex flex-wrap gap-2">
          <button className="btn btn-secondary">Test All Motors</button>
          <button className="btn btn-secondary">Calibrate Motors</button>
          <button className="btn btn-secondary">Reset Hardware</button>
          <button className="btn btn-secondary">Clear Logs</button>
          <button className="btn btn-secondary">Export Diagnostics</button>
        </div>
      </div>
    </div>
  )
}

export default Diagnostics