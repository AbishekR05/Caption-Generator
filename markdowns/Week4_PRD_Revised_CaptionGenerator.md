# PRD — Week 4 (Revised): Live Captions + Overlay + System Audio + Translation Toggle
### Caption Generator with Translation — Desktop App
**Phase:** Week 4 of 8 | **Prepared For:** Antigravity (Autonomous Coding Agent)
**Depends On:** Week 1 ✅ Week 2 ✅ Week 3 ✅
**Estimated Duration:** 7 Days
**Revision Note:** This replaces the original Week 4 PRD. Key additions: system audio (WASAPI loopback) input mode, translation as an optional toggle (off by default), and English-first subtitle display.

---

## 1. Document Overview

| Field | Value |
|---|---|
| Document Title | Week 4 PRD (Revised) — Live Captions + Overlay + System Audio + Translation Toggle |
| Project | Caption Generator with Translation (Desktop App) |
| Phase | Week 4 of 8 |
| Prepared For | Antigravity (Autonomous Coding Agent) |
| Tech Stack | Python sounddevice (WASAPI), Flask-SocketIO, Electron IPC, React |
| Builds On | All Week 1–3 deliverables |
| Status | Ready for Implementation |

---

## 2. Project Motto (Read First)

> **The primary goal of this app is English subtitle generation.**
> Translation (English ↔ Tamil) is a secondary, optional feature toggled on demand.

This means:
- English subtitles are shown **by default**, always, with no extra steps
- Translation only runs when the user explicitly enables it via a toggle
- The overlay displays **English only** by default — Tamil appears below only when translation is ON
- Latency is optimized for English-first — translation is never in the critical path unless requested

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
- Do not upgrade or downgrade Tailwind — leave the version exactly as Week 3 installed it

---

## 4. Context & Carry-Forward

### Existing Infrastructure
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

```
caption-app/
├── backend/
│   ├── audio_capture.py        # IMPLEMENT THIS WEEK (was empty)
│   ├── app.py                  # MODIFY — wire emit_caption(), add mic/system audio routes
│   └── test_mic.py             # CREATE — audio capture test script
│
├── electron/
│   ├── main.js                 # MODIFY — add overlay BrowserWindow, globalShortcut
│   ├── preload.js              # MODIFY — add IPC bridge for overlay
│   ├── overlay.html            # MODIFY — was placeholder, now real overlay UI
│   └── renderer/
│       └── src/
│           ├── App.jsx                 # MODIFY — wire caption_update, mic toggle, translation toggle
│           ├── components/
│           │   ├── Controls.jsx        # MODIFY — add input mode switch, translation toggle
│           │   └── CaptionPanel.jsx    # MODIFY — English-first, conditional Tamil panel
│           └── Overlay.jsx             # (not needed — overlay uses overlay.html directly)
```

---

## 6. Audio Input — Two Modes

The app must support two audio input modes selectable from the UI:

| Mode | What it captures | Use case |
|---|---|---|
| 🎤 Microphone | Your voice via mic | Lectures, meetings, live speech |
| 🖥️ System Audio | Everything playing on PC | Movies, YouTube, any media |

### 6.1 `backend/audio_capture.py` — Full Implementation

