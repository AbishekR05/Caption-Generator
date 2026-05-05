# backend/post_processor.py
# Profanity censoring and sentiment analysis for caption text.
# Both operations are CPU-based and complete in under 5ms combined.
# Must not be called if both features are disabled — check flags before calling.

import time
import re
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
    Replace profane words with censored versions leaving the first and last letters intact.
    e.g. "fuck" → "f**k", "bitch" → "b***h"

    Args:
        text (str): Raw transcript text

    Returns:
        str: Censored text
    """
    def _replace(match):
        word = match.group(0)
        # Check if this specific word is profane
        if profanity.contains_profanity(word.lower()):
            if len(word) > 2:
                return word[0] + '*' * (len(word) - 2) + word[-1]
            return '*' * len(word)
        return word
        
    return re.sub(r'\b[a-zA-Z]+\b', _replace, text)


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
