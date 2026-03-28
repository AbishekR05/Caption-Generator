# PRD — Week 2: Python Backend (Flask + SocketIO)
### Caption Generator with Translation — Desktop App
**Phase:** Week 2 of 8 | **Prepared For:** Antigravity (Autonomous Coding Agent)  
**Depends On:** Week 1 complete (all tests passing) ✅  
**Estimated Duration:** 7 Days

---

## 1. Document Overview

| Field | Value |
|---|---|
| Document Title | Week 2 PRD — Flask Backend + SocketIO Server |
| Project | Caption Generator with Translation (Desktop App) |
| Phase | Week 2 of 8 |
| Prepared For | Antigravity (Autonomous Coding Agent) |
| Tech Stack | Python, Flask, Flask-SocketIO, openai-whisper, HuggingFace Transformers |
| Builds On | `backend/transcriber.py`, `backend/translator.py` from Week 1 |
| Status | Ready for Implementation |

---

## 2. Objective

Week 1 produced a working AI pipeline that runs via terminal script. The goal of Week 2 is to **wrap that pipeline in a local HTTP + WebSocket server** so that the Electron frontend (built in Week 3) can communicate with it programmatically.

By end of Week 2, the following must work:

- A Flask server running at `http://localhost:5000`
- A `POST /transcribe` endpoint that accepts an audio file and returns a transcript
- A `POST /translate` endpoint that accepts text and a direction and returns translated text
- A `POST /transcribe-and-translate` endpoint that does both in one call
- A WebSocket channel (via SocketIO) that the frontend can connect to for real-time caption streaming
- A test script (`test_api.py`) that validates all endpoints without needing Postman
- The hardcoded absolute path bug from Week 1 must be fixed

---

## 3. Context & Carry-Forward from Week 1

### What Week 1 Delivered
- `backend/transcriber.py` — Whisper `small` on CUDA, exposes `transcribe(audio_path, language=None) -> dict`
- `backend/translator.py` — MarianMT via HuggingFace, exposes `translate(text, direction) -> str`
- `backend/test_pipeline.py` — all 4 tests passing
- PyTorch `cu118` installed, GPU confirmed working

### Important Week 1 Deviations (carry these forward)
- Translation models are `Helsinki-NLP/opus-mt-en-mul` (not `opus-mt-en-ta`) and `Helsinki-NLP/opus-mt-mul-en` (not `opus-mt-ta-en`)
- EN→TA translation requires prepending the `>>tam<<` token to input text — this logic lives in `translator.py` and must not be removed
- The `test_pipeline.py` output showed an absolute Windows path for the audio file — Week 2 must fix this by using relative paths or accepting paths dynamically from the request

> **AGENT NOTE:** Do not modify `transcriber.py` or `translator.py` logic unless explicitly stated in this document. Import them as-is into `app.py`.

---

## 4. Scope

### In Scope
- `backend/app.py` — Flask + SocketIO server (primary deliverable)
- `backend/test_api.py` — automated API test script using `requests`
- Minor fix to path handling in `transcriber.py` if needed (relative path support)
- SocketIO event scaffolding for live mic streaming (connection/disconnection only — actual streaming is Week 4)
- Updating `README.md` with server start instructions

### Out of Scope
- Live microphone capture — Week 4
- Electron/React frontend — Week 3
- Any cloud API calls
- Authentication or security (this is localhost only)

---

## 5. File Changes

| File | Action | Notes |
|---|---|---|
| `backend/app.py` | **Implement** | Primary deliverable — Flask server |
| `backend/test_api.py` | **Create** | Automated endpoint tests |
| `backend/transcriber.py` | **Minor edit only** | Fix absolute path issue if present |
| `backend/translator.py` | **No changes** | Import as-is |
| `README.md` | **Update** | Add server start instructions |
| All other files | **No changes** | Leave Week 1 files untouched |

---

## 6. Technical Specifications

### 6.1 Server Configuration

| Parameter | Value |
|---|---|
| Framework | Flask + Flask-SocketIO |
| Host | `0.0.0.0` (accessible from localhost) |
| Port | `5000` |
| Debug Mode | `True` (development only) |
| CORS | Enabled for all origins (`flask-cors`) |
| Async Mode | `threading` (required for SocketIO with Flask) |

