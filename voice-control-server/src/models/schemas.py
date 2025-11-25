"""
Pydantic models for API message schemas

Defines all message types for WebSocket communication between
the React Native app and FastAPI server.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    """WebSocket message types"""
    CONNECTION_REQUEST = "connection_request"
    CONNECTION_RESPONSE = "connection_response"
    AUDIO_START = "audio_start"
    AUDIO_DATA = "audio_data"
    AUDIO_STOP = "audio_stop"
    STT_REQUEST = "stt_request"
    STT_RESPONSE = "stt_response"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    LLM_STREAM = "llm_stream"
    MCP_REQUEST = "mcp_request"
    MCP_RESPONSE = "mcp_response"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_RESPONSE = "heartbeat_response"


class AudioFormat(BaseModel):
    """Audio format configuration"""
    sample_rate: int = Field(default=16000, description="Sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")
    bit_depth: int = Field(default=16, description="Audio bit depth")
    encoding: str = Field(default="pcm", description="Audio encoding")


class ProcessingOptions(BaseModel):
    """Audio processing options"""
    stt_model: str = Field(default="base", description="STT model to use")
    auto_process: bool = Field(default=True, description="Auto process audio")
    language: str = Field(default="en", description="Language for processing")
    temperature: Optional[float] = Field(default=None, description="LLM temperature")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens for LLM")


class ConnectionRequest(BaseModel):
    """Client connection request"""
    client_id: str = Field(..., description="Unique client identifier")
    client_version: str = Field(default="1.0.0", description="Client version")
    capabilities: List[str] = Field(..., description="Client capabilities")
    audio_format: AudioFormat = Field(..., description="Client audio format")


class ServerInfo(BaseModel):
    """Server information"""
    version: str = Field(..., description="Server version")
    capabilities: List[str] = Field(..., description="Server capabilities")
    supported_models: List[str] = Field(..., description="Supported AI models")


class ConnectionResponse(BaseModel):
    """Server connection response"""
    status: str = Field(..., description="Connection status")
    server_info: ServerInfo = Field(..., description="Server information")
    session_id: str = Field(..., description="Unique session identifier")


class AudioStart(BaseModel):
    """Start audio recording"""
    session_id: str = Field(..., description="Session identifier")
    audio_config: AudioFormat = Field(..., description="Audio configuration")
    processing_options: ProcessingOptions = Field(..., description="Processing options")


class AudioData(BaseModel):
    """Audio data chunk"""
    session_id: str = Field(..., description="Session identifier")
    audio_chunk: str = Field(..., description="Base64 encoded audio data")
    sequence: int = Field(..., description="Chunk sequence number")
    is_final: bool = Field(default=False, description="Is this the final chunk")


class AudioStop(BaseModel):
    """Stop audio recording"""
    session_id: str = Field(..., description="Session identifier")
    sequence: int = Field(..., description="Final chunk sequence number")
    duration_ms: int = Field(..., description="Total duration in milliseconds")


class STTSegment(BaseModel):
    """STT transcription segment"""
    text: str = Field(..., description="Segment text")
    start: float = Field(..., description="Start timestamp")
    end: float = Field(..., description="End timestamp")
    confidence: float = Field(..., description="Segment confidence")


class STTResponse(BaseModel):
    """Speech-to-text response"""
    session_id: str = Field(..., description="Session identifier")
    text: str = Field(..., description="Transcribed text")
    confidence: float = Field(..., description="Overall confidence")
    language: str = Field(..., description="Detected language")
    processing_time_ms: int = Field(..., description="Processing time")
    audio_duration_ms: int = Field(..., description="Audio duration")
    segments: List[STTSegment] = Field(..., description="Text segments")


class STTRequest(BaseModel):
    """Speech-to-text request"""
    session_id: str = Field(..., description="Session identifier")
    audio_url: Optional[str] = Field(default=None, description="Audio file URL")
    model: str = Field(default="base", description="STT model")
    language: str = Field(default="en", description="Language")


class LLMOptions(BaseModel):
    """LLM generation options"""
    temperature: float = Field(default=0.7, description="Model temperature")
    max_tokens: int = Field(default=150, description="Maximum tokens")
    stream: bool = Field(default=False, description="Stream response")


class LLMRequest(BaseModel):
    """Language model request"""
    session_id: str = Field(..., description="Session identifier")
    text: str = Field(..., description="Input text")
    model: str = Field(default="llama2", description="LLM model")
    context: str = Field(default="user_query", description="Request context")
    options: LLMOptions = Field(default_factory=LLMOptions, description="Generation options")


class LLMResponse(BaseModel):
    """Language model response"""
    session_id: str = Field(..., description="Session identifier")
    response: str = Field(..., description="Model response")
    model: str = Field(..., description="Model used")
    processing_time_ms: int = Field(..., description="Processing time")
    tokens_used: int = Field(..., description="Tokens consumed")
    confidence: float = Field(..., description="Response confidence")


class LLMStream(BaseModel):
    """Streaming LLM response chunk"""
    session_id: str = Field(..., description="Session identifier")
    chunk: str = Field(..., description="Response chunk")
    is_final: bool = Field(default=False, description="Is this final chunk")


class MCPRequest(BaseModel):
    """Model Context Protocol request"""
    session_id: str = Field(..., description="Session identifier")
    tool: str = Field(..., description="MCP tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class MCPResult(BaseModel):
    """MCP tool execution result"""
    temperature: Optional[float] = None
    condition: Optional[str] = None
    humidity: Optional[int] = None
    wind_speed: Optional[int] = None
    # Add other common result fields as needed
    raw_result: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """Model Context Protocol response"""
    session_id: str = Field(..., description="Session identifier")
    result: Dict[str, Any] = Field(..., description="Tool execution result")
    success: bool = Field(..., description="Execution success")


class StatusUpdate(BaseModel):
    """Processing status update"""
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="Processing status")
    progress: int = Field(..., description="Progress percentage")
    message: str = Field(..., description="Status message")


class ErrorDetails(BaseModel):
    """Error details"""
    supported_formats: Optional[List[str]] = None
    received_format: Optional[str] = None
    # Add other error details as needed


class Error(BaseModel):
    """Error message"""
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    error_type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[ErrorDetails] = Field(default=None, description="Additional error details")


class Heartbeat(BaseModel):
    """Heartbeat message"""
    server_time: str = Field(..., description="Server timestamp")
    uptime: int = Field(..., description="Server uptime in seconds")


class HeartbeatResponse(BaseModel):
    """Heartbeat response"""
    client_time: str = Field(..., description="Client timestamp")


class WebSocketMessage(BaseModel):
    """Base WebSocket message"""
    type: MessageType = Field(..., description="Message type")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Message timestamp")
    data: Dict[str, Any] = Field(..., description="Message data")
    message_id: str = Field(..., description="Unique message identifier")


# Utility functions for message creation
def create_connection_response(status: str, server_info: ServerInfo, session_id: str) -> WebSocketMessage:
    """Create connection response message"""
    return WebSocketMessage(
        type=MessageType.CONNECTION_RESPONSE,
        data=ConnectionResponse(
            status=status,
            server_info=server_info,
            session_id=session_id
        ).dict(),
        message_id=f"msg_{int(datetime.utcnow().timestamp() * 1000)}"
    )


def create_error_message(error_type: str, message: str, error_code: str, session_id: str = None) -> WebSocketMessage:
    """Create error message"""
    return WebSocketMessage(
        type=MessageType.ERROR,
        data=Error(
            session_id=session_id,
            error_type=error_type,
            message=message,
            error_code=error_code
        ).dict(),
        message_id=f"error_{int(datetime.utcnow().timestamp() * 1000)}"
    )


def create_status_update(session_id: str, status: str, progress: int, message: str) -> WebSocketMessage:
    """Create status update message"""
    return WebSocketMessage(
        type=MessageType.STATUS_UPDATE,
        data=StatusUpdate(
            session_id=session_id,
            status=status,
            progress=progress,
            message=message
        ).dict(),
        message_id=f"status_{int(datetime.utcnow().timestamp() * 1000)}"
    )


# Configuration models
class STTConfig(BaseModel):
    """STT service configuration"""
    model: str = Field(default="base", description="Whisper model")
    device: str = Field(default="cpu", description="Compute device")
    compute_type: str = Field(default="int8", description="Compute type")
    confidence_threshold: float = Field(default=0.7, description="Confidence threshold")
    max_duration: int = Field(default=300, description="Max audio duration (seconds)")


class LLMConfig(BaseModel):
    """LLM service configuration"""
    base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    model: str = Field(default="llama2", description="Default model")
    timeout: int = Field(default=30, description="Request timeout")
    max_tokens: int = Field(default=150, description="Max tokens")
    temperature: float = Field(default=0.7, description="Temperature")
    system_prompt: str = Field(default="You are a helpful voice assistant.", description="System prompt")


class MCPConfig(BaseModel):
    """MCP service configuration"""
    timeout: int = Field(default=10, description="MCP timeout")
    max_results: int = Field(default=100, description="Max results")
    enabled_tools: List[str] = Field(default=["calculator"], description="Enabled tools")


class ServerConfig(BaseModel):
    """Complete server configuration"""
    stt: STTConfig = Field(default_factory=STTConfig, description="STT configuration")
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM configuration")
    mcp: MCPConfig = Field(default_factory=MCPConfig, description="MCP configuration")
    audio: AudioFormat = Field(default_factory=AudioFormat, description="Audio configuration")