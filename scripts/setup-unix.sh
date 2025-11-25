#!/bin/bash
# ===============================================
# Voice Control Ecosystem - Unix Setup Script
# ===============================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Set error handling
set -e  # Exit on any error
set -u  # Exit on undefined variable

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VOICE_CONTROL_ROOT="$(dirname "$SCRIPT_DIR")"

# Functions for colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to check command existence
command_exists() { command -v "$1" >/dev/null 2>&1; }

# Function to check if directory exists
dir_exists() { [ -d "$1" ]; }

# Function to check file exists
file_exists() { [ -f "$1" ]; }

# Error handling function
error_exit() {
    print_error "$1"
    echo ""
    echo "Setup failed. Please check the error messages above and:"
    echo "1. Install missing prerequisites"
    echo "2. Run the script again"
    echo "3. Check the troubleshooting guide"
    echo ""
    exit 1
}

# Success completion function
completion_message() {
    echo ""
    echo "==============================================="
    echo "  SETUP COMPLETE - NEXT STEPS"
    echo "==============================================="
    echo ""
    echo "1. START THE PYTHON SERVER:"
    echo "   cd voice-control-server"
    echo "   source venv/bin/activate"
    echo "   python start_server.py"
    echo ""
    echo "2. START THE REACT NATIVE APP:"
    echo "   cd voice-control-app"
    echo "   npx react-native start"
    echo "   # In another terminal:"
    echo "   npx react-native run-android"
    echo ""
    echo "3. OR USE THE CONVENIENCE SCRIPTS:"
    echo "   ./scripts/start_unix.sh       - Start both components"
    echo "   ./scripts/start_server.sh     - Start Python server only"
    echo "   ./scripts/start_app.sh        - Start React Native app only"
    echo ""
    echo "==============================================="
    echo "  DOCUMENTATION & TROUBLESHOOTING"
    echo "==============================================="
    echo ""
    echo "- Documentation: docs/README.md"
    echo "- API Reference: docs/API.md"
    echo "- Setup Guide: docs/setup.md"
    echo "- Troubleshooting: docs/troubleshooting.md"
    echo ""
    echo "==============================================="
    echo ""
    print_success "Setup completed successfully!"
    echo "Thank you for using Voice Control Ecosystem!"
    echo "Enjoy your voice-controlled experience! 🎤💻"
    echo ""
}

# Trap errors
trap 'error_exit "Setup failed at line $LINENO"' ERR

# Main script starts here
echo ""
echo "==============================================="
echo "  Voice Control Ecosystem - Unix Setup"
echo "==============================================="
echo ""

print_info "Voice Control Root Directory: $VOICE_CONTROL_ROOT"
echo ""

# ===============================================
# 1. PREREQUISITE CHECKS
# ===============================================
echo "[STEP 1/8] Checking Prerequisites..."
echo ""

# Check Node.js
echo "Checking Node.js..."
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js $NODE_VERSION found"
else
    error_exit "Node.js not found. Please install Node.js 18+ from https://nodejs.org/"
fi

# Check Python
echo "Checking Python..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    print_success "$PYTHON_VERSION found"
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
elif command_exists python; then
    PYTHON_VERSION=$(python --version)
    print_success "$PYTHON_VERSION found"
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    error_exit "Python not found. Please install Python 3.10+ from https://python.org/"
fi

# Check Git
echo "Checking Git..."
if command_exists git; then
    print_success "Git found"
else
    print_warning "Git not found. Some features may require manual setup."
fi

# Check OS-specific package manager
echo "Checking package manager..."
if command_exists apt-get; then
    PACKAGE_MANAGER="apt"
    print_info "Using APT package manager (Ubuntu/Debian)"
elif command_exists yum; then
    PACKAGE_MANAGER="yum"
    print_info "Using YUM package manager (RHEL/CentOS)"
elif command_exists brew; then
    PACKAGE_MANAGER="brew"
    print_info "Using Homebrew (macOS)"
elif command_exists pacman; then
    PACKAGE_MANAGER="pacman"
    print_info "Using Pacman (Arch Linux)"
else
    print_warning "No recognized package manager found"
fi

echo ""
print_success "Prerequisites check completed successfully"
echo ""