### 6.2 Dependencies to Add

These must be added to `requirements.txt` if not already present:

```
flask>=3.0.0
flask-socketio>=5.3.6
flask-cors>=4.0.0
requests>=2.31.0
python-socketio>=5.10.0
```

Install with:
```bash
pip install flask flask-socketio flask-cors requests python-socketio
```

---

## 7. API Endpoint Specifications

### 7.1 `POST /transcribe`

Accepts an audio file upload, runs it through Whisper, returns the transcript.

**Request:**
```
Content-Type: multipart/form-data
Body:
  - file     (required) — audio file (.mp3 or .wav)
  - language (optional) — 'en' or 'ta'. If omitted, Whisper auto-detects.
```

**Success Response — `200 OK`:**
```json
{
  "success": true,
  "transcript": "Hello, this is a test audio file for the caption app.",
  "language": "en",
  "duration_seconds": 1.4
}
```

**Error Response — `400 Bad Request`:**
```json
{
  "success": false,
  "error": "No audio file provided."
}
```

**Error Response — `500 Internal Server Error`:**
```json
{
  "success": false,
  "error": "Transcription failed: <exception message>"
}
```

**Implementation Notes:**
- Save the uploaded file to a temp location (`tempfile.NamedTemporaryFile`) before passing to Whisper
- Delete the temp file after transcription is complete (use `finally` block)
- Pass `language` param to `transcribe()` only if it was provided in the request
- Log the request and result to console using the `[API]` prefix

---

### 7.2 `POST /translate`

Accepts a text string and direction, returns translated text.

**Request:**
```
Content-Type: application/json
Body:
{
  "text": "Hello, this is a test.",
  "direction": "en-ta"
}
```

**Supported direction values:**
- `"en-ta"` — English to Tamil
- `"ta-en"` — Tamil to English

**Success Response — `200 OK`:**
```json
{
  "success": true,
  "translated": "வணக்கம், இது ஒரு சோதனை.",
  "direction": "en-ta",
  "duration_seconds": 0.8
}
```

**Error Response — `400 Bad Request`:**
```json
{
  "success": false,
  "error": "Missing required field: text"
}
```

```json
{
  "success": false,
  "error": "Invalid direction. Must be 'en-ta' or 'ta-en'."
}
```

**Implementation Notes:**
- Validate that both `text` and `direction` are present in the request body
- Validate that `direction` is one of the two allowed values before calling `translate()`
- Return 400 for validation errors, 500 for unexpected errors

---

### 7.3 `POST /transcribe-and-translate`

Convenience endpoint — does transcription + translation in a single call. This is what the Electron frontend will primarily use.

**Request:**
```
Content-Type: multipart/form-data
Body:
  - file      (required) — audio file (.mp3 or .wav)
  - direction (required) — 'en-ta' or 'ta-en'
  - language  (optional) — force Whisper language detection
```

**Success Response — `200 OK`:**
```json
{
  "success": true,
  "transcript": "Hello, this is a test audio file for the caption app.",
  "translated": "வணக்கம், இது தலைப்பு பயன்பாட்டிற்கான சோதனை ஆடியோ கோப்பு.",
  "language_detected": "en",
  "direction": "en-ta",
  "transcription_time": 1.4,
  "translation_time": 0.8,
  "total_time": 2.2
}
```

**Implementation Notes:**
- Internally call `transcribe()` first, then pass the result to `translate()`
- Track timing for each step separately and include in response
- Same temp file handling as `/transcribe`

---

### 7.4 `GET /health`

Simple health check endpoint. Electron will ping this on startup to confirm the backend is running.

**Response — `200 OK`:**
```json
{
  "status": "ok",
  "whisper_model": "small",
  "device": "cuda",
  "gpu": "NVIDIA GeForce GTX 1650"
}
```

**Implementation Notes:**
- Use `torch.cuda.get_device_name(0)` to get the GPU name
- If CUDA is not available, return `"device": "cpu"` and `"gpu": null`

---

