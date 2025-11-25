# Voice Control Ecosystem - Troubleshooting Guide

This comprehensive troubleshooting guide helps resolve common issues encountered when setting up, deploying, and using the Voice Control Ecosystem.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Connection Problems](#connection-problems)
3. [Performance Issues](#performance-issues)
4. [Audio and Speech Recognition Problems](#audio-and-speech-recognition-problems)
5. [LLM and AI Integration Issues](#llm-and-ai-integration-issues)
6. [MCP Server Issues](#mcp-server-issues)
7. [Android App Problems](#android-app-problems)
8. [Docker Deployment Issues](#docker-deployment-issues)
9. [Network and Security Issues](#network-and-security-issues)
10. [Log Analysis](#log-analysis)
11. [Emergency Procedures](#emergency-procedures)

## Installation Issues

### Python Environment Problems

**Problem**: Python virtual environment creation fails
```
ERROR: Could not create virtual environment
```

**Solutions**:
```bash
# Update pip and venv
python -m pip install --upgrade pip setuptools wheel

# Install venv if missing
sudo apt-get install python3-venv  # Ubuntu/Debian
sudo yum install python3-venv      # RHEL/CentOS

# Clear cache and retry
pip cache purge
python -m venv venv
```

**Problem**: Dependencies installation fails
```
ERROR: Could not find a version that satisfies the requirement
```

**Solutions**:
```bash
# Update pip
pip install --upgrade pip

# Install from requirements.txt with verbose output
pip install -r requirements.txt -v

# Install individual packages
pip install fastapi uvicorn faster-whisper ollama
```

### Node.js and React Native Issues

**Problem**: npm install fails with permission errors
```
npm ERR! code EACCES
```

**Solutions**:
```bash
# Fix npm permissions (Linux/macOS)
sudo chown -R $(whoami) ~/.npm
sudo chown -R $(whoami) ~/.cache

# Use yarn instead of npm
npm install -g yarn
yarn install

# Use npm with --unsafe-perm flag
npm install --unsafe-perm
```

**Problem**: React Native Metro bundler issues
```
Metro bundler failed to start
```

**Solutions**:
```bash
# Clear Metro cache
npx react-native start --reset-cache

# Delete node_modules and reinstall
rm -rf node_modules
npm install
npx react-native start

# Check for port conflicts
netstat -tulpn | grep 8081
```

### Android Development Setup

**Problem**: Android SDK not found
```
ANDROID_HOME is not set
```

**Solutions**:
```bash
# Set Android SDK path (add to ~/.bashrc or ~/.zshrc)
export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools

# Verify setup
echo $ANDROID_HOME
adb version
```

**Problem**: No Android device detected
```
adb: no devices/emulators found
```

**Solutions**:
```bash
# Check device connection
adb devices

# Enable USB debugging on Android device
# Settings > Developer Options > USB Debugging

# Check USB drivers (Windows)
# Install Google USB Driver from Android SDK Manager

# Restart adb server
adb kill-server
adb start-server
```

## Connection Problems

### Server Connection Issues

**Problem**: Cannot connect to Python server
```
WebSocket connection failed: ECONNREFUSED
```

**Solutions**:
```bash
# Check if server is running
curl http://localhost:8000/health

# Check server logs
tail -f voice-control-server/storage/logs/production.log

# Verify port availability
netstat -tulpn | grep 8000

# Start server manually
cd voice-control-server
source venv/bin/activate
python start_server.py
```

**Problem**: WebSocket connection drops frequently
```
WebSocket connection closed unexpectedly
```

**Solutions**:
```bash
# Check network stability
ping -c 10 your-server-ip

# Increase timeout values in configuration
# In .env file:
WEBSOCKET_PING_INTERVAL=60
WEBSOCKET_CLOSE_TIMEOUT=120

# Check firewall settings
sudo ufw status
sudo iptables -L
```

### Android App Connection Issues

**Problem**: App cannot find server on network
```
Failed to connect to WebSocket
```

**Solutions**:
1. **Verify network connectivity**:
   ```bash
   # Check if server is accessible from Android device
   ping your-pc-ip
   curl http://your-pc-ip:8000/health
   ```

2. **Check firewall settings**:
   ```bash
   # Windows
   netsh advfirewall firewall add rule name="Voice Control" dir=in action=allow protocol=TCP localport=8000

   # Linux
   sudo ufw allow 8000/tcp
   ```

3. **Update server IP in app settings**:
   - Open Voice Control app
   - Go to Settings
   - Update server address
   - Test connection

4. **Network discovery issues**:
   ```bash
   # Enable network discovery
   # Windows: Network and Sharing Center > Advanced sharing settings
   # Linux: Check avahi-daemon or mDNS service
   ```

## Performance Issues

### High CPU Usage

**Problem**: Server consuming too much CPU
```
High CPU usage detected
```

**Solutions**:
1. **Reduce worker processes**:
   ```bash
   # In production configuration
   WORKERS=2  # Reduce from 4
   
   # In docker-compose.yml
   environment:
     - WORKERS=2
   ```

2. **Optimize LLM model**:
   ```bash
   # Use smaller models
   OLLAMA_MODEL=llama2:7b  # Instead of 70b
   LLM_MAX_TOKENS=256     # Reduce from 512
   ```

3. **Enable GPU acceleration**:
   ```bash
   # Verify CUDA installation
   nvidia-smi
   
   # Enable in configuration
   WHISPER_DEVICE=cuda
   OLLAMA_GPU_LAYERS=35
   ```

### High Memory Usage

**Problem**: Server running out of memory
```
Out of memory error
```

**Solutions**:
1. **Monitor memory usage**:
   ```bash
   # Check current usage
   free -h
   ps aux --sort=-%mem | head
   
   # Monitor over time
   watch -n 5 free -h
   ```

2. **Optimize models**:
   ```bash
   # Use smaller models
   WHISPER_MODEL=base      # Instead of large
   OLLAMA_MODEL=mistral:7b # Smaller LLM
   
   # Reduce context window
   LLM_CONTEXT_SIZE=2048   # Reduce from 4096
   ```

3. **Enable memory management**:
   ```bash
   # Add to configuration
   MAX_MEMORY_USAGE=2048  # MB
   ENABLE_MEMORY_LIMITING=true
   ```

### Slow Response Times

**Problem**: Voice commands take too long to process
```
Command processing timeout
```

**Solutions**:
1. **Check system resources**:
   ```bash
   # Monitor performance during command processing
   htop
   iotop
   ```

2. **Optimize audio settings**:
   ```bash
   # Reduce audio quality for faster processing
   AUDIO_SAMPLE_RATE=16000
   AUDIO_CHUNK_SIZE=1024
   STT_TIMEOUT=15  # Reduce timeout
   ```

3. **Cache optimization**:
   ```bash
   # Enable response caching
   CACHE_ENABLED=true
   CACHE_TTL=300
   ```

## Audio and Speech Recognition Problems

### Microphone Issues

**Problem**: No audio input detected
```
Audio recording failed
```

**Solutions**:
1. **Check microphone permissions**:
   ```bash
   # Linux
   arecord -l
   alsamixer
   
   # Check permissions
   sudo usermod -a -G audio $USER
   ```

2. **Test microphone directly**:
   ```bash
   # Record test audio
   arecord -d 5 test.wav
   aplay test.wav
   
   # Check audio devices
   pactl list sources
   ```

3. **Android app permissions**:
   - Go to Android Settings > Apps > Voice Control > Permissions
   - Enable Microphone permission
   - Grant permission when prompted

### Speech Recognition Accuracy

**Problem**: Poor speech recognition accuracy
```
Low confidence scores
```

**Solutions**:
1. **Adjust STT settings**:
   ```bash
   # Improve accuracy settings
   WHISPER_MODEL=medium     # Better than base
   WHISPER_COMPUTE_TYPE=float16
   STT_CONFIDENCE_THRESHOLD=0.6  # Lower threshold
   ```

2. **Audio quality improvements**:
   ```bash
   # Higher quality audio
   AUDIO_SAMPLE_RATE=44100
   AUDIO_CHANNELS=1
   AUDIO_BIT_DEPTH=16
   ```

3. **Noise reduction**:
   ```bash
   # Enable noise suppression
   NOISE_REDUCTION_ENABLED=true
   AUDIO_NORMALIZATION=true
   ```

### Audio Processing Errors

**Problem**: Audio processing pipeline failures
```
Audio pipeline error
```

**Solutions**:
1. **Check FFmpeg installation**:
   ```bash
   # Verify FFmpeg
   ffmpeg -version
   
   # Install if missing
   sudo apt-get install ffmpeg  # Ubuntu/Debian
   brew install ffmpeg          # macOS
   ```

2. **Test audio formats**:
   ```bash
   # Check supported formats
   ffmpeg -formats | grep -i pcm
   ```

3. **Validate audio data**:
   ```bash
   # Check audio file integrity
   ffprobe audio_file.wav
   
   # Convert to supported format
   ffmpeg -i input.wav -acodec pcm_s16le -ar 16000 output.wav
   ```

## LLM and AI Integration Issues

### Ollama Connection Problems

**Problem**: Cannot connect to Ollama server
```
Connection refused to Ollama
```

**Solutions**:
1. **Check Ollama service**:
   ```bash
   # Verify Ollama is running
   ollama ps
   
   # Start Ollama service
   ollama serve
   
   # Check port
   netstat -tulpn | grep 11434
   ```

2. **Test Ollama API**:
   ```bash
   # Test connection
   curl http://localhost:11434/api/tags
   
   # Test model generation
   curl http://localhost:11434/api/generate -d '{
     "model": "llama2:7b",
     "prompt": "Hello",
     "stream": false
   }'
   ```

3. **Fix configuration**:
   ```bash
   # Update environment variables
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_HOST=0.0.0.0:11434
   ```

### Model Loading Failures

**Problem**: LLM models fail to load
```
Model loading failed
```

**Solutions**:
1. **Check disk space**:
   ```bash
   # Verify sufficient space
   df -h
   
   # Clean up old models
   ollama rm model-name
   ```

2. **Verify model files**:
   ```bash
   # List installed models
   ollama list
   
   # Pull missing model
   ollama pull llama2:7b
   ```

3. **Check memory requirements**:
   ```bash
   # Monitor memory during model loading
   free -h
   htop
   
   # Use smaller models if memory limited
   ollama pull llama2:7b  # Instead of 70b
   ```

### LLM Response Issues

**Problem**: LLM produces poor or irrelevant responses
```
LLM response quality issues
```

**Solutions**:
1. **Improve system prompt**:
   ```bash
   # Update LLM configuration
   LLM_SYSTEM_PROMPT="You are a helpful voice assistant that can control computer systems safely. Always confirm potentially dangerous operations."
   
   # Adjust creativity settings
   LLM_TEMPERATURE=0.7  # Balance creativity and accuracy
   LLM_MAX_TOKENS=512   # Sufficient response length
   ```

2. **Use better models**:
   ```bash
   # Try different models
   OLLAMA_MODEL=llama2:13b    # Better than 7b
   OLLAMA_MODEL=mistral:7b    # Alternative
   OLLAMA_MODEL=codeqwen:7b   # For technical tasks
   ```

## MCP Server Issues

### Windows MCP Problems

**Problem**: Windows MCP tools not working
```
Permission denied for Windows operation
```

**Solutions**:
1. **Run as Administrator**:
   ```bash
   # Right-click command prompt > Run as Administrator
   # Or create elevated shortcut
   ```

2. **Check UAC settings**:
   ```bash
   # Temporary disable UAC (not recommended)
   # Or use auto-elevation for scripts
   ```

3. **Verify Windows version**:
   ```bash
   # Check Windows compatibility
   winver
   # Ensure Windows 10/11
   ```

### Chrome DevTools Issues

**Problem**: Cannot connect to Chrome DevTools
```
Chrome DevTools connection failed
```

**Solutions**:
1. **Start Chrome with debugging**:
   ```powershell
   # Create startup script
   $chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
   $arguments = "--remote-debugging-port=9222 --user-data-dir=C:\chrome-dev-session"
   Start-Process -FilePath $chromePath -ArgumentList $arguments
   ```

2. **Check Chrome processes**:
   ```powershell
   # Kill existing Chrome instances
   taskkill /f /im chrome.exe
   
   # Start with debugging enabled
   start chrome.exe --remote-debugging-port=9222
   ```

3. **Verify connection**:
   ```bash
   # Test DevTools API
   curl http://localhost:9222/json/version
   curl http://localhost:9222/json
   ```

## Android App Problems

### App Crashes

**Problem**: Voice Control app crashes unexpectedly
```
Application has stopped
```

**Solutions**:
1. **Check Android logs**:
   ```bash
   # View React Native logs
   npx react-native log-android
   
   # View system logs
   adb logcat | grep -i "voice"
   ```

2. **Clear app data**:
   - Go to Android Settings > Apps > Voice Control
   - Clear cache and data
   - Restart app

3. **Update app**:
   ```bash
   # Check for updates
   npm install
   npx react-native build-android --mode=debug
   ```

### Permission Issues

**Problem**: App requests permissions repeatedly
```
Permission denied
```

**Solutions**:
1. **Grant permissions manually**:
   - Android Settings > Apps > Voice Control > Permissions
   - Enable all required permissions

2. **Check permission declarations**:
   ```xml
   <!-- In AndroidManifest.xml -->
   <uses-permission android:name="android.permission.RECORD_AUDIO" />
   <uses-permission android:name="android.permission.INTERNET" />
   <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
   ```

### Network Discovery Issues

**Problem**: App cannot find server automatically
```
Network discovery failed
```

**Solutions**:
1. **Manual IP configuration**:
   - Open app settings
   - Enter server IP manually
   - Test connection

2. **Check network settings**:
   ```bash
   # Verify both devices on same network
   ipconfig  # Windows
   ifconfig  # Linux/macOS
   
   # Test connectivity
   ping android-device-ip
   ```

3. **Enable network discovery**:
   ```bash
   # Windows
   netsh advfirewall firewall add rule name="mDNS" dir=in action=allow protocol=UDP localport=5353
   
   # Linux
   sudo systemctl enable avahi-daemon
   sudo systemctl start avahi-daemon
   ```

## Docker Deployment Issues

### Container Startup Failures

**Problem**: Docker containers fail to start
```
Container exited with code 1
```

**Solutions**:
1. **Check container logs**:
   ```bash
   # View container logs
   docker-compose logs voice-control-server
   
   # Follow logs in real-time
   docker-compose logs -f
   ```

2. **Validate configuration**:
   ```bash
   # Check Docker Compose file
   docker-compose config
   
   # Validate environment files
   cat .env.production
   ```

3. **Resource issues**:
   ```bash
   # Check available resources
   docker system df
   docker system prune
   
   # Monitor resource usage
   docker stats
   ```

### Volume Mount Problems

**Problem**: Data not persisting between container restarts
```
Volume mount failed
```

**Solutions**:
1. **Check volume permissions**:
   ```bash
   # Set proper permissions
   sudo chown -R $USER:$USER ./storage
   
   # Verify volume mounts
   docker-compose config | grep -A 10 volumes
   ```

2. **Fix volume paths**:
   ```yaml
   # In docker-compose.yml
   volumes:
     - ./storage:/app/storage
     - ./configs:/app/configs
   ```

## Network and Security Issues

### Firewall Problems

**Problem**: Firewall blocking connections
```
Connection timeout
```

**Solutions**:
1. **Windows Firewall**:
   ```powershell
   # Allow ports
   netsh advfirewall firewall add rule name="Voice Control Server" dir=in action=allow protocol=TCP localport=8000
   netsh advfirewall firewall add rule name="Ollama" dir=in action=allow protocol=TCP localport=11434
   
   # Check active rules
   netsh advfirewall firewall show rule name="Voice Control Server"
   ```

2. **Linux Firewall (UFW)**:
   ```bash
   # Allow ports
   sudo ufw allow 8000/tcp
   sudo ufw allow 11434/tcp
   
   # Enable UFW
   sudo ufw enable
   
   # Check status
   sudo ufw status
   ```

3. **iptables**:
   ```bash
   # Add rules
   sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
   sudo iptables -A INPUT -p tcp --dport 11434 -j ACCEPT
   
   # Save rules
   sudo iptables-save
   ```

### SSL/TLS Issues

**Problem**: HTTPS/WSS connection failures
```
SSL certificate error
```

**Solutions**:
1. **Generate self-signed certificates**:
   ```bash
   # Create SSL directory
   mkdir -p ssl
   
   # Generate certificate
   openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes
   ```

2. **Update configuration**:
   ```bash
   # In production .env
   SSL_CERT_PATH=/path/to/ssl/cert.pem
   SSL_KEY_PATH=/path/to/ssl/key.pem
   ENABLE_HTTPS=true
   ```

3. **Certificate verification**:
   ```bash
   # Test certificate
   openssl x509 -in ssl/cert.pem -text -noout
   
   # Verify connection
   curl -k https://localhost:8000/health
   ```

## Log Analysis

### Common Log Patterns

| Pattern | Severity | Meaning | Action |
|---------|----------|---------|---------|
| `Connection timeout` | ERROR | Network connectivity issue | Check firewall, restart services |
| `Permission denied` | ERROR | Access control issue | Run as administrator, check permissions |
| `Model not found` | ERROR | Ollama model missing | Install model: `ollama pull <model>` |
| `Audio pipeline error` | ERROR | Audio processing failed | Check FFmpeg, microphone permissions |
| `High CPU usage` | WARN | Performance issue | Optimize models, reduce workers |
| `WebSocket disconnected` | INFO | Normal operation | Check network stability |

### Log Locations

```bash
# Application logs
voice-control-server/storage/logs/production.log
voice-control-server/storage/logs/audit.log

# System logs
/var/log/syslog                     # Linux
C:\Windows\System32\winevt\Logs\Application.evtx  # Windows

# Docker logs
docker-compose logs voice-control-server
docker logs voice-control-server

# Android logs
adb logcat | grep -i "voice"
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# In configuration file
DEBUG=true
LOG_LEVEL=DEBUG
WEBSOCKET_DEBUG=true
MCP_DEBUG=true
AUDIO_DEBUG=true

# Restart services to apply changes
```

### Log Analysis Tools

```bash
# Search for errors
grep -i "error" storage/logs/production.log | tail -20

# Monitor logs in real-time
tail -f storage/logs/production.log | grep -i "error"

# Analyze WebSocket connections
grep "WebSocket" storage/logs/production.log | grep -i "connect\|disconnect"

# Check performance metrics
grep "performance" storage/logs/production.log
```

## Emergency Procedures

### Service Recovery

**System unresponsive**:
1. **Restart services**:
   ```bash
   # Stop all services
   docker-compose down
   
   # Kill Python processes
   pkill -f "python.*start_server"
   
   # Restart services
   docker-compose up -d
   ```

2. **Reboot system if needed**:
   ```bash
   # Save work and shutdown
   sudo reboot
   ```

### Data Recovery

**Configuration corruption**:
1. **Restore from backup**:
   ```bash
   ./scripts/config-manager.sh restore -e production
   ```

2. **Reset to defaults**:
   ```bash
   # Copy example configuration
   cp configs/.env.production.example voice-control-server/.env
   ```

### Complete System Reset

**Last resort - full system reset**:
1. **Stop all services**:
   ```bash
   docker-compose down
   pkill -f "voice-control"
   ```

2. **Clear data**:
   ```bash
   rm -rf voice-control-server/storage/*
   rm -rf docker-compose.override.yml
   ```

3. **Reinstall**:
   ```bash
   ./scripts/setup-unix.sh  # or setup-windows.bat
   ```

### Emergency Contacts and Resources

- **Documentation**: Check `docs/` directory for guides
- **Configuration backup**: `backups/config/` directory
- **Logs**: Check `storage/logs/` for troubleshooting info
- **Test suite**: Run `./scripts/test-integration.sh` for diagnostics

This troubleshooting guide covers the most common issues encountered with the Voice Control Ecosystem. For issues not covered here, check the main documentation or run the integration test suite for comprehensive diagnostics.
