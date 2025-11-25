# Setup Instructions

This guide provides detailed installation and setup instructions for the Voice Control Ecosystem.

## Prerequisites

### System Requirements
- **Node.js** 18+ and npm
- **Python** 3.10+
- **React Native** development environment
- **Android Studio** with Android SDK
- **Git**

### Development Tools
- **VS Code** (recommended)
- **Android Emulator** or physical device
- **Python virtual environment** (venv or conda)

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd voice-control-ecosystem
```

### 2. React Native App Setup

```bash
cd voice-control-app
```

#### Install Dependencies
```bash
npm install
```

#### Android Development Setup
1. Install Android Studio
2. Set up Android SDK and Android Virtual Device
3. Configure environment variables:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export ANDROID_HOME=$HOME/Android/Sdk
   export PATH=$PATH:$ANDROID_HOME/emulator
   export PATH=$PATH:$ANDROID_HOME/tools
   export PATH=$PATH:$ANDROID_HOME/tools/bin
   export PATH=$PATH:$ANDROID_HOME/platform-tools
   ```

#### Environment Configuration
Create `.env` file:
```bash
# voice-control-app/.env
WEBSOCKET_URL=ws://10.0.2.2:8000/ws
API_BASE_URL=http://10.0.2.2:8000
DEBUG=true
```

#### Build and Run
```bash
# Start Metro bundler
npx react-native start

# In another terminal, run on Android
npx react-native run-android

# Or run on specific device/emulator
npx react-native run-android --deviceId <device-id>
```

### 3. Python FastAPI Server Setup

```bash
cd voice-control-server
```

#### Create Virtual Environment
```bash
# Using venv (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

#### Install Dependencies
```bash
pip install -r requirements.txt
```

#### Install Additional System Dependencies

**For Speech-to-Text (faster-whisper):**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows (using chocolatey)
choco install ffmpeg
```

**For Ollama (LLM Integration):**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download a model
ollama pull llama2
ollama pull mistral
```

#### Environment Configuration
Create `.env` file:
```bash
# voice-control-server/.env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Server Configuration
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:3000", "http://10.0.2.2:3000"]

# WebSocket Configuration
WEBSOCKET_MAX_CONNECTIONS=10
WEBSOCKET_PING_INTERVAL=30

# STT Configuration
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_TIMEOUT=30

# MCP Configuration
MCP_TIMEOUT=10

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### Build and Run
```bash
# Development mode with hot reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Database Setup (Optional)

If using database for storing conversations or user data:

```bash
# Install PostgreSQL or use SQLite (default)
cd voice-control-server

# For PostgreSQL
pip install psycopg2-binary
createdb voice_control_db

# Set DATABASE_URL environment variable
export DATABASE_URL=postgresql://username:password@localhost/voice_control_db
```

## Configuration Files

### React Native Configuration
- `android/app/src/main/AndroidManifest.xml` - Android permissions and components
- `tsconfig.json` - TypeScript configuration
- `metro.config.js` - Metro bundler configuration

### Python Configuration
- `config/settings.py` - Application settings
- `requirements.txt` - Python dependencies
- `.env` - Environment variables

## Development Workflow

### 1. Start Development Environment

```bash
# Terminal 1: Start FastAPI server
cd voice-control-server
source venv/bin/activate
uvicorn src.main:app --reload

# Terminal 2: Start React Native app
cd voice-control-app
npx react-native start

# Terminal 3: Run Android app
npx react-native run-android
```

### 2. Testing

```bash
# Python tests
cd voice-control-server
pytest

# React Native tests
cd voice-control-app
npm test

# Integration tests
npm run test:integration
```

### 3. Code Quality

```bash
# Python linting and formatting
cd voice-control-server
black .
flake8 .
mypy src/

# React Native linting and formatting
cd voice-control-app
npm run lint
npm run format
```

## Troubleshooting

### Common Issues

**React Native Metro bundler issues:**
```bash
npx react-native start --reset-cache
```

**Android build issues:**
```bash
cd android
./gradlew clean
cd ..
npx react-native run-android
```

**Python dependency issues:**
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**WebSocket connection failed:**
- Ensure server is running on correct host/port
- Check firewall settings
- Verify ANDROID_EMULATOR_HOST variable

**STT not working:**
- Verify ffmpeg installation
- Check microphone permissions
- Test whisper installation: `python -c "import faster_whisper; print('OK')"`

### Logs and Debugging

**Python Server Logs:**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn src.main:app --reload
```

**React Native Logs:**
```bash
# Android logs
npx react-native log-android

# Metro bundler logs
npx react-native start --verbose
```

## Production Deployment

### Building for Production

**Android APK:**
```bash
cd voice-control-app/android
./gradlew assembleRelease
```

**Python Server:**
```bash
cd voice-control-server
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Environment Variables for Production
Update `.env` files with production values:
- Set `DEBUG=false`
- Use strong `SECRET_KEY`
- Configure proper `CORS_ORIGINS`
- Set production database URLs

## Next Steps

1. Review [API.md](API.md) for WebSocket protocol documentation
2. Test the integration between React Native app and Python server
3. Customize LLM models and STT settings for your use case
4. Implement additional features as needed