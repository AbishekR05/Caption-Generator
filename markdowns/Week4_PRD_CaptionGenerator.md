# PRD — Week 4: Live Mic Captions + Overlay Window
### Caption Generator with Translation — Desktop App
**Phase:** Week 4 of 8 | **Prepared For:** Antigravity (Autonomous Coding Agent)
**Depends On:** Week 1 ✅ Week 2 ✅ Week 3 ✅
**Estimated Duration:** 7 Days

---

## 1. Document Overview

| Field | Value |
|---|---|
| Document Title | Week 4 PRD — Live Mic Captions + Overlay Window |
| Project | Caption Generator with Translation (Desktop App) |
| Phase | Week 4 of 8 |
| Prepared For | Antigravity (Autonomous Coding Agent) |
| Tech Stack | Python sounddevice, Flask-SocketIO, Electron IPC, React |
| Builds On | All Week 1–3 deliverables |
| Status | Ready for Implementation |

---

## 2. Objective

Week 3 delivered a working desktop UI with file-based transcription and translation. Week 4 adds the two most visually impressive features of the project:

1. **Live Mic Captions** — capture microphone audio in 4-second chunks, transcribe + translate each chunk via Whisper, and stream results to the UI in near real-time via SocketIO
2. **Overlay Window** — a second transparent, frameless, always-on-top Electron window that floats over any application and displays live captions like a subtitle bar

By end of Week 4:
- The Start/Stop mic button (stubbed in Week 3) must be fully wired
- Captions must stream live from mic → Whisper → SocketIO → UI
- A floating overlay window must display captions on top of any app
- A hotkey (`Ctrl+Shift+C`) must toggle the overlay on/off
- The overlay must be draggable and repositionable

---

## 3. Critical — Tailwind CSS Version Notice

> ⚠️ **AGENT: READ THIS BEFORE TOUCHING ANY STYLING.**

Week 3 used **Tailwind CSS v4** (not v3). Tailwind v4 has **breaking changes** from v3:

- The `tailwind.config.js` file is **deprecated** in v4 — do not create or modify it
- Configuration is done via CSS `@theme` directives inside the CSS file, not via JS config
- The PostCSS plugin is `@tailwindcss/postcss` — not `tailwindcss` (v3 name)
- Utility class names are largely the same but some v3 plugins do not exist in v4

**Rules for this week:**
- Do NOT install `tailwindcss` v3 — it will conflict with v4
- Do NOT create a `tailwind.config.js` — it will be ignored or cause errors
- All new components must use the same Tailwind utility classes already working in Week 3
- If a utility class doesn't work, check the [Tailwind v4 docs](https://tailwindcss.com/docs) before assuming it's broken
- Do not upgrade or downgrade Tailwind — leave the version exactly as Week 3 installed it

---

## 4. Context & Carry-Forward

### Existing Infrastructure to Build On
- `backend/transcriber.py` — `transcribe(audio_path, language=None) -> dict` ✅
- `backend/translator.py` — `translate(text, direction) -> str` with `>>tam<<` fix ✅
- `backend/app.py` — Flask + SocketIO on `localhost:5000`, `emit_caption()` stub exists ✅
- `backend/audio_capture.py` — empty placeholder, **implement this week** ✅
- `electron/main.js` — single BrowserWindow, `preload.js` stub ✅
- `App.jsx` — SocketIO connected, `micActive` state exists, `caption_update` stub commented out ✅

### Key Stubs to Wire This Week
| File | Stub | Action |
|---|---|---|
| `backend/app.py` | `emit_caption()` | Wire to audio capture loop |
| `backend/audio_capture.py` | Empty file | Implement fully |
| `App.jsx` | `caption_update` SocketIO listener | Uncomment and wire |
| `Controls.jsx` | Mic button onClick | Wire to actual mic start/stop |
| `electron/main.js` | Single window only | Add overlay window |

---

## 5. Folder Structure Changes

Only new files are listed. All existing files remain unless explicitly stated.

```
caption-app/
├── backend/
│   ├── audio_capture.py        # IMPLEMENT THIS WEEK (was empty)
│   ├── app.py                  # MODIFY — wire emit_caption(), add mic routes
│   └── test_mic.py             # CREATE — mic capture test script
│
├── electron/
│   ├── main.js                 # MODIFY — add overlay BrowserWindow
│   ├── preload.js              # MODIFY — add IPC bridge for overlay
│   ├── overlay.html            # MODIFY — was placeholder, now real overlay UI
│   └── renderer/
│       └── src/
│           ├── App.jsx         # MODIFY — wire caption_update + mic toggle
│           ├── components/
│           │   ├── Controls.jsx        # MODIFY — wire mic button
│           │   └── CaptionPanel.jsx    # MODIFY — add streaming animation
│           └── Overlay.jsx             # CREATE — overlay React component
```

