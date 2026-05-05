import os
import time
import tempfile
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import torch

from transcriber import transcribe
from translator import translate
from post_processor import process as post_process

# ── App Init ─────────────────────────────────────────────
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── REST Endpoints ────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    print("[API] GET /health")
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        device = "cuda"
    else:
        gpu_name = None
        device = "cpu"
        
    return jsonify({
        "status": "ok",
        "whisper_model": "small",
        "device": device,
        "gpu": gpu_name
    }), 200

@app.route('/transcribe', methods=['POST'])
def handle_transcribe():
    """Accepts an audio file upload, runs it through Whisper, returns the transcript."""
    print("[API] POST /transcribe")
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No audio file provided."}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No audio file provided."}), 400
        
    language = request.form.get('language')  # Optional
    tmp = None
    
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        file.save(tmp.name)
        tmp.close()
        
        start_time = time.time()
        
        # pass language explicitly if defined
        kwargs = {}
        if language:
            kwargs['language'] = language
            
        result = transcribe(tmp.name, **kwargs)
        duration = time.time() - start_time
        
        return jsonify({
            "success": True,
            "transcript": result['text'],
            "language": result['language'],
            "duration_seconds": round(duration, 1)
        }), 200
        
    except Exception as e:
        print(f"[Error] Transcription failed: {str(e)}")
        return jsonify({"success": False, "error": f"Transcription failed: {str(e)}"}), 500
    finally:
        if tmp and os.path.exists(tmp.name):
            try:
                os.unlink(tmp.name)
            except Exception as e:
                print(f"[Error] Failed to remove temp file: {e}")

@app.route('/translate', methods=['POST'])
def handle_translate():
    """Accepts a text string and direction, returns translated text."""
    print("[API] POST /translate")
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({"success": False, "error": "Missing required field: text"}), 400
        
    direction = data.get('direction')
    if direction not in ['en-ta', 'ta-en']:
        return jsonify({"success": False, "error": "Invalid direction. Must be 'en-ta' or 'ta-en'."}), 400
        
    text = data['text']
    try:
        start_time = time.time()
        translated = translate(text, direction=direction)
        duration = time.time() - start_time
        
        return jsonify({
            "success": True,
            "translated": translated,
            "direction": direction,
            "duration_seconds": round(duration, 1)
        }), 200
    except Exception as e:
        print(f"[Error] Translation failed: {str(e)}")
        return jsonify({"success": False, "error": f"Translation failed: {str(e)}"}), 500

@app.route('/transcribe-and-translate', methods=['POST'])
def handle_transcribe_and_translate():
    """Convenience endpoint — does transcription + (optional) translation in a single call."""
    print("[API] POST /transcribe-and-translate")
    
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No audio file provided."}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No audio file provided."}), 400
        
    translate_enabled = request.form.get('translate', 'false').lower() == 'true'
    censor_enabled = request.form.get('censor', 'false').lower() == 'true'
    sentiment_enabled = request.form.get('sentiment', 'false').lower() == 'true'
    direction = request.form.get('direction', 'en-ta')
    if translate_enabled and direction not in ['en-ta', 'ta-en']:
        return jsonify({"success": False, "error": "Invalid direction. Must be 'en-ta' or 'ta-en'."}), 400
        
    language = request.form.get('language')  # Optional
    tmp = None
    
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        file.save(tmp.name)
        tmp.close()
        
        # 1. Transcribe
        t_start = time.time()
        kwargs = {}
        if language:
            kwargs['language'] = language
            
        transcribe_result = transcribe(tmp.name, **kwargs)
        t_duration = time.time() - t_start
        transcript = transcribe_result['text'].strip()
        detected_language = transcribe_result['language']
        
        # Post-process
        post = post_process(transcript, censor_enabled, sentiment_enabled)
        
        # 2. Translate only if enabled
        translated = None
        if translate_enabled and post['text']:
            tr_start = time.time()
            translated = translate(post['text'], direction=direction)
            tr_duration = time.time() - tr_start
        else:
            tr_duration = 0
        
        total_time = t_duration + tr_duration
        
        return jsonify({
            "success": True,
            "transcript": post['text'],
            "translated": translated,
            "sentiment": post['sentiment'],
            "language_detected": detected_language,
            "direction": direction if translate_enabled else None,
            "transcription_time": round(t_duration, 1),
            "translation_time": round(tr_duration, 1),
            "total_time": round(total_time, 1)
        }), 200
        
    except Exception as e:
        print(f"[Error] Combined pipeline failed: {str(e)}")
        return jsonify({"success": False, "error": f"Pipeline failed: {str(e)}"}), 500
    finally:
        if tmp and os.path.exists(tmp.name):
            try:
                os.unlink(tmp.name)
            except Exception as e:
                print(f"[Error] Failed to remove temp file: {e}")

from exporter import export_srt, export_txt, save_file
from datetime import datetime

@app.route('/export', methods=['POST'])
def export_captions():
    """
    Export caption history as SRT or TXT file.
    """
    data = request.get_json()

    if not data or 'captions' not in data:
        return jsonify({'success': False, 'error': 'No captions provided'}), 400

    captions = data.get('captions', [])
    fmt = data.get('format', 'srt').lower()
    include_translation = data.get('include_translation', False)

    if not captions:
        return jsonify({'success': False, 'error': 'Caption history is empty'}), 400

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'captions_{timestamp}.{fmt}'

    try:
        if fmt == 'srt':
            content = export_srt(captions, include_translation)
        elif fmt == 'txt':
            content = export_txt(captions, include_translation)
        else:
            return jsonify({'success': False, 'error': 'Invalid format. Use srt or txt'}), 400

        filepath = save_file(content, filename)

        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'format': fmt,
            'caption_count': len(captions)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ── SocketIO Events ───────────────────────────────────────

@socketio.on('connect')
def handle_connect():
    print(f'[SocketIO] Client connected: {request.sid}')
    emit('connected', {'message': 'Connected to Caption Generator backend.'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'[SocketIO] Client disconnected: {request.sid}')

@socketio.on('ping')
def handle_ping():
    emit('pong', {'timestamp': time.time()})

# ── Week 4 Placeholder ───────────────────────────────────

from audio_capture import start_capture, stop_capture
import threading

@socketio.on('start_mic')
def handle_start_mic(data):
    mode = data.get('mode', 'mic')           # 'mic' or 'system'
    direction = data.get('direction', 'en-ta')
    translate_enabled = data.get('translate', False)  # OFF by default
    censor_enabled = data.get('censor', False)
    sentiment_enabled = data.get('sentiment', False)

    print(f'[SocketIO] start_mic | mode: {mode} | translate: {translate_enabled}')

    def on_chunk(audio_path):
        try:
            result = transcribe(audio_path)
            transcript = result['text'].strip()

            if not transcript:
                return

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
                sentiment=post['sentiment']
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


@socketio.on('stop_mic')
def handle_stop_mic():
    print('[SocketIO] stop_mic received.')
    stop_capture()

# ── Week 4 Emitters ──────────────────────────────────────

def emit_caption(text, translated=None, sentiment=None):
    socketio.emit('caption_update', {
        'transcript': text,
        'translated': translated,   # None if translation is off
        'sentiment': sentiment,
        'timestamp': time.time()
    })
    label = sentiment['label'] if sentiment else 'off'
    print(f'[SocketIO] caption_update | sentiment:{label} | {text[:40]}')

# ── Entry Point ───────────────────────────────────────────

if __name__ == '__main__':
    print("[Server] Starting Caption Generator backend on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
