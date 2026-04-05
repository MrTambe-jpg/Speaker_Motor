import { History, Play, Trash2, Download, Upload } from 'lucide-react'
import { useState } from 'react'
import useStore from '../store'

function Sequences() {
  const { config, sendCommand } = useStore()
  const sequences = config?.sequences?.saved || []
  const [selectedSequence, setSelectedSequence] = useState(null)
  const [isRecording, setIsRecording] = useState(false)

  const handlePlay = async (seq, e) => {
    e.stopPropagation()
    sendCommand({ cmd: 'sequence_play', sequence: seq })
  }

  const handleDelete = async (seqId, e) => {
    e.stopPropagation()
    const updated = sequences.filter(s => s.id !== seqId)
    sendCommand({ cmd: 'set_config', path: 'sequences.saved', value: updated })
  }

  const handleRecord = () => {
    if (isRecording) {
      sendCommand({ cmd: 'record_stop', name: `Sequence ${sequences.length + 1}` })
      setIsRecording(false)
    } else {
      sendCommand({ cmd: 'record_start' })
      setIsRecording(true)
    }
  }

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(sequences, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'omnisound_sequences.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async (e) => {
      const file = e.target.files[0]
      if (!file) return
      const text = await file.text()
      try {
        const imported = JSON.parse(text)
        sendCommand({ cmd: 'set_config', path: 'sequences.saved', value: imported })
      } catch (err) {
        console.error('Failed to import sequences:', err)
      }
    }
    input.click()
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <History className="w-6 h-6 text-primary-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Sequences</h1>
            <p className="text-dark-400 mt-1">Record and playback motor sequences</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-secondary flex items-center gap-2" onClick={handleImport}>
            <Upload className="w-4 h-4" />
            Import
          </button>
          <button className="btn btn-secondary flex items-center gap-2" onClick={handleExport}>
            <Download className="w-4 h-4" />
            Export
          </button>
          <button
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200
              ${isRecording
                ? 'bg-red-500 text-white hover:bg-red-600'
                : 'bg-primary-500 text-white hover:bg-primary-600'}`}
            onClick={handleRecord}
          >
            <div className={`w-3 h-3 rounded-full ${isRecording ? 'bg-white animate-pulse' : 'bg-white'}`} />
            {isRecording ? 'Stop Recording' : 'Record'}
          </button>
        </div>
      </div>

      {/* Sequence List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sequences.length > 0 ? (
          sequences.map((seq, index) => (
            <div
              key={seq.id || index}
              className={`card card-hover cursor-pointer ${selectedSequence === index ? 'border-primary-500' : ''}`}
              onClick={() => setSelectedSequence(index)}
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-medium text-white">{seq.name}</h3>
                  <p className="text-sm text-dark-400">{seq.duration}s • {seq.motor_count} motors</p>
                </div>
                <div className="flex items-center gap-2">
                  <button className="p-2 hover:bg-dark-700 rounded" onClick={(e) => handlePlay(seq, e)}>
                    <Play className="w-4 h-4 text-primary-400" />
                  </button>
                  <button className="p-2 hover:bg-dark-700 rounded" onClick={(e) => handleDelete(seq.id, e)}>
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              </div>
              <div className="text-xs text-dark-500">
                Created: {new Date(seq.timestamp).toLocaleDateString()}
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full text-center py-12 text-dark-400">
            <History className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No sequences recorded yet</p>
            <p className="text-sm mt-2">Start recording from the dashboard</p>
          </div>
        )}
      </div>

      {/* Empty State */}
      {sequences.length === 0 && (
        <div className="card">
          <div className="text-center py-8">
            <h3 className="text-lg font-medium text-white mb-2">Getting Started with Sequences</h3>
            <p className="text-dark-400 mb-4">
              Record motor movements to create reusable sequences. Perfect for
              creating music-reactive animations that sync with your favorite tracks.
            </p>
            <div className="flex justify-center gap-4">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-primary-500/20 flex items-center justify-center mx-auto mb-2">
                  <span className="text-primary-400 font-bold">1</span>
                </div>
                <p className="text-sm text-dark-300">Select audio source</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-primary-500/20 flex items-center justify-center mx-auto mb-2">
                  <span className="text-primary-400 font-bold">2</span>
                </div>
                <p className="text-sm text-dark-300">Click Record</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-primary-500/20 flex items-center justify-center mx-auto mb-2">
                  <span className="text-primary-400 font-bold">3</span>
                </div>
                <p className="text-sm text-dark-300">Save sequence</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Sequences