---

## 6. Feature 1 — Live Mic Captions

### 6.1 How It Works (Architecture)

```
User clicks "Start Live Captions"
        ↓
React sets micActive = true → emits 'start_mic' via SocketIO
        ↓
Flask SocketIO receives 'start_mic' → starts audio_capture loop in background thread
        ↓
audio_capture.py records 4-second audio chunk via sounddevice
        ↓
Chunk saved to temp file → passed to transcribe() → passed to translate()
        ↓
Flask calls emit_caption(transcript, translated) → SocketIO pushes to frontend
        ↓
React receives 'caption_update' → updates CaptionPanel + Overlay
        ↓
Loop repeats until 'stop_mic' event received
```

### 6.2 `backend/audio_capture.py` — Full Implementation

```python
# backend/audio_capture.py
import sounddevice as sd
import numpy as np
import tempfile
import os
import threading
import time
import scipy.io.wavfile as wav

SAMPLE_RATE = 16000       # Whisper expects 16kHz
CHUNK_DURATION = 4        # seconds per chunk — optimal for GTX 1650
CHANNELS = 1              # mono audio

_recording = False
_thread = None

def start_capture(on_chunk_ready):
    """
    Start continuous mic capture in a background thread.

    Args:
        on_chunk_ready (callable): Called with (audio_path: str) for each chunk.
                                   The caller is responsible for deleting the temp file.
    """
    global _recording, _thread
    _recording = True
    _thread = threading.Thread(target=_capture_loop, args=(on_chunk_ready,), daemon=True)
    _thread.start()
    print('[AudioCapture] Mic capture started.')

def stop_capture():
    """Stop the capture loop."""
    global _recording
    _recording = False
    print('[AudioCapture] Mic capture stopped.')

def _capture_loop(on_chunk_ready):
    global _recording
    while _recording:
        try:
            audio = sd.rec(
                int(CHUNK_DURATION * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='int16'
            )
            sd.wait()  # Block until chunk is fully recorded

            if not _recording:
                break

            # Save chunk to temp wav file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            wav.write(tmp.name, SAMPLE_RATE, audio)
            tmp.close()

            on_chunk_ready(tmp.name)

        except Exception as e:
            print(f'[AudioCapture] Error during capture: {e}')
            break

    print('[AudioCapture] Capture loop ended.')
```

**Implementation Notes:**
- Use `scipy.io.wavfile` to write WAV — do not use soundfile or any other library
- `CHUNK_DURATION = 4` is the sweet spot for GTX 1650 (see performance notes in Section 6.4)
- The `on_chunk_ready` callback is responsible for deleting the temp file after use
- `daemon=True` ensures the thread dies when the main process exits
- `sd.wait()` blocks the loop — this is intentional, it creates a natural 4-second rhythm

### 6.3 `backend/app.py` — Mic SocketIO Events

Add the following to `app.py`. Do NOT remove any existing Week 2 code.

```python
from audio_capture import start_capture, stop_capture
import threading

# ── Mic SocketIO Events ───────────────────────────────────

@socketio.on('start_mic')
def handle_start_mic(data):
    direction = data.get('direction', 'en-ta')
    print(f'[SocketIO] start_mic received. Direction: {direction}')

    def on_chunk(audio_path):
        try:
            result = transcribe(audio_path)
            transcript = result['text'].strip()
            if transcript:
                translated = translate(transcript, direction)
                emit_caption(transcript, translated)
        except Exception as e:
            print(f'[Error] Chunk processing failed: {e}')
        finally:
            if os.path.exists(audio_path):
                os.unlink(audio_path)

    # Run in background so SocketIO handler returns immediately
    threading.Thread(target=start_capture, args=(on_chunk,), daemon=True).start()

@socketio.on('stop_mic')
def handle_stop_mic():
    print('[SocketIO] stop_mic received.')
    stop_capture()
```

**Wire `emit_caption()` — replace the Week 2 stub with this:**
```python
def emit_caption(text, translated):
    socketio.emit('caption_update', {
        'transcript': text,
        'translated': translated,
        'timestamp': time.time()
    })
    print(f'[SocketIO] caption_update emitted: {text[:40]}...')
```

### 6.4 Performance Notes for GTX 1650

