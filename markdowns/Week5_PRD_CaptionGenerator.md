# PRD — Week 5: UI Polish + SRT Export + Overlay Customization
### Caption Generator with Translation — Desktop App
**Phase:** Week 5 of 8 | **Prepared For:** Antigravity (Autonomous Coding Agent)
**Depends On:** Week 1 ✅ Week 2 ✅ Week 3 ✅ Week 4 ✅ All hotfixes ✅
**Estimated Duration:** 7 Days

---

## 1. Document Overview

| Field | Value |
|---|---|
| Document Title | Week 5 PRD — UI Polish + SRT Export + Overlay Customization |
| Project | Caption Generator with Translation (Desktop App) |
| Phase | Week 5 of 8 |
| Prepared For | Antigravity (Autonomous Coding Agent) |
| Primary Goal | Make the app look and feel like a real product |
| Status | Ready for Implementation |

---

## 2. Objective

The app is functionally complete from Week 4. Week 5 is entirely about **polish, usability, and extra features** that make this feel like a real product rather than a college project prototype.

Three focus areas this week:

1. **Overlay overhaul** — proper subtitle styling, draggable anywhere on screen, font/color customization
2. **SRT / TXT export** — save captions with timestamps as standard subtitle files
3. **Main UI polish** — clean up the React app so it looks presentable for demo day

---

## 3. Critical — Tailwind CSS Version Notice

> ⚠️ **AGENT: READ THIS BEFORE TOUCHING ANY STYLING.**

**Tailwind CSS v4 is installed.** Do NOT install v3. Do NOT create or modify `tailwind.config.js`.
- Use only utility classes already confirmed working in Week 3 components
- The PostCSS plugin is `@tailwindcss/postcss` — not the v3 `tailwindcss` plugin
- Do not upgrade or downgrade Tailwind — leave version exactly as installed

---

## 4. Context & Carry-Forward from Week 4

### What's Working
- Live mic captions via queue-based producer/consumer threading ✅
- System audio (WASAPI Stereo Mix) capture ✅
- faster-whisper `medium` model on CUDA (int8) ✅
- Translation toggle — English first, Tamil on demand ✅
- Overlay window (`overlay.html`) — functional but rough looking ✅
- `Ctrl+Shift+C` hotkey toggles overlay ✅
- Drag handle exists in overlay but dragging is unreliable ✅ (needs fix)

### Known Issues Going Into Week 5
- Overlay is not reliably draggable — this is the primary overlay bug to fix
- Overlay styling is rough — needs proper subtitle aesthetic
- No caption export yet
- Main app UI needs visual polish

---

## 5. Files Changed This Week

| File | Action | Notes |
|---|---|---|
| `electron/overlay.html` | **Rewrite** | Full subtitle styling + reliable drag |
| `electron/main.js` | **Modify** | Fix drag IPC, add overlay settings IPC |
| `electron/preload.js` | **Modify** | Expose overlay settings API |
| `electron/renderer/src/components/OverlaySettings.jsx` | **Create** | Font/color customization panel |
| `electron/renderer/src/components/Controls.jsx` | **Modify** | Add export buttons, overlay settings trigger |
| `electron/renderer/src/components/CaptionPanel.jsx` | **Modify** | Visual polish |
| `electron/renderer/src/App.jsx` | **Modify** | Caption history state, export logic, settings state |
| `backend/exporter.py` | **Create** | SRT and TXT export logic |
| `backend/app.py` | **Modify** | Add `/export` endpoint |
| All other files | **No changes** | Leave untouched |

---

## 6. Feature 1 — Overlay Overhaul

### 6.1 The Drag Problem — Root Cause & Fix

The current drag implementation uses `-webkit-app-region: drag` on the handle bar combined with IPC calls to toggle `setIgnoreMouseEvents`. This approach is unreliable because:

