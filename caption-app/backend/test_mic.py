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