## 8. WebSocket (SocketIO) Specifications

Week 2 only sets up the **scaffolding** for WebSocket. Actual audio streaming happens in Week 4. The following events must be implemented now so Week 3 Electron frontend can connect.

### 8.1 Events to Implement

| Event | Direction | Description |
|---|---|---|
| `connect` | Client → Server | Client connects. Log the connection. |
| `disconnect` | Client → Server | Client disconnects. Log it. |
| `ping` | Client → Server | Client sends a ping. Server responds with `pong`. |
| `pong` | Server → Client | Server response to `ping` with a timestamp. |
| `caption_update` | Server → Client | **Placeholder for Week 4** — server will emit this with live caption chunks. Implement the emit function but don't call it yet. |

### 8.2 SocketIO Event Implementation

```python
@socketio.on('connect')
def handle_connect():
    print(f'[SocketIO] Client connected: {request.sid}')
    emit('connected', {'message': 'Connected to Caption Generator backend.'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'[SocketIO] Client disconnected: {request.sid}')

@socketio.on('ping')
def handle_ping():
    emit('pong', {'timestamp': time.time()})
```

```python
# Week 4 placeholder — do not call yet
def emit_caption(text, translated):
    socketio.emit('caption_update', {
        'transcript': text,
        'translated': translated,
        'timestamp': time.time()
    })
```

> **AGENT NOTE:** `emit_caption` must be defined but never called in Week 2. It will be wired to the mic input pipeline in Week 4.

---

## 9. Implementation Specification — `app.py`

### 9.1 File Structure

```python
# backend/app.py

# ── Imports ──────────────────────────────────────────────
import os, time, tempfile
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import torch

from transcriber import transcribe
from translator import translate

# ── App Init ─────────────────────────────────────────────
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── REST Endpoints ────────────────────────────────────────
# /health
# /transcribe
# /translate
# /transcribe-and-translate

# ── SocketIO Events ───────────────────────────────────────
# connect, disconnect, ping → pong

# ── Week 4 Placeholder ───────────────────────────────────
# emit_caption()

# ── Entry Point ───────────────────────────────────────────
if __name__ == '__main__':
    print("[Server] Starting Caption Generator backend on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
```

### 9.2 Temp File Handling Pattern

All endpoints that accept audio files must follow this exact pattern:

```python
tmp = None
try:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
    file.save(tmp.name)
    tmp.close()
    result = transcribe(tmp.name)
finally:
    if tmp and os.path.exists(tmp.name):
        os.unlink(tmp.name)
```

### 9.3 Console Logging Format

All server logs must use these exact prefixes for consistency (the frontend may parse these later):

| Prefix | Used For |
|---|---|
| `[Server]` | Server startup, shutdown |
| `[API]` | Incoming HTTP requests and responses |
| `[SocketIO]` | WebSocket connect/disconnect/events |
| `[Error]` | Any exceptions or failures |

---

## 10. Implementation Specification — `test_api.py`

This script tests all endpoints automatically using the `requests` library. It must not require Postman or any external tool.

### 10.1 Test Cases

| # | Test | Method | Endpoint | Expected |
|---|---|---|---|---|
| T-01 | Health check | GET | `/health` | `status: ok`, `device: cuda` |
| T-02 | Transcribe audio file | POST | `/transcribe` | Non-empty transcript string |
| T-03 | Translate EN→TA | POST | `/translate` | Tamil Unicode characters in response |
| T-04 | Translate TA→EN | POST | `/translate` | English text in response |
| T-05 | Transcribe + Translate | POST | `/transcribe-and-translate` | Both transcript and translated present |
| T-06 | Missing file error | POST | `/transcribe` | `success: false`, HTTP 400 |
| T-07 | Invalid direction error | POST | `/translate` | `success: false`, HTTP 400 |

### 10.2 Expected Output

