import { useState, useEffect } from 'react'
import { io } from 'socket.io-client'
import axios from 'axios'

import StatusBar from './components/StatusBar'
import Controls from './components/Controls'
import CaptionPanel from './components/CaptionPanel'

function App() {
  const [transcript, setTranscript] = useState('')
  const [translated, setTranslated] = useState('')
  const [direction, setDirection] = useState('en-ta') // 'en-ta' or 'ta-en'
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [micActive, setMicActive] = useState(false)
  const [socket, setSocket] = useState(null)
  
  // Revised PRD Context
  const [inputMode, setInputMode] = useState('mic')
  const [translateEnabled, setTranslateEnabled] = useState(false)
  const [captionHistory, setCaptionHistory] = useState([])
  const [censorEnabled, setCensorEnabled] = useState(false)
  const [sentimentEnabled, setSentimentEnabled] = useState(false)
  const [sentiment, setSentiment] = useState(null)

  // Socket setup
  useEffect(() => {
    const newSocket = io('http://localhost:5000')
    setSocket(newSocket)

    newSocket.on('connect', () => setIsConnected(true))
    newSocket.on('disconnect', () => setIsConnected(false))

    // Wire caption_update SocketIO event
    newSocket.on('caption_update', (data) => {
      setTranscript(data.transcript)
      setTranslated(data.translated || '')
      setSentiment(data.sentiment || null)

      // Append to history with timing
      setCaptionHistory(prev => {
        const updated = [...prev, {
          index: prev.length + 1,
          startTime: data.timestamp,
          endTime: data.timestamp ? data.timestamp + 4 : undefined,
          transcript: data.transcript,
          translated: data.translated || null
        }]
        return updated.slice(-500) // cap size preventing unbounded leakage 
      })

      // Forward to overlay via Electron IPC
      if (window.electronAPI) {
        window.electronAPI.sendCaption({
          transcript: data.transcript,
          translated: data.translated || '',
          sentiment: data.sentiment || null
        })
      }
    })

    return () => newSocket.disconnect()
  }, [])

  const handleFileUpload = async (file) => {
    setIsLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('direction', direction)
    formData.append('translate', translateEnabled.toString())
    formData.append('censor', censorEnabled.toString())
    formData.append('sentiment', sentimentEnabled.toString())

    try {
      const res = await axios.post('http://localhost:5000/transcribe-and-translate', formData)
      setTranscript(res.data.transcript)
      setTranslated(res.data.translated || '')
      setSentiment(res.data.sentiment || null)
      
      // Add offline payload to history
      setCaptionHistory(prev => [...prev, {
        index: prev.length + 1,
        startTime: 0,
        endTime: 4,
        transcript: res.data.transcript,
        translated: res.data.translated || null
      }])
    } catch (err) {
      setError('Failed to process file. Is the backend running?')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleExport = async (format) => {
    try {
      const res = await axios.post('http://localhost:5000/export', {
        captions: captionHistory,
        format,
        include_translation: translateEnabled
      })
      if (res.data.success) {
        alert(`Saved: ${res.data.filename} (${res.data.caption_count} captions)`)
      }
    } catch (err) {
      alert('Export failed. Is the backend running?')
    }
  }

  const handleClearHistory = () => {
    setCaptionHistory([])
  }

  const handleMicToggle = () => {
    if (!micActive && socket) {
      handleClearHistory() // clear old trails
      socket.emit('start_mic', {
        mode: inputMode,
        direction,
        translate: translateEnabled,
        censor: censorEnabled,
        sentiment: sentimentEnabled
      })
      setMicActive(true)
    } else if (socket) {
      socket.emit('stop_mic')
      setMicActive(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col font-sans">
      <StatusBar 
        isConnected={isConnected} 
        inputMode={inputMode} 
        micActive={micActive} 
        captionCount={captionHistory.length} 
      />
      
      <main className="flex-1 max-w-6xl w-full mx-auto p-4 md:p-6 flex flex-col md:flex-row gap-6">
        {/* Left Side: Controls */}
        <div className="w-full md:w-1/3">
          <Controls 
            direction={direction}
            onDirectionChange={setDirection}
            onFileUpload={handleFileUpload}
            isLoading={isLoading}
            micActive={micActive}
            onMicToggle={handleMicToggle}
            inputMode={inputMode}
            onInputModeChange={setInputMode}
            translateEnabled={translateEnabled}
            onTranslateToggle={setTranslateEnabled}
            censorEnabled={censorEnabled}
            onCensorToggle={() => setCensorEnabled(prev => !prev)}
            sentimentEnabled={sentimentEnabled}
            onSentimentToggle={() => setSentimentEnabled(prev => !prev)}
            captionHistory={captionHistory}
            onExport={handleExport}
            onClearHistory={handleClearHistory}
            isConnected={isConnected}
          />
          {error && (
            <div className="mt-4 p-4 bg-red-900/50 border border-red-500 rounded-xl text-red-200 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Right Side: Captions */}
        <div className="w-full md:w-2/3 flex flex-col">
          <CaptionPanel 
            transcript={transcript}
            translated={translated}
            direction={direction}
            isLoading={isLoading}
            translateEnabled={translateEnabled}
            micActive={micActive}
            sentiment={sentiment}
          />
        </div>
      </main>
    </div>
  )
}

export default App
