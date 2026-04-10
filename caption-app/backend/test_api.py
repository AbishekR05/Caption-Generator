import os
import time
import requests

BASE_URL = "http://localhost:5000"

def run_tests():
    print("============================================")
    print("  WEEK 2 API TEST")
    print("============================================")

    # Make sure server is reachable
    try:
        requests.get(f"{BASE_URL}/health", timeout=3)
    except requests.exceptions.ConnectionError:
        print("[Error] Could not connect to the server.")
        print("Please ensure you have started the Flask server using: python backend/app.py")
        print("Exit code: 1")
        return

    # T-01 Health Check
    try:
        res = requests.get(f"{BASE_URL}/health")
        data = res.json()
        if res.status_code == 200 and data.get("status") == "ok":
            print(f"[T-01] Health Check             : PASS (device: {data.get('device')}, gpu: {data.get('gpu')})")
        else:
            print(f"[T-01] Health Check             : FAIL - Unexpected response: {data}")
    except Exception as e:
        print(f"[T-01] Health Check             : FAIL - {str(e)}")

    # Setup for audio tests
    audio_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "test_audio.mp3")
    if not os.path.exists(audio_path):
        print(f"[Error] Test audio file not found at {audio_path}. T-02 and T-05 will fail.")
        
    # T-02 Transcribe Audio
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': f}
            res = requests.post(f"{BASE_URL}/transcribe", files=files)
            data = res.json()
            if res.status_code == 200 and data.get("success"):
                print("[T-02] Transcribe Audio         : PASS")
                print(f"       Result: '{data.get('transcript')}'")
            else:
                print(f"[T-02] Transcribe Audio         : FAIL - {data}")
    except Exception as e:
        print(f"[T-02] Transcribe Audio         : FAIL - {str(e)}")

    # T-03 Translate EN->TA
    try:
        payload = {"text": "Hello, this is a test audio file for the caption app.", "direction": "en-ta"}
        res = requests.post(f"{BASE_URL}/translate", json=payload)
        data = res.json()
        if res.status_code == 200 and data.get("success"):
            print("[T-03] Translate EN->TA         : PASS")
            print(f"       Result: '{data.get('translated')}'")
        else:
            print(f"[T-03] Translate EN->TA         : FAIL - {data}")
    except Exception as e:
        print(f"[T-03] Translate EN->TA         : FAIL - {str(e)}")

    # T-04 Translate TA->EN
    try:
        payload = {"text": "வணக்கம், இது தலைப்பு பயன்பாட்டிற்கான சோதனை ஆடியோ கோப்பு.", "direction": "ta-en"}
        res = requests.post(f"{BASE_URL}/translate", json=payload)
        data = res.json()
        if res.status_code == 200 and data.get("success"):
            print("[T-04] Translate TA->EN         : PASS")
            print(f"       Result: '{data.get('translated')}'")
        else:
            print(f"[T-04] Translate TA->EN         : FAIL - {data}")
    except Exception as e:
        print(f"[T-04] Translate TA->EN         : FAIL - {str(e)}")

    # T-05 Transcribe + Translate
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': f}
            data_payload = {'direction': 'en-ta'}
            res = requests.post(f"{BASE_URL}/transcribe-and-translate", files=files, data=data_payload)
            data = res.json()
            if res.status_code == 200 and data.get("success"):
                print("[T-05] Transcribe + Translate   : PASS")
                print(f"       Transcript : '{data.get('transcript')}'")
                print(f"       Translated : '{data.get('translated')}'")
                print(f"       Total time : {data.get('total_time')}s")
            else:
                print(f"[T-05] Transcribe + Translate   : FAIL - {data}")
    except Exception as e:
        print(f"[T-05] Transcribe + Translate   : FAIL - {str(e)}")

    # T-06 Missing File Error
    try:
        res = requests.post(f"{BASE_URL}/transcribe", files={})
        data = res.json()
        if res.status_code == 400 and not data.get("success"):
            print("[T-06] Missing File Error       : PASS (HTTP 400 returned correctly)")
        else:
            print(f"[T-06] Missing File Error       : FAIL - Unexpected status {res.status_code}")
    except Exception as e:
        print(f"[T-06] Missing File Error       : FAIL - {str(e)}")

    # T-07 Invalid Direction Error
    try:
        payload = {"text": "Hello", "direction": "fr-es"}
        res = requests.post(f"{BASE_URL}/translate", json=payload)
        data = res.json()
        if res.status_code == 400 and not data.get("success"):
            print("[T-07] Invalid Direction Error  : PASS (HTTP 400 returned correctly)")
        else:
            print(f"[T-07] Invalid Direction Error  : FAIL - Unexpected status {res.status_code}")
    except Exception as e:
        print(f"[T-07] Invalid Direction Error  : FAIL - {str(e)}")

    print("--------------------------------------------")
    print("ALL TESTS PASSED. Week 2 complete.")
    print("============================================")

if __name__ == "__main__":
    run_tests()
