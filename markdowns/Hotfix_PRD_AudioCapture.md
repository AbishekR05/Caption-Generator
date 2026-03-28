# HOTFIX PRD — Audio Capture: Queue Fix + System Audio
### Caption Generator with Translation — Desktop App
**Type:** Hotfix (between Week 4 and Week 5)
**Prepared For:** Antigravity (Autonomous Coding Agent)
**Scope:** `backend/audio_capture.py` ONLY — do not touch any other file
**Priority:** Critical — app is unusable for continuous speech without this fix

---

## 1. Overview

Two bugs are being fixed in this hotfix:

| Bug | Symptom | Root Cause |
|---|---|---|
| BUG-01 | Mic skips sentences — only first and last captured | Recording thread blocks while Whisper processes — chunks dropped in between |
| BUG-02 | System audio mode doesn't work | Stereo Mix device not found or WASAPI not configured correctly |

**Only `backend/audio_capture.py` needs to be rewritten.** No changes to `app.py`, `transcriber.py`, `translator.py`, or any frontend file.

---

## 2. BUG-01 — Mic Dropping Sentences

### Why It Happens

The current implementation processes each chunk **inside** the recording loop:

```
record 4 sec → call on_chunk_ready() → Whisper takes 3-4 sec → record next chunk
```

While `on_chunk_ready()` is running (Whisper is thinking), **the mic is completely idle**. Any speech during those 3-4 seconds is lost forever. For a 1-minute continuous speech:

```
Chunk 1 → recorded ✅ → processed ✅
Chunks 2, 3, 4, 5... → DROPPED (mic idle while Whisper works)
Last chunk → recorded ✅ → processed ✅
```

This is why only the first and last sentences appear.

### The Fix — Producer/Consumer Queue

Separate recording and processing into two independent threads connected by a queue:

```
┌─────────────────────┐        ┌──────────────────────────┐
│  Recording Thread   │        │   Processing Thread       │
│  (producer)         │        │   (consumer)              │
│                     │        │                           │
│  record 4 sec chunk │──────▶ │  queue.get()              │
│  save to temp file  │  queue │  transcribe(chunk)        │
│  push to queue      │        │  translate(chunk)         │
│  immediately loop   │        │  emit_caption()           │
│  back to recording  │        │  loop back to queue.get() │
└─────────────────────┘        └──────────────────────────┘
```

The recording thread **never waits for Whisper**. It records, saves, pushes to queue, and immediately starts recording the next chunk. The processing thread runs independently and works through the queue at its own pace.

**Result:** If Whisper takes 4 seconds to process a chunk but chunks are 4 seconds each, the queue grows by 1 item per chunk but nothing is ever dropped. All speech is captured.

---

## 3. BUG-02 — System Audio Not Working

### Diagnosis Steps First

Before implementing the fix, run this diagnostic in the terminal:

```bash
cd caption-app
venv\Scripts\activate
python -c "import sounddevice as sd; [print(f'[{i}] {d[\"name\"]} | in:{d[\"max_input_channels\"]} out:{d[\"max_output_channels\"]}') for i, d in enumerate(sd.query_devices())]"
```

The output will show all audio devices. Look for any of these names:
- `Stereo Mix`
- `What U Hear`
- `Loopback`
- Any device with `max_input_channels > 0` that isn't a physical mic

**If none of these appear** → Stereo Mix is disabled in Windows. Enable it (instructions below).

**If they appear but system audio still fails** → The device name matching logic needs updating for that specific device name.

### Stereo Mix Enable Instructions (Windows)

The agent must add these steps as a console print when system audio mode fails:

```
1. Right-click the speaker icon in the Windows taskbar
2. Click "Sound Settings" → "More sound settings"
3. Go to the "Recording" tab
4. Right-click in empty space → "Show Disabled Devices"
5. If "Stereo Mix" appears: right-click it → "Enable" → "Set as Default" → OK
6. Restart the app and try System Audio mode again

If "Stereo Mix" does not appear at all:
- Your audio hardware may not support it
- Install and use VB-Audio Virtual Cable (free): https://vb-audio.com/Cable/
- Set "CABLE Output" as your playback device when watching movies
- The app will capture from "CABLE Output (VB-Audio Virtual Cable)"
```

---

## 4. Full Rewrite — `backend/audio_capture.py`

Replace the entire contents of `backend/audio_capture.py` with the following:

```python
# backend/audio_capture.py
# Hotfix: queue-based producer/consumer architecture to prevent chunk dropping

import sounddevice as sd
import numpy as np
import tempfile
import os
import threading
import queue
import scipy.io.wavfile as wav

# ── Configuration ─────────────────────────────────────────
SAMPLE_RATE = 16000       # Whisper expects 16kHz
CHUNK_DURATION = 4        # seconds per chunk
CHANNELS = 1              # mono

# ── Internal State ────────────────────────────────────────
_recording = False
_record_thread = None
_process_thread = None
_audio_queue = queue.Queue()   # thread-safe queue between recorder and processor


# ── Device Utilities ──────────────────────────────────────

def get_input_devices():
    """
    Returns all available audio input devices.

    Returns:
        list of dicts: [{ 'id': int, 'name': str, 'is_loopback': bool }]
    """
    devices = []
    for i, d in enumerate(sd.query_devices()):
        if d['max_input_channels'] > 0:
            name_lower = d['name'].lower()
            is_loopback = any(kw in name_lower for kw in [
                'loopback', 'stereo mix', 'what u hear',
                'virtual cable', 'vb-audio', 'cable output'
            ])
            devices.append({
                'id': i,
                'name': d['name'],
                'is_loopback': is_loopback
            })
    return devices


def get_system_audio_device():
    """
    Auto-detect system audio loopback device.

    Returns:
        int: device ID if found
        None: if not found
    """
    for d in get_input_devices():
        if d['is_loopback']:
            print(f"[AudioCapture] System audio device found: '{d['name']}' (id: {d['id']})")
            return d['id']

    # Not found — print helpful instructions
    print('[AudioCapture] ERROR: No system audio loopback device found.')
    print('[AudioCapture] Available input devices:')
    for d in get_input_devices():
        print(f"  [{d['id']}] {d['name']}")
    print('[AudioCapture] Fix options:')
    print('  Option A: Enable "Stereo Mix" in Windows Sound Settings > Recording tab')
    print('  Option B: Install VB-Audio Virtual Cable from https://vb-audio.com/Cable/')
    return None


# ── Public API ────────────────────────────────────────────

def start_capture(on_chunk_ready, mode='mic'):
    """
    Start continuous audio capture using a producer/consumer queue.
    Recording and processing run in separate threads — no chunks are dropped.

    Args:
        on_chunk_ready (callable): Called with (audio_path: str) for each chunk.
                                   Caller is responsible for deleting the temp file.
        mode (str): 'mic' for microphone, 'system' for system audio loopback.

    Raises:
        RuntimeError: If system audio device is not found.
    """
    global _recording, _record_thread, _process_thread

    if _recording:
        print('[AudioCapture] Already recording. Call stop_capture() first.')
        return

    # Clear any leftover items in queue from previous session
    while not _audio_queue.empty():
        try:
            _audio_queue.get_nowait()
        except queue.Empty:
            break

    # Resolve device
    device_id = None
    if mode == 'system':
        device_id = get_system_audio_device()
        if device_id is None:
            raise RuntimeError(
                'System audio device not found. '
                'Enable Stereo Mix in Windows Sound Settings or install VB-Audio Virtual Cable.'
            )

    _recording = True

    # Start recording thread (producer)
    _record_thread = threading.Thread(
        target=_record_loop,
        args=(device_id,),
        daemon=True
    )
    _record_thread.start()

    # Start processing thread (consumer)
    _process_thread = threading.Thread(
        target=_process_loop,
        args=(on_chunk_ready,),
        daemon=True
    )
    _process_thread.start()

    print(f'[AudioCapture] Started. Mode: {mode} | Chunk: {CHUNK_DURATION}s | Queue-based ✓')


def stop_capture():
    """
    Stop audio capture. Signals both threads to exit cleanly.
    Remaining items in the queue are still processed before the thread exits.
    """
    global _recording
    _recording = False

    # Push a sentinel value to unblock the processing thread if it's waiting
    _audio_queue.put(None)

    print('[AudioCapture] Stop signal sent. Processing remaining queue items...')


# ── Internal Threads ──────────────────────────────────────

def _record_loop(device_id):
    """
    Producer thread — records audio chunks continuously and pushes to queue.
    Never waits for processing. If processing is slow, queue grows but nothing is dropped.
    """
    global _recording
    print('[AudioCapture] Recording thread started.')

    while _recording:
        try:
            # Record one chunk
            audio = sd.rec(
                int(CHUNK_DURATION * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='int16',
                device=device_id
            )
            sd.wait()  # Wait only for THIS chunk to finish recording (not processing)

            if not _recording:
                break

            # Check if audio has actual content (not silence)
            if np.max(np.abs(audio)) < 100:
                print('[AudioCapture] Silent chunk detected — skipping.')
                continue

            # Save to temp file and push to queue immediately
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            wav.write(tmp.name, SAMPLE_RATE, audio)
            tmp.close()

            _audio_queue.put(tmp.name)
            print(f'[AudioCapture] Chunk queued. Queue size: {_audio_queue.qsize()}')

        except Exception as e:
            print(f'[AudioCapture] Recording error: {e}')
            break

    print('[AudioCapture] Recording thread stopped.')


def _process_loop(on_chunk_ready):
    """
    Consumer thread — pulls audio chunks from queue and processes them.
    Runs independently of recording. Processing lag does not affect recording.
    """
    print('[AudioCapture] Processing thread started.')

    while True:
        try:
            # Block until a chunk is available (or sentinel None is received)
            audio_path = _audio_queue.get(timeout=10)

            # None is the stop sentinel
            if audio_path is None:
                break

            # Process the chunk
            try:
                on_chunk_ready(audio_path)
            except Exception as e:
                print(f'[AudioCapture] Processing error: {e}')
            finally:
                # Always clean up temp file
                if audio_path and os.path.exists(audio_path):
                    os.unlink(audio_path)

            _audio_queue.task_done()

        except queue.Empty:
            # No chunks for 10 seconds — check if we should still be running
            if not _recording:
                break
            continue

    print('[AudioCapture] Processing thread stopped.')
```