- `CHUNK_DURATION = 4` seconds means a new caption appears every ~6-8 seconds (4s recording + ~2-4s Whisper processing)
- This is the realistic best-case for this hardware — do not reduce chunk size below 3 seconds or accuracy drops significantly
- `fp16=True` must remain set in `transcriber.py` — already set from Week 1
- If the agent wants to experiment with faster processing, suggest `faster-whisper` as an optional upgrade — but do NOT implement it this week, keep it as a comment note

---

## 7. Feature 2 — Overlay Window

### 7.1 What the Overlay Is

A second Electron `BrowserWindow` that:
- Is transparent with no frame or title bar
- Floats on top of ALL other windows (even fullscreen apps)
- Displays only the latest caption text
- Does not steal focus or intercept mouse clicks (click-through)
- Can be dragged to reposition
- Can be toggled on/off with `Ctrl+Shift+C`

### 7.2 `electron/main.js` — Add Overlay Window

Add the following to `main.js`. The existing main window code must remain unchanged.

```javascript
const { app, BrowserWindow, globalShortcut, ipcMain } = require('electron')
const path = require('path')

let mainWindow = null
let overlayWindow = null
const isDev = process.env.NODE_ENV !== 'production'

function createOverlay() {
  overlayWindow = new BrowserWindow({
    width: 800,
    height: 120,
    x: 100,
    y: 50,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  })

  overlayWindow.setIgnoreMouseEvents(true, { forward: true })
  overlayWindow.loadFile(path.join(__dirname, 'overlay.html'))
  overlayWindow.hide() // Hidden by default — toggled via hotkey
}

function toggleOverlay() {
  if (!overlayWindow) return
  if (overlayWindow.isVisible()) {
    overlayWindow.hide()
  } else {
    overlayWindow.show()
  }
}

app.whenReady().then(() => {
  createWindow()    // existing main window function
  createOverlay()   // new overlay window

  // Global hotkey — works even when app is not focused
  globalShortcut.register('CommandOrControl+Shift+C', toggleOverlay)
})

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
})
```

**Notes:**
- `setIgnoreMouseEvents(true, { forward: true })` makes the overlay click-through — clicks pass to the window underneath
- `alwaysOnTop: true` keeps it above all other windows including fullscreen
- `skipTaskbar: true` hides it from the Windows taskbar
- The overlay starts hidden — user toggles it with `Ctrl+Shift+C`

### 7.3 Overlay Dragging

Since `setIgnoreMouseEvents(true)` makes the whole window click-through, dragging requires a special approach. Add a small drag handle zone that temporarily re-enables mouse events:

```javascript
// In main.js — IPC handler for drag handle hover
ipcMain.on('overlay-drag-start', () => {
  overlayWindow.setIgnoreMouseEvents(false)
})

ipcMain.on('overlay-drag-end', () => {
  overlayWindow.setIgnoreMouseEvents(true, { forward: true })
})
```

### 7.4 `electron/preload.js` — Expose IPC + Caption Bridge

Replace the Week 3 preload stub with:

```javascript
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  version: process.versions.electron,

  // Overlay drag handle
  startDrag: () => ipcRenderer.send('overlay-drag-start'),
  endDrag: () => ipcRenderer.send('overlay-drag-end'),

  // Send captions to overlay from main window
  sendCaption: (data) => ipcRenderer.send('caption-to-overlay', data),

  // Receive captions in overlay window
  onCaption: (callback) => ipcRenderer.on('caption-from-main', (_, data) => callback(data))
})
```

Add this IPC bridge in `main.js` to forward captions from main window to overlay:

```javascript
ipcMain.on('caption-to-overlay', (event, data) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.webContents.send('caption-from-main', data)
  }
})
```

### 7.5 `electron/overlay.html`

Replace the Week 1 placeholder with a real overlay UI:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      background: transparent;
      overflow: hidden;
      font-family: 'Noto Sans Tamil', 'Segoe UI', sans-serif;
      -webkit-app-region: no-drag;
    }

    #drag-handle {
      position: absolute;
      top: 0; left: 0;
      width: 100%; height: 20px;
      background: rgba(0, 0, 0, 0.4);
      cursor: move;
      -webkit-app-region: drag;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    #drag-handle span {
      font-size: 10px;
      color: rgba(255,255,255,0.4);
      letter-spacing: 2px;
    }

    #caption-box {
      margin-top: 20px;
      padding: 10px 20px;
      background: rgba(0, 0, 0, 0.75);
      border-radius: 12px;
      margin-left: 10px;
      margin-right: 10px;
    }

    #transcript {
      font-size: 16px;
      color: #ffffff;
      margin-bottom: 4px;
      min-height: 22px;
    }

    #translated {
      font-size: 15px;
      color: #a5f3fc;
      min-height: 22px;
    }

    #placeholder {
      font-size: 14px;
      color: rgba(255,255,255,0.3);
      text-align: center;
      padding: 10px;
    }
  </style>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil&display=swap" rel="stylesheet">
