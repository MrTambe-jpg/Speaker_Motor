import { useState } from 'react'
import { Settings, Cpu, Volume2, Sliders, Database, Info } from 'lucide-react'
import useStore from '../store'

const TABS = [
  { id: 'hardware', icon: Cpu, label: 'Hardware' },
  { id: 'audio', icon: Volume2, label: 'Audio Sources' },
  { id: 'motors', icon: Sliders, label: 'Motors' },
  { id: 'processors', icon: Database, label: 'Processors' },
  { id: 'system', icon: Info, label: 'System' },
]

function SettingsPage() {
  const [activeTab, setActiveTab] = useState('hardware')
  const { config, plugins, updateConfig, setHardware, setAudioSource } = useStore()

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Settings className="w-6 h-6 text-primary-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="text-dark-400 mt-1">Configure your OMNISOUND system</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-dark-700">
        <nav className="flex gap-4">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 transition
                ${activeTab === tab.id
                  ? 'border-primary-500 text-primary-400'
                  : 'border-transparent text-dark-400 hover:text-white hover:border-dark-500'}`}
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="card">
        {activeTab === 'hardware' && (
          <HardwareSettings config={config} plugins={plugins}
            updateConfig={updateConfig} setHardware={setHardware} />
        )}
        {activeTab === 'audio' && (
          <AudioSettings config={config} plugins={plugins}
            updateConfig={updateConfig} setAudioSource={setAudioSource} />
        )}
        {activeTab === 'motors' && (
          <MotorSettings config={config} updateConfig={updateConfig} />
        )}
        {activeTab === 'processors' && (
          <ProcessorSettings config={config} plugins={plugins} updateConfig={updateConfig} />
        )}
        {activeTab === 'system' && (
          <SystemSettings config={config} updateConfig={updateConfig} />
        )}
      </div>
    </div>
  )
}

// Hardware Settings Tab
function HardwareSettings({ config, plugins, updateConfig, setHardware }) {
  const hardwarePlugins = plugins?.hardware || []
  const activeHardware = config?.hardware?.active_plugin || 'simulation'

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-white mb-2">Hardware Plugin</h3>
        <p className="text-sm text-dark-400 mb-4">
          Select the hardware interface for your motor controller
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {hardwarePlugins.map((plugin) => (
            <div
              key={plugin.id}
              onClick={() => plugin.available && setHardware(plugin.id)}
              className={`plugin-card ${activeHardware === plugin.id ? 'active' : ''}
                         ${!plugin.available ? 'unavailable' : ''}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-white">{plugin.name}</span>
                <div className={`w-2 h-2 rounded-full
                  ${plugin.available ? 'bg-green-500' : 'bg-red-500'}`} />
              </div>
              <p className="text-sm text-dark-400">{plugin.description}</p>
              {!plugin.available && plugin.unavailable_reason && (
                <p className="text-xs text-red-400 mt-2">{plugin.unavailable_reason}</p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Plugin-specific settings */}
      {activeHardware && config?.hardware?.plugins?.[activeHardware] && (
        <div className="border-t border-dark-700 pt-6">
          <h3 className="text-lg font-medium text-white mb-4">
            {activeHardware} Settings
          </h3>
          <PluginConfigForm
            schema={hardwarePlugins.find(p => p.id === activeHardware)?.config_schema}
            values={config.hardware.plugins[activeHardware]}
            onChange={(key, value) => updateConfig(`hardware.plugins.${activeHardware}.${key}`, value)}
          />
        </div>
      )}
    </div>
  )
}

