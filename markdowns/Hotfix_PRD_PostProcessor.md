# HOTFIX PRD — Profanity Censoring + Sentiment Analysis
### Caption Generator with Translation — Desktop App
**Type:** Feature Hotfix (additive — no existing code broken)
**Prepared For:** Antigravity (Autonomous Coding Agent)
**Scope:** New `backend/post_processor.py` + updates to `app.py`, `App.jsx`, `CaptionPanel.jsx`, `overlay.html`
**Priority:** Medium — optional feature toggles, must be lag-free

---

## 1. Overview

Two new optional features are added as toggleable modules, similar to how translation works:

| Feature | Toggle | Default | Processing time |
|---|---|---|---|
| Profanity censoring | ON/OFF switch in UI | OFF | < 1ms (string matching) |
| Sentiment analysis | ON/OFF switch in UI | OFF | < 5ms (VADER rule-based) |

Both features:
- Apply to the **English transcript only** (not Tamil translation)
- Appear in **both the main app CaptionPanel and the overlay window**
- Are processed **after** Whisper transcription, before emitting to frontend
- Add **zero meaningful latency** — both run on CPU in under 5ms combined

---

## 2. Why VADER for Sentiment (Not a Transformer)

VADER (Valence Aware Dictionary and sEntiment Reasoner) is the correct choice here:

- Rule-based — no GPU, no model loading time, no warm-up
- Processes a sentence in < 1ms
- Specifically tuned for spoken/conversational English
- Already part of the `nltk` library — no extra large downloads
- Accuracy is good enough for color-coding captions (positive/negative/neutral)

Do NOT use transformer-based sentiment models (like `cardiffnlp/twitter-roberta`) — they would add 200-500ms per chunk which defeats the purpose.

---

## 3. Files Changed

| File | Action | Notes |
|---|---|---|
| `backend/post_processor.py` | **Create** | Profanity + sentiment logic |
| `backend/app.py` | **Modify** | Pass flags to post_processor, include sentiment in emit |
| `electron/renderer/src/App.jsx` | **Modify** | Add censorEnabled, sentimentEnabled state |
| `electron/renderer/src/components/Controls.jsx` | **Modify** | Add two new toggle switches |
| `electron/renderer/src/components/CaptionPanel.jsx` | **Modify** | Apply sentiment color to transcript text |
| `electron/overlay.html` | **Modify** | Apply sentiment color to overlay transcript |
| `requirements.txt` | **Modify** | Add nltk, better-profanity |
| All other files | **No changes** | Leave untouched |

---

## 4. Install Dependencies

```bash
pip install nltk better-profanity
```

After installing `nltk`, the VADER lexicon must be downloaded once:

```python
import nltk
nltk.download('vader_lexicon')
```

Add this to `requirements.txt`:
```
nltk>=3.8.0
better-profanity>=0.7.0
```

> **AGENT NOTE:** The `nltk.download('vader_lexicon')` call only needs to happen once — it downloads a small ~1MB file to `~/nltk_data/`. Add this download call inside `post_processor.py` at module level with a try/except so it only downloads if not already present. It must NOT be called on every request.

---

## 5. `backend/post_processor.py` — Full Implementation

