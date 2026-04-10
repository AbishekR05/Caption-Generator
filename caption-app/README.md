# Caption Generator with Translation

A desktop caption generator with live transcription and translation between English and Tamil, powered by OpenAI Whisper and HuggingFace, running entirely locally on GPU.

## Tech Stack
* **Python**: Core language
* **OpenAI Whisper**: Local transcription
* **HuggingFace Transformers**: Local translation (MarianMT)
* **PyTorch**: Deep learning framework with CUDA support

## Installation

### Prerequisites
* Windows PC with an- NVIDIA GTX 1650 (or similar CUDA-capable GPU)
* 4GB+ VRAM

## Running the Backend

### Start the Flask server
```bash
cd caption-app
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac
python backend/app.py
```

Server will start at: http://localhost:5000

### Run API tests (server must be running first)
```bash
python backend/test_api.py
```

### Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Check server + GPU status |
| POST | /transcribe | Transcribe audio file |
| POST | /translate | Translate text EN↔TA |
| POST | /transcribe-and-translate | Transcribe + translate in one call |

## Running the App (Development)

> Both the backend and frontend must run simultaneously in separate terminals.

### Terminal 1 — Start Flask Backend
```bash
cd caption-app
venv\Scripts\activate
python backend/app.py
```

### Terminal 2 — Start Electron + React
```bash
cd caption-app
npm install         # first time only
npm run dev
```

The Electron window will open automatically once the Vite dev server is ready.
* Python 3.10 or 3.11 installed
* Git

### Step-by-Step Setup

1. **Clone the repository**
   ```bash
   git clone <repository_url>
   cd caption-app
   ```

2. **Create and activate the virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/Mon macOS:
   source venv/bin/activate
   ```

3. **Install PyTorch with CUDA 11.8 (CRITICAL)**
   > Note: Do not install PyTorch from requirements.txt. You must use the specific index URL below to ensure CUDA support.
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

4. **Install remaining dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the integration test**
   ```bash
   python backend/test_pipeline.py
   ```
   *The script will download the required ML models (~2GB for Whisper and ~600MB for Translators) on the first run.*

## Project Phases

### Week 1: Environment Setup & First Transcription
- Set up local Python environment with PyTorch and CUDA.
- Integrated OpenAI Whisper for transcription and Helsinki-NLP for EN<->TA translation.
- Verified local GPU inference.

### Week 2: (Coming Soon)
- Flask server integration

### Week 3: (Coming Soon)
- Electron/React UI

### Week 4: (Coming Soon)
- Live microphone input and overlay window
