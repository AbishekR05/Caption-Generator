# HOTFIX PRD — Swap openai-whisper to faster-whisper
### Caption Generator with Translation — Desktop App
**Type:** Hotfix
**Prepared For:** Antigravity (Autonomous Coding Agent)
**Scope:** `backend/transcriber.py` ONLY + `requirements.txt` update
**Priority:** Performance improvement — reduces caption latency by 2x-4x

---

## 1. Overview

| Field | Value |
|---|---|
| What's changing | Speech-to-text engine: `openai-whisper` → `faster-whisper` |
| Why | faster-whisper is 2x-4x faster with identical accuracy, uses less VRAM |
| Files changed | `backend/transcriber.py` (rewrite), `requirements.txt` (update) |
| Files NOT changed | Everything else — `translator.py`, `app.py`, `audio_capture.py`, all frontend files |
| Translation model | Helsinki-NLP MarianMT — completely unchanged, not related to this hotfix |

---

## 2. What Is NOT Changing

> **AGENT: Read this first.**

| Component | Status | Notes |
|---|---|---|
| `translator.py` | ❌ Do not touch | Helsinki-NLP `opus-mt-en-mul` + `opus-mt-mul-en` stays exactly as is |
| `>>tam<<` token fix | ❌ Do not touch | Lives in `translator.py`, unrelated to Whisper |
| `app.py` | ❌ Do not touch | Calls `transcribe()` — function signature unchanged |
| `audio_capture.py` | ❌ Do not touch | Queue-based capture is separate from transcription |
| All frontend files | ❌ Do not touch | No frontend changes needed |
| `requirements.txt` | ✅ Update only | Remove `openai-whisper`, add `faster-whisper` |

---

## 3. Uninstall openai-whisper

Run these commands in the project venv before making any code changes:

```bash
cd caption-app
venv\Scripts\activate
pip uninstall openai-whisper -y
```

Then delete the cached model files to free up disk space (~500MB):

```bash
rmdir /s /q C:\Users\karth\.cache\whisper
```

> **AGENT NOTE:** Only delete the `whisper` folder inside `.cache`. Do NOT delete `.cache\huggingface` — that contains the Helsinki-NLP translation models which are still needed.

---

## 4. Install faster-whisper

```bash
pip install faster-whisper
```

faster-whisper uses CTranslate2 for optimized inference. It automatically uses the existing CUDA installation (cu118 on this machine) — no additional CUDA setup needed.

---

## 5. Update `requirements.txt`

Make the following change in `requirements.txt`:

Remove:
```
openai-whisper>=20231117
```

Add:
```
faster-whisper>=1.0.0
```

The file should look like this in the ML section:

```
# ML / AI
faster-whisper>=1.0.0        # Replaces openai-whisper — 2x-4x faster, same accuracy
transformers>=4.35.0          # Helsinki-NLP MarianMT translation — unchanged
sentencepiece>=0.1.99
sacremoses>=0.0.53
```

---

## 6. Rewrite `backend/transcriber.py`

Replace the entire contents of `backend/transcriber.py` with the following:

```python
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
        language=language,          # None = auto-detect
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
```

---

## 7. Key Differences from Old Implementation

| Aspect | openai-whisper (old) | faster-whisper (new) |
|---|---|---|
| Import | `import whisper` | `from faster_whisper import WhisperModel` |
| Model load | `whisper.load_model("small", device="cuda")` | `WhisperModel("small", device="cuda", compute_type="int8")` |
| Transcribe call | `model.transcribe(path, fp16=True)` | `model.transcribe(path, beam_size=5, vad_filter=True)` |
| Output | Single dict with `text` key | Generator of segments + info object |
| Silence handling | Manual (done in audio_capture.py) | Built-in VAD filter ✅ |
| Speed | Baseline | 2x-4x faster ✅ |
| VRAM | ~2GB for small | ~1GB for small (int8) ✅ |
| Return format | Same `{'text', 'language', 'segments'}` dict | Same ✅ |

