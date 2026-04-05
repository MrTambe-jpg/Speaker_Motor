import { Settings, RotateCcw, Zap } from 'lucide-react'
import useStore from '../store'

function MotorConfig() {
  const { config, motors, updateConfig, testMotor, setMotorAngle } = useStore()
  const motorConfig = config?.motors?.mapping || []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Slider className="w-6 h-6 text-primary-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">Motor Configuration</h1>
          <p className="text-dark-400 mt-1">Configure motor frequency mapping and response</p>
        </div>
      </div>

      {/* Motor Count */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium text-white">Number of Motors</h3>
            <p className="text-sm text-dark-400">Configure how many motors are connected</p>
          </div>
          <select
            className="select w-24"
            value={config?.motors?.count || 4}
            onChange={(e) => updateConfig('motors.count', parseInt(e.target.value))}
          >
            {[1, 2, 3, 4, 5, 6, 7, 8].map(n => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Motor Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {motorConfig.map((motor, index) => (
          <MotorCard
            key={motor.id}
            motor={motor}
            index={index}
            liveState={motors?.find(m => m.id === motor.id)}
            updateConfig={updateConfig}
            onTest={() => testMotor(motor.id)}
          />
        ))}
      </div>

      {/* Frequency Preview */}
      <div className="card">
        <h3 className="font-medium text-white mb-4">Frequency Range Preview</h3>
        <div className="h-8 bg-dark-700 rounded relative overflow-hidden">
          {motorConfig.map((motor, index) => {
            const colors = ['bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-red-500']
            const left = (motor.freq_min_hz / 20000) * 100
            const right = (motor.freq_max_hz / 20000) * 100
            const width = right - left

            return (
              <div
                key={motor.id}
                className={`absolute h-full ${colors[index % colors.length]} opacity-50`}
                style={{ left: `${left}%`, width: `${width}%` }}
              >
                <span className="absolute inset-0 flex items-center justify-center text-xs text-white font-medium">
                  {motor.name}
                </span>
              </div>
            )
          })}
        </div>
        <div className="flex justify-between text-xs text-dark-400 mt-2">
          <span>20 Hz</span>
          <span>200 Hz</span>
          <span>2 kHz</span>
          <span>20 kHz</span>
        </div>
      </div>
    </div>
  )
}

function MotorCard({ motor, index, liveState, updateConfig, onTest }) {
  const mode = motor.mode || 'frequency_band'

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary-500/20 flex items-center justify-center">
            <span className="text-primary-400 font-bold">{motor.id + 1}</span>
          </div>
          <div>
            <input
              type="text"
              className="bg-transparent border-none text-white font-medium focus:outline-none focus:ring-0"
              value={motor.name}
              onChange={(e) => updateConfig(`motors.mapping.${index}.name`, e.target.value)}
            />
            <div className="flex items-center gap-2 text-sm text-dark-400">
              <span>{mode}</span>
              {liveState && (
                <span>• {liveState.angle?.toFixed(0)}°</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onTest}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Zap className="w-4 h-4" />
            Test
          </button>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={motor.enabled}
              onChange={(e) => updateConfig(`motors.mapping.${index}.enabled`, e.target.checked)}
              className="toggle"
            />
          </label>
        </div>
      </div>

      {/* Mode selector */}
      <div className="mb-4">
        <label className="block text-sm text-dark-400 mb-2">Mode</label>
        <select
          className="select"
          value={mode}
          onChange={(e) => updateConfig(`motors.mapping.${index}.mode`, e.target.value)}
        >
          <option value="frequency_band">Frequency Band</option>
          <option value="beat">Beat Detection</option>
          <option value="pitch_track">Pitch Track</option>
          <option value="manual">Manual</option>
        </select>
      </div>

      {mode === 'frequency_band' && (
        <div className="space-y-4">
          {/* Frequency range */}
          <div>
            <label className="block text-sm text-dark-400 mb-2">
              Frequency Range: {motor.freq_min_hz} Hz - {motor.freq_max_hz} Hz
            </label>
            <div className="flex gap-4">
              <input
                type="range"
                className="slider flex-1"
                min="20"
                max="20000"
                step="10"
                value={motor.freq_min_hz}
                onChange={(e) => updateConfig(`motors.mapping.${index}.freq_min_hz`, parseInt(e.target.value))}
              />
              <input
                type="range"
                className="slider flex-1"
                min="20"
                max="20000"
                step="10"
                value={motor.freq_max_hz}
                onChange={(e) => updateConfig(`motors.mapping.${index}.freq_max_hz`, parseInt(e.target.value))}
              />
            </div>
          </div>

          {/* Angle range */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-dark-400 mb-2">Min Angle (°)</label>
              <input
                type="number"
                className="input"
                min="0"
                max="180"
                value={motor.angle_min}
                onChange={(e) => updateConfig(`motors.mapping.${index}.angle_min`, parseInt(e.target.value))}
              />
            </div>
            <div>
              <label className="block text-sm text-dark-400 mb-2">Max Angle (°)</label>
              <input
                type="number"
                className="input"
                min="0"
                max="180"
                value={motor.angle_max}
                onChange={(e) => updateConfig(`motors.mapping.${index}.angle_max`, parseInt(e.target.value))}
              />
            </div>
          </div>

          {/* Smoothing */}
          <div>
            <label className="block text-sm text-dark-400 mb-2">
              Smoothing: {motor.smoothing}
            </label>
            <input
              type="range"
              className="slider w-full"
              min="0"
              max="1"
              step="0.05"
              value={motor.smoothing}
              onChange={(e) => updateConfig(`motors.mapping.${index}.smoothing`, parseFloat(e.target.value))}
            />
          </div>
        </div>
      )}

      {mode === 'beat' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-dark-400 mb-2">Kick Angle (°)</label>
              <input
                type="number"
                className="input"
                min="0"
                max="180"
                value={motor.beat_kick_angle}
                onChange={(e) => updateConfig(`motors.mapping.${index}.beat_kick_angle`, parseInt(e.target.value))}
              />
            </div>
            <div>
              <label className="block text-sm text-dark-400 mb-2">Rest Angle (°)</label>
              <input
                type="number"
                className="input"
                min="0"
                max="180"
                value={motor.beat_rest_angle}
                onChange={(e) => updateConfig(`motors.mapping.${index}.beat_rest_angle`, parseInt(e.target.value))}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-2">
              Hold Time: {motor.beat_hold_ms} ms
            </label>
            <input
              type="range"
              className="slider w-full"
              min="20"
              max="500"
              step="10"
              value={motor.beat_hold_ms}
              onChange={(e) => updateConfig(`motors.mapping.${index}.beat_hold_ms`, parseInt(e.target.value))}
            />
          </div>
        </div>
      )}

      {mode === 'manual' && (
        <div>
          <label className="block text-sm text-dark-400 mb-2">
            Manual Angle: {liveState?.angle?.toFixed(0) || 90}°
          </label>
          <input
            type="range"
            className="slider w-full"
            min={motor.angle_min || 0}
            max={motor.angle_max || 180}
            step="1"
            value={liveState?.angle || 90}
            onChange={(e) => setMotorAngle(motor.id, parseInt(e.target.value))}
          />
        </div>
      )}
    </div>
  )
}

export default MotorConfig