```python
# backend/audio_capture.py
import sounddevice as sd
import numpy as np
import tempfile
import os
import threading
import scipy.io.wavfile as wav

SAMPLE_RATE = 16000       # Whisper expects 16kHz
CHUNK_DURATION = 4        # seconds per chunk — optimal for GTX 1650
CHANNELS = 1              # mono audio

_recording = False
_thread = None


def get_input_devices():
    """
    Returns a dict of available input devices.
    Includes both mic devices and WASAPI loopback (system audio) devices.

    Returns:
        list of dicts: [{ 'id': int, 'name': str, 'is_loopback': bool }]
    """
    devices = []
    for i, d in enumerate(sd.query_devices()):
        if d['max_input_channels'] > 0:
            is_loopback = 'loopback' in d['name'].lower() or 'stereo mix' in d['name'].lower() or 'what u hear' in d['name'].lower()
            devices.append({
                'id': i,
                'name': d['name'],
                'is_loopback': is_loopback
            })
    return devices


def get_system_audio_device():
    """
    Auto-detect the system audio loopback device (WASAPI loopback).
    Returns the device ID if found, None otherwise.

    On Windows, the loopback device is typically named one of:
    - 'Stereo Mix'
    - 'What U Hear'
    - Any device with 'loopback' in the name
    """
    for d in get_input_devices():
        if d['is_loopback']:
            print(f"[AudioCapture] Found system audio device: {d['name']} (id: {d['id']})")
            return d['id']
    print('[AudioCapture] WARNING: No system audio loopback device found.')
    print('[AudioCapture] Enable "Stereo Mix" in Windows Sound settings > Recording tab.')
    return None


def start_capture(on_chunk_ready, mode='mic'):
    """
    Start continuous audio capture in a background thread.

    Args:
        on_chunk_ready (callable): Called with (audio_path: str) for each chunk.
                                   Caller is responsible for deleting the temp file.
        mode (str): 'mic' for microphone input, 'system' for system audio (WASAPI loopback).
    """
    global _recording, _thread

    if _recording:
        print('[AudioCapture] Already recording. Stop first.')
        return

    device_id = None
    if mode == 'system':
        device_id = get_system_audio_device()
        if device_id is None:
            raise RuntimeError(
                'System audio device not found. '
                'Please enable Stereo Mix in Windows Sound Settings > Recording devices.'
            )

    _recording = True
    _thread = threading.Thread(
        target=_capture_loop,
        args=(on_chunk_ready, device_id),
        daemon=True
    )
    _thread.start()
    print(f'[AudioCapture] Capture started. Mode: {mode}')


def stop_capture():
    """Stop the capture loop."""
    global _recording
    _recording = False
    print('[AudioCapture] Capture stopped.')


def _capture_loop(on_chunk_ready, device_id):
    global _recording
    while _recording:
        try:
            audio = sd.rec(
                int(CHUNK_DURATION * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='int16',
                device=device_id   # None = default mic, int = specific device
            )
            sd.wait()

            if not _recording:
                break

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            wav.write(tmp.name, SAMPLE_RATE, audio)
            tmp.close()

            on_chunk_ready(tmp.name)

        except Exception as e:
            print(f'[AudioCapture] Error: {e}')
            break

    print('[AudioCapture] Capture loop ended.')
```

### 6.2 Enabling Stereo Mix on Windows (Document in README)

System audio capture requires **Stereo Mix** to be enabled in Windows. Add these steps to `README.md`:

```
Enabling System Audio Capture (Windows):
1. Right-click the speaker icon in taskbar → Sound Settings
2. Scroll to "More sound settings"
3. Go to the Recording tab
4. Right-click in empty space → Show Disabled Devices
5. Right-click "Stereo Mix" → Enable
6. Click OK
```

> **AGENT NOTE:** If Stereo Mix is not available on the user's hardware (some modern laptops don't have it), the system audio mode will fail gracefully with a clear error message — already handled in `get_system_audio_device()`. Do not crash the app.

---

## 7. Translation Toggle — Off by Default

### Core Principle
Translation is **disabled by default**. The pipeline when translation is OFF:

```
Audio → Whisper → English text → emit_caption(transcript, translated=None) → UI shows English only
```

When translation is ON:
```
Audio → Whisper → English text → translate() → emit_caption(transcript, translated) → UI shows both
```

### 7.1 `backend/app.py` — Mic SocketIO Events

```python
from audio_capture import start_capture, stop_capture
import threading, os, time

@socketio.on('start_mic')
def handle_start_mic(data):
    mode = data.get('mode', 'mic')           # 'mic' or 'system'
    direction = data.get('direction', 'en-ta')
    translate_enabled = data.get('translate', False)  # OFF by default

    print(f'[SocketIO] start_mic | mode: {mode} | translate: {translate_enabled}')

    def on_chunk(audio_path):
        try:
            result = transcribe(audio_path)
            transcript = result['text'].strip()

            if not transcript:
                return

            translated = None
            if translate_enabled:
                translated = translate(transcript, direction)

            emit_caption(transcript, translated)

        except Exception as e:
            print(f'[Error] Chunk processing failed: {e}')
        finally:
            if os.path.exists(audio_path):
                os.unlink(audio_path)

    threading.Thread(
        target=start_capture,
        args=(on_chunk, mode),
        daemon=True
    ).start()


@socketio.on('stop_mic')
def handle_stop_mic():
    print('[SocketIO] stop_mic received.')
    stop_capture()
```