# ===============================================
# 2. REACT NATIVE APP SETUP
# ===============================================
echo "[STEP 2/8] Setting up React Native App..."
echo ""

cd "$VOICE_CONTROL_ROOT/voice-control-app"

# Install dependencies
echo "Installing React Native dependencies..."
if [ -f "package-lock.json" ]; then
    print_info "Using npm install with package-lock.json"
    npm install --production=false
else
    print_info "Running fresh npm install"
    npm install
fi

if [ $? -ne 0 ]; then
    error_exit "Failed to install React Native dependencies"
fi
print_success "React Native dependencies installed"

# Setup environment file
if [ ! -f ".env" ]; then
    print_info "Creating environment configuration..."
    cp .env.example .env
    print_success "Environment configuration created"
else
    print_info "Environment file already exists, skipping..."
fi

# Check Android development setup
echo "Checking Android development environment..."
if command_exists adb; then
    print_success "Android SDK tools found"
    if adb devices | grep -q "List of devices"; then
        device_count=$(adb devices | grep -v "List of devices" | grep -v "^$" | wc -l)
        if [ "$device_count" -gt 0 ]; then
            print_success "Android device connection verified"
        else
            print_warning "No Android device connected or not authorized"
            print_warning "Please connect Android device with USB debugging enabled"
        fi
    fi
else
    print_warning "Android SDK not found in PATH"
    print_warning "Please install Android Studio and add Android SDK tools to PATH"
fi

echo ""
print_success "React Native app setup completed"
echo ""

# ===============================================
# 3. PYTHON SERVER SETUP
# ===============================================
echo "[STEP 3/8] Setting up Python Server..."
echo ""

cd "$VOICE_CONTROL_ROOT/voice-control-server"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        error_exit "Failed to create virtual environment"
    fi
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
$PIP_CMD install --upgrade pip

# Install dependencies
echo "Installing Python dependencies..."
$PIP_CMD install -r requirements.txt

if [ $? -ne 0 ]; then
    error_exit "Failed to install Python dependencies"
fi
print_success "Python dependencies installed"

# Setup environment file
if [ ! -f ".env" ]; then
    print_info "Creating environment configuration..."
    cp .env.example .env
    print_success "Environment configuration created"
else
    print_info "Environment file already exists, skipping..."
fi

# Install FFmpeg (for STT)
echo "Checking FFmpeg installation..."
if command_exists ffmpeg; then
    print_success "FFmpeg found"
else
    print_warning "FFmpeg not found"
    print_info "Installing FFmpeg..."
    
    case $PACKAGE_MANAGER in
        "apt")
            sudo apt update
            sudo apt install -y ffmpeg
            ;;
        "yum")
            sudo yum install -y ffmpeg
            ;;
        "brew")
            brew install ffmpeg
            ;;
        "pacman")
            sudo pacman -S --noconfirm ffmpeg
            ;;
        *)
            print_warning "Unable to install FFmpeg automatically"
            print_warning "Please install FFmpeg manually from https://ffmpeg.org/"
            ;;
    esac
    
    if command_exists ffmpeg; then
        print_success "FFmpeg installed successfully"
    else
        print_warning "FFmpeg installation may have failed"
    fi
fi

echo ""
print_success "Python server setup completed"
echo ""

# ===============================================
# 4. OLLAMA SETUP
# ===============================================
echo "[STEP 4/8] Setting up Ollama (LLM Integration)..."
echo ""

# Check if Ollama is installed
if command_exists ollama; then
    print_success "Ollama found"
    echo "Testing Ollama connection..."
    if ollama list >/dev/null 2>&1; then
        print_success "Ollama service is running"
        echo ""
        print_info "Downloading recommended LLM models..."
        ollama pull llama2 2>/dev/null || print_info "Llama2 model may already be available"
        ollama pull mistral 2>/dev/null || print_info "Mistral model may already be available"
        print_success "LLM models setup completed"
    else
        print_warning "Ollama service not running"
        print_warning "Please start Ollama: ollama serve"
    fi
