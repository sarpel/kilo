"""
Voice Control Server

Complete Python FastAPI server for voice control ecosystem.
Provides speech-to-text, language model integration, and system automation via MCP protocol.
"""

__version__ = "1.0.0"
__author__ = "Voice Control Team"
__description__ = "FastAPI server for voice control ecosystem with STT, LLM, and MCP support"

# Main exports
from src.main import app
from src.services.stt_service import STTService
from src.services.llm_service import LLMService
from src.services.mcp_service import MCPService
from src.services.audio_pipeline import get_audio_processor
from src.websocket.handlers import WebSocketHandler
from src.websocket.connection_manager import ConnectionManager

__all__ = [
    "app",
    "STTService", 
    "LLMService",
    "MCPService",
    "get_audio_processor",
    "WebSocketHandler",
    "ConnectionManager"
]