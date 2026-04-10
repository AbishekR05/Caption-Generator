import { useState, useEffect } from 'react'
import axios from 'axios'
import PropTypes from 'prop-types'

function StatusBar({ isConnected, inputMode, micActive, captionCount }) {
  const [gpuName, setGpuName] = useState('Checking...')

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await axios.get('http://localhost:5000/health')
        if (res.data.status === 'ok') {
          setGpuName(res.data.gpu ? res.data.gpu : res.data.device)
        }
      } catch {
        setGpuName('Backend Unreachable')
      }
    }
    checkHealth()
  }, [])

  return (
    <div className="w-full bg-gray-900 border-b border-gray-800 text-gray-300 text-xs py-2 px-4 flex justify-between items-center shadow-md">
      <div className="flex items-center gap-6">
        {/* Connection status */}
        <div className="flex items-center gap-2">
          <div className="relative flex h-2.5 w-2.5">
            {isConnected && micActive && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            )}
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
          </div>
          <span className="font-semibold tracking-wide uppercase">{isConnected ? 'Backend Connected' : 'Disconnected'}</span>
        </div>

        {/* Microphones tracking */}
        <div className="flex items-center gap-2 text-gray-400 border-l border-gray-700 pl-4">
          <span title="Active input channel">
            {inputMode === 'mic' ? '🎤 Mic Active' : '🖥️ System Audio'}
          </span>
          {micActive && (
             <span className="bg-indigo-500/20 text-indigo-400 font-semibold px-2 rounded-md ml-2">
               {captionCount} Captions
             </span>
          )}
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <span className="text-gray-400">GPU: <span className="text-gray-200">{gpuName}</span></span>
        <span className="text-gray-500">v1.1.0</span>
      </div>
    </div>
  )
}

StatusBar.propTypes = {
  isConnected: PropTypes.bool,
  inputMode: PropTypes.string,
  micActive: PropTypes.bool,
  captionCount: PropTypes.number
}

export default StatusBar
