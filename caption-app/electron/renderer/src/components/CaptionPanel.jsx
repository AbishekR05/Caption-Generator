import { useState, useEffect } from 'react'
import PropTypes from 'prop-types'

function CaptionPanel({ transcript, translated, direction, isLoading, translateEnabled, micActive }) {
  const [elapsed, setElapsed] = useState(0)

  // Track session timer dynamically
  useEffect(() => {
    let interval = null
    if (micActive) {
      interval = setInterval(() => setElapsed(e => e + 1), 1000)
    } else {
      setElapsed(0)
    }
    return () => clearInterval(interval)
  }, [micActive])

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0')
    const s = (secs % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  const isEnToTa = direction === 'en-ta'
  const isTranscriptEmpty = !transcript && !isLoading
  const isTranslationEmpty = !translated && !isLoading

  return (
    <div className="flex-1 flex flex-col gap-4 min-h-[500px]">
      
      {/* Dynamic Session Timer Render */}
      {micActive && (
        <div className="flex justify-end text-xs font-semibold text-gray-400 animate-fade-in-down pr-2">
           Session Time: <span className="ml-2 text-indigo-300 tracking-wider font-mono">{formatTime(elapsed)}</span>
        </div>
      )}

      {/* Tailwind grid gracefully stretches single column to dual columns seamlessly tracking translations */}
      <div className={`flex-1 grid grid-cols-1 ${translateEnabled ? 'md:grid-cols-2' : ''} gap-4 transition-all duration-500 ease-in-out`}>
        
        {/* Source Text Panel */}
        <div className="bg-gray-800 rounded-xl overflow-hidden shadow-lg flex flex-col border border-gray-700">
          <div className="bg-gray-900 px-4 py-3 border-b border-gray-700 flex justify-between items-center">
            <span className="text-gray-300 font-semibold text-sm tracking-wide uppercase">Original Stream</span>
            <span className="bg-indigo-500/20 text-indigo-400 px-2 py-1 rounded text-xs font-bold">
              English
            </span>
          </div>
          <div className="p-6 overflow-y-auto flex-1 bg-gradient-to-br from-gray-800 to-gray-850">
            {isLoading ? (
              <div className="animate-pulse flex space-x-4">
                <div className="flex-1 space-y-4 py-1">
                  <div className="h-4 bg-gray-700 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-700 rounded w-full"></div>
                  <div className="h-4 bg-gray-700 rounded w-5/6"></div>
                </div>
              </div>
            ) : isTranscriptEmpty ? (
              <div className="h-full flex flex-col gap-2 items-center justify-center text-gray-500">
                <span className="text-4xl opacity-50">🎙️</span>
                <span className="italic text-sm">Awaiting Subtitle Trace...</span>
              </div>
            ) : (
              <div key={transcript} className="animate-fade-in-up">
                <p className="text-xl leading-relaxed text-gray-100 font-medium">
                  {transcript}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Translation Text Panel (Conditionally rendered) */}
        {translateEnabled && (
          <div className="bg-gray-800 rounded-xl overflow-hidden shadow-lg flex flex-col border border-gray-700 animate-fade-in-left">
            <div className="bg-gray-900 px-4 py-3 border-b border-gray-700 flex justify-between items-center">
              <span className="text-gray-300 font-semibold text-sm tracking-wide uppercase">AI Translation</span>
              <span className="bg-indigo-500/20 text-indigo-400 px-2 py-1 rounded text-xs font-bold">
                Tamil
              </span>
            </div>
            <div className="p-6 overflow-y-auto flex-1 bg-gradient-to-br from-gray-800 to-gray-850">
              {isLoading ? (
               <div className="animate-pulse flex space-x-4">
                 <div className="flex-1 space-y-4 py-1">
                   <div className="h-4 bg-gray-700 rounded w-full"></div>
                   <div className="h-4 bg-gray-700 rounded w-5/6"></div>
                   <div className="h-4 bg-gray-700 rounded w-4/6"></div>
                 </div>
               </div>
              ) : isTranslationEmpty ? (
                <div className="h-full flex flex-col gap-2 items-center justify-center text-gray-500">
                  <span className="text-4xl opacity-50">🌐</span>
                  <span className="italic text-sm">Awaiting Translator Pipeline...</span>
                </div>
              ) : (
                <div key={translated} className="animate-fade-in-up">
                  <p className="text-lg leading-relaxed text-indigo-100 font-['Noto_Sans_Tamil']">
                    {translated}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}

CaptionPanel.propTypes = {
  transcript: PropTypes.string,
  translated: PropTypes.string,
  direction: PropTypes.string,
  isLoading: PropTypes.bool,
  translateEnabled: PropTypes.bool,
  micActive: PropTypes.bool
}

export default CaptionPanel