// Audio Settings Tab
function AudioSettings({ config, plugins, updateConfig, setAudioSource }) {
  const audioPlugins = plugins?.audio_source || []
  const activeSource = config?.audio?.active_source || 'microphone'

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-white mb-2">Audio Source</h3>
        <p className="text-sm text-dark-400 mb-4">
          Select the audio input for motor control
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {audioPlugins.map((plugin) => (
            <div
              key={plugin.id}
              onClick={() => plugin.available && setAudioSource(plugin.id)}
              className={`plugin-card ${activeSource === plugin.id ? 'active' : ''}
                         ${!plugin.available ? 'unavailable' : ''}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-white">{plugin.name}</span>
                <div className={`w-2 h-2 rounded-full
                  ${plugin.available ? 'bg-green-500' : 'bg-red-500'}`} />
              </div>
              <p className="text-sm text-dark-400">{plugin.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Audio settings */}
      <div className="border-t border-dark-700 pt-6">
        <h3 className="text-lg font-medium text-white mb-4">Audio Settings</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-dark-400 mb-2">Sample Rate</label>
            <select
              className="select"
              value={config?.audio?.sample_rate || 44100}
              onChange={(e) => updateConfig('audio.sample_rate', parseInt(e.target.value))}
            >
              <option value={22050}>22050 Hz</option>
              <option value={44100}>44100 Hz</option>
              <option value={48000}>48000 Hz</option>
              <option value={96000}>96000 Hz</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-2">Chunk Size</label>
            <select
              className="select"
              value={config?.audio?.chunk_size || 512}
              onChange={(e) => updateConfig('audio.chunk_size', parseInt(e.target.value))}
            >
              <option value={256}>256 samples</option>
              <option value={512}>512 samples</option>
              <option value={1024}>1024 samples</option>
              <option value={2048}>2048 samples</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}

// Motor Settings Tab
function MotorSettings({ config, updateConfig }) {
  const motors = config?.motors?.mapping || []

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-white mb-2">Motor Configuration</h3>
        <p className="text-sm text-dark-400 mb-4">
          Configure frequency bands and response parameters for each motor
        </p>

        {motors.map((motor, index) => (
          <div key={motor.id} className="card mb-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h4 className="font-medium text-white">{motor.name}</h4>
                <p className="text-xs text-dark-400">Motor {motor.id + 1}</p>
              </div>
              <label className="flex items-center gap-2">
                <span className="text-sm text-dark-400">Enabled</span>
                <input
                  type="checkbox"
                  checked={motor.enabled}
                  onChange={(e) => updateConfig(`motors.mapping.${index}.enabled`, e.target.checked)}
                  className="toggle"
                />
              </label>
            </div>

            {motor.mode === 'frequency_band' && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-dark-400 mb-2">Min Frequency (Hz)</label>
                  <input
                    type="number"
                    className="input"
                    value={motor.freq_min_hz}
                    onChange={(e) => updateConfig(`motors.mapping.${index}.freq_min_hz`, parseInt(e.target.value))}
                  />
                </div>
                <div>
                  <label className="block text-sm text-dark-400 mb-2">Max Frequency (Hz)</label>
                  <input
                    type="number"
                    className="input"
                    value={motor.freq_max_hz}
                    onChange={(e) => updateConfig(`motors.mapping.${index}.freq_max_hz`, parseInt(e.target.value))}
                  />
                </div>
                <div>
                  <label className="block text-sm text-dark-400 mb-2">Min Angle (°)</label>
                  <input
                    type="number"
                    className="input"
                    value={motor.angle_min}
                    onChange={(e) => updateConfig(`motors.mapping.${index}.angle_min`, parseInt(e.target.value))}
                  />
                </div>
                <div>
                  <label className="block text-sm text-dark-400 mb-2">Max Angle (°)</label>
                  <input
                    type="number"
                    className="input"
                    value={motor.angle_max}
                    onChange={(e) => updateConfig(`motors.mapping.${index}.angle_max`, parseInt(e.target.value))}
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm text-dark-400 mb-2">Smoothing: {motor.smoothing}</label>
                  <input
                    type="range"
                    className="slider w-full"
                    min="0"
                    max="1"
                    step="0.1"
                    value={motor.smoothing}
                    onChange={(e) => updateConfig(`motors.mapping.${index}.smoothing`, parseFloat(e.target.value))}
                  />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// Processor Settings Tab
function ProcessorSettings({ config, plugins, updateConfig }) {
  const processors = plugins?.processor || []
  const activeProcessors = config?.processors?.active || []

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-white mb-2">Audio Processors</h3>
        <p className="text-sm text-dark-400 mb-4">
          Configure real-time audio analysis processors
        </p>

        {processors.map((processor) => (
          <div key={processor.id} className="card mb-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-white">{processor.name}</h4>
                <p className="text-sm text-dark-400">{processor.description}</p>
              </div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={activeProcessors.includes(processor.id)}
                  onChange={(e) => {
                    const newProcessors = e.target.checked
                      ? [...activeProcessors, processor.id]
                      : activeProcessors.filter(p => p !== processor.id)
                    updateConfig('processors.active', newProcessors)
                  }}
                  className="toggle"
                />
              </label>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// System Settings Tab
function SystemSettings({ config, updateConfig }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-white mb-4">System Settings</h3>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-dark-400 mb-2">Host</label>
            <input
              type="text"
              className="input"
              value={config?.system?.host || '0.0.0.0'}
              onChange={(e) => updateConfig('system.host', e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-2">Port</label>
            <input
              type="number"
              className="input"
              value={config?.system?.port || 8000}
              onChange={(e) => updateConfig('system.port', parseInt(e.target.value))}
            />
          </div>
          <div className="col-span-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={config?.system?.auto_open_browser || false}
                onChange={(e) => updateConfig('system.auto_open_browser', e.target.checked)}
                className="toggle"
              />
              <span className="text-sm text-dark-300">Auto-open browser on start</span>
            </label>
          </div>
          <div className="col-span-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={config?.system?.auto_start || false}
                onChange={(e) => updateConfig('system.auto_start', e.target.checked)}
                className="toggle"
              />
              <span className="text-sm text-dark-300">Auto-start audio processing</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  )
}

// Generic Plugin Config Form
function PluginConfigForm({ schema, values, onChange }) {
  if (!schema?.properties) return null

  return (
    <div className="grid grid-cols-2 gap-4">
      {Object.entries(schema.properties).map(([key, prop]) => (
        <div key={key}>
          <label className="block text-sm text-dark-400 mb-2">{prop.title || key}</label>
          {prop.type === 'string' && (
            <input
              type="text"
              className="input"
              value={values?.[key] || ''}
              onChange={(e) => onChange(key, e.target.value)}
              placeholder={prop.description}
            />
          )}
          {prop.type === 'integer' && (
            <input
              type="number"
              className="input"
              value={values?.[key] || prop.default || 0}
              onChange={(e) => onChange(key, parseInt(e.target.value))}
              min={prop.minimum}
              max={prop.maximum}
            />
          )}
          {prop.type === 'number' && (
            <input
              type="number"
              className="input"
              value={values?.[key] || prop.default || 0}
              onChange={(e) => onChange(key, parseFloat(e.target.value))}
              min={prop.minimum}
              max={prop.maximum}
              step="0.01"
            />
          )}
          {prop.type === 'boolean' && (
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={values?.[key] || false}
                onChange={(e) => onChange(key, e.target.checked)}
                className="toggle"
              />
              <span className="text-sm text-dark-300">{prop.description}</span>
            </label>
          )}
          {prop.enum && (
            <select
              className="select"
              value={values?.[key] || prop.default}
              onChange={(e) => onChange(key, e.target.value)}
            >
              {prop.enum.map((val) => (
                <option key={val} value={val}>{val}</option>
              ))}
            </select>
          )}
        </div>
      ))}
    </div>
  )
}

export default SettingsPage