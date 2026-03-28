# PRD — Week 3: Electron + React Frontend (Main App UI)
### Caption Generator with Translation — Desktop App
**Phase:** Week 3 of 8 | **Prepared For:** Antigravity (Autonomous Coding Agent)
**Depends On:** Week 1 ✅ Week 2 ✅
**Estimated Duration:** 7 Days

---

## 1. Document Overview

| Field | Value |
|---|---|
| Document Title | Week 3 PRD — Electron + React Frontend (Main App UI) |
| Project | Caption Generator with Translation (Desktop App) |
| Phase | Week 3 of 8 |
| Prepared For | Antigravity (Autonomous Coding Agent) |
| Tech Stack | Electron, React, Vite, Tailwind CSS, socket.io-client |
| Builds On | Flask backend running at `http://localhost:5000` (Week 2) |
| Status | Ready for Implementation |

---

## 2. Objective

Week 2 delivered a fully working Flask backend with REST endpoints and SocketIO. Week 3 builds the **desktop application shell** — the Electron wrapper and the React UI that the user will actually see and interact with.

By end of Week 3, the following must work:

- Electron app launches with a single `npm start` command
- A React + Vite frontend renders inside the Electron window
- The UI has a **Start/Stop** button for mic capture (wired in Week 4 — stub only this week)
- The UI has a **file upload** input for audio/video files
- The UI has a **language direction toggle** (EN→TA / TA→EN)
- Uploading a file triggers a call to the Flask `/transcribe-and-translate` endpoint
- The transcript and translation are displayed in the UI in real time
- A SocketIO connection is established from the frontend to the Flask backend on app launch
- Tailwind CSS is used for all styling
- The app looks clean and usable — not a placeholder

---

## 3. Context & Carry-Forward

### What Exists So Far
- `backend/app.py` — Flask server on `localhost:5000`
- `backend/transcriber.py` — Whisper small on CUDA
- `backend/translator.py` — MarianMT EN↔TA with `>>tam<<` token fix
- `electron/` folder — currently empty placeholder files from Week 1
- `package.json` — currently empty (created via `npm init -y`)

### Week 3 Starts Fresh on the Electron Side
The `electron/` folder contents from Week 1 were placeholders. Week 3 **replaces them entirely** with a proper Electron + Vite + React setup. The agent must scaffold this from scratch using the setup steps in Section 6.

> **AGENT NOTE:** The Flask backend must be running on `localhost:5000` for the frontend to work. The Electron app does NOT start the Python server — they are separate processes. Document this clearly in the README.

---

## 4. Scope

### In Scope
- Electron main process (`electron/main.js`)
- React + Vite frontend scaffold inside `electron/renderer/`
- Tailwind CSS setup
- Main UI component with all controls
- Caption display panel
- SocketIO client connection to Flask backend
- File upload → `/transcribe-and-translate` → display result flow
- Language direction toggle (EN→TA / TA→EN)
- Start/Stop mic button (UI only — not wired, stub for Week 4)
- `README.md` update with frontend start instructions

### Out of Scope
- Overlay window — Week 4
- Live mic capture — Week 4
- Hotkeys — Week 4
- App packaging/installer — Week 7
- Any backend changes

---

## 5. Folder Structure After Week 3

The `electron/` folder must be restructured as follows. **Replace all Week 1 placeholder files.**

```
caption-app/
├── backend/                        # Unchanged from Week 2
│   ├── app.py
│   ├── transcriber.py
│   ├── translator.py
│   ├── audio_capture.py
│   ├── test_pipeline.py
│   └── test_api.py
│
├── electron/
│   ├── main.js                     # Electron main process (rewritten)
│   ├── preload.js                  # Electron preload script (new)
│   ├── renderer/                   # React + Vite app (new)
│   │   ├── index.html
│   │   ├── vite.config.js
│   │   ├── tailwind.config.js
│   │   ├── postcss.config.js
│   │   ├── package.json
│   │   ├── src/
│   │   │   ├── main.jsx            # React entry point
│   │   │   ├── App.jsx             # Root component
│   │   │   ├── index.css           # Tailwind base imports
│   │   │   └── components/
│   │   │       ├── Controls.jsx    # Start/Stop, file upload, direction toggle
│   │   │       ├── CaptionPanel.jsx # Displays transcript + translation
│   │   │       └── StatusBar.jsx   # Connection status, GPU info
│   │   └── public/
│   │       └── icon.png            # App icon placeholder (any PNG)
│
├── assets/
├── .gitignore
├── package.json                    # Root — Electron dependencies
├── requirements.txt
└── README.md
```

