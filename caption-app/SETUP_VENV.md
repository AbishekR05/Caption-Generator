# Local Python Virtual Environment Setup Guide

This guide explains how to recreate the local virtual environment (`venv`) for the Caption Generator application from scratch, including setting up CUDA-enabled PyTorch for GPU acceleration.

---

## Prerequisite
Ensure you have **Python 3.10 or 3.11** installed. You can check your version by running:
```powershell
python --version
```

---

## Setup Instructions

### 1. Create a Virtual Environment
Navigate to the `caption-app` directory and create a new virtual environment named `venv`:
```powershell
cd "d:\Full Stack\Caption Generator\caption-app"
python -m venv venv
```

### 2. Activate the Virtual Environment
Activate the environment in your terminal:
- **Windows PowerShell**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows Command Prompt**:
  ```cmd
  .\venv\Scripts\activate.bat
  ```
- **Linux / macOS**:
  ```bash
  source venv/bin/activate
  ```

### 3. Install PyTorch with CUDA (GPU Support)
Since this project runs local ML models (`faster-whisper` and Hugging Face `transformers` translation), GPU acceleration via CUDA is highly recommended for real-time performance.

Install PyTorch built with CUDA support (adjust the CUDA version index-url if needed, e.g., `cu121` or `cu118`):
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 4. Install Project Dependencies
Install all remaining required Python packages using `requirements.txt`:
```powershell
pip install -r requirements.txt
```

---

## VS Code Configuration
To ensure VS Code automatically recognizes this virtual environment:
1. Open the Command Palette (`Ctrl+Shift+P`).
2. Select **Python: Select Interpreter**.
3. Choose the python executable inside your new environment (`caption-app/venv/Scripts/python.exe`).

Alternatively, create/update `.vscode/settings.json` at the root of the workspace:
```json
{
  "python.defaultInterpreterPath": "d:\\Full Stack\\Caption Generator\\caption-app\\venv\\Scripts\\python.exe"
}
```

---

## Sharing Virtual Environments (Optional)
To save storage space across multiple AI/ML projects (since PyTorch is ~5GB+), you can share a single virtual environment.
1. Identify a shared venv location (e.g., `D:\College\Sem 7\GenAI\Lab\venv`).
2. Install dependencies there:
   ```powershell
   & "D:\College\Sem 7\GenAI\Lab\venv\Scripts\pip.exe" install -r "d:\Full Stack\Caption Generator\caption-app\requirements.txt"
   ```
3. Update `.vscode/settings.json` to point to the shared venv:
   ```json
   {
     "python.defaultInterpreterPath": "D:\\College\\Sem 7\\GenAI\\Lab\\venv\\Scripts\\python.exe"
   }
   ```
4. Delete the local `caption-app/venv` directory to free up space.
