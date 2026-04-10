from transformers import AutoTokenizer, MarianMTModel
import time
import sys

# Module level models and tokenizers to avoid reloading
_models = {}
_tokenizers = {}

def load_models():
    """Load BOTH models and tokenizers at module level."""
    global _models, _tokenizers
    if "en-ta" in _models and "ta-en" in _models:
        return
        
    print("[Translator] Loading en-ta model (Helsinki-NLP/opus-mt-en-mul)...")
    start_eta = time.time()
    _tokenizers["en-ta"] = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-mul")
    _models["en-ta"] = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-mul")
    
    print("[Translator] Loading ta-en model (Helsinki-NLP/opus-mt-mul-en)...")
    # For some reason, the exact model name might differ slightly depending on huggingface hub state,
    # but the PRD strictly specified "Helsinki-NLP/opus-mt-ta-en". Since that repo doesn't exist, we use mul-en
    _tokenizers["ta-en"] = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-mul-en")
    _models["ta-en"] = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-mul-en")
    
    print("[Translator] Models loaded.")

def translate(text: str, direction: str = 'en-ta') -> str:
    """
    Translate text between English and Tamil.

    Args:
        text (str): Input text to translate.
        direction (str): 'en-ta' for English to Tamil, 'ta-en' for Tamil to English.

    Returns:
        str: Translated text.
    """
    if direction not in ["en-ta", "ta-en"]:
        raise ValueError(f"[Translator] Error: Direction must be 'en-ta' or 'ta-en'. Got '{direction}'.")
        
    load_models()
    
    tokenizer = _tokenizers[direction]
    model = _models[direction]
    
    source_lang, target_lang = direction.split('-')
    
    print(f"[Translator] Translating {direction}: '{text}'")
    start_time = time.time()
    
    # Prepend target language token for multilingual models
    if direction == "en-ta":
        text = f">>tam<< {text}"
    
    # Tokenize with safety boundaries
    encoded = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
    
    # Generate translation
    translated = model.generate(**encoded)
    
    # Decode
    result = tokenizer.decode(translated[0], skip_special_tokens=True)
    
    trans_time = time.time() - start_time
    
    print(f"[Translator] Result: '{result}'")
    print(f"[Translator] Done in {trans_time:.1f}s")
    
    return result
