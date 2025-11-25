# API Documentation

This document describes the WebSocket protocol and message formats for communication between the React Native application and FastAPI server.

## WebSocket Connection

**URL:** `ws://<server-host>:<port>/ws`
**Protocol:** WebSocket with JSON message payloads
**Connection State Management:** Automatic reconnection with exponential backoff

## Message Format

All messages follow a standardized JSON structure:

```json
{
  "type": "message_type",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {},
  "message_id": "unique-uuid"
}
```

## Message Types

### 1. Connection Messages

#### Client → Server: Connection Request
```json
{
  "type": "connection_request",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "client_id": "app-12345",
    "client_version": "1.0.0",
    "capabilities": ["stt", "llm", "mcp"],
    "audio_format": {
      "sample_rate": 16000,
      "channels": 1,
      "bit_depth": 16,
      "encoding": "pcm"
    }
  },
  "message_id": "msg-001"
}
```

#### Server → Client: Connection Response
```json
{
  "type": "connection_response",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "status": "connected",
    "server_info": {
      "version": "1.0.0",
      "capabilities": ["stt", "llm", "mcp"],
      "supported_models": ["whisper-base", "llama2", "mistral"]
    },
    "session_id": "session-abc123"
  },
  "message_id": "msg-002"
}
```

### 2. Audio Stream Messages

#### Client → Server: Start Recording
```json
{
  "type": "audio_start",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "audio_config": {
      "sample_rate": 16000,
      "channels": 1,
      "bit_depth": 16,
      "encoding": "pcm"
    },
    "processing_options": {
      "stt_model": "whisper-base",
      "auto_process": true
    }
  },
  "message_id": "msg-003"
}
```

#### Client → Server: Audio Data (Base64 Encoded)
```json
{
  "type": "audio_data",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "audio_chunk": "base64_encoded_audio_data",
    "sequence": 0,
    "is_final": false
  },
  "message_id": "msg-004"
}
```

#### Client → Server: Stop Recording
```json
{
  "type": "audio_stop",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "sequence": 42,
    "duration_ms": 3500
  },
  "message_id": "msg-005"
}
```

### 3. Speech-to-Text Messages

#### Server → Client: STT Response
```json
{
  "type": "stt_response",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "text": "What is the weather like today?",
    "confidence": 0.92,
    "language": "en",
    "processing_time_ms": 1250,
    "audio_duration_ms": 3500,
    "segments": [
      {
        "text": "What is the weather like today?",
        "start": 0.0,
        "end": 3.5,
        "confidence": 0.92
      }
    ]
  },
  "message_id": "msg-006"
}
```

#### Client → Server: STT Request (Alternative)
```json
{
  "type": "stt_request",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "audio_url": "optional-audio-url",
    "model": "whisper-base",
    "language": "en"
  },
  "message_id": "msg-007"
}
```

### 4. LLM Integration Messages

#### Client → Server: LLM Request
```json
{
  "type": "llm_request",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "text": "What is the weather like today?",
    "model": "llama2",
    "context": "user_query",
    "options": {
      "temperature": 0.7,
      "max_tokens": 150,
      "stream": false
    }
  },
  "message_id": "msg-008"
}
```

#### Server → Client: LLM Response
```json
{
  "type": "llm_response",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "response": "The weather today looks sunny with temperatures around 22°C. Perfect for outdoor activities!",
    "model": "llama2",
    "processing_time_ms": 2100,
    "tokens_used": 45,
    "confidence": 0.88
  },
  "message_id": "msg-009"
}
```

#### Server → Client: LLM Stream Response (If streaming enabled)
```json
{
  "type": "llm_stream",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "chunk": "The weather today looks sunny",
    "is_final": false
  },
  "message_id": "msg-010"
}
```

### 5. MCP (Model Context Protocol) Messages

#### Client → Server: MCP Request
```json
{
  "type": "mcp_request",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "tool": "get_weather",
    "arguments": {
      "location": "Istanbul",
      "unit": "celsius"
    }
  },
  "message_id": "msg-011"
}
```

#### Server → Client: MCP Response
```json
{
  "type": "mcp_response",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "result": {
      "temperature": 22,
      "condition": "sunny",
      "humidity": 65,
      "wind_speed": 15
    },
    "success": true
  },
  "message_id": "msg-012"
}
```

### 6. Status and Error Messages

#### Server → Client: Processing Status
```json
{
  "type": "status_update",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "status": "processing_stt",
    "progress": 50,
    "message": "Converting speech to text..."
  },
  "message_id": "msg-013"
}
```

#### Server → Client: Error
```json
{
  "type": "error",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "session_id": "session-abc123",
    "error_type": "stt_processing_error",
    "message": "Failed to process audio: Unsupported format",
    "error_code": "AUDIO_FORMAT_INVALID",
    "details": {
      "supported_formats": ["pcm", "wav", "mp3"],
      "received_format": "aac"
    }
  },
  "message_id": "msg-014"
}
```

### 7. Control Messages

#### Server → Client: Heartbeat
```json
{
  "type": "heartbeat",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "server_time": "2025-11-24T23:56:11.538Z",
    "uptime": 3600
  },
  "message_id": "msg-015"
}
```

