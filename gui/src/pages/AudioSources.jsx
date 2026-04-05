import { useState } from 'react'
import { Music, Mic, FileAudio, Radio, Youtube, Volume2, CheckCircle, XCircle } from 'lucide-react'
import useStore from '../store'

// Audio source icons
const SOURCE_ICONS = {
  microphone: Mic,
  file_player: FileAudio,
  system_audio: Radio,
  youtube: Youtube,
  spotify: Music,
  default: Volume2
}

function AudioSources() {
  const { config, plugins, setAudioSource } = useStore()
  const audioPlugins = plugins?.audio_source || []
  const activeSource = config?.audio?.active_source || 'microphone'

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Music className="w-6 h-6 text-primary-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">Audio Sources</h1>
          <p className="text-dark-400 mt-1">Select and configure audio input</p>
        </div>
      </div>

      {/* Source Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {audioPlugins.map((plugin) => {
          const Icon = SOURCE_ICONS[plugin.id] || SOURCE_ICONS.default
          const isActive = activeSource === plugin.id

          return (
            <div
              key={plugin.id}
              onClick={() => plugin.available && setAudioSource(plugin.id)}
              className={`card card-hover cursor-pointer ${isActive ? 'border-primary-500' : ''}`}
            >
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center
                  ${plugin.available ? 'bg-primary-500/20' : 'bg-dark-700'}`}>
                  <Icon className={`w-6 h-6 ${plugin.available ? 'text-primary-400' : 'text-dark-400'}`} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-white">{plugin.name}</h3>
                    {isActive && (
                      <CheckCircle className="w-4 h-4 text-primary-400" />
                    )}
                  </div>
                  <p className="text-sm text-dark-400 mt-1">{plugin.description}</p>
                  {!plugin.available && (
                    <div className="flex items-center gap-1 mt-2 text-red-400">
                      <XCircle className="w-3 h-3" />
                      <span className="text-xs">{plugin.unavailable_reason}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Active Source Configuration */}
      {activeSource && (
        <div className="card">
          <h3 className="text-lg font-medium text-white mb-4">
            {activeSource} Configuration
          </h3>
          <SourceConfig sourceId={activeSource} config={config} />
        </div>
      )}
    </div>
  )
}

// Source-specific configuration
function SourceConfig({ sourceId, config }) {
  const { updateConfig } = useStore()

  switch (sourceId) {
    case 'microphone':
      return <MicrophoneConfig config={config} updateConfig={updateConfig} />
    case 'file_player':
      return <FilePlayerConfig config={config} updateConfig={updateConfig} />
    case 'system_audio':
      return <SystemAudioConfig config={config} updateConfig={updateConfig} />
    default:
      return (
        <div className="text-dark-400">
          No configuration available for this source.
        </div>
      )
  }
}

function MicrophoneConfig({ config, updateConfig }) {
  const micConfig = config?.audio?.plugins?.microphone || {}

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-dark-400 mb-2">Sample Rate</label>
          <select
            className="select"
            value={micConfig.sample_rate || 44100}
            onChange={(e) => updateConfig('audio.plugins.microphone.sample_rate', parseInt(e.target.value))}
          >
            <option value={22050}>22050 Hz</option>
            <option value={44100}>44100 Hz</option>
            <option value={48000}>48000 Hz</option>
            <option value={96000}>96000 Hz</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-dark-400 mb-2">Channels</label>
          <select
            className="select"
            value={micConfig.channels || 1}
            onChange={(e) => updateConfig('audio.plugins.microphone.channels', parseInt(e.target.value))}
          >
            <option value={1}>Mono</option>
            <option value={2}>Stereo</option>
          </select>
        </div>
      </div>
      <div>
        <label className="block text-sm text-dark-400 mb-2">Gain: {micConfig.gain || 1.0}</label>
        <input
          type="range"
          className="slider w-full"
          min="0.1"
          max="10"
          step="0.1"
          value={micConfig.gain || 1.0}
          onChange={(e) => updateConfig('audio.plugins.microphone.gain', parseFloat(e.target.value))}
        />
      </div>
    </div>
  )
}

function FilePlayerConfig({ config, updateConfig }) {
  const fileConfig = config?.audio?.plugins?.file_player || {}

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm text-dark-400 mb-2">File Path</label>
        <input
          type="text"
          className="input"
          placeholder="Select or drag a file..."
          value={fileConfig.file_path || ''}
          onChange={(e) => updateConfig('audio.plugins.file_player.file_path', e.target.value)}
        />
      </div>
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={fileConfig.shuffle || false}
            onChange={(e) => updateConfig('audio.plugins.file_player.shuffle', e.target.checked)}
            className="toggle"
          />
          <span className="text-sm text-dark-300">Shuffle</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={fileConfig.repeat || false}
            onChange={(e) => updateConfig('audio.plugins.file_player.repeat', e.target.checked)}
            className="toggle"
          />
          <span className="text-sm text-dark-300">Repeat</span>
        </label>
      </div>
    </div>
  )
}

function SystemAudioConfig({ config, updateConfig }) {
  return (
    <div className="space-y-4">
      <div className="bg-dark-700 rounded-lg p-4">
        <h4 className="font-medium text-white mb-2">System Audio Setup</h4>
        <p className="text-sm text-dark-400 mb-3">
          Captures whatever is playing on your computer's speakers.
        </p>
        <div className="text-sm text-dark-300">
          <p><strong>Windows:</strong> Works automatically via WASAPI loopback</p>
          <p><strong>macOS:</strong> Requires BlackHole or similar virtual audio device</p>
          <p><strong>Linux:</strong> Use PulseAudio monitor source or PipeWire</p>
        </div>
      </div>
    </div>
  )
}

export default AudioSources