> **AGENT NOTE:** The `segments` generator from faster-whisper **must be fully consumed** before the function returns — hence the `for segment in segments` loop. If you try to return the generator directly, it will be empty by the time the caller reads it.

---

## 8. VAD Filter Note

faster-whisper has a built-in **Voice Activity Detection (VAD)** filter (`vad_filter=True`). This automatically skips silent portions of audio before sending to the model. This means:

- The silence detection in `audio_capture.py` (`np.max(np.abs(audio)) < 100`) is now a first-pass filter
- VAD in faster-whisper is a second, more accurate pass
- Together they ensure Whisper never wastes time on silence
- Do NOT remove the silence check in `audio_capture.py` — both layers work together

---

## 9. Model Size Guide (for reference — do not change this week)

| Model | VRAM (int8) | Speed vs small | Accuracy | Best for |
|---|---|---|---|---|
| `tiny` | ~0.5GB | 2x faster | Lower | Testing only |
| `base` | ~0.7GB | 1.5x faster | Decent | Low-end hardware |
| `small` | ~1GB | Baseline | Good | ✅ GTX 1650 (this machine) |
| `medium` | ~2.5GB | 0.6x | Better | ✅ RTX 3060 (friend's machine) |
| `large-v3` | ~4GB | 0.3x | Best | RTX 3080+ |

> **For the friend with RTX 3060:** Change `MODEL_SIZE = "small"` to `MODEL_SIZE = "medium"` in their copy of `transcriber.py` for better accuracy with still-fast performance.

---

## 10. Test After Implementation

Run the existing test scripts to confirm nothing broke:

```bash
# Test 1 — pipeline test (transcription + translation)
python backend/test_pipeline.py

# Test 2 — API test (requires Flask server running)
python backend/app.py          # Terminal 1
python backend/test_api.py     # Terminal 2

# Test 3 — mic test
python backend/test_mic.py
```

All three must pass with identical output to before. The only difference in console output will be the loading message changing from:

```
[Whisper] Loading model 'small' on cuda...
```

To:
```
[Whisper] Loading faster-whisper model "small" on cuda (int8)...
```

---

## 11. Acceptance Criteria

| # | Criterion | How to Verify |
|---|---|---|
| AC-01 | `openai-whisper` is uninstalled | `pip show openai-whisper` returns "not found" |
| AC-02 | `faster-whisper` is installed | `pip show faster-whisper` returns version info |
| AC-03 | Model loads on CUDA without error | Console shows model loaded message |
| AC-04 | `test_pipeline.py` still passes | ALL TESTS PASSED printed |
| AC-05 | `test_api.py` still passes | ALL TESTS PASSED printed |
| AC-06 | Transcription is noticeably faster | Compare chunk processing time in console logs |
| AC-07 | `translator.py` is completely unchanged | Git diff shows no changes to translator.py |
| AC-08 | `app.py` is completely unchanged | Git diff shows no changes to app.py |

---

## 12. Handoff Notes to Agent

> **READ THIS BEFORE STARTING.**

- **Only rewrite `transcriber.py` and update `requirements.txt`.** Do not touch anything else.
- The `transcribe(audio_path, language)` function signature must stay **identical** — `app.py` and `test_pipeline.py` call it and cannot change.
- The return dict must have the same keys: `text`, `language`, `segments` — same as before.
- The segments generator from `model.transcribe()` **must be consumed in a loop** — it cannot be returned directly.
- `vad_filter=True` replaces the need for manual silence detection inside the transcriber — but do NOT remove the silence check in `audio_capture.py`.
- Do not change `MODEL_SIZE` — keep it as `"small"` for the GTX 1650.
- Translation is handled by `translator.py` using Helsinki-NLP MarianMT models — this is completely separate from Whisper and must not be touched.
- Commit message: `fix(transcriber): swap openai-whisper to faster-whisper for 2x-4x speed improvement`

---

*End of Hotfix PRD — faster-whisper swap*
