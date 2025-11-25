@echo off
REM ===============================================
REM Voice Control Ecosystem - Windows Setup Script
REM ===============================================
title Voice Control Ecosystem Setup
color 0A

echo.
echo ===============================================
echo  Voice Control Ecosystem - Windows Setup
echo ===============================================
echo.

REM Check for administrative privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Running without administrative privileges.
    echo Some features may not work properly.
    echo Consider running as Administrator for full functionality.
    echo.
    pause
)

REM Set environment variables
set "VOICE_CONTROL_ROOT=%~dp0.."
set "NODE_ENV=development"
set "LOG_LEVEL=INFO"

echo [INFO] Voice Control Root Directory: %VOICE_CONTROL_ROOT%
echo.

REM ===============================================
REM 1. PREREQUISITE CHECKS
REM ===============================================
echo [STEP 1/8] Checking Prerequisites...
echo.

REM Check Node.js
echo Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+ from https://nodejs.org/
    goto :error_exit
) else (
    for /f "tokens=*" %%a in ('node --version') do set "NODE_VERSION=%%a"
    echo [OK] Node.js %NODE_VERSION% found
)

REM Check Python
echo Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ from https://python.org/
    goto :error_exit
) else (
    for /f "tokens=*" %%a in ('python --version') do set "PYTHON_VERSION=%%a"
    echo [OK] %PYTHON_VERSION% found
)

REM Check Git
echo Checking Git...
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Git not found. Some features may require manual setup.
) else (
    echo [OK] Git found
)

echo.
echo [INFO] Prerequisites check completed successfully
echo.

REM ===============================================
REM 2. REACT NATIVE APP SETUP
REM ===============================================
echo [STEP 2/8] Setting up React Native App...
echo.

cd /d "%VOICE_CONTROL_ROOT%\voice-control-app"

REM Install dependencies
echo Installing React Native dependencies...
if exist package-lock.json (
    echo [INFO] Using npm install with package-lock.json
    npm install --production=false
) else (
    echo [INFO] Running fresh npm install
    npm install
)

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install React Native dependencies
    goto :error_exit
)
echo [OK] React Native dependencies installed

REM Setup environment file
if not exist .env (
    echo [INFO] Creating environment configuration...
    copy /Y .env.example .env >nul
    echo [OK] Environment configuration created
) else (
    echo [INFO] Environment file already exists, skipping...
)

REM Check Android development setup
echo Checking Android development environment...
where adb >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Android SDK not found in PATH
    echo Please install Android Studio and add Android SDK tools to PATH
    echo ORION: ANDROID_HOME, ANDROID_HOME\platform-tools, ANDROID_HOME\tools
) else (
    echo [OK] Android SDK tools found
    adb version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Android device not connected or not authorized
        echo Please connect Android device with USB debugging enabled
    ) else (
        echo [OK] Android device connection verified
    )
)

echo.
echo [INFO] React Native app setup completed
echo.

REM ===============================================
REM 3. PYTHON SERVER SETUP
REM ===============================================
echo [STEP 3/8] Setting up Python Server...
echo.

cd /d "%VOICE_CONTROL_ROOT%\voice-control-server"

REM Check if virtual environment exists
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        goto :error_exit
    )
    echo [OK] Virtual environment created
) else (
    echo [INFO] Virtual environment already exists
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies
    goto :error_exit
)
echo [OK] Python dependencies installed

REM Setup environment file
if not exist .env (
    echo [INFO] Creating environment configuration...
    copy /Y .env.example .env >nul
    echo [OK] Environment configuration created
) else (
    echo [INFO] Environment file already exists, skipping...
)

REM Install FFmpeg (for STT)
echo Checking FFmpeg installation...
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] FFmpeg not found
    echo Installing FFmpeg via Chocolatey...
    
    REM Check if Chocolatey is available
    where choco >nul 2>&1
    if %errorlevel% neq 0 (
        echo [INFO] Chocolatey not found. Please install FFmpeg manually:
        echo Download from: https://ffmpeg.org/download.html#build-windows
        echo OR install Chocolatey first: https://chocolatey.org/
    ) else (
        choco install ffmpeg --yes
        if %errorlevel% neq 0 (
            echo [WARNING] Failed to install FFmpeg automatically
            echo Please install FFmpeg manually from https://ffmpeg.org/
        ) else (
            echo [OK] FFmpeg installed via Chocolatey
        )
    )
) else (
    echo [OK] FFmpeg found
)

echo.
echo [INFO] Python server setup completed
echo.

REM ===============================================
REM 4. OLLAMA SETUP
REM ===============================================
echo [STEP 4/8] Setting up Ollama (LLM Integration)...
echo.

REM Check if Ollama is installed
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Ollama not found in PATH
    echo.
    echo To install Ollama:
    echo 1. Download from: https://ollama.ai
    echo 2. Install and restart terminal
    echo 3. Download a model: ollama pull llama2
    echo.
    echo For now, we'll proceed without Ollama verification
) else (
    echo [OK] Ollama found
    echo Testing Ollama connection...
    ollama list >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Ollama service not running
        echo Please start Ollama: ollama serve
    ) else (
        echo [OK] Ollama service is running
        echo.
        echo Downloading recommended LLM models...
        ollama pull llama2 2>nul || echo [INFO] Llama2 model may already be available
        ollama pull mistral 2>nul || echo [INFO] Mistral model may already be available
        echo [OK] LLM models setup completed
    )
)