**Replace `emit_caption()` stub with:**
```python
def emit_caption(transcript, translated=None):
    socketio.emit('caption_update', {
        'transcript': transcript,
        'translated': translated,   # None if translation is off
        'timestamp': time.time()
    })
    print(f'[SocketIO] caption_update: {transcript[:40]}')
```

---

## 8. React Changes

### 8.1 New State in `App.jsx`

Add these new state variables:

```javascript
const [inputMode, setInputMode] = useState('mic')          // 'mic' or 'system'
const [translateEnabled, setTranslateEnabled] = useState(false)  // OFF by default
```

**Updated mic toggle handler:**
```javascript
const handleMicToggle = () => {
  if (!micActive) {
    socket.emit('start_mic', {
      mode: inputMode,
      direction,
      translate: translateEnabled
    })
    setMicActive(true)
  } else {
    socket.emit('stop_mic')
    setMicActive(false)
  }
}
```

**Wire `caption_update` SocketIO event:**
```javascript
socket.on('caption_update', (data) => {
  setTranscript(data.transcript)
  setTranslated(data.translated || '')   // null becomes empty string

  if (window.electronAPI) {
    window.electronAPI.sendCaption({
      transcript: data.transcript,
      translated: data.translated || ''
    })
  }
})
```

### 8.2 `Controls.jsx` — Updated Controls

The control panel must now have **four controls**:

**A. Input Mode Switch**
A two-option toggle: `🎤 Microphone` / `🖥️ System Audio`
```jsx
<div className="flex gap-2">
  <button
    onClick={() => onInputModeChange('mic')}
    className={inputMode === 'mic' ? 'bg-indigo-500 ...' : 'bg-gray-600 ...'}
  >
    🎤 Microphone
  </button>
  <button
    onClick={() => onInputModeChange('system')}
    className={inputMode === 'system' ? 'bg-indigo-500 ...' : 'bg-gray-600 ...'}
  >
    🖥️ System Audio
  </button>
</div>
```
- Disabled while mic is active (`micActive === true`)

**B. Start/Stop Mic Button**
- Same as original Week 4 spec
- Red + `animate-pulse` when active, grey when inactive
- Label: "Start Subtitles" / "Stop Subtitles" (renamed from "Live Captions" — reflects the primary subtitle goal)

**C. Translation Toggle**
- A simple on/off toggle switch
- Label: "Tamil Translation"
- Default: OFF
- When OFF: only English subtitles shown (faster)
- When ON: Tamil translation shown below English
- Can be toggled while mic is running — but changes only take effect on next chunk (note this in UI as a small hint)

**D. File Upload**
- Unchanged from Week 3
- Accepts `.mp3`, `.wav`, `.mp4`, `.mkv`, `.m4a`

**Updated props interface:**
```javascript
Controls.propTypes = {
  direction: PropTypes.string,
  onDirectionChange: PropTypes.func,
  onFileUpload: PropTypes.func,
  isLoading: PropTypes.bool,
  micActive: PropTypes.bool,
  onMicToggle: PropTypes.func,
  inputMode: PropTypes.string,          // NEW
  onInputModeChange: PropTypes.func,    // NEW
  translateEnabled: PropTypes.bool,     // NEW
  onTranslateToggle: PropTypes.func     // NEW
}
```

### 8.3 `CaptionPanel.jsx` — English First, Conditional Tamil

```jsx
const CaptionPanel = ({ transcript, translated, translateEnabled, isLoading }) => {
  return (
    <div className="...">
      {/* English subtitle — always shown */}
      <div className="...">
        <h3 className="...">English</h3>
        {isLoading
          ? <p className="animate-pulse ...">Processing audio...</p>
          : <p className="text-white text-lg ...">
              {transcript || 'Subtitles will appear here...'}
            </p>
        }
      </div>

      {/* Tamil translation — only shown when translateEnabled is true */}
      {translateEnabled && (
        <div className="...">
          <h3 className="...">Tamil</h3>
          <p className="text-cyan-300 text-lg" style={{ fontFamily: 'Noto Sans Tamil, sans-serif' }}>
            {translated || (isLoading ? '...' : 'Translation will appear here...')}
          </p>
        </div>
      )}
    </div>
  )
}
```

> **AGENT NOTE:** When `translateEnabled` is false, the Tamil panel must be **completely unmounted** (not just hidden with CSS) — this prevents stale translations from showing when the user turns translation back on after a while.

---

## 9. File Upload — Update for Translation Toggle

The `/transcribe-and-translate` endpoint must also respect the translation toggle. Update `app.py`:

```python
@app.route('/transcribe-and-translate', methods=['POST'])
def transcribe_and_translate():
    # ... existing file handling ...

    translate_enabled = request.form.get('translate', 'false').lower() == 'true'
    direction = request.form.get('direction', 'en-ta')

    result = transcribe(tmp.name)
    transcript = result['text'].strip()

    translated = None
    if translate_enabled:
        t_start = time.time()
        translated = translate(transcript, direction)
        t_translate = round(time.time() - t_start, 2)
    else:
        t_translate = 0

    return jsonify({
        'success': True,
        'transcript': transcript,
        'translated': translated,       # null if translation off
        'language_detected': result.get('language'),
        'direction': direction if translate_enabled else None,
        'transcription_time': ...,
        'translation_time': t_translate,
        'total_time': ...
    })
```

Update `handleFileUpload` in `App.jsx` to pass `translate` flag:
```javascript
formData.append('translate', translateEnabled.toString())
formData.append('direction', direction)
```

---

## 10. Overlay Window

### 10.1 `electron/main.js` — Overlay BrowserWindow

```javascript
const { app, BrowserWindow, globalShortcut, ipcMain } = require('electron')
const path = require('path')

let mainWindow = null
let overlayWindow = null
const isDev = process.env.NODE_ENV !== 'production'

function createOverlay() {
  overlayWindow = new BrowserWindow({
    width: 800,
    height: 100,
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
  overlayWindow.hide()
}

function toggleOverlay() {
  if (!overlayWindow) return
  overlayWindow.isVisible() ? overlayWindow.hide() : overlayWindow.show()
}

app.whenReady().then(() => {
  createWindow()
  createOverlay()
  globalShortcut.register('CommandOrControl+Shift+C', toggleOverlay)
})

app.on('will-quit', () => globalShortcut.unregisterAll())

// Forward captions from main window to overlay
ipcMain.on('caption-to-overlay', (event, data) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.webContents.send('caption-from-main', data)
  }
})

// Drag handle mouse event control
ipcMain.on('overlay-drag-start', () => overlayWindow.setIgnoreMouseEvents(false))
ipcMain.on('overlay-drag-end', () => overlayWindow.setIgnoreMouseEvents(true, { forward: true }))
```

### 10.2 `electron/preload.js`

```javascript
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  version: process.versions.electron,
  startDrag: () => ipcRenderer.send('overlay-drag-start'),
  endDrag: () => ipcRenderer.send('overlay-drag-end'),
  sendCaption: (data) => ipcRenderer.send('caption-to-overlay', data),
  onCaption: (callback) => ipcRenderer.on('caption-from-main', (_, data) => callback(data))
})
```

### 10.3 `electron/overlay.html` — English First Overlay

The overlay displays **English subtitle by default**. Tamil only appears if `translated` is non-null in the caption data.

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      background: transparent;
      overflow: hidden;
      font-family: 'Segoe UI', sans-serif;
      -webkit-app-region: no-drag;
    }

    #drag-handle {
      width: 100%;
      height: 18px;
      background: rgba(0,0,0,0.5);
      cursor: move;
      display: flex;
      align-items: center;
      justify-content: center;
      -webkit-app-region: drag;
    }

    #drag-handle span {
      font-size: 9px;
      color: rgba(255,255,255,0.3);
      letter-spacing: 2px;
    }

    #caption-box {
      margin: 4px 10px;
      padding: 8px 16px;
      background: rgba(0,0,0,0.78);
      border-radius: 10px;
      text-align: center;
    }

    /* English — primary, always visible */
    #transcript {
      font-size: 18px;
      font-weight: 500;
      color: #ffffff;
      line-height: 1.4;
      min-height: 26px;
    }

    /* Tamil — secondary, smaller, only shown when present */
    #translated {
      font-size: 14px;
      color: #a5f3fc;
      font-family: 'Noto Sans Tamil', 'Segoe UI', sans-serif;
      margin-top: 4px;
      min-height: 0;
      display: none;
    }

    #placeholder {
      font-size: 13px;
      color: rgba(255,255,255,0.25);
    }
  </style>
</head>
<body>
  <div id="drag-handle">
    <span>⠿ SUBTITLES — Ctrl+Shift+C to hide</span>
  </div>
  <div id="caption-box">
    <div id="placeholder">Waiting for subtitles...</div>
    <div id="transcript"></div>
    <div id="translated"></div>
  </div>

  <script>
    const transcriptEl = document.getElementById('transcript')
    const translatedEl = document.getElementById('translated')
    const placeholderEl = document.getElementById('placeholder')
    const dragHandle = document.getElementById('drag-handle')

    window.electronAPI.onCaption((data) => {
      placeholderEl.style.display = 'none'

      // Always show English
      transcriptEl.textContent = data.transcript || ''

      // Only show Tamil if translation was enabled and returned
      if (data.translated) {
        translatedEl.textContent = data.translated
        translatedEl.style.display = 'block'
      } else {
        translatedEl.textContent = ''
        translatedEl.style.display = 'none'
      }
    })

    dragHandle.addEventListener('mouseenter', () => window.electronAPI.startDrag())
    dragHandle.addEventListener('mouseleave', () => window.electronAPI.endDrag())
  </script>
</body>
</html>
```

---

## 11. `backend/test_mic.py`

```python
# backend/test_mic.py
# Tests 1 chunk of audio capture → transcription (no translation)

from audio_capture import start_capture, stop_capture, get_input_devices
from transcriber import transcribe
import time, os

print('============================================')
print('  WEEK 4 AUDIO CAPTURE TEST (1 chunk)')
print('============================================')

# List available devices
print('\n[Devices] Available input devices:')
for d in get_input_devices():
    tag = ' ← LOOPBACK (system audio)' if d['is_loopback'] else ''
    print(f"  [{d['id']}] {d['name']}{tag}")

print('\n[Test] Using microphone (default). Speak for 4 seconds...\n')

captured = []

def on_chunk(audio_path):
    captured.append(audio_path)
    stop_capture()

start_capture(on_chunk, mode='mic')
time.sleep(7)

if captured:
    path = captured[0]
    result = transcribe(path)
    transcript = result['text'].strip()
    print(f'[Test] Transcript: "{transcript}"')
    print('--------------------------------------------')
    print('MIC TEST PASSED.' if transcript else 'WARNING: Empty transcript. Check mic.')
    if os.path.exists(path):
        os.unlink(path)
else:
    print('[Test] FAILED: No audio chunk captured.')

print('============================================')
```

---

## 12. README.md Updates

```markdown
## Running the App (Development)

### Terminal 1 — Flask Backend
```bash
cd caption-app
venv\Scripts\activate
python backend/app.py
```

### Terminal 2 — Electron + React
```bash
cd caption-app
npm run dev
```

## Using the App

### English Subtitles (Default — Fastest)
1. Select input mode: Microphone or System Audio
2. Click **"Start Subtitles"**
3. Subtitles appear in the app and overlay

### Adding Tamil Translation
1. Toggle **"Tamil Translation"** ON in the controls
2. Tamil text appears below English subtitles
3. Toggle OFF to return to English-only mode (faster)

### Overlay
- Press `Ctrl+Shift+C` to toggle the subtitle overlay
- Overlay floats above all windows including media players
- Drag the top handle bar to reposition

### System Audio (Movies / YouTube)
1. Enable Stereo Mix in Windows Sound Settings (see below)
2. Select **"System Audio"** input mode
3. Play your movie/video and click Start Subtitles