---

## 6. Setup & Scaffold Instructions

### 6.1 Root `package.json` — Electron Dependencies

Replace the existing `package.json` at project root with:

```json
{
  "name": "caption-app",
  "version": "1.0.0",
  "description": "Caption Generator with Translation",
  "main": "electron/main.js",
  "scripts": {
    "start": "electron .",
    "dev": "concurrently \"npm run vite\" \"wait-on http://localhost:5173 && electron .\"",
    "vite": "npm run dev --prefix electron/renderer"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "concurrently": "^8.2.0",
    "wait-on": "^7.2.0"
  }
}
```

Install with:
```bash
npm install
```

### 6.2 React + Vite Setup inside `electron/renderer/`

```bash
cd electron/renderer
npm create vite@latest . -- --template react
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install socket.io-client axios
```

### 6.3 Tailwind Config (`electron/renderer/tailwind.config.js`)

```js
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: { extend: {} },
  plugins: []
}
```

### 6.4 Tailwind Base CSS (`electron/renderer/src/index.css`)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 6.5 Vite Config (`electron/renderer/vite.config.js`)

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  base: './'
})
```

---

## 7. Electron Main Process — `electron/main.js`

### 7.1 Requirements

- Create a single `BrowserWindow` (main app window)
- Window size: `900 x 650` minimum, resizable
- In development: load `http://localhost:5173` (Vite dev server)
- `nodeIntegration: false`, `contextIsolation: true` (security best practice)
- Load `preload.js` as the preload script
- App name in title bar: `Caption Generator`
- On macOS: quit when all windows closed (standard behavior)

### 7.2 Implementation

```javascript
const { app, BrowserWindow } = require('electron')
const path = require('path')

const isDev = process.env.NODE_ENV !== 'production'

function createWindow() {
  const win = new BrowserWindow({
    width: 900,
    height: 650,
    minWidth: 800,
    minHeight: 600,
    title: 'Caption Generator',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  })

  if (isDev) {
    win.loadURL('http://localhost:5173')
    win.webContents.openDevTools()
  } else {
    win.loadFile(path.join(__dirname, 'renderer/dist/index.html'))
  }
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
```

### 7.3 `electron/preload.js`

```javascript
// Preload script — exposes safe APIs to renderer if needed
// Currently a stub — will be expanded in Week 4 for IPC
const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  version: process.versions.electron
})
```

---

## 8. React Component Specifications

### 8.1 `App.jsx` — Root Component

Responsibilities:
- Holds all global state (transcript, translation, direction, isConnected, isLoading)
- Establishes SocketIO connection to `http://localhost:5000` on mount
- Passes state and handlers down to child components as props
- Renders: `<StatusBar />`, `<Controls />`, `<CaptionPanel />`

**State shape:**
```javascript
const [transcript, setTranscript] = useState('')
const [translated, setTranslated] = useState('')
const [direction, setDirection] = useState('en-ta')   // 'en-ta' or 'ta-en'
const [isConnected, setIsConnected] = useState(false)
const [isLoading, setIsLoading] = useState(false)
const [error, setError] = useState(null)
const [micActive, setMicActive] = useState(false)      // stub for Week 4
```

**SocketIO setup in `useEffect`:**
```javascript
import { io } from 'socket.io-client'

useEffect(() => {
  const socket = io('http://localhost:5000')
  socket.on('connect', () => setIsConnected(true))
  socket.on('disconnect', () => setIsConnected(false))

  // Week 4: wire caption_update event here
  // socket.on('caption_update', (data) => { ... })

  return () => socket.disconnect()
}, [])
```

**File upload handler:**
```javascript
const handleFileUpload = async (file) => {
  setIsLoading(true)
  setError(null)
  const formData = new FormData()
  formData.append('file', file)
  formData.append('direction', direction)

  try {
    const res = await axios.post('http://localhost:5000/transcribe-and-translate', formData)
    setTranscript(res.data.transcript)
    setTranslated(res.data.translated)
  } catch (err) {
    setError('Failed to process file. Is the backend running?')
  } finally {
    setIsLoading(false)
  }
}
```

---

### 8.2 `Controls.jsx` — Control Panel

Renders three controls:

**A. File Upload**
- A styled drag-and-drop zone OR a simple file input button
- Accepted formats: `.mp3`, `.wav`, `.mp4`, `.mkv`, `.m4a`
- On file select: call `onFileUpload(file)` prop
- While loading: show a spinner or "Processing..." text, disable the input
- Supported formats listed below the input

