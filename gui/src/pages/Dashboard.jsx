import { useMemo } from 'react'
import { Activity, Music, Radio, Zap } from 'lucide-react'
import useStore from '../store'
import MotorArcWidget from '../components/MotorArcWidget'
import WaveformCanvas from '../components/WaveformCanvas'

function Dashboard() {
  const { config, motors, audioData, beatData, isRunning, connected } = useStore()

  const motorConfig = useMemo(() => {
    return config?.motors?.mapping || []
  }, [config])

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-dark-400 mt-1">Real-time motor control visualization</p>
        </div>
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm
                        ${isRunning ? 'bg-green-500/20 text-green-400' : 'bg-dark-700 text-dark-400'}`}>
            <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-dark-500'}`} />
            {isRunning ? 'Running' : 'Stopped'}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Audio & Source */}
        <div className="space-y-6">
          {/* Audio Source Card */}
          <div className="card">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 rounded-lg bg-primary-500/20 flex items-center justify-center">
                <Music className="w-6 h-6 text-primary-400" />
              </div>
              <div>
                <h3 className="font-medium text-white">
                  {config?.audio?.active_source || 'No Source Selected'}
                </h3>
                <p className="text-sm text-dark-400">
                  {connected ? 'Connected' : 'Disconnected'}
                </p>
              </div>
            </div>

            {/* Audio visualization */}
            <WaveformCanvas />

            {/* Beat indicator */}
            {beatData && (
              <div className="mt-4 flex items-center gap-4">
                <div className={`beat-indicator ${beatData.is_beat ? 'active' : ''}`} />
                <div className="flex-1">
                  <div className="text-sm text-dark-400">BPM</div>
                  <div className="text-2xl font-bold text-white">
                    {Math.round(beatData.bpm || 0)}
                  </div>
                </div>
                <div className="flex-1">
                  <div className="text-sm text-dark-400">Confidence</div>
                  <div className="text-lg text-primary-400">
                    {Math.round((beatData.confidence || 0) * 100)}%
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Status Cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="card text-center">
              <Radio className="w-5 h-5 text-primary-400 mx-auto mb-2" />
              <div className="text-xs text-dark-400">Sample Rate</div>
              <div className="font-medium text-white">
                {config?.audio?.sample_rate || 44100} Hz
              </div>
            </div>
            <div className="card text-center">
              <Activity className="w-5 h-5 text-green-400 mx-auto mb-2" />
              <div className="text-xs text-dark-400">Motors</div>
              <div className="font-medium text-white">
                {motors?.length || config?.motors?.count || 4}
              </div>
            </div>
            <div className="card text-center">
              <Zap className="w-5 h-5 text-yellow-400 mx-auto mb-2" />
              <div className="text-xs text-dark-400">Chunk Size</div>
              <div className="font-medium text-white">
                {config?.audio?.chunk_size || 512}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Motors */}
        <div className="space-y-6">
          <div className="card">
            <h3 className="font-medium text-white mb-4">Motor Status</h3>
            <div className="grid grid-cols-2 gap-4">
              {motors?.length > 0 ? (
                motors.map((motor) => (
                  <MotorArcWidget
                    key={motor.id}
                    motor={motor}
                    config={motorConfig.find(m => m.id === motor.id)}
                  />
                ))
              ) : (
                <div className="col-span-2 text-center py-8 text-dark-400">
                  No motors configured
                </div>
              )}
            </div>
          </div>

          {/* Frequency Bands */}
          <div className="card">
            <h3 className="font-medium text-white mb-4">Frequency Bands</h3>
            <div className="space-y-3">
              {motorConfig.map((motor, index) => (
                <div key={motor.id} className="flex items-center gap-3">
                  <div className="w-16 text-sm text-dark-300">{motor.name}</div>
                  <div className="flex-1 h-2 bg-dark-700 rounded overflow-hidden">
                    <div
                      className="h-full bg-primary-500 transition-all"
                      style={{
                        width: `${(motor.freq_min_hz / 20000) * 100}%`
                      }}
                    />
                  </div>
                  <div className="w-24 text-right text-sm">
                    <span className="text-dark-400">{motor.freq_min_hz}Hz</span>
                    <span className="text-dark-500"> - </span>
                    <span className="text-dark-300">{motor.freq_max_hz}Hz</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard