import sys
import torch
from transcriber import load_model as load_transcriber_model, transcribe
from translator import load_models as load_translator_models, translate

def run_tests():
    print("=" * 44)
    print("  WEEK 1 PIPELINE TEST")
    print("=" * 44)
    
    # 1. Load Whisper model and confirm it is on CUDA.
    try:
        load_transcriber_model()
        cuda_status = f"PASS ({torch.cuda.get_device_name(0)})"
    except Exception as e:
        cuda_status = f"FAIL (Error: {e})"
        print(f"\n[TEST 1] CUDA Available      : {cuda_status}")
        sys.exit(1)

        
    # 2. Load both Helsinki-NLP translation models.
    try:
        load_translator_models()
        translator_status = "PASS"
    except Exception as e:
        translator_status = f"FAIL (Error: {e})"
        print(f"\n[TEST 2] Load Translators  : {translator_status}")
        sys.exit(1)
        
    print("\n" + "-" * 44)
    
    print(f"[TEST 1] CUDA Available      : {cuda_status}")
    
    # 3. Transcribe test audio using Whisper
    import os
    audio_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "test_audio.mp3")
    try:
        transcription_result = transcribe(audio_path)
        transcript_text = transcription_result['text']
        print(f"[TEST 2] Whisper Transcribe  : PASS\n         Result: '{transcript_text}'")
    except Exception as e:
        print(f"[TEST 2] Whisper Transcribe  : FAIL (Error: {e})")
        sys.exit(1)
        
    # 5. Translate transcription EN to TA
    try:
        ta_translation = translate(transcript_text, direction="en-ta")
        print(f"[TEST 3] EN->TA Translation  : PASS\n         Result: '{ta_translation}'")
    except Exception as e:
        print(f"[TEST 3] EN->TA Translation  : FAIL (Error: {e})")
        sys.exit(1)
        
    # Translate back TA to EN to verify the pipeline
    try:
        en_translation = translate(ta_translation, direction="ta-en")
        print(f"[TEST 4] TA->EN Translation  : PASS\n         Result: '{en_translation}'")
    except Exception as e:
        print(f"[TEST 4] TA->EN Translation  : FAIL (Error: {e})")
        sys.exit(1)
        
    print("-" * 44)
    print("ALL TESTS PASSED. Week 1 complete.")
    print("=" * 44)

if __name__ == "__main__":
    run_tests()