- `-webkit-app-region: drag` only works when the window is NOT set to `setIgnoreMouseEvents(true)`
- The IPC round-trip (renderer → main → setIgnoreMouseEvents) has a small delay causing missed drag starts
- On some Windows configurations the drag region conflicts with the transparent background

**The correct approach — use Electron's `win.setPosition()` via IPC instead of CSS drag:**

```javascript
// In overlay.html — track mouse manually and move window via IPC
let isDragging = false
let dragStartX, dragStartY

dragHandle.addEventListener('mousedown', (e) => {
  isDragging = true
  dragStartX = e.screenX
  dragStartY = e.screenY
  window.electronAPI.startDrag()  // disable click-through
})

document.addEventListener('mousemove', (e) => {
  if (!isDragging) return
  const dx = e.screenX - dragStartX
  const dy = e.screenY - dragStartY
  window.electronAPI.moveOverlay(dx, dy)  // tell main process to move window
  dragStartX = e.screenX
  dragStartY = e.screenY
})

document.addEventListener('mouseup', () => {
  if (isDragging) {
    isDragging = false
    window.electronAPI.endDrag()  // re-enable click-through
  }
})
```

```javascript
// In main.js — move the overlay window on IPC
ipcMain.on('move-overlay', (event, { dx, dy }) => {
  if (!overlayWindow) return
  const [x, y] = overlayWindow.getPosition()
  overlayWindow.setPosition(x + dx, y + dy)
})
```

```javascript
// In preload.js — expose moveOverlay
moveOverlay: (dx, dy) => ipcRenderer.send('move-overlay', { dx, dy })
```

### 6.2 Overlay Visual Redesign — `overlay.html`

The overlay must look like **real movie/TV subtitles** — not a debug panel. Full rewrite:

**Design spec:**
- Transparent background on the window itself
- Caption text centered horizontally
- Text has a subtle dark shadow/outline for readability on any background
- English text: large, white, bold
- Tamil text (when present): smaller, light blue, below English
- No visible border or box unless background opacity > 0
- Drag handle: very subtle, only visible on hover
- Default position: bottom center of screen

**Layout structure:**
```
┌─────────────────────────────────────────┐  ← transparent window
│  ⠿  (drag handle — subtle, top center) │
│                                         │
│     This is the English subtitle.       │  ← large white text, centered
│       இது தமிழ் மொழிபெயர்ப்பு.         │  ← smaller, light blue (conditional)
│                                         │
└─────────────────────────────────────────┘
```

**CSS requirements:**
```css
body {
  background: transparent;
  margin: 0;
  padding: 0;
  overflow: hidden;
  -webkit-app-region: no-drag;  /* IMPORTANT: entire body is no-drag */
}

#drag-handle {
  /* Do NOT use -webkit-app-region: drag — use JS mouse tracking instead */
  height: 20px;
  width: 100%;
  cursor: grab;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;  /* hidden by default */
  transition: opacity 0.2s;
}

#drag-handle:hover {
  opacity: 1;  /* appears on hover */
}

#drag-handle span {
  font-size: 10px;
  color: rgba(255,255,255,0.5);
  letter-spacing: 3px;
  user-select: none;
}

#caption-container {
  padding: 8px 24px 12px;
  text-align: center;
}

/* Background box — controlled by user settings */
#caption-box {
  display: inline-block;
  padding: 6px 20px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.0);  /* default: no background */
  transition: background 0.2s;
}

#transcript {
  font-family: 'Segoe UI', Arial, sans-serif;
  font-size: 22px;           /* default — user can change */
  font-weight: 600;
  color: #ffffff;            /* default — user can change */
  text-shadow:
    -1px -1px 0 #000,
     1px -1px 0 #000,
    -1px  1px 0 #000,
     1px  1px 0 #000,
     0px  2px 4px rgba(0,0,0,0.8);
  line-height: 1.4;
  min-height: 30px;
}

#translated {
  font-family: 'Noto Sans Tamil', 'Segoe UI', sans-serif;
  font-size: 16px;
  color: #a5f3fc;
  text-shadow:
    -1px -1px 0 #000,
     1px -1px 0 #000,
    -1px  1px 0 #000,
     1px  1px 0 #000;
  margin-top: 2px;
  display: none;
}

#placeholder {
  font-size: 14px;
  color: rgba(255,255,255,0.2);
  font-style: italic;
}
```