</head>
<body>
  <div id="drag-handle">
    <span>⠿ CAPTION OVERLAY — Ctrl+Shift+C to hide</span>
  </div>

  <div id="caption-box">
    <div id="placeholder">Captions will appear here...</div>
    <div id="transcript" style="display:none"></div>
    <div id="translated" style="display:none"></div>
  </div>

  <script>
    const transcriptEl = document.getElementById('transcript')
    const translatedEl = document.getElementById('translated')
    const placeholderEl = document.getElementById('placeholder')
    const dragHandle = document.getElementById('drag-handle')

    // Receive captions via IPC
    window.electronAPI.onCaption((data) => {
      placeholderEl.style.display = 'none'
      transcriptEl.style.display = 'block'
      translatedEl.style.display = 'block'
      transcriptEl.textContent = data.transcript
      translatedEl.textContent = data.translated
    })

    // Drag handle — temporarily enable mouse events
    dragHandle.addEventListener('mouseenter', () => window.electronAPI.startDrag())
    dragHandle.addEventListener('mouseleave', () => window.electronAPI.endDrag())
  </script>
</body>
</html>
```

---

## 8. React Changes — Wiring the Frontend

### 8.1 `App.jsx` — Wire caption_update and mic events

Replace the commented-out stub from Week 3 with the full implementation:

```javascript
// Wire caption_update SocketIO event
socket.on('caption_update', (data) => {
  setTranscript(data.transcript)
  setTranslated(data.translated)

  // Forward to overlay via Electron IPC
  if (window.electronAPI) {
    window.electronAPI.sendCaption({
      transcript: data.transcript,
      translated: data.translated
    })
  }
})
```

**Mic toggle handler — add to App.jsx:**
```javascript
const handleMicToggle = () => {
  if (!micActive) {
    socket.emit('start_mic', { direction })
    setMicActive(true)
  } else {
    socket.emit('stop_mic')
    setMicActive(false)
  }
}
```

Pass `handleMicToggle` to `<Controls onMicToggle={handleMicToggle} />`

### 8.2 `Controls.jsx` — Wire Mic Button

Replace the "Coming Soon" alert with the real handler:

```javascript
// Before (Week 3 stub):
onClick={() => alert('Coming Soon')}

// After (Week 4):
onClick={onMicToggle}
```

Update button styling to reflect active state:
- `micActive === false` → grey/neutral button, label "Start Live Captions"
- `micActive === true` → red button with pulse animation, label "Stop Live Captions"

Pulse animation using Tailwind:
```jsx
className={`... ${micActive ? 'bg-red-500 animate-pulse' : 'bg-gray-600'}`}
```

> **AGENT NOTE:** `animate-pulse` is a standard Tailwind utility — it exists in both v3 and v4. Safe to use.

### 8.3 `CaptionPanel.jsx` — Streaming Animation

Add a subtle fade-in animation when new captions arrive so the UI feels live:

```jsx
// Add a key prop that changes on each new caption to trigger re-render animation
<div key={transcript} className="transition-opacity duration-300 opacity-100">
  {transcript}
</div>
```

---

## 9. Backend — `test_mic.py`

Create a standalone mic test script that validates the audio capture pipeline without needing the full server running.

```python
# backend/test_mic.py
# Tests mic capture → transcription → translation for 1 chunk only

from audio_capture import start_capture, stop_capture
from transcriber import transcribe
from translator import translate
import time
import os

print('============================================')
print('  WEEK 4 MIC CAPTURE TEST (1 chunk)')
print('============================================')
print('[Test] Speak into your mic for 4 seconds...')

captured = []

def on_chunk(audio_path):
    captured.append(audio_path)
    stop_capture()  # Stop after first chunk

start_capture(on_chunk)
time.sleep(6)  # Wait for 1 chunk (4s record + 2s buffer)

if captured:
    path = captured[0]
    print(f'[Test] Audio chunk captured: {path}')

    result = transcribe(path)
    transcript = result['text'].strip()
    print(f'[Test] Transcript: {transcript}')

    if transcript:
        translated = translate(transcript, 'en-ta')
        print(f'[Test] Translation: {translated}')
        print('--------------------------------------------')
        print('MIC TEST PASSED.')
    else:
        print('[Test] WARNING: Empty transcript. Check mic input.')

    if os.path.exists(path):
        os.unlink(path)
else:
    print('[Test] FAILED: No audio chunk captured.')

