import React, { useState } from 'react'

const OverlaySettings = ({ onSettingsChange }) => {
  const [fontSize, setFontSize] = useState(22)
  const [textColor, setTextColor] = useState('#ffffff')
  const [bgOpacity, setBgOpacity] = useState(0)
  const [bgColor, setBgColor] = useState('#000000')

  const handleChange = (key, value) => {
    const settings = { fontSize, textColor, bgOpacity, bgColor, [key]: value }
    onSettingsChange(settings)
    // Also send via electronAPI immediately for live preview
    if (window.electronAPI) {
      window.electronAPI.sendOverlaySettings({ [key]: value })
    }
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 mt-4 text-sm text-slate-300">
      <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
        <span className="text-xl">⚙️</span> Overlay Settings
      </h3>

      <div className="grid grid-cols-2 gap-4">
        {/* Font Size */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium">Font Size: {fontSize}px</label>
          <input type="range" min="14" max="36" value={fontSize}
            className="w-full accent-blue-500"
            onChange={(e) => { setFontSize(+e.target.value); handleChange('fontSize', +e.target.value) }} />
        </div>

        {/* Text Color */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium">Text Color</label>
          <input type="color" value={textColor}
            className="w-full h-8 rounded cursor-pointer border-none p-0 bg-transparent"
            onChange={(e) => { setTextColor(e.target.value); handleChange('textColor', e.target.value) }} />
        </div>

        {/* Background Opacity */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium">BG Opacity: {bgOpacity}%</label>
          <input type="range" min="0" max="90" value={bgOpacity}
            className="w-full accent-blue-500"
            onChange={(e) => { setBgOpacity(+e.target.value); handleChange('bgOpacity', +e.target.value) }} />
        </div>

        {/* Background Color */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium">BG Color</label>
          <input type="color" value={bgColor}
            className="w-full h-8 rounded cursor-pointer border-none p-0 bg-transparent"
            onChange={(e) => { setBgColor(e.target.value); handleChange('bgColor', e.target.value) }} />
        </div>
      </div>

      {/* Reset button */}
      <div className="mt-4 pt-4 border-t border-slate-700 flex justify-end">
        <button 
          className="text-xs px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-slate-200 transition-colors"
          onClick={() => {
            const defaults = { fontSize: 22, textColor: '#ffffff', bgOpacity: 0, bgColor: '#000000' }
            setFontSize(defaults.fontSize)
            setTextColor(defaults.textColor)
            setBgOpacity(defaults.bgOpacity)
            setBgColor(defaults.bgColor)
            Object.entries(defaults).forEach(([k, v]) => handleChange(k, v))
          }}>
          Reset to Default
        </button>
      </div>
    </div>
  )
}

export default OverlaySettings
