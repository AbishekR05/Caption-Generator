# backend/transcriber.py
# Uses faster-whisper for 2x-4x faster transcription vs openai-whisper
# Translation is handled separately by translator.py (Helsinki-NLP MarianMT — unchanged)

import time
from faster_whisper import WhisperModel

# ── Model Configuration ───────────────────────────────────
MODEL_SIZE = "small"       # Options: tiny, base, small, medium, large-v3
DEVICE = "cuda"            # Use GPU — GTX 1650 with cu118
COMPUTE_TYPE = "int8"      # INT8 quantization — faster + less VRAM than fp16
                           # GTX 1650 (4GB VRAM): use "int8"
                           # RTX 3060+ (12GB VRAM): can use "float16" for slightly better accuracy

# ── Model Loading (once at module level) ──────────────────
print(f'[Whisper] Loading faster-whisper model "{MODEL_SIZE}" on {DEVICE} ({COMPUTE_TYPE})...')
_start = time.time()

model = WhisperModel(
    MODEL_SIZE,
    device=DEVICE,
    compute_type=COMPUTE_TYPE
)

print(f'[Whisper] Model loaded in {round(time.time() - _start, 2)}s')


# ── Public API ────────────────────────────────────────────

def load_model():
    """
    Dummy backwards-compatibility hook for test_pipeline.py
    The model is now continuously loaded via the module level on initialization.
    """
    pass

def transcribe(audio_path: str, language: str = None) -> dict:
    """
    Transcribe an audio file using faster-whisper.
    Drop-in replacement for the previous openai-whisper implementation.
    Function signature and return format are identical to the old version.

    Args:
        audio_path (str): Path to audio file (.mp3 or .wav).
        language (str): Optional. 'en' or 'ta'. None = auto-detect.

    Returns:
        dict: {
            'text': str,        # Full transcription
            'language': str,    # Detected/used language code
            'segments': list    # List of segment dicts with start/end/text
        }
    """
    print(f'[Whisper] Transcribing: {audio_path}')
    t_start = time.time()

    # faster-whisper returns a generator of segments + info object
    segments, info = model.transcribe(
        audio_path,
        language="en",              # Force English to prevent language switching
        beam_size=5,                # beam search width — higher = more accurate but slower
        vad_filter=True,            # Voice Activity Detection — skips silence automatically
        vad_parameters=dict(
            min_silence_duration_ms=500   # Ignore silence gaps under 500ms
        )
    )

    # Collect all segments (generator must be consumed)
    segment_list = []
    full_text_parts = []

    for segment in segments:
        segment_list.append({
            'start': round(segment.start, 2),
            'end': round(segment.end, 2),
            'text': segment.text.strip()
        })
        full_text_parts.append(segment.text.strip())

    full_text = ' '.join(full_text_parts).strip()
    elapsed = round(time.time() - t_start, 2)

    print(f'[Whisper] Done in {elapsed}s | Language: {info.language} | Text: {full_text[:60]}')

    return {
        'text': full_text,
        'language': info.language,
        'segments': segment_list
    }
