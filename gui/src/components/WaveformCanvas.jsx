import { useRef, useEffect, useState } from 'react'

function WaveformCanvas({ audioData, fftData }) {
  const canvasRef = useRef(null)
  const [mode, setMode] = useState('waveform') // 'waveform' or 'spectrum'
  const animationRef = useRef(null)
  const dataArray = useRef([])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const width = canvas.width
    const height = canvas.height

    // Handle resize
    const handleResize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio
      canvas.height = canvas.offsetHeight * window.devicePixelRatio
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
    }

    handleResize()
    window.addEventListener('resize', handleResize)

    // Animation loop
    const draw = () => {
      const displayWidth = canvas.offsetWidth
      const displayHeight = canvas.offsetHeight

      // Clear canvas
      ctx.fillStyle = '#0f172a'
      ctx.fillRect(0, 0, displayWidth, displayHeight)

      if (mode === 'waveform') {
        drawWaveform(ctx, displayWidth, displayHeight)
      } else {
        drawSpectrum(ctx, displayWidth, displayHeight)
      }

      animationRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      window.removeEventListener('resize', handleResize)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [mode])

  // Update data when audioData changes
  useEffect(() => {
    if (audioData?.samples) {
      dataArray.current = audioData.samples
    }
  }, [audioData])

  const drawWaveform = (ctx, width, height) => {
    const samples = dataArray.current
    const centerY = height / 2

    ctx.strokeStyle = '#0ea5e9'
    ctx.lineWidth = 2
    ctx.beginPath()

    if (samples && samples.length > 0) {
      const step = width / samples.length
      for (let i = 0; i < samples.length; i++) {
        const x = i * step
        const y = centerY + samples[i] * (height / 2) * 0.8
        if (i === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      }
    } else {
      // Draw flat line if no data
      ctx.moveTo(0, centerY)
      ctx.lineTo(width, centerY)
    }

    ctx.stroke()

    // Draw center line
    ctx.strokeStyle = '#334155'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, centerY)
    ctx.lineTo(width, centerY)
    ctx.stroke()
  }

  const drawSpectrum = (ctx, width, height) => {
    const magnitudes = fftData?.magnitudes || []
    const frequencies = fftData?.frequencies || []

    if (magnitudes.length === 0) {
      // Draw placeholder
      ctx.fillStyle = '#334155'
      ctx.font = '14px system-ui'
      ctx.textAlign = 'center'
      ctx.fillText('No spectrum data', width / 2, height / 2)
      return
    }

    const barCount = 64 // Number of bars to display
    const barWidth = width / barCount - 2
    const step = Math.floor(magnitudes.length / barCount)

    for (let i = 0; i < barCount; i++) {
      const index = i * step
      const magnitude = magnitudes[index] || 0
      const barHeight = magnitude * height * 0.8

      const x = i * (barWidth + 2)
      const y = height - barHeight

      // Gradient color based on frequency
      const hue = (i / barCount) * 240 // Blue to red
      ctx.fillStyle = `hsl(${200 + hue * 0.3}, 80%, 60%)`
      ctx.fillRect(x, y, barWidth, barHeight)
    }
  }

  return (
    <div className="relative">
      <canvas
        ref={canvasRef}
        className="w-full h-48 bg-dark-900 rounded-lg"
      />
      <div className="absolute bottom-2 right-2 flex gap-2">
        <button
          onClick={() => setMode('waveform')}
          className={`px-2 py-1 text-xs rounded ${mode === 'waveform' ? 'bg-primary-500 text-white' : 'bg-dark-700 text-dark-300'}`}
        >
          Waveform
        </button>
        <button
          onClick={() => setMode('spectrum')}
          className={`px-2 py-1 text-xs rounded ${mode === 'spectrum' ? 'bg-primary-500 text-white' : 'bg-dark-700 text-dark-300'}`}
        >
          Spectrum
        </button>
      </div>
    </div>
  )
}

export default WaveformCanvas