```python
# backend/post_processor.py
# Profanity censoring and sentiment analysis for caption text.
# Both operations are CPU-based and complete in under 5ms combined.
# Must not be called if both features are disabled — check flags before calling.

import time
import nltk
from better_profanity import profanity
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# ── One-time setup at module level ────────────────────────
# Download VADER lexicon if not already present
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    print('[PostProcessor] Downloading VADER lexicon (one time)...')
    nltk.download('vader_lexicon', quiet=True)

# Load profanity filter
profanity.load_censor_words()

# Load VADER sentiment analyzer
_sentiment_analyzer = SentimentIntensityAnalyzer()

print('[PostProcessor] Ready — profanity filter + VADER sentiment loaded.')


# ── Sentiment Labels ──────────────────────────────────────
SENTIMENT_POSITIVE = 'positive'
SENTIMENT_NEGATIVE = 'negative'
SENTIMENT_NEUTRAL  = 'neutral'

# VADER compound score thresholds (standard values)
POSITIVE_THRESHOLD =  0.05
NEGATIVE_THRESHOLD = -0.05


# ── Public API ────────────────────────────────────────────

def censor(text: str) -> str:
    """
    Replace profane words with censored versions.
    e.g. "fuck" → "f**k", "shit" → "s**t"

    Args:
        text (str): Raw transcript text

    Returns:
        str: Censored text
    """
    return profanity.censor(text, censor_char='*')


def analyze_sentiment(text: str) -> dict:
    """
    Analyze the sentiment of a text string using VADER.

    Args:
        text (str): Transcript text (post-censoring if censoring is on)

    Returns:
        dict: {
            'label': 'positive' | 'negative' | 'neutral',
            'score': float,   # VADER compound score (-1.0 to 1.0)
            'color': str      # hex color for UI rendering
        }
    """
    scores = _sentiment_analyzer.polarity_scores(text)
    compound = scores['compound']

    if compound >= POSITIVE_THRESHOLD:
        return {'label': SENTIMENT_POSITIVE, 'score': compound, 'color': '#4ade80'}  # green-400
    elif compound <= NEGATIVE_THRESHOLD:
        return {'label': SENTIMENT_NEGATIVE, 'score': compound, 'color': '#f87171'}  # red-400
    else:
        return {'label': SENTIMENT_NEUTRAL,  'score': compound, 'color': '#ffffff'}  # white


def process(text: str, censor_enabled: bool = False, sentiment_enabled: bool = False) -> dict:
    """
    Main entry point — run enabled post-processing steps on transcript text.
    Returns processed text and sentiment data.

    Args:
        text (str): Raw transcript from Whisper
        censor_enabled (bool): Apply profanity censoring
        sentiment_enabled (bool): Analyze sentiment

    Returns:
        dict: {
            'text': str,               # processed transcript (censored if enabled)
            'sentiment': dict | None   # sentiment result or None if disabled
        }
    """
    t_start = time.time()

    processed_text = text

    # Step 1 — Profanity censoring
    if censor_enabled:
        processed_text = censor(processed_text)

    # Step 2 — Sentiment analysis (on processed text)
    sentiment = None
    if sentiment_enabled:
        sentiment = analyze_sentiment(processed_text)

    elapsed = round((time.time() - t_start) * 1000, 2)
    print(f'[PostProcessor] Done in {elapsed}ms | censor:{censor_enabled} | sentiment:{sentiment["label"] if sentiment else "off"}')

    return {
        'text': processed_text,
        'sentiment': sentiment
    }
```

---

## 6. `backend/app.py` — Updates

### 6.1 Import post_processor

Add at the top of `app.py`:
```python
from post_processor import process as post_process
```

### 6.2 Update `handle_start_mic` SocketIO event

Add `censor` and `sentiment` flags from the incoming data:

```python
@socketio.on('start_mic')
def handle_start_mic(data):
    mode             = data.get('mode', 'mic')
    direction        = data.get('direction', 'en-ta')
    translate_enabled   = data.get('translate', False)
    censor_enabled      = data.get('censor', False)       # NEW
    sentiment_enabled   = data.get('sentiment', False)    # NEW

    def on_chunk(audio_path):
        try:
            result = transcribe(audio_path)
            transcript = result['text'].strip()
            if not transcript:
                return

            # Post-processing (censoring + sentiment) — runs in < 5ms
            post = post_process(
                transcript,
                censor_enabled=censor_enabled,
                sentiment_enabled=sentiment_enabled
            )

            translated = None
            if translate_enabled:
                translated = translate(post['text'], direction)

            emit_caption(
                text=post['text'],
                translated=translated,
                sentiment=post['sentiment']   # NEW — None if disabled
            )

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
```

### 6.3 Update `emit_caption()`

```python
def emit_caption(text, translated=None, sentiment=None):
    socketio.emit('caption_update', {
        'transcript': text,
        'translated': translated,
        'sentiment': sentiment,    # NEW — { label, score, color } or None
        'timestamp': time.time()
    })
    label = sentiment['label'] if sentiment else 'off'
    print(f'[SocketIO] caption_update | sentiment:{label} | {text[:40]}')
```

### 6.4 Update `/transcribe-and-translate` endpoint

Add `censor` and `sentiment` support to the file upload endpoint:

```python
@app.route('/transcribe-and-translate', methods=['POST'])
def transcribe_and_translate():
    # ... existing file handling and transcription ...

    censor_enabled    = request.form.get('censor', 'false').lower() == 'true'
    sentiment_enabled = request.form.get('sentiment', 'false').lower() == 'true'
    translate_enabled = request.form.get('translate', 'false').lower() == 'true'

    result     = transcribe(tmp.name)
    transcript = result['text'].strip()

    # Post-process
    post = post_process(transcript, censor_enabled, sentiment_enabled)

    translated = None
    if translate_enabled:
        translated = translate(post['text'], direction)

    return jsonify({
        'success': True,
        'transcript': post['text'],
        'translated': translated,
        'sentiment': post['sentiment'],
        # ... existing timing fields ...
    })
```

---

## 7. React Frontend Updates

### 7.1 New State in `App.jsx`

```javascript
const [censorEnabled,    setCensorEnabled]    = useState(false)
const [sentimentEnabled, setSentimentEnabled] = useState(false)
const [sentiment,        setSentiment]        = useState(null)
// sentiment shape: { label: 'positive'|'negative'|'neutral', score: float, color: '#hex' } | null
```

