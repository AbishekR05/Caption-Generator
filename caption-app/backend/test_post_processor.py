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