**B. Language Direction Toggle**
- A toggle switch or segmented button with two states: `EN → TA` and `TA → EN`
- Current direction shown clearly
- On toggle: call `onDirectionChange(newDirection)` prop
- Must be disabled while a file is being processed (`isLoading === true`)

**C. Start/Stop Mic Button**
- A prominent button, red when active, grey when inactive
- Label: "Start Live Captions" / "Stop Live Captions"
- On click: toggle `micActive` state and show a "Coming Soon" toast or alert for now
- **Do NOT wire any actual mic logic** — that is Week 4

**Props interface:**
```javascript
Controls.propTypes = {
  direction: PropTypes.string,
  onDirectionChange: PropTypes.func,
  onFileUpload: PropTypes.func,
  isLoading: PropTypes.bool,
  micActive: PropTypes.bool,
  onMicToggle: PropTypes.func
}
```

---

### 8.3 `CaptionPanel.jsx` — Caption Display

Renders the transcription and translation results.

**Layout:**
- Two side-by-side panels (or stacked on small windows)
- Left panel: "Original" — shows `transcript`
- Right panel: "Translation" — shows `translated`
- Panel headers show the language: e.g. "English" and "Tamil"
- When empty: show a placeholder message — "Captions will appear here"
- When loading: show a pulsing skeleton loader or "Processing audio..."
- Text should be large and readable (min 16px)
- Tamil text must render correctly — use a font that supports Tamil Unicode (e.g. `Noto Sans Tamil` from Google Fonts)

**Props interface:**
```javascript
CaptionPanel.propTypes = {
  transcript: PropTypes.string,
  translated: PropTypes.string,
  direction: PropTypes.string,
  isLoading: PropTypes.bool
}
```

> **AGENT NOTE:** Tamil Unicode rendering is critical. Add `@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil&display=swap')` to `index.css` and apply the font to the translation panel. Without this, Tamil characters may render as boxes on some Windows systems.

---

### 8.4 `StatusBar.jsx` — Status Bar

A slim bar at the bottom or top of the app showing:

- 🟢 / 🔴 Backend connection indicator with text: "Backend Connected" / "Backend Disconnected"
- GPU info fetched from `/health` endpoint on app load (show `NVIDIA GeForce GTX 1650` or equivalent)
- App version (read from `package.json` or hardcode `v1.0.0`)

**On mount:** call `GET /health` and store the GPU name. Show "Checking..." until the response arrives.

**Props interface:**
```javascript
StatusBar.propTypes = {
  isConnected: PropTypes.bool,
  gpuName: PropTypes.string
}
```

---

## 9. UI Design Requirements

The UI must look **clean and functional** — not a default browser form. Use Tailwind utility classes throughout.

### Color Scheme
- Background: dark (`gray-900` or `slate-900`)
- Surface: `gray-800` for panels and cards
- Accent: `indigo-500` for buttons and active states
- Text: `white` primary, `gray-400` secondary
- Error: `red-400`
- Success/connected: `green-400`

### Layout
- Fixed top `StatusBar`
- Main content area with `Controls` on the left (or top) and `CaptionPanel` taking the majority of the space
- Padding: `p-4` or `p-6` throughout
- Rounded corners on all panels: `rounded-xl`

### Typography
- UI text: system font stack or any clean sans-serif via Tailwind
- Caption text (Tamil + English): `Noto Sans Tamil` — ensures both scripts render correctly

> **AGENT NOTE:** The UI does not need to be pixel-perfect or beautifully designed at this stage. It must be usable, readable, and not broken. Polish comes in Week 5. Focus on wiring over aesthetics.

---

## 10. Development Workflow

### Starting the App in Development Mode

Two terminals are required:

**Terminal 1 — Flask backend:**
```bash
cd caption-app
venv\Scripts\activate
python backend/app.py
```

**Terminal 2 — Electron + Vite:**
```bash
cd caption-app
npm run dev
```

`npm run dev` uses `concurrently` to start Vite on port 5173 and Electron simultaneously, with `wait-on` ensuring Electron only opens after Vite is ready.

> **AGENT NOTE:** Document both terminal commands clearly in README.md. The most common mistake will be forgetting to start the Flask backend first.

---

## 11. Test Checklist (`test_frontend.md`)

Create a manual test checklist file at `electron/test_frontend.md`. This is a markdown file the human tester runs through manually (no automation needed for Week 3 UI tests).

