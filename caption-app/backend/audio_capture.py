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

def get_mic_device():
    """Auto-detect microphone — never relies on system default."""
    for d in get_input_devices():
        if not d['is_loopback']:
            name_lower = d['name'].lower()
            # Prefer real mic over Sound Mapper
            if any(kw in name_lower for kw in ['microphone', 'mic', 'input']):
                if 'sound mapper' not in name_lower and 'primary' not in name_lower:
                    print(f"[AudioCapture] Mic device found: '{d['name']}' (id: {d['id']})")
                    return d['id']
    # Fallback to system default
    print('[AudioCapture] No specific mic found — using system default.')
    return None


# ── Public API ────────────────────────────────────────────

def start_capture(on_chunk_ready, mode='mic'):
    """
    Start continuous audio capture using a producer/consumer queue.
    Recording and processing run in separate threads — no chunks are dropped.
    """
    global _recording, _record_thread, _process_thread

    # Ensure previous recording thread completely terminates to avoid PaErrorCode crashes
    if _record_thread and _record_thread.is_alive():
        print('[AudioCapture] Waiting for previous recording thread to terminate safely...')
        _recording = False
        sd.stop()
        _record_thread.join(timeout=5)

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
    if mode == 'mic':
        device_id = get_mic_device()   # explicit — not None
    elif mode == 'system':
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
    if not _recording:
        return
        
    _recording = False
    try:
        sd.stop() # Aborts current sd.rec() immediately preventing 4s hang
    except Exception:
        pass

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

            # Extremely high silence sensitivity to prevent clipping valid microphones natively
            if np.max(np.abs(audio)) < 5:
                # print('[AudioCapture] Absolute silence detected — skipping.')
                continue

            # Save to temp file and push to queue immediately
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            wav.write(tmp.name, SAMPLE_RATE, audio)
            tmp.close()

            _audio_queue.put(tmp.name)
            # print(f'[AudioCapture] Chunk queued. Queue size: {_audio_queue.qsize()}')

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
