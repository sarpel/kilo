# Voice Control Server - Complete Implementation

This is the complete Python FastAPI server implementation for the voice control ecosystem. The server provides comprehensive speech-to-text, language model integration, and system automation capabilities through the MCP (Model Context Protocol).

## 🚀 Features

### Core Features
- **Real-time Speech-to-Text**: Powered by faster-whisper with multiple model support
- **Language Model Integration**: Ollama integration with gemma3 and other models
- **MCP Protocol Support**: Complete Model Context Protocol implementation
- **WebSocket Streaming**: Real-time audio streaming with low latency
- **System Automation**: Windows and browser automation capabilities

### Advanced Features
- **Non-blocking Pipeline**: Async/await throughout for optimal performance
- **Multi-language Support**: Automatic language detection and translation
- **Audio Processing**: Noise reduction, normalization, and VAD
- **Function Calling**: Intelligent mapping between LLM responses and MCP tools
- **Error Handling**: Comprehensive error handling and recovery
- **Monitoring**: Performance metrics and audit logging
- **Rate Limiting**: Built-in rate limiting and security measures

## 🏗️ Architecture

```
voice-control-server/
├── src/
│   ├── main.py                 # FastAPI application entry point
│   ├── config/
│   │   └── settings.py         # Configuration management
│   ├── models/
│   │   └── schemas.py          # Pydantic models for API
│   ├── services/
│   │   ├── stt_service.py      # Speech-to-text service
│   │   ├── llm_service.py      # Language model service
│   │   ├── mcp_service.py      # MCP protocol service
│   │   └── audio_pipeline.py   # Audio processing pipeline
│   ├── websocket/
│   │   ├── connection_manager.py # WebSocket connection management
│   │   └── handlers.py         # WebSocket message handlers
│   ├── integrations/
│   │   ├── windows_mcp.py      # Windows system control
│   │   └── chrome_devtools_mcp.py # Browser automation
│   └── utils/
│       └── logger.py           # Logging and monitoring
├── tests/
│   └── test_server.py          # Comprehensive test suite
├── requirements.txt            # Python dependencies
├── start_server.py            # Startup script
└── README.md                  # This file
```

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB+ RAM (8GB recommended for model loading)
- Windows 10/11 (for Windows MCP integration)
- Chrome browser (for Chrome DevTools integration)

### Dependencies
- Ollama server running locally (for LLM support)
- Chrome browser with DevTools enabled (optional)
- Microsoft Visual C++ Redistributable (Windows)

## 🛠️ Installation

1. **Clone and setup**:
```bash
cd voice-control-server
python -m venv venv

# Windows
venv\\Scripts\\activate

# Linux/macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

2. **Install Ollama** (for LLM support):
```bash
# Download from https://ollama.ai
ollama pull gemma2  # or your preferred model
ollama serve        # Start Ollama server
```

3. **Configure Chrome DevTools** (optional, for browser automation):
   - Start Chrome with `--remote-debugging-port=9222`
   - Or enable "Remote Debugging" in Chrome settings

## 🚀 Running the Server

### Quick Start
```bash
python start_server.py
```

This will:
1. Check all dependencies
2. Validate configuration
3. Initialize services
4. Start the FastAPI server

### Direct Run
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### With Debug Mode
```bash
python -c "from src.config.settings import get_settings; import os; os.environ['DEBUG']='true'; import uvicorn; uvicorn.run('src.main:app', host='0.0.0.0', port=8000, reload=True, log_level='debug')"
```

## 🧪 Testing

Run the comprehensive test suite:
```bash
python tests/test_server.py
```

Run specific test categories:
```bash
# Basic functionality tests
python -c "from tests.test_server import run_basic_tests; run_basic_tests()"

# Async integration tests  
python -c "import asyncio; from tests.test_server import run_async_tests; asyncio.run(run_async_tests())"
```

## 📡 API Endpoints

### HTTP Endpoints
- `GET /health` - Server health check
- `GET /api/config` - Server configuration
- `GET /api/status` - Detailed status
- `POST /api/reload-models` - Reload AI models
- `GET /files/{path}` - Static file serving

### WebSocket Endpoints
- `WS /ws` - Main WebSocket endpoint for voice control

### WebSocket Message Types
- `connection_request` / `connection_response` - Connection establishment
- `audio_start` / `audio_data` / `audio_stop` - Audio streaming
- `stt_request` / `stt_response` - Speech-to-text
- `llm_request` / `llm_response` - Language model processing
- `mcp_request` / `mcp_response` - MCP tool execution
- `status_update` / `error` - Status and error messages
- `heartbeat` / `heartbeat_response` - Connection health

## 🔧 Configuration

### Environment Variables (.env)
```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
ENVIRONMENT=development

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000","http://10.0.2.2:3000"]

# STT Configuration
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
STT_CONFIDENCE_THRESHOLD=0.7

# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
LLM_MAX_TOKENS=150
LLM_TEMPERATURE=0.7