```markdown
# Week 3 Frontend Test Checklist

## Setup
- [ ] Flask backend running on localhost:5000
- [ ] `npm run dev` started successfully
- [ ] Electron window opened

## Status Bar
- [ ] Status bar shows "Backend Connected" with green indicator
- [ ] GPU name displayed (e.g. NVIDIA GeForce GTX 1650)
- [ ] If backend is stopped, indicator turns red

## File Upload (EN → TA)
- [ ] Set direction to EN → TA
- [ ] Upload a .mp3 file
- [ ] Loading state shown while processing
- [ ] Transcript appears in left panel (English)
- [ ] Tamil translation appears in right panel
- [ ] Tamil characters render correctly (not boxes)

## File Upload (TA → EN)
- [ ] Set direction to TA → EN
- [ ] Upload a Tamil audio file (or reuse test_audio.mp3 — result will just be EN→EN)
- [ ] Both panels populate

## Direction Toggle
- [ ] Toggle switches between EN→TA and TA→EN
- [ ] Toggle is disabled while processing

## Mic Button
- [ ] Button visible and styled
- [ ] Clicking shows "Coming Soon" message
- [ ] Does not crash the app

## Error Handling
- [ ] Stop Flask backend, try uploading a file
- [ ] Error message appears in UI (not a blank screen or console-only error)
```

---

## 12. README.md Updates

Add the following to `README.md`:

```markdown
## Running the App (Development)

> Both the backend and frontend must run simultaneously in separate terminals.

### Terminal 1 — Start Flask Backend
```bash
cd caption-app
venv\Scripts\activate
python backend/app.py
```

### Terminal 2 — Start Electron + React
```bash
cd caption-app
npm install         # first time only
npm run dev
```

The Electron window will open automatically once the Vite dev server is ready.
```

---

## 13. Acceptance Criteria

Week 3 is complete ONLY when ALL of the following are true:

| # | Criterion | How to Verify |
|---|---|---|
| AC-01 | `npm run dev` opens the Electron window | Run the command |
| AC-02 | Status bar shows backend connected | Green indicator visible |
| AC-03 | GPU name fetched and displayed | Check status bar |
| AC-04 | File upload triggers `/transcribe-and-translate` | Check Flask console logs |
| AC-05 | Transcript shown in left caption panel | Upload a file and observe |
| AC-06 | Tamil translation shown in right panel | Tamil Unicode renders, not boxes |
| AC-07 | Direction toggle switches EN↔TA | Toggle and re-upload |
| AC-08 | Loading state shown during processing | Observe spinner/disabled state |
| AC-09 | Error message shown if backend is down | Stop Flask, try uploading |
| AC-10 | Mic button shows "Coming Soon" on click | Click the button |
| AC-11 | SocketIO connects on app launch | Check Flask console for connect log |
| AC-12 | `test_frontend.md` checklist passes | Run through it manually |

---

## 14. Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Vite and Electron port conflict | Vite on 5173, Flask on 5000 — no overlap. Use `wait-on` to sequence startup. |
| Tamil characters render as boxes | Import `Noto Sans Tamil` from Google Fonts and apply to translation panel |
| CORS errors from Electron to Flask | Already handled by `flask-cors` in Week 2 — confirm it's still active |
| Electron can't load Vite in dev | Ensure `NODE_ENV` is not set to `production` when running `npm run dev` |
| `axios` POST with FormData fails | Set no manual `Content-Type` header — let axios set it automatically with the boundary |
| React state not updating after upload | Ensure `setTranscript` and `setTranslated` are called inside the `try` block after response |

---

## 15. Handoff Notes to Agent

> **READ THIS BEFORE STARTING.**

- The Flask backend is a completely separate process. The Electron app must never attempt to start or manage the Python process. They run independently.
- Use `axios` for HTTP calls — not `fetch`. It handles FormData multipart uploads more reliably in this setup.
- Do NOT set `Content-Type: multipart/form-data` manually in axios headers when sending FormData — axios sets it automatically with the correct boundary string. Setting it manually will break the upload.
- Tamil font rendering is not optional — it is a core feature of this project. `Noto Sans Tamil` must be loaded and applied.
- The mic button must exist in the UI this week even though it does nothing useful yet. It will be wired in Week 4.
- `contextIsolation: true` and `nodeIntegration: false` are mandatory in the Electron window config — do not change these for convenience.
- All SocketIO event listeners from Week 4 (`caption_update`) must be added as commented-out stubs in `App.jsx` so they are easy to wire next week.
- On completion, run through `test_frontend.md` manually and confirm all checkboxes pass, then commit with message: `feat(week3): electron react frontend with file upload and caption display`

---

*End of Week 3 PRD — Caption Generator with Translation Project*
