import { useRef, useState } from 'react'
import PropTypes from 'prop-types'
import OverlaySettings from './OverlaySettings'

function Controls({ 
  direction, onDirectionChange, 
  onFileUpload, isLoading, 
  micActive, onMicToggle,
  inputMode, onInputModeChange,
  translateEnabled, onTranslateToggle,
  captionHistory = [], onExport, onClearHistory,
  isConnected
}) {
  const fileInputRef = useRef(null)
  const [showSettings, setShowSettings] = useState(false)

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileUpload(e.target.files[0])
      e.target.value = null
    }
  }

  return (
    <div className={`bg-gray-800 rounded-xl p-6 shadow-lg flex flex-col gap-6 transition-opacity ${!isConnected ? 'opacity-50 pointer-events-none' : ''}`}>
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
          Caption Controls
        </h2>
        <button 
          onClick={() => setShowSettings(!showSettings)}
          className={`p-2 rounded-lg transition-colors ${showSettings ? 'bg-indigo-500/20 text-indigo-400' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'}`}
          title="Toggle Overlay Settings"
        >
          ⚙️
        </button>
      </div>

      {showSettings && <OverlaySettings onSettingsChange={() => {}} />}

      {/* 1. Input Mode Switch */}
      <div className="flex flex-col gap-2">
        <label className="text-sm font-semibold text-gray-400">Audio Input Mode</label>
        <div className="flex gap-2" title="Select what audio to capture">
          <button
            disabled={micActive || isLoading}
            onClick={() => onInputModeChange('mic')}
            className={`flex-1 py-2 px-3 text-sm font-bold rounded-lg transition-all ${
              inputMode === 'mic'
                ? 'bg-indigo-500 text-white shadow'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            } ${(micActive || isLoading) ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            🎤 Microphone
          </button>
          <button
            disabled={micActive || isLoading}
            onClick={() => onInputModeChange('system')}
            className={`flex-1 py-2 px-3 text-sm font-bold rounded-lg transition-all ${
              inputMode === 'system'
                ? 'bg-indigo-500 text-white shadow'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            } ${(micActive || isLoading) ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            🖥️ System Audio
          </button>
        </div>
      </div>

      {/* 2. Mic Control */}
      <div className="flex flex-col gap-2">
        <button
          onClick={onMicToggle}
          title={micActive ? 'Stop capturing audio' : 'Start live captions'}
          className={`py-3 px-4 rounded-lg font-bold transition-all shadow-md active:scale-95 ${
            micActive
              ? 'bg-red-500 hover:bg-red-600 text-white shadow-red-500/20 animate-pulse'
              : 'bg-gray-700 hover:bg-gray-600 text-gray-200 shadow-gray-900/50'
          }`}
        >
          {micActive ? 'Stop Subtitles' : 'Start Subtitles'}
        </button>
      </div>

      <hr className="border-gray-700" />
      
      {/* 3. Translation Toggle */}
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center" title="Toggle Tamil translations below English">
            <label className="text-sm font-semibold text-gray-400">Tamil Translation</label>
            <button 
                onClick={() => onTranslateToggle(!translateEnabled)}
                className={`w-12 h-6 rounded-full transition-colors relative ${translateEnabled ? 'bg-indigo-500' : 'bg-gray-600'}`}
            >
                <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${translateEnabled ? 'translate-x-7' : 'translate-x-1'}`}></div>
            </button>
        </div>
        <span className="text-xs text-gray-500 italic block">Changes apply to next audio chunk</span>
      </div>

      {/* 4. Translation Direction */}
      <div className={`flex flex-col gap-2 transition-opacity ${!translateEnabled ? 'opacity-50 pointer-events-none' : ''}`}>
        <label className="text-sm font-semibold text-gray-400">Direction</label>
        <div className="flex bg-gray-900 rounded-lg p-1">
          <button
            onClick={() => onDirectionChange('en-ta')}
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
              direction === 'en-ta'
                ? 'bg-indigo-500 text-white shadow'
                : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
            }`}
          >
            EN → TA
          </button>
        </div>
      </div>

      {/* 5. Audio File Upload */}
      <div className="flex flex-col gap-2">
        <label className="text-sm font-semibold text-gray-400">File Analysis Pipeline</label>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".mp3,.wav,.m4a,.mp4,.mkv"
          className="hidden"
          disabled={isLoading}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading}
          className={`py-6 border-2 border-dashed rounded-xl transition-colors flex flex-col items-center justify-center gap-2 ${
            isLoading
              ? 'border-indigo-500/50 bg-indigo-500/10 cursor-wait'
              : 'border-gray-600 hover:border-indigo-400 hover:bg-gray-700/50'
          }`}
        >
          {isLoading ? (
            <>
              <div className="w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-indigo-400 font-medium">Processing Audio...</span>
            </>
          ) : (
            <>
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span className="text-gray-300 font-medium">Click to Upload Audio</span>
              <span className="text-xs text-gray-500">Supports .mp3, .wav, .m4a</span>
            </>
          )}
        </button>
      </div>

      {/* 6. Export Block */}
      {captionHistory.length > 0 && (
        <div className="flex gap-2 pt-2 border-t border-gray-700 animate-fade-in-up">
          <button onClick={() => onExport('srt')}
            className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-2 rounded-lg text-sm font-semibold transition-colors shadow"
            title="Export standard subtitle timeline">
            💾 .SRT
          </button>
          <button onClick={() => onExport('txt')}
            className="flex-1 bg-blue-600 hover:bg-blue-500 text-white px-2 py-2 rounded-lg text-sm font-semibold transition-colors shadow"
            title="Export raw textual transcripts">
            📄 .TXT
          </button>
          <button onClick={onClearHistory}
            className="flex-1 bg-rose-900/40 hover:bg-rose-900/60 text-rose-300 px-2 py-2 rounded-lg text-sm font-semibold transition-colors"
            title="Wipe current caption queues">
            🗑 Clear
          </button>
        </div>
      )}

    </div>
  )
}

Controls.propTypes = {
  direction: PropTypes.string,
  onDirectionChange: PropTypes.func,
  onFileUpload: PropTypes.func,
  isLoading: PropTypes.bool,
  micActive: PropTypes.bool,
  onMicToggle: PropTypes.func,
  inputMode: PropTypes.string,
  onInputModeChange: PropTypes.func,
  translateEnabled: PropTypes.bool,
  onTranslateToggle: PropTypes.func,
  captionHistory: PropTypes.array,
  onExport: PropTypes.func,
  onClearHistory: PropTypes.func,
  isConnected: PropTypes.bool
}

export default Controls