# Audio Configuration
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
AUDIO_BIT_DEPTH=16
```

### Advanced Configuration

The server supports extensive configuration through `src/config/settings.py`. Key areas:

- **Audio Processing**: Sample rates, chunk sizes, buffer limits
- **Security**: Rate limiting, CORS, authentication
- **Performance**: Worker processes, connection limits, timeouts
- **Logging**: Log levels, file output, audit logging
- **Monitoring**: Metrics collection, health checks

## 🛠️ MCP Tools

### Built-in Tools
- `echo` - Echo messages for testing
- `calculate` - Mathematical calculations
- `get_time` - Current time retrieval
- `get_system_info` - System information

### Windows Tools
- `list_processes` - List running processes
- `kill_process` - Terminate processes
- `start_process` - Launch applications
- `list_files` - File system operations
- `read_file` / `write_file` - File I/O
- `list_windows` - Window management
- `focus_window` - Window control
- `resize_window` / `minimize_window` / `maximize_window` - Window operations
- `run_command` - Shell command execution

### Chrome DevTools Tools
- `chrome_connect` / `chrome_disconnect` - Connection management
- `chrome_navigate` - Navigate to URLs
- `chrome_screenshot` - Capture screenshots
- `chrome_click` - Click elements
- `chrome_type` - Type text
- `chrome_get_text` - Extract text
- `chrome_get_html` - Get page source
- `chrome_scroll` - Page scrolling
- `chrome_reload` - Page reload
- `chrome_execute_script` - JavaScript execution

## 🔄 Processing Pipeline

The server implements a complete audio processing pipeline:

1. **Audio Reception**: WebSocket streaming with chunk management
2. **Speech-to-Text**: Faster-whisper with confidence scoring
3. **Language Processing**: LLM with function calling extraction
4. **Tool Execution**: MCP protocol with tool mapping
5. **Response Generation**: Structured response formatting

### Pipeline Features
- **Non-blocking**: Async/await throughout
- **Error Recovery**: Graceful degradation and retry logic
- **Performance Monitoring**: Comprehensive metrics collection
- **Audit Logging**: Complete action tracking
- **Memory Management**: Efficient buffer handling

## 🔒 Security Features

### Built-in Security
- **Input Validation**: Pydantic models for all inputs
- **Rate Limiting**: Per-IP connection and request limits
- **CORS Protection**: Configurable origin restrictions
- **Error Handling**: Sanitized error messages
- **Resource Limits**: Audio size and duration limits
- **Audit Trail**: Complete security event logging

### Best Practices
- **No Hardcoded Secrets**: Environment variable configuration
- **Input Sanitization**: All user inputs validated
- **Output Encoding**: Proper response encoding
- **Connection Management**: Secure WebSocket handling

## 📊 Monitoring and Logging

### Logging Features
- **Structured Logging**: JSON-formatted logs
- **Colorized Console**: Easy-to-read terminal output
- **File Rotation**: Automated log file management
- **Performance Metrics**: Request timing and resource usage
- **Audit Trail**: Security and user action logging

### Metrics Collection
- **Processing Times**: STT, LLM, and MCP execution times
- **Resource Usage**: Memory and CPU monitoring
- **Connection Statistics**: WebSocket and HTTP metrics
- **Error Rates**: Failure tracking and analysis

## 🔧 Development

### Development Mode
```bash
export DEBUG=true
python start_server.py
```

### Code Quality
- **Type Hints**: Full type annotation coverage
- **Documentation**: Comprehensive docstrings
- **Error Handling**: Robust exception management
- **Testing**: Comprehensive test coverage
- **Logging**: Detailed debugging information

### Architecture Patterns
- **Dependency Injection**: Service container pattern
- **Factory Pattern**: Configuration and service creation
- **Observer Pattern**: Event handling and notifications
- **Strategy Pattern**: Algorithm selection and switching
- **Decorator Pattern**: Cross-cutting concerns (logging, timing)

## 📝 Usage Examples

### React Native Integration
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

// Send connection request
ws.send(JSON.stringify({
  type: 'connection_request',
  data: {
    client_id: 'react-native-app',
    capabilities: ['stt', 'llm', 'mcp'],
    audio_format: {
      sample_rate: 16000,
      channels: 1,
      bit_depth: 16,
      encoding: 'pcm'
    }
  }
}));

// Stream audio
ws.send(JSON.stringify({
  type: 'audio_start',
  data: {
    session_id: 'session-123',
    processing_options: {
      stt_model: 'base',
      auto_process: true
    }
  }
}));

// Send audio chunks (base64 encoded)
ws.send(JSON.stringify({
  type: 'audio_data',
  data: {
    session_id: 'session-123',
    audio_chunk: base64AudioData,
    sequence: 0,
    is_final: false
  }
}));
```

### Direct API Usage
```bash
# Health check
curl http://localhost:8000/health

# Server status
curl http://localhost:8000/api/status

# Get configuration
curl http://localhost:8000/api/config
```

## 🐛 Troubleshooting

### Common Issues

1. **Ollama Connection Failed**
   - Ensure Ollama is running: `ollama serve`
   - Check default port: `http://localhost:11434`
   - Verify model is installed: `ollama list`

2. **Chrome DevTools Not Working**
   - Start Chrome with: `chrome --remote-debugging-port=9222`
   - Or enable in Chrome settings

3. **Port Already in Use**
   - Change PORT in .env file
   - Or kill process using the port: `lsof -ti:8000 | xargs kill`

4. **STT Model Loading Failed**
   - Check available disk space
   - Verify model name in configuration
   - Ensure sufficient RAM for model loading

### Debug Mode
Enable debug logging:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python start_server.py
```

### Log Files
Check logs in the `storage/logs/` directory:
- `voice_control_server.log` - Main application logs
- `audit.log` - Security and audit trail

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a virtual environment
3. Install development dependencies
4. Run tests to verify setup
5. Make changes with tests
6. Submit pull request

### Code Standards
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Include comprehensive docstrings
- Write tests for new features
- Update documentation

## 📄 License

This project is part of the Voice Control ecosystem. See the main project license for details.

## 🙏 Acknowledgments

- **Faster-Whisper** - Speech-to-text engine
- **Ollama** - Language model serving
- **FastAPI** - Web framework
- **Pydantic** - Data validation
- **React Native** - Mobile application framework

---

**Ready to start controlling your computer with voice commands!** 🎤💻