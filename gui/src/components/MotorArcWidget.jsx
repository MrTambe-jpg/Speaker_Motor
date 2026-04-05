import { useMemo } from 'react'

function MotorArcWidget({ motor, config }) {
  const angle = motor?.angle ?? config?.center_angle ?? 90
  const amplitude = motor?.amplitude ?? 0

  // Calculate arc path
  const { arcPath, indicatorX, indicatorY, color } = useMemo(() => {
    const minAngle = config?.angle_min ?? 45
    const maxAngle = config?.angle_max ?? 135
    const centerAngle = config?.center_angle ?? 90
    const range = maxAngle - minAngle

    // Map angle to indicator position
    const normalizedAngle = (angle - minAngle) / range
    const arcRadius = 40

    // Calculate arc endpoints
    const startAngle = ((minAngle - 90) * Math.PI) / 180
    const endAngle = ((maxAngle - 90) * Math.PI) / 180

    // SVG arc path
    const cx = 50 // center x
    const cy = 50 // center y

    const x1 = cx + arcRadius * Math.cos(startAngle)
    const y1 = cy + arcRadius * Math.sin(startAngle)
    const x2 = cx + arcRadius * Math.cos(endAngle)
    const y2 = cy + arcRadius * Math.sin(endAngle)

    // Indicator position
    const indicatorAngle = ((angle - 90) * Math.PI) / 180
    const ix = cx + arcRadius * Math.cos(indicatorAngle)
    const iy = cy + arcRadius * Math.sin(indicatorAngle)

    // Color based on mode
    const mode = config?.mode || 'frequency_band'
    let color
    switch (mode) {
      case 'beat':
        color = '#ef4444' // red
        break
      case 'pitch_track':
        color = '#22c55e' // green
        break
      default:
        color = '#0ea5e9' // primary blue
    }

    return {
      arcPath: `M ${x1} ${y1} A ${arcRadius} ${arcRadius} 0 0 1 ${x2} ${y2}`,
      indicatorX: ix,
      indicatorY: iy,
      color
    }
  }, [angle, config])

  return (
    <div className="bg-dark-700 rounded-lg p-4">
      {/* SVG Arc Display */}
      <div className="relative w-24 h-24 mx-auto">
        <svg viewBox="0 0 100 100" className="w-full h-full">
          {/* Background arc */}
          <path
            d={arcPath}
            fill="none"
            stroke="#334155"
            strokeWidth="8"
            strokeLinecap="round"
          />
          {/* Active arc */}
          <path
            d={arcPath}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${(angle - (config?.angle_min ?? 45)) / (config?.angle_max ?? 135 - (config?.angle_min ?? 45)) * 100} 100`}
            opacity={0.8}
          />
          {/* Indicator */}
          <circle
            cx={indicatorX}
            cy={indicatorY}
            r="6"
            fill={color}
            className="drop-shadow-lg"
          />
          {/* Center */}
          <circle cx="50" cy="50" r="3" fill="#64748b" />
        </svg>

        {/* Angle display */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-white font-bold text-lg">
            {Math.round(angle)}°
          </span>
        </div>
      </div>

      {/* Motor name and info */}
      <div className="mt-3 text-center">
        <div className="text-white font-medium">{config?.name || `Motor ${motor?.id + 1}`}</div>
        <div className="text-xs text-dark-400">
          {config?.mode === 'beat' ? 'Beat' : `${config?.freq_min_hz || 0}-${config?.freq_max_hz || 0} Hz`}
        </div>
      </div>

      {/* Amplitude bar */}
      <div className="mt-2">
        <div className="h-1 bg-dark-600 rounded overflow-hidden">
          <div
            className="h-full transition-all duration-75"
            style={{
              width: `${amplitude * 100}%`,
              backgroundColor: color
            }}
          />
        </div>
      </div>

      {/* Status */}
      <div className="flex items-center justify-center gap-2 mt-2">
        <div className={`w-2 h-2 rounded-full ${motor?.enabled !== false ? 'bg-green-500' : 'bg-dark-500'}`} />
        <span className="text-xs text-dark-400">
          {motor?.enabled !== false ? 'Active' : 'Disabled'}
        </span>
      </div>
    </div>
  )
}

export default MotorArcWidget