#### Client → Server: Heartbeat Response
```json
{
  "type": "heartbeat_response",
  "timestamp": "2025-11-24T23:56:11.538Z",
  "data": {
    "client_time": "2025-11-24T23:56:11.538Z"
  },
  "message_id": "msg-016"
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `AUDIO_FORMAT_INVALID` | Unsupported audio format or encoding |
| `AUDIO_TOO_LONG` | Audio duration exceeds maximum limit |
| `STT_PROCESSING_ERROR` | Speech-to-text processing failed |
| `LLM_PROCESSING_ERROR` | Language model processing failed |
| `MCP_TOOL_ERROR` | MCP tool execution failed |
| `NETWORK_ERROR` | Network connection issues |
| `AUTHENTICATION_ERROR` | Authentication failed |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INTERNAL_SERVER_ERROR` | Server internal error |

## Connection Lifecycle

### 1. Initial Connection
1. Client connects to WebSocket endpoint
2. Client sends `connection_request`
3. Server validates and sends `connection_response`
4. Connection established

### 2. Voice Processing Flow
1. Client sends `audio_start`
2. Client streams audio data with `audio_data`
3. Client sends `audio_stop`
4. Server processes STT and sends `stt_response`
5. (Optional) Client requests LLM processing with `llm_request`
6. Server sends `llm_response`

### 3. MCP Tool Usage
1. Client sends `mcp_request` with tool name and arguments
2. Server executes MCP tool
3. Server sends `mcp_response` with results

### 4. Heartbeat and Health Checks
1. Server periodically sends `heartbeat`
2. Client responds with `heartbeat_response`
3. If no response, server may disconnect client

## Audio Specifications

### Supported Formats
- **PCM**: 16-bit, mono/stereo
- **Sample Rates**: 16000 Hz (recommended), 22050 Hz, 44100 Hz
- **Channels**: 1 (mono) or 2 (stereo)
- **Encoding**: Linear PCM, base64 encoded for transmission

### Audio Chunk Size
- **Recommended**: 1024-4096 bytes per chunk
- **Maximum**: 16384 bytes per chunk
- **Chunk Duration**: 63-250ms at 16kHz sample rate

## Rate Limits

| Operation | Limit | Window |
|-----------|-------|--------|
| Connections | 10 | Per IP |
| STT Requests | 60 | Per minute |
| LLM Requests | 30 | Per minute |
| MCP Requests | 100 | Per minute |
| Audio Data | 10MB | Per session |

## Security Considerations

1. **Authentication**: JWT tokens in WebSocket headers
2. **Rate Limiting**: Prevent abuse and DoS attacks
3. **Audio Validation**: Validate audio format and size
4. **Input Sanitization**: Sanitize all text inputs
5. **CORS**: Restrict origins in production
6. **HTTPS**: Use HTTPS/WSS in production environments

## Example Usage

### React Native Implementation

```javascript
import { io } from 'socket.io-client';

class VoiceControlService {
  constructor(serverUrl) {
    this.socket = io(serverUrl, {
      transports: ['websocket'],
      autoConnect: false
    });
    this.setupEventHandlers();
  }

  connect() {
    this.socket.connect();
    
    this.socket.on('connect', () => {
      this.sendConnectionRequest();
    });
  }

  sendConnectionRequest() {
    this.socket.emit('connection_request', {
      type: 'connection_request',
      data: {
        client_id: 'app-12345',
        capabilities: ['stt', 'llm', 'mcp'],
        audio_format: {
          sample_rate: 16000,
          channels: 1,
          bit_depth: 16,
          encoding: 'pcm'
        }
      }
    });
  }

  startRecording() {
    this.socket.emit('audio_start', {
      type: 'audio_start',
      data: {
        processing_options: {
          stt_model: 'whisper-base',
          auto_process: true
        }
      }
    });
  }

  sendAudioChunk(audioData, isFinal = false) {
    this.socket.emit('audio_data', {
      type: 'audio_data',
      data: {
        audio_chunk: audioData, // base64 encoded
        sequence: this.sequence++,
        is_final: isFinal
      }
    });
  }

  setupEventHandlers() {
    this.socket.on('connection_response', (response) => {
      console.log('Connected:', response.data);
    });

    this.socket.on('stt_response', (response) => {
      console.log('STT Result:', response.data.text);
    });

    this.socket.on('llm_response', (response) => {
      console.log('LLM Response:', response.data.response);
    });
  }
}
```

## Testing

### WebSocket Testing with curl
```bash
# Using wscat
npm install -g wscat
wscat -c ws://localhost:8000/ws

# Send connection request
{"type":"connection_request","data":{"client_id":"test-client"}}
```

### Testing with Python
```python
import websockets
import json

async def test_connection():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Send connection request
        message = {
            "type": "connection_request",
            "data": {"client_id": "test-client"}
        }
        await websocket.send(json.dumps(message))
        
        # Receive response
        response = await websocket.recv()
        print(response)

# Run test
import asyncio
asyncio.run(test_connection())
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-24 | Initial API specification |
| | | Core WebSocket protocol |
| | | STT and LLM integration |
| | | MCP protocol support |