### 6.3 Overlay Customization Settings

The user must be able to customize the overlay appearance from the main app window. Settings to expose:

| Setting | Type | Default | Options |
|---|---|---|---|
| Font size | Slider | 22px | 14px — 36px |
| Text color | Color picker | #ffffff | Any color |
| Background opacity | Slider | 0% | 0% — 90% |
| Background color | Color picker | #000000 | Any color |

These settings are sent from the React app to the overlay via Electron IPC.

**IPC flow:**
```
User changes setting in OverlaySettings.jsx
        ↓
App.jsx calls window.electronAPI.sendOverlaySettings(settings)
        ↓
preload.js → ipcRenderer.send('overlay-settings', settings)
        ↓
main.js ipcMain.on('overlay-settings') → overlayWindow.webContents.send('apply-settings', settings)
        ↓
overlay.html applies CSS changes live
```

**`overlay.html` settings receiver:**
```javascript
window.electronAPI.onSettings((settings) => {
  if (settings.fontSize) {
    transcriptEl.style.fontSize = settings.fontSize + 'px'
  }
  if (settings.textColor) {
    transcriptEl.style.color = settings.textColor
  }
  if (settings.bgOpacity !== undefined || settings.bgColor) {
    const opacity = settings.bgOpacity ?? currentSettings.bgOpacity
    const color = settings.bgColor ?? currentSettings.bgColor
    // Convert hex color to rgb and apply with opacity
    const r = parseInt(color.slice(1,3), 16)
    const g = parseInt(color.slice(3,5), 16)
    const b = parseInt(color.slice(5,7), 16)
    captionBox.style.background = `rgba(${r},${g},${b},${opacity / 100})`
  }
  // Store current settings
  Object.assign(currentSettings, settings)
})
```

### 6.4 `OverlaySettings.jsx` — New Component

A collapsible settings panel in the main app window for overlay customization.

```jsx
// Renders when user clicks an "Overlay Settings" button in Controls
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
    <div className="...">
      <h3>Overlay Settings</h3>

      {/* Font Size */}
      <label>Font Size: {fontSize}px</label>
      <input type="range" min="14" max="36" value={fontSize}
        onChange={(e) => { setFontSize(+e.target.value); handleChange('fontSize', +e.target.value) }} />

      {/* Text Color */}
      <label>Text Color</label>
      <input type="color" value={textColor}
        onChange={(e) => { setTextColor(e.target.value); handleChange('textColor', e.target.value) }} />

      {/* Background Opacity */}
      <label>Background Opacity: {bgOpacity}%</label>
      <input type="range" min="0" max="90" value={bgOpacity}
        onChange={(e) => { setBgOpacity(+e.target.value); handleChange('bgOpacity', +e.target.value) }} />

      {/* Background Color */}
      <label>Background Color</label>
      <input type="color" value={bgColor}
        onChange={(e) => { setBgColor(e.target.value); handleChange('bgColor', e.target.value) }} />

      {/* Reset button */}
      <button onClick={() => {
        const defaults = { fontSize: 22, textColor: '#ffffff', bgOpacity: 0, bgColor: '#000000' }
        Object.entries(defaults).forEach(([k, v]) => handleChange(k, v))
      }}>
        Reset to Default
      </button>
    </div>
  )
}
```

**Changes to `preload.js`** — add these to the existing `contextBridge.exposeInMainWorld`:
```javascript
sendOverlaySettings: (settings) => ipcRenderer.send('overlay-settings', settings),
onSettings: (callback) => ipcRenderer.on('apply-settings', (_, s) => callback(s))
```

---

## 7. Feature 2 — SRT / TXT Export