#### Enabling Stereo Mix (Windows)
1. Right-click speaker in taskbar → Sound Settings → More sound settings
2. Go to Recording tab
3. Right-click empty area → Show Disabled Devices
4. Right-click **Stereo Mix** → Enable → OK
```

---

## 13. Acceptance Criteria

| # | Criterion | How to Verify |
|---|---|---|
| AC-01 | `test_mic.py` lists input devices including loopback if available | Run script |
| AC-02 | `test_mic.py` captures mic audio and prints transcript | Speak into mic |
| AC-03 | "Start Subtitles" starts capture, "Stop Subtitles" stops it | Click buttons |
| AC-04 | English subtitles appear in CaptionPanel by default | Start mic, speak |
| AC-05 | Tamil panel is hidden when translation toggle is OFF | Default state check |
| AC-06 | Tamil panel appears when translation toggle is ON | Toggle and speak |
| AC-07 | Switching to System Audio mode captures PC audio | Play music, check transcript |
| AC-08 | File upload respects translation toggle | Upload file with toggle ON and OFF |
| AC-09 | `Ctrl+Shift+C` toggles overlay | Press hotkey |
| AC-10 | Overlay shows English subtitle only by default | Check overlay with translation OFF |
| AC-11 | Overlay shows Tamil below English when translation ON | Toggle translation, check overlay |
| AC-12 | Overlay is click-through | Click through overlay onto another window |
| AC-13 | Overlay drag handle repositions window | Drag the handle |
| AC-14 | No crash when toggling mic start/stop rapidly | Toggle 5 times fast |
| AC-15 | System audio fails gracefully if Stereo Mix not enabled | Disable Stereo Mix, try system mode |

---

## 14. Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Stereo Mix not available on hardware | `get_system_audio_device()` returns None and raises a friendly RuntimeError — show this as a UI error message, do not crash |
| `sounddevice` can't find default mic | Run `python -c "import sounddevice; print(sounddevice.query_devices())"` to debug |
| Overlay not on top of fullscreen games | Exclusive fullscreen mode bypasses `alwaysOnTop` — this is a Windows limitation, not a bug. Windowed/borderless fullscreen works fine. |
| `globalShortcut` conflicts with another app | Change to `Ctrl+Shift+X` in `main.js` if needed |
| Translation toggle changed mid-capture | Changes only apply to next chunk — add a small UI hint: "Changes apply to next chunk" |
| Tailwind `animate-pulse` not working | Core Tailwind utility present in v4 — if broken check CSS build cache |
| IPC bridge not working for overlay | Confirm `preload.js` path is correctly set in BOTH BrowserWindow configs |
| Empty transcripts on silent chunks | Already handled — `if not transcript: return` in chunk handler |

---

## 15. Handoff Notes to Agent

> **READ THIS BEFORE STARTING.**

- **PRIMARY GOAL: English subtitles.** Translation is secondary and optional. Design and implement with this priority in mind.
- **Tailwind CSS v4 is installed.** Do NOT install v3. Do NOT create `tailwind.config.js`. See Section 3.
- `audio_capture.py` was an empty placeholder — implement it fully per Section 6.1.
- System audio capture uses WASAPI loopback via `sounddevice` — the device is auto-detected by name. Do not hardcode device IDs.
- Translation is OFF by default — the `translate` flag is passed from the frontend via SocketIO and HTTP. Never run `translate()` unless this flag is explicitly `True`.
- The overlay shows English by default. Tamil is only rendered when `data.translated` is non-null and non-empty.
- `emit_caption(transcript, translated=None)` — `translated` defaults to `None`. The frontend handles `null` gracefully.
- Do NOT use `app.run()` — always `socketio.run(app, ...)`.
- Test audio capture with `test_mic.py` BEFORE testing through the UI.
- Caption flow: audio → `audio_capture.py` → `transcriber.py` → (optionally) `translator.py` → `emit_caption()` → SocketIO → `App.jsx` → `CaptionPanel.jsx` AND `overlay.html`.
- On completion, run through all 15 acceptance criteria and commit with message: `feat(week4): live subtitles, system audio input, overlay window, translation toggle`

---

*End of Week 4 PRD (Revised) — Caption Generator with Translation Project*