**Updated `handleMicToggle`:**
```javascript
socket.emit('start_mic', {
    mode,
    direction,
    translate:  translateEnabled,
    censor:     censorEnabled,      // NEW
    sentiment:  sentimentEnabled    // NEW
})
```

**Updated `caption_update` handler:**
```javascript
socket.on('caption_update', (data) => {
    setTranscript(data.transcript)
    setTranslated(data.translated || '')
    setSentiment(data.sentiment || null)   // NEW

    if (window.electronAPI) {
        window.electronAPI.sendCaption({
            transcript: data.transcript,
            translated: data.translated || '',
            sentiment:  data.sentiment || null   // NEW
        })
    }
})
```

**Updated `handleFileUpload`:**
```javascript
formData.append('censor',    censorEnabled.toString())
formData.append('sentiment', sentimentEnabled.toString())
```
After response:
```javascript
setSentiment(res.data.sentiment || null)
```

**Pass new props to Controls:**
```jsx
<Controls
    ...
    censorEnabled={censorEnabled}
    onCensorToggle={() => setCensorEnabled(prev => !prev)}
    sentimentEnabled={sentimentEnabled}
    onSentimentToggle={() => setSentimentEnabled(prev => !prev)}
/>
```

**Pass sentiment to CaptionPanel:**
```jsx
<CaptionPanel
    ...
    sentiment={sentiment}
/>
```

---

### 7.2 `Controls.jsx` — Two New Toggles

Add below the existing translation toggle:

```jsx
{/* Profanity Censor Toggle */}
<div className="flex items-center justify-between gap-4">
    <span className="text-sm text-gray-300">🤬 Censor profanity</span>
    <button
        onClick={onCensorToggle}
        className={`w-12 h-6 rounded-full transition-colors ${
            censorEnabled ? 'bg-indigo-500' : 'bg-gray-600'
        }`}
        title="Replace profane words with asterisks"
    >
        <div className={`w-5 h-5 bg-white rounded-full shadow transition-transform mx-0.5 ${
            censorEnabled ? 'translate-x-6' : 'translate-x-0'
        }`}/>
    </button>
</div>

{/* Sentiment Analysis Toggle */}
<div className="flex items-center justify-between gap-4">
    <span className="text-sm text-gray-300">💬 Sentiment colors</span>
    <button
        onClick={onSentimentToggle}
        className={`w-12 h-6 rounded-full transition-colors ${
            sentimentEnabled ? 'bg-indigo-500' : 'bg-gray-600'
        }`}
        title="Color captions: green=positive, red=negative, white=neutral"
    >
        <div className={`w-5 h-5 bg-white rounded-full shadow transition-transform mx-0.5 ${
            sentimentEnabled ? 'translate-x-6' : 'translate-x-0'
        }`}/>
    </button>
</div>
```

**Updated Controls props:**
```javascript
Controls.propTypes = {
    // ... existing props ...
    censorEnabled:    PropTypes.bool,
    onCensorToggle:   PropTypes.func,
    sentimentEnabled: PropTypes.bool,
    onSentimentToggle: PropTypes.func
}
```

---

### 7.3 `CaptionPanel.jsx` — Sentiment Color

Apply the sentiment color to the English transcript text:

```jsx
const CaptionPanel = ({ transcript, translated, translateEnabled, isLoading, sentiment }) => {

    // Color from sentiment, default white
    const transcriptColor = sentiment?.color || '#ffffff'

    return (
        <div className="...">
            <div className="...">
                <h3 className="text-gray-400 text-sm mb-2">
                    English
                    {sentiment && (
                        <span className="ml-2 text-xs px-2 py-0.5 rounded-full"
                            style={{ backgroundColor: sentiment.color + '22', color: sentiment.color }}>
                            {sentiment.label}
                        </span>
                    )}
                </h3>

                <p
                    className="text-lg font-medium transition-colors duration-300"
                    style={{ color: transcriptColor }}   // ← sentiment color applied here
                >
                    {transcript || 'Subtitles will appear here...'}
                </p>
            </div>

            {/* Tamil panel — unchanged */}
            {translateEnabled && (
                <div className="...">
                    <h3 className="text-gray-400 text-sm mb-2">Tamil</h3>
                    <p style={{ fontFamily: 'Noto Sans Tamil, sans-serif', color: '#a5f3fc' }}>
                        {translated || '...'}
                    </p>
                </div>
            )}
        </div>
    )
}
```

> **AGENT NOTE:** The sentiment color applies to the English transcript ONLY — never to the Tamil translation text. Tamil always stays `#a5f3fc` (light blue) regardless of sentiment.

---

## 8. `overlay.html` — Sentiment Color

Update the `onCaption` handler in `overlay.html` to apply sentiment color:

```javascript
window.electronAPI.onCaption((data) => {
    placeholderEl.style.display = 'none'

    // Apply sentiment color to English transcript
    const color = data.sentiment?.color || '#ffffff'
    transcriptEl.style.color = color
    transcriptEl.style.textShadow = `
        -1px -1px 0 #000,
         1px -1px 0 #000,
        -1px  1px 0 #000,
         1px  1px 0 #000,
         0px  2px 4px rgba(0,0,0,0.8)
    `
    transcriptEl.textContent = data.transcript || ''

    // Tamil — always light blue, unaffected by sentiment
    if (data.translated) {
        translatedEl.textContent = data.translated
        translatedEl.style.display = 'block'
    } else {
        translatedEl.style.display = 'none'
    }
})
```

---

## 9. Sentiment Color Reference

| Sentiment | VADER compound score | Text color | Hex |
|---|---|---|---|
| Positive | ≥ 0.05 | Green | `#4ade80` |
| Negative | ≤ -0.05 | Red | `#f87171` |
| Neutral | between -0.05 and 0.05 | White | `#ffffff` |

**Examples from movie audio:**
- *"This is absolutely wonderful, I love it!"* → 🟢 positive
- *"He was murdered in cold blood."* → 🔴 negative
- *"She walked into the room and sat down."* → ⚪ neutral

---

## 10. Testing

Run a quick standalone test before integrating with the full app:

```python
# backend/test_post_processor.py

from post_processor import process

tests = [
    ("This is absolutely wonderful, I love it!", True, True),
    ("He was brutally murdered in cold blood.", True, True),
    ("She walked into the room and sat down.", True, True),
    ("What the fuck is going on here?", True, True),
    ("Shit, we need to get out now.", True, True),
]

print('============================================')
print('  POST PROCESSOR TEST')
print('============================================')

for text, censor, sentiment in tests:
    result = process(text, censor_enabled=censor, sentiment_enabled=sentiment)
    s = result['sentiment']
    print(f'\nInput:     {text}')
    print(f'Censored:  {result["text"]}')
    print(f'Sentiment: {s["label"]} (score: {s["score"]}) — color: {s["color"]}')

print('\n============================================')
print('POST PROCESSOR TEST COMPLETE.')
print('============================================')
```

Expected output:
```
Input:     What the fuck is going on here?
Censored:  What the f**k is going on here?
Sentiment: negative (score: -0.34) — color: #f87171

Input:     This is absolutely wonderful, I love it!
Censored:  This is absolutely wonderful, I love it!
Sentiment: positive (score: 0.77) — color: #4ade80
```

---

## 11. Acceptance Criteria

| # | Criterion | How to Verify |
|---|---|---|
| AC-01 | `test_post_processor.py` passes all cases | Run script |
| AC-02 | Profanity toggle OFF by default | Check UI on launch |
| AC-03 | Profanity toggle ON censors words in captions | Say/play audio with profanity |
| AC-04 | Censored text appears in overlay too | Check overlay while toggle is ON |
| AC-05 | Sentiment toggle OFF by default | Check UI on launch |
| AC-06 | Positive sentence → green text in CaptionPanel | Play positive audio |
| AC-07 | Negative sentence → red text in CaptionPanel | Play negative audio |
| AC-08 | Neutral sentence → white text in CaptionPanel | Play neutral audio |
| AC-09 | Sentiment color applies in overlay too | Check overlay during live capture |
| AC-10 | Tamil translation text is NEVER colored by sentiment | Toggle sentiment ON, check Tamil text stays light blue |
| AC-11 | Sentiment label badge shown next to "English" header | Check CaptionPanel header area |
| AC-12 | No noticeable latency added | Compare chunk timing before and after |
| AC-13 | Both toggles work independently | Toggle one on, other off — both combinations |

---

## 12. Handoff Notes to Agent

> **READ THIS BEFORE STARTING.**

- **Only add new code — do not refactor existing working code.** `transcriber.py`, `translator.py`, `audio_capture.py` must not be touched.
- `post_processor.py` models load at **module level** — not inside functions. VADER and the profanity filter load once when `app.py` imports `post_processor`. This is critical for performance.
- `nltk.download('vader_lexicon')` must be wrapped in a try/except that only downloads if not already present — never download on every request.
- `better-profanity` censors full words by default. The censor character is set to `'*'` — so "fuck" becomes "f**k" not "****". This is intentional.
- Sentiment color applies to **English transcript text only** — never Tamil. This must be enforced in both `CaptionPanel.jsx` and `overlay.html`.
- Both features default to **OFF** — same pattern as translation toggle.
- Run `test_post_processor.py` first before testing through the full UI.
- Commit message: `feat(post-processor): profanity censoring + sentiment analysis with color coding`

---

*End of Hotfix PRD — Profanity Censoring + Sentiment Analysis*