```
============================================
  WEEK 2 API TEST
============================================
[T-01] Health Check             : PASS (device: cuda, gpu: NVIDIA GeForce GTX 1650)
[T-02] Transcribe Audio         : PASS
       Result: 'Hello, this is a test audio file for the caption app.'
[T-03] Translate EN->TA         : PASS
       Result: 'வணக்கம், இது தலைப்பு பயன்பாட்டிற்கான சோதனை ஆடியோ கோப்பு.'
[T-04] Translate TA->EN         : PASS
       Result: 'Hello, this is a test audio file for the title application.'
[T-05] Transcribe + Translate   : PASS
       Transcript : 'Hello, this is a test audio file for the caption app.'
       Translated : 'வணக்கம், இது தலைப்பு பயன்பாட்டிற்கான சோதனை ஆடியோ கோப்பு.'
       Total time : 2.2s
[T-06] Missing File Error       : PASS (HTTP 400 returned correctly)
[T-07] Invalid Direction Error  : PASS (HTTP 400 returned correctly)
--------------------------------------------
ALL TESTS PASSED. Week 2 complete.
============================================
```

> **AGENT NOTE:** `test_api.py` assumes the Flask server is already running on `localhost:5000`. Print a clear error and exit if the server is not reachable. Do not start the server from within the test script.

---

## 11. README.md Updates

Add the following section to `README.md` under a `## Running the Backend` heading:

```markdown
## Running the Backend

### Start the Flask server
```bash
cd caption-app
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac
python backend/app.py
```

Server will start at: http://localhost:5000

### Run API tests (server must be running first)
```bash
python backend/test_api.py
```

### Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Check server + GPU status |
| POST | /transcribe | Transcribe audio file |
| POST | /translate | Translate text EN↔TA |
| POST | /transcribe-and-translate | Transcribe + translate in one call |
```

---

## 12. Acceptance Criteria

Week 2 is complete ONLY when ALL of the following are true:

| # | Criterion | How to Verify |
|---|---|---|
| AC-01 | Flask server starts without errors | `python backend/app.py` runs cleanly |
| AC-02 | `/health` returns `device: cuda` | T-01 in `test_api.py` passes |
| AC-03 | `/transcribe` returns correct transcript | T-02 passes |
| AC-04 | `/translate` EN→TA returns Tamil text | T-03 passes |
| AC-05 | `/translate` TA→EN returns English text | T-04 passes |
| AC-06 | `/transcribe-and-translate` works end to end | T-05 passes |
| AC-07 | Bad requests return HTTP 400 with `success: false` | T-06 and T-07 pass |
| AC-08 | SocketIO connect/disconnect logs appear in console | Connect using a browser or test client |
| AC-09 | `emit_caption()` function exists in `app.py` | Code review |
| AC-10 | `test_api.py` prints ALL TESTS PASSED | Run the script |

---

## 13. Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Port 5000 already in use | Change to port `5001` in `app.py` and update `test_api.py` accordingly |
| Whisper reloads model on every request (slow) | Model must be loaded at module level in `transcriber.py` — confirm this from Week 1 |
| Temp file not deleted on crash | Use `finally` block for cleanup — never rely on normal flow |
| CORS errors when Electron connects | `flask-cors` with `CORS(app)` handles this — confirm it's installed |
| SocketIO and Flask dev server conflict | Use `socketio.run(app, ...)` instead of `app.run(...)` — never mix them |
| Large audio file causes timeout | Add a max file size check (reject files over 25MB with HTTP 413) |

---

## 14. Handoff Notes to Agent

> **READ THIS BEFORE STARTING.**

- The Flask server must import `transcribe` and `translate` from `transcriber.py` and `translator.py` directly — do not rewrite or duplicate any ML logic in `app.py`.
- Models are loaded at module level in Week 1 files — this means they load once when `app.py` imports them. This is intentional and correct. Do not move model loading inside request handlers.
- The `>>tam<<` token prepending logic for EN→TA translation already lives in `translator.py`. Do not add it again in `app.py`.
- All response bodies must be valid JSON — use `jsonify()` for every response, never return raw strings.
- Do not use `app.run()` — always use `socketio.run(app, ...)` to avoid SocketIO conflicts.
- On completion, start the server, run `test_api.py`, confirm `ALL TESTS PASSED`, then commit with message: `feat(week2): flask backend with rest endpoints and socketio scaffolding`

---

*End of Week 2 PRD — Caption Generator with Translation Project*