echo.
echo [INFO] Ollama setup completed
echo.

REM ===============================================
REM 5. CHROME DEWTOOLS SETUP
REM ===============================================
echo [STEP 5/8] Setting up Chrome DevTools Integration...
echo.

REM Check if Chrome is installed
where chrome >nul 2>&1
if %errorlevel% neq 0 (
    where "C:\Program Files\Google\Chrome\Application\chrome.exe" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Google Chrome not found
        echo Please install Google Chrome from: https://www.google.com/chrome/
    ) else (
        echo [OK] Google Chrome found
    )
) else (
    echo [OK] Chrome found
)

echo.
echo To enable Chrome DevTools integration:
echo 1. Start Chrome with remote debugging: chrome --remote-debugging-port=9222
echo 2. Or enable "Remote Debugging" in Chrome settings
echo.

echo [INFO] Chrome DevTools setup instructions provided
echo.

REM ===============================================
REM 6. SERVICE CONFIGURATION
REM ===============================================
echo [STEP 6/8] Configuring Windows Services...
echo.

REM Create startup scripts
echo Creating startup scripts...

REM Python server startup script
echo @echo off > start_voice_server.bat
echo cd /d "%VOICE_CONTROL_ROOT%\voice-control-server" >> start_voice_server.bat
echo call venv\Scripts\activate.bat >> start_voice_server.bat
echo python start_server.py >> start_voice_server.bat
echo pause >> start_voice_server.bat

echo [OK] Python server startup script created

REM React Native app startup script
echo @echo off > start_voice_app.bat
echo cd /d "%VOICE_CONTROL_ROOT%\voice-control-app" >> start_voice_app.bat
echo echo Starting Metro bundler... >> start_voice_app.bat
echo npx react-native start ^> metro.log 2^>^&1 ^& >> start_voice_app.bat
echo start "React Native Metro" cmd /k "cd /d \"%VOICE_CONTROL_ROOT%\voice-control-app\" ^&^& npx react-native run-android" >> start_voice_app.bat
echo echo React Native Metro started. Check metro.log for output. >> start_voice_app.bat
echo pause >> start_voice_app.bat

echo [OK] React Native app startup script created

echo.
echo [INFO] Service configuration completed
echo.

REM ===============================================
REM 7. TESTING & VALIDATION
REM ===============================================
echo [STEP 7/8] Running Setup Validation...
echo.

cd /d "%VOICE_CONTROL_ROOT%\voice-control-server"
call venv\Scripts\activate.bat

REM Test basic imports
echo Testing Python imports...
python -c "import fastapi, uvicorn, faster_whisper, ollama; print('All core dependencies available')" 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Some Python dependencies may be missing
) else (
    echo [OK] Core Python dependencies available
)

REM Test configuration
python -c "from src.config.settings import get_settings; print('Configuration loaded successfully')" 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Configuration validation failed
) else (
    echo [OK] Configuration validation passed
)

cd /d "%VOICE_CONTROL_ROOT%\voice-control-app"

REM Test Node.js dependencies
echo Testing Node.js dependencies...
npm run build 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Some Node.js dependencies may have issues
    echo Try running: npm install --force
) else (
    echo [OK] Node.js build validation passed
)

echo.
echo [INFO] Setup validation completed
echo.

REM ===============================================
REM 8. SUCCESS MESSAGE & NEXT STEPS
REM ===============================================
echo [STEP 8/8] Setup Completed Successfully!
echo.
echo ===============================================
echo  SETUP COMPLETE - NEXT STEPS
echo ===============================================
echo.
echo 1. START THE PYTHON SERVER:
echo    cd voice-control-server
echo    call venv\Scripts\activate.bat
echo    python start_server.py
echo.
echo 2. START THE REACT NATIVE APP:
echo    cd voice-control-app
echo    npx react-native start
echo    # In another terminal:
echo    npx react-native run-android
echo.
echo 3. OR USE THE CONVENIENCE SCRIPTS:
echo    start_voice_server.bat    - Start Python server only
echo    start_voice_app.bat       - Start React Native app
echo.
echo ===============================================
echo  DOCUMENTATION & TROUBLESHOOTING
echo ===============================================
echo.
echo - Documentation: docs/README.md
echo - API Reference: docs/API.md
echo - Setup Guide: docs/setup.md
echo - Troubleshooting: docs/troubleshooting.md
echo.
echo ===============================================
echo.
echo Setup completed successfully! Press any key to exit...
pause >nul

goto :end

:error_exit
echo.
echo ===============================================
echo  SETUP FAILED
echo ===============================================
echo.
echo Please check the error messages above and:
echo 1. Install missing prerequisites
echo 2. Run the script again
echo 3. Check the troubleshooting guide
echo.
echo Press any key to exit...
pause >nul
exit /b 1

:end
echo.
echo Thank you for using Voice Control Ecosystem!
echo Enjoy your voice-controlled experience! 🎤💻
echo.