### 7.1 What is SRT Format

SRT (SubRip Subtitle) is the universal subtitle format supported by VLC, video editors, YouTube, and every media player. Format:

```
1
00:00:01,000 --> 00:00:05,000
This is the first subtitle line.

2
00:00:06,500 --> 00:00:10,200
This is the second subtitle line.
இது இரண்டாவது வரி. (Tamil if translation was on)

```

### 7.2 Caption History — Track in `App.jsx`

To export, the app needs to remember all captions with timestamps. Add this state to `App.jsx`:

```javascript
const [captionHistory, setCaptionHistory] = useState([])
// Each entry: { index: int, startTime: float, endTime: float, transcript: str, translated: str|null }
```

Update the `caption_update` SocketIO handler to append to history:
```javascript
socket.on('caption_update', (data) => {
  setTranscript(data.transcript)
  setTranslated(data.translated || '')

  // Append to history with timing
  setCaptionHistory(prev => [...prev, {
    index: prev.length + 1,
    startTime: data.timestamp,
    endTime: data.timestamp + 4,   // approximate chunk duration
    transcript: data.transcript,
    translated: data.translated || null
  }])

  if (window.electronAPI) {
    window.electronAPI.sendCaption({
      transcript: data.transcript,
      translated: data.translated || ''
    })
  }
})
```

Add a **Clear History** button that resets `captionHistory` to `[]` — useful before starting a new session.

### 7.3 `backend/exporter.py` — New File

```python
# backend/exporter.py
# Generates SRT and TXT subtitle files from caption history

import os
from datetime import datetime

def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def export_srt(captions: list, include_translation: bool = False) -> str:
    """
    Generate SRT file content from caption history.

    Args:
        captions: list of { index, startTime, endTime, transcript, translated }
        include_translation: if True, Tamil line added below English

    Returns:
        str: SRT file content
    """
    lines = []
    for i, cap in enumerate(captions, 1):
        start = format_srt_time(cap.get('startTime', i * 4))
        end = format_srt_time(cap.get('endTime', i * 4 + 4))
        text = cap.get('transcript', '').strip()

        if not text:
            continue

        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)

        if include_translation and cap.get('translated'):
            lines.append(cap['translated'].strip())

        lines.append('')  # blank line between entries

    return '\n'.join(lines)


def export_txt(captions: list, include_translation: bool = False) -> str:
    """
    Generate plain text transcript from caption history.

    Args:
        captions: list of caption dicts
        include_translation: if True, Tamil line added after each English line

    Returns:
        str: Plain text content
    """
    lines = []
    for cap in captions:
        text = cap.get('transcript', '').strip()
        if not text:
            continue
        lines.append(text)
        if include_translation and cap.get('translated'):
            lines.append(cap['translated'].strip())
        lines.append('')

    return '\n'.join(lines)


def save_file(content: str, filename: str, output_dir: str = 'exports') -> str:
    """
    Save content to a file. Creates output_dir if it doesn't exist.

    Returns:
        str: Full path to saved file
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[Exporter] Saved: {filepath}')
    return filepath
```

### 7.4 `backend/app.py` — Add `/export` Endpoint

Add to `app.py`:

```python
from exporter import export_srt, export_txt, save_file
from datetime import datetime
import json

@app.route('/export', methods=['POST'])
def export_captions():
    """
    Export caption history as SRT or TXT file.

    Body (JSON):
    {
        "captions": [...],          # caption history array from frontend
        "format": "srt" | "txt",
        "include_translation": bool
    }

    Returns:
        JSON with file path and content
    """
    data = request.get_json()

    if not data or 'captions' not in data:
        return jsonify({'success': False, 'error': 'No captions provided'}), 400

    captions = data.get('captions', [])
    fmt = data.get('format', 'srt').lower()
    include_translation = data.get('include_translation', False)

    if not captions:
        return jsonify({'success': False, 'error': 'Caption history is empty'}), 400

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'captions_{timestamp}.{fmt}'

    try:
        if fmt == 'srt':
            content = export_srt(captions, include_translation)
        elif fmt == 'txt':
            content = export_txt(captions, include_translation)
        else:
            return jsonify({'success': False, 'error': 'Invalid format. Use srt or txt'}), 400

        filepath = save_file(content, filename)

        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'format': fmt,
            'caption_count': len(captions)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

Also create an `exports/` folder at project root and add it to `.gitignore`:
```
# Exported subtitle files
exports/
```

### 7.5 Export Buttons in `Controls.jsx`

Add two export buttons that only appear when `captionHistory.length > 0`:

```jsx
{captionHistory.length > 0 && (
  <div className="flex gap-2 mt-4">
    <button onClick={() => onExport('srt')}
      className="bg-green-600 hover:bg-green-500 text-white px-4 py-2 rounded-lg text-sm">
      💾 Export .SRT
    </button>
    <button onClick={() => onExport('txt')}
      className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm">
      📄 Export .TXT
    </button>
    <button onClick={onClearHistory}
      className="bg-gray-600 hover:bg-gray-500 text-white px-4 py-2 rounded-lg text-sm">
      🗑 Clear
    </button>
  </div>
)}
```

**Export handler in `App.jsx`:**
```javascript
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
```

---

## 8. Main UI Polish

### 8.1 Overall UI Goals

The main window should look like a **real desktop app**, not a styled HTML page. Key improvements:

- Consistent dark theme throughout (`slate-900` background)
- Proper spacing and visual hierarchy
- Clear section separation between controls and captions
- Status bar always visible and informative
- Smooth transitions on state changes

### 8.2 Specific Polish Tasks

**StatusBar:**
- Show current input mode (🎤 Mic / 🖥️ System Audio) dynamically
- Show caption count during live session: `12 captions captured`
- Pulse green dot animation when mic is active

**CaptionPanel:**
- Add a subtle fade-in animation on each new caption (`transition-opacity`)
- Show elapsed session time when mic is active (e.g. `Session: 01:23`)
- Empty state: centered placeholder text with a subtle icon
- Smooth height transition when Tamil panel mounts/unmounts

**Controls:**
- Add an `Overlay Settings` toggle button that expands/collapses `OverlaySettings.jsx`
- Visual separation between input controls and export controls
- Tooltip hints on hover for each control (HTML `title` attribute is fine)
- Disable all controls gracefully when backend is disconnected

### 8.3 App Layout Structure

```
┌─────────────────────────────────────────────────────┐
│  StatusBar — connection, GPU, mode, caption count   │
├──────────────────┬──────────────────────────────────┤
│                  │                                  │
│   Controls       │      CaptionPanel                │
│   (left ~35%)    │      (right ~65%)                │
│                  │                                  │
│  • Input mode    │   [ English subtitle text ]      │
│  • Start/Stop    │                                  │
│  • Lang toggle   │   [ Tamil text — conditional ]   │
│  • File upload   │                                  │
│  • Export btns   │   Session timer                  │
│  • Overlay set.  │                                  │
│                  │                                  │
└──────────────────┴──────────────────────────────────┘
```

---

## 9. Updated Project Folder Structure

```
caption-app/
├── backend/
│   ├── exporter.py             # NEW — SRT/TXT export logic
│   ├── app.py                  # MODIFIED — /export endpoint added
│   └── ... (all others unchanged)
│
├── electron/
│   ├── main.js                 # MODIFIED — drag IPC fix, settings IPC
│   ├── preload.js              # MODIFIED — moveOverlay, sendOverlaySettings, onSettings
│   ├── overlay.html            # REWRITTEN — proper subtitle styling + JS drag
│   └── renderer/src/
│       ├── App.jsx             # MODIFIED — caption history, export handler
│       └── components/
│           ├── Controls.jsx            # MODIFIED — export buttons, overlay settings toggle
│           ├── CaptionPanel.jsx        # MODIFIED — animations, session timer
│           ├── StatusBar.jsx           # MODIFIED — input mode display, caption count
│           └── OverlaySettings.jsx     # NEW — font/color customization panel
│
├── exports/                    # NEW — created by exporter.py at runtime
└── .gitignore                  # MODIFIED — add exports/
```

---

## 10. Acceptance Criteria

| # | Criterion | How to Verify |
|---|---|---|
| AC-01 | Overlay is freely draggable to any screen position | Drag overlay, release, confirm position held |
| AC-02 | Overlay drag handle appears on hover, hidden otherwise | Hover over overlay top edge |
| AC-03 | Overlay shows captions with proper subtitle styling | Play audio, check overlay appearance |
| AC-04 | Font size slider changes overlay text size live | Move slider, observe overlay instantly |
| AC-05 | Text color picker changes overlay text color live | Change color, observe overlay instantly |
| AC-06 | Background opacity slider adds/removes background box | Move slider, observe overlay |
| AC-07 | Export .SRT button saves a valid .srt file | Capture some captions, export, open in VLC |
| AC-08 | Export .TXT button saves a plain text transcript | Capture captions, export, open in Notepad |
| AC-09 | Exported SRT file has correct timestamps | Open .srt in text editor, verify format |
| AC-10 | Export buttons only appear when captions exist | Check UI before and after capturing |
| AC-11 | Clear button resets caption history | Click clear, confirm export buttons disappear |
| AC-12 | StatusBar shows active input mode | Switch modes, check status bar updates |
| AC-13 | StatusBar shows caption count during session | Capture captions, check count increments |
| AC-14 | New captions fade in smoothly in CaptionPanel | Observe transition during live capture |
| AC-15 | All controls disabled when backend disconnected | Stop Flask, check UI state |

---

## 11. Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| JS drag tracking loses mouse on fast movement | Use `document` level mousemove/mouseup listeners — not element level |
| Overlay jumps on first drag | Initialize `dragStartX/Y` on mousedown, not before |
| SRT timestamps inaccurate | They are approximate (chunk-based) — note this in UI as "approximate timestamps" |
| Export directory not found | `os.makedirs(output_dir, exist_ok=True)` handles creation |
| `OverlaySettings` color picker not supported in Electron | HTML `<input type="color">` works natively in Electron's Chromium — no library needed |
| Tailwind transition classes not working | Use inline `style` transitions as fallback if Tailwind transitions don't apply |
| Caption history grows indefinitely in long sessions | Add a max cap of 500 entries — slice oldest if exceeded: `prev.slice(-500)` |

---

## 12. Handoff Notes to Agent

> **READ THIS BEFORE STARTING.**

- **Tailwind CSS v4 is installed.** Do NOT install v3. Do NOT create `tailwind.config.js`. See Section 3.
- The overlay drag MUST use JS mouse tracking + `ipcRenderer.send('move-overlay', {dx, dy})` + `win.setPosition()` in main process. Do NOT use `-webkit-app-region: drag` for dragging — it is unreliable with transparent click-through windows. The drag handle can use it as a fallback only.
- `OverlaySettings.jsx` sends settings changes **immediately on every input event** (slider move, color change) for live preview — not just on save/confirm.
- The `/export` endpoint saves files to `caption-app/exports/` on the server (Python side). The frontend just calls the endpoint and shows the filename in an alert — no file download dialog needed this week.
- `exporter.py` must handle empty transcript strings gracefully — skip any caption entry where `transcript` is empty or whitespace only.
- Caption history must be cleared when the user clicks "Clear" AND when a new mic session starts (optional but good UX).
- Do not change `audio_capture.py`, `transcriber.py`, or `translator.py` — they are working correctly after Week 4 hotfixes.
- On completion, run through all 15 acceptance criteria manually and commit with message: `feat(week5): overlay polish + drag fix + srt export + ui improvements`

---

*End of Week 5 PRD — Caption Generator with Translation Project*