---

## 5. Updated `test_mic.py`

Replace `backend/test_mic.py` with this updated version that tests the queue properly:

```python
# backend/test_mic.py
# Tests queue-based audio capture for 3 consecutive chunks

from audio_capture import start_capture, stop_capture, get_input_devices
from transcriber import transcribe
from translator import translate
import time, os

print('============================================')
print('  HOTFIX MIC TEST (3 consecutive chunks)')
print('============================================')

print('\n[Devices] Available input devices:')
for d in get_input_devices():
    tag = ' ← SYSTEM AUDIO (loopback)' if d['is_loopback'] else ''
    print(f"  [{d['id']}] {d['name']}{tag}")

print('\n[Test] Speak continuously for 15 seconds...')
print('[Test] You should see 3 captions appear in sequence.\n')

chunk_count = [0]
MAX_CHUNKS = 3

def on_chunk(audio_path):
    chunk_count[0] += 1
    print(f'\n--- Chunk {chunk_count[0]} ---')
    result = transcribe(audio_path)
    transcript = result['text'].strip()
    print(f'[Transcript] {transcript}')

    if transcript:
        translated = translate(transcript, 'en-ta')
        print(f'[Tamil]      {translated}')

    if chunk_count[0] >= MAX_CHUNKS:
        stop_capture()

start_capture(on_chunk, mode='mic')

# Wait long enough for 3 chunks (3 * 4s record + 3 * 4s process + buffer)
time.sleep(35)

print('\n============================================')
if chunk_count[0] >= MAX_CHUNKS:
    print(f'HOTFIX TEST PASSED. {chunk_count[0]} chunks processed without dropping.')
else:
    print(f'WARNING: Only {chunk_count[0]} chunks processed. Expected {MAX_CHUNKS}.')
print('============================================')
```

---

## 6. No Changes Required Elsewhere

| File | Action |
|---|---|
| `backend/audio_capture.py` | ✅ Full rewrite (above) |
| `backend/test_mic.py` | ✅ Replace with updated version (above) |
| `backend/app.py` | ❌ No changes — `start_capture()` API is identical |
| `backend/transcriber.py` | ❌ No changes |
| `backend/translator.py` | ❌ No changes |
| All frontend files | ❌ No changes |

The `start_capture(on_chunk_ready, mode)` signature is **unchanged** — `app.py` calls it the same way and will work immediately with the new implementation.

---

## 7. Acceptance Criteria

| # | Criterion | How to Verify |
|---|---|---|
| AC-01 | `test_mic.py` prints 3 consecutive chunk transcripts | Run script, speak continuously for 15 sec |
| AC-02 | No chunks skipped between first and last | All 3 chunks appear in order |
| AC-03 | Queue size logged per chunk in console | Check console output for "Chunk queued. Queue size: N" |
| AC-04 | Silent chunks are skipped (not sent to Whisper) | Stay silent for one chunk — console shows "Silent chunk detected" |
| AC-05 | `stop_capture()` cleanly stops both threads | Call stop, confirm both thread stopped messages appear |
| AC-06 | `get_input_devices()` lists all devices with loopback tagged | Run diagnostic command in Section 3 |
| AC-07 | System audio fails with helpful error if Stereo Mix disabled | Disable Stereo Mix, try system mode — readable error shown |

---

## 8. Handoff Notes to Agent

> **READ THIS BEFORE STARTING.**

- **Only rewrite `audio_capture.py` and `test_mic.py`.** Do not touch any other file.
- The `start_capture(on_chunk_ready, mode)` function signature must remain identical — `app.py` depends on it.
- The `on_chunk_ready` callback must NOT delete the temp file — `_process_loop` handles deletion in its `finally` block. Do not add `os.unlink()` inside the callback in `app.py`.
- The silence detection threshold (`np.max(np.abs(audio)) < 100`) skips near-silent chunks so Whisper doesn't waste time transcribing silence. This value may need tuning — if real speech is being skipped, lower it to `50`. If too much silence is getting through, raise it to `200`.
- The `None` sentinel in the queue is how `stop_capture()` signals the processing thread to exit. Do not remove it.
- After the fix, run `test_mic.py` and confirm 3 consecutive chunks all produce transcripts before testing through the full UI.
- Commit message: `fix(audio): queue-based capture to prevent chunk dropping, improved system audio detection`

---

*End of Hotfix PRD — Caption Generator with Translation Project*