print('============================================')
```

---

## 10. README.md Updates

Add the following section:

```markdown
## Overlay Window

The overlay window floats on top of all applications and displays live captions.

- **Toggle overlay:** `Ctrl+Shift+C`
- The overlay is hidden by default when the app starts
- Drag the handle bar at the top to reposition it
- Works on top of fullscreen applications

## Live Captions

1. Start the Flask backend: `python backend/app.py`
2. Start the Electron app: `npm run dev`
3. Click **"Start Live Captions"** in the app
4. Speak into your microphone
5. Captions appear in the app and in the overlay (if visible)
6. Click **"Stop Live Captions"** to stop

> Note: There is a ~6-8 second delay between speaking and caption appearing.
> This is expected on GTX 1650 hardware — each 4-second audio chunk takes ~2-4 seconds to process.
```

---

## 11. Acceptance Criteria

Week 4 is complete ONLY when ALL of the following are true:

| # | Criterion | How to Verify |
|---|---|---|
| AC-01 | `test_mic.py` captures audio and prints transcript | Run the script, speak into mic |
| AC-02 | "Start Live Captions" button starts mic capture | Click button, check Flask console for `start_mic` |
| AC-03 | Captions appear in CaptionPanel during live capture | Speak, wait ~6-8 sec, observe UI |
| AC-04 | "Stop Live Captions" stops mic capture | Click stop, check Flask console for `stop_mic` |
| AC-05 | `Ctrl+Shift+C` toggles overlay visibility | Press hotkey, observe overlay |
| AC-06 | Overlay shows captions from live mic | Start mic, toggle overlay on, speak |
| AC-07 | Overlay shows captions from file upload | Upload file, toggle overlay on |
| AC-08 | Overlay is click-through (clicks pass to other windows) | Open a browser behind overlay, click through it |
| AC-09 | Overlay drag handle repositions the window | Drag the handle bar |
| AC-10 | Overlay stays on top of all windows | Alt-tab to another app, overlay stays visible |
| AC-11 | Mic button turns red + pulses when active | Click Start, observe button |
| AC-12 | No crash when mic is started then stopped repeatedly | Toggle mic 5 times quickly |

---

## 12. Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `sounddevice` can't find mic | Run `python -c "import sounddevice; print(sounddevice.query_devices())"` to list devices. Default device is used automatically. |
| Overlay not appearing on top of fullscreen apps | `alwaysOnTop: true` handles most cases. Some games with exclusive fullscreen may block it — this is a hardware limitation, not a bug. |
| `globalShortcut` conflicts with another app | If `Ctrl+Shift+C` is taken, change to `Ctrl+Shift+X` in `main.js` |
| Caption update causes React re-render lag | Only update state if new transcript is non-empty and different from current |
| Multiple mic capture threads stacking | `start_capture()` must check `_recording` flag before starting — already handled in `audio_capture.py` |
| Tailwind `animate-pulse` not working | This is a core Tailwind utility present in both v3 and v4 — if it fails, check that the CSS build is not cached |
| IPC bridge between windows not working | Confirm `preload.js` is loaded in BOTH BrowserWindows — both main and overlay need it |

---

## 13. Handoff Notes to Agent

> **READ THIS BEFORE STARTING.**

- **Tailwind CSS v4 is installed.** Do NOT install tailwindcss v3. Do NOT create or modify `tailwind.config.js`. Use the same utility classes already working in Week 3 components. See Section 3 for full details.
- `audio_capture.py` was an empty placeholder — implement it fully using the spec in Section 6.2. Do not use any library other than `sounddevice`, `numpy`, and `scipy.io.wavfile` for audio capture and saving.
- The overlay window is a **separate** `BrowserWindow` — it is NOT a React component rendered inside the main window. It is a second Electron window loaded from `overlay.html`.
- `setIgnoreMouseEvents(true, { forward: true })` is mandatory on the overlay — without `forward: true`, clicks will be swallowed on Windows.
- Do NOT use `app.run()` anywhere — always `socketio.run(app, ...)`.
- The `emit_caption()` function already exists as a stub in `app.py` from Week 2 — replace it with the full implementation in Section 6.3, do not create a duplicate.
- Test mic capture with `test_mic.py` BEFORE testing through the UI — isolate the pipeline first.
- Caption flow is: mic → `audio_capture.py` → `transcriber.py` → `translator.py` → `emit_caption()` → SocketIO → `App.jsx` → `CaptionPanel.jsx` AND `overlay.html`. Both destinations must receive captions.
- On completion, run through all 12 acceptance criteria and commit with message: `feat(week4): live mic captions and overlay window`

---

*End of Week 4 PRD — Caption Generator with Translation Project*