else
    print_warning "Ollama not found in PATH"
    echo ""
    echo "To install Ollama:"
    echo "1. Download from: https://ollama.ai"
    echo "2. Install and restart terminal"
    echo "3. Download a model: ollama pull llama2"
    echo ""
    print_info "For now, we'll proceed without Ollama verification"
fi

echo ""
print_success "Ollama setup completed"
echo ""

# ===============================================
# 5. CHROME DEWTOOLS SETUP
# ===============================================
echo "[STEP 5/8] Setting up Chrome DevTools Integration..."
echo ""

# Check if Chrome is installed
if command_exists google-chrome || command_exists chromium-browser || command_exists chrome; then
    print_success "Chrome/Chromium browser found"
else
    print_warning "Chrome browser not found"
    print_warning "Please install Google Chrome from: https://www.google.com/chrome/"
fi

echo ""
echo "To enable Chrome DevTools integration:"
echo "1. Start Chrome with remote debugging: google-chrome --remote-debugging-port=9222"
echo "2. Or enable \"Remote Debugging\" in Chrome settings"
echo ""

print_success "Chrome DevTools setup instructions provided"
echo ""

# ===============================================
# 6. SERVICE CONFIGURATION
# ===============================================
echo "[STEP 6/8] Configuring Unix Services..."
echo ""

# Create startup scripts
print_info "Creating startup scripts..."

# Create scripts directory if it doesn't exist
mkdir -p "$VOICE_CONTROL_ROOT/scripts"

# Python server startup script
cat > "$VOICE_CONTROL_ROOT/scripts/start_server.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../voice-control-server"
source venv/bin/activate
python start_server.py
EOF

chmod +x "$VOICE_CONTROL_ROOT/scripts/start_server.sh"
print_success "Python server startup script created"

# React Native app startup script
cat > "$VOICE_CONTROL_ROOT/scripts/start_app.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../voice-control-app"
echo "Starting Metro bundler..."
npx react-native start > metro.log 2>&1 &
sleep 5
echo "React Native Metro started. Check metro.log for output."
echo "Starting Android app..."
npx react-native run-android
EOF

chmod +x "$VOICE_CONTROL_ROOT/scripts/start_app.sh"
print_success "React Native app startup script created"

# Combined startup script
cat > "$VOICE_CONTROL_ROOT/scripts/start_unix.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../voice-control-server"
source venv/bin/activate
echo "Starting Voice Control Server..."
python start_server.py &
SERVER_PID=$!
sleep 5

cd "$SCRIPT_DIR/../voice-control-app"
echo "Starting React Native App..."
npx react-native start &
APP_PID=$!

echo "Both services started!"
echo "Server PID: $SERVER_PID"
echo "App PID: $APP_PID"
echo "Press Ctrl+C to stop both services"

trap "kill $SERVER_PID $APP_PID; exit" SIGINT
wait
EOF

chmod +x "$VOICE_CONTROL_ROOT/scripts/start_unix.sh"
print_success "Combined startup script created"

echo ""
print_success "Service configuration completed"
echo ""

# ===============================================
# 7. TESTING & VALIDATION
# ===============================================
echo "[STEP 7/8] Running Setup Validation..."
echo ""

cd "$VOICE_CONTROL_ROOT/voice-control-server"
source venv/bin/activate

# Test basic imports
echo "Testing Python imports..."
if python -c "import fastapi, uvicorn, faster_whisper, ollama; print('All core dependencies available')" 2>/dev/null; then
    print_success "Core Python dependencies available"
else
    print_warning "Some Python dependencies may be missing"
fi

# Test configuration
echo "Testing configuration..."
if python -c "from src.config.settings import get_settings; print('Configuration loaded successfully')" 2>/dev/null; then
    print_success "Configuration validation passed"
else
    print_warning "Configuration validation failed"
fi

cd "$VOICE_CONTROL_ROOT/voice-control-app"

# Test Node.js dependencies
echo "Testing Node.js dependencies..."
if npm run build >/dev/null 2>&1; then
    print_success "Node.js build validation passed"
else
    print_warning "Some Node.js dependencies may have issues"
    print_info "Try running: npm install --force"
fi

echo ""
print_success "Setup validation completed"
echo ""

# ===============================================
# 8. SUCCESS MESSAGE & NEXT STEPS
# ===============================================
completion_message
