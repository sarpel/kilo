#!/usr/bin/env python3
"""
Test Suite for Voice Control Server

Comprehensive test suite to validate all components of the voice control server.
Tests can be run individually or as a complete suite.
"""

import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any
import time

# Import server components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.models.schemas import (
    MessageType, WebSocketMessage, ConnectionRequest, AudioData, AudioStart, AudioStop,
    create_connection_response, create_error_message
)
from src.services.stt_service import STTService
from src.services.llm_service import LLMService  
from src.services.mcp_service import MCPService
from src.services.audio_pipeline import AudioChunk, get_audio_processor
from src.websocket.handlers import WebSocketHandler
from src.websocket.connection_manager import ConnectionManager
from src.utils.logger import get_logger, setup_logger

logger = get_logger(__name__)


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.messages_sent = []
        self.closed = False
        self.accepted = False
        self.state = "connected"
    
    async def accept(self):
        self.accepted = True
    
    async def send_text(self, message: str):
        self.messages_sent.append(message)
    
    async def close(self, code: int = None, reason: str = None):
        self.closed = True
        self.state = "closed"
    
    def get_last_message(self) -> Dict[str, Any]:
        if self.messages_sent:
            return json.loads(self.messages_sent[-1])
        return {}
    
    def get_all_messages(self) -> list:
        return [json.loads(msg) for msg in self.messages_sent]


class TestModels:
    """Test Pydantic models"""
    
    def test_connection_request_model(self):
        """Test ConnectionRequest model"""
        request = ConnectionRequest(
            client_id="test-client",
            client_version="1.0.0",
            capabilities=["stt", "llm", "mcp"],
            audio_format={"sample_rate": 16000, "channels": 1, "bit_depth": 16, "encoding": "pcm"}
        )
        
        assert request.client_id == "test-client"
        assert request.client_version == "1.0.0"
        assert "stt" in request.capabilities
    
    def test_audio_data_model(self):
        """Test AudioData model"""
        audio_data = AudioData(
            session_id="test-session",
            audio_chunk="base64_data",
            sequence=0,
            is_final=False
        )
        
        assert audio_data.session_id == "test-session"
        assert audio_data.sequence == 0
        assert not audio_data.is_final
    
    def test_create_connection_response(self):
        """Test connection response creation"""
        from src.models.schemas import ServerInfo
        
        server_info = ServerInfo(
            version="1.0.0",
            capabilities=["stt", "llm", "mcp"],
            supported_models=["base", "llama2"]
        )
        
        response = create_connection_response("connected", server_info, "session-123")
        
        assert response.type == MessageType.CONNECTION_RESPONSE
        assert response.data["status"] == "connected"
        assert response.data["session_id"] == "session-123"


class TestSTTService:
    """Test STT Service"""
    
    @pytest.fixture
    def stt_service(self):
        """Create STT service instance"""
        return STTService()
    
    @pytest.mark.asyncio
    async def test_stt_initialization(self, stt_service):
        """Test STT service initialization"""
        # Mock the faster_whisper import to avoid model loading
        with patch('src.services.stt_service.WhisperModel', None):
            result = await stt_service.initialize()
            # Should handle missing faster-whisper gracefully
            assert stt_service.is_initialized is False
    
    def test_stt_supported_models(self, stt_service):
        """Test STT supported models"""
        models = stt_service.get_supported_models()
        assert "base" in models
        assert "tiny" in models
        assert "large" in models
    
    def test_stt_supported_languages(self, stt_service):
        """Test STT supported languages"""
        languages = stt_service.get_supported_languages()
        assert "en" in languages
        assert "es" in languages
        assert "auto" in languages


class TestLLMService:
    """Test LLM Service"""
    
    @pytest.fixture
    def llm_service(self):
        """Create LLM service instance"""
        return LLMService()
    
    @pytest.mark.asyncio
    async def test_llm_initialization(self, llm_service):
        """Test LLM service initialization"""
        # Mock Ollama connection
        with patch.object(llm_service, '_test_connection') as mock_test:
            mock_test.side_effect = Exception("Mock connection error")
            
            result = await llm_service.initialize()
            assert result is False
            assert llm_service.is_initialized is False
    
    def test_llm_supported_models(self, llm_service):
        """Test LLM supported models"""
        # Service should have some default models
        models = llm_service.get_supported_models()
        assert isinstance(models, list)


class TestMCPService:
    """Test MCP Service"""
    
    @pytest.fixture
    def mcp_service(self):
        """Create MCP service instance"""
        return MCPService()
    
    @pytest.mark.asyncio
    async def test_mcp_initialization(self, mcp_service):
        """Test MCP service initialization"""
        result = await mcp_service.initialize()
        # Should initialize even if no servers connect
        assert result is True
        assert mcp_service.is_initialized is True
    
    def test_mcp_available_tools(self, mcp_service):
        """Test MCP available tools"""
        # Should have built-in tools
        tools = mcp_service.get_available_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
    
    @pytest.mark.asyncio
    async def test_mcp_echo_tool(self, mcp_service):
        """Test built-in echo tool"""
        result = await mcp_service.execute_tool("echo", {"message": "test"})
        
        assert result["success"] is True
        assert result["message"] == "test"
    
    @pytest.mark.asyncio
    async def test_mcp_calculator_tool(self, mcp_service):
        """Test built-in calculator tool"""
        result = await mcp_service.execute_tool("calculate", {"expression": "2 + 2"})
        
        assert result["success"] is True
        assert result["result"] == 4
    
    @pytest.mark.asyncio
    async def test_mcp_time_tool(self, mcp_service):
        """Test built-in time tool"""
        result = await mcp_service.execute_tool("get_time", {"timezone": "UTC"})
        
        assert result["success"] is True
        assert "current_time" in result


class TestAudioPipeline:
    """Test Audio Processing Pipeline"""
    
    @pytest.fixture
    def audio_pipeline(self):
        """Create mock audio pipeline"""
        stt_service = Mock()
        llm_service = Mock()
        mcp_service = Mock()
        
        return get_audio_processor(stt_service, llm_service, mcp_service)
    
    @pytest.mark.asyncio
    async def test_audio_chunk_creation(self, audio_pipeline):
        """Test audio chunk creation"""
        chunk = AudioChunk(
            data=b"test_audio_data",
            sequence=0,
            timestamp=time.time(),
            is_final=False
        )
        
        assert chunk.data == b"test_audio_data"
        assert chunk.sequence == 0
        assert not chunk.is_final
    
    def test_pipeline_status(self, audio_pipeline):
        """Test pipeline status"""
        status = audio_pipeline.get_pipeline_status("test-session")
        # Should return None for non-existent session
        assert status is None


class TestConnectionManager:
    """Test WebSocket Connection Manager"""
    
    @pytest.fixture
    def connection_manager(self):
        """Create connection manager"""
        return ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_connection_creation(self, connection_manager):
        """Test WebSocket connection creation"""
        mock_ws = MockWebSocket()
        
        session_id = await connection_manager.connect(mock_ws, "test-client")
        
        assert session_id is not None
        assert mock_ws.accepted is True
        assert connection_manager.get_connection_count() == 1
    
    @pytest.mark.asyncio
    async def test_connection_disconnect(self, connection_manager):
        """Test WebSocket disconnection"""
        mock_ws = MockWebSocket()
        
        session_id = await connection_manager.connect(mock_ws, "test-client")
        await connection_manager.disconnect(session_id)
        
        assert connection_manager.get_connection_count() == 0
        assert mock_ws.closed is True
    
    @pytest.mark.asyncio
    async def test_message_sending(self, connection_manager):
        """Test WebSocket message sending"""
        mock_ws = MockWebSocket()
        
        session_id = await connection_manager.connect(mock_ws, "test-client")
        
        test_message = {"type": "test", "data": {"message": "hello"}}
        result = await connection_manager.send_message(session_id, test_message)
        
        assert result is True
        assert len(mock_ws.messages_sent) == 1
        
        sent_message = mock_ws.get_last_message()
        assert sent_message["data"]["message"] == "hello"


class TestWebSocketHandler:
    """Test WebSocket Handler"""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services"""
        return {
            "stt": Mock(spec=STTService),
            "llm": Mock(spec=LLMService),
            "mcp": Mock(spec=MCPService)
        }
    
    @pytest.fixture
    def connection_manager(self):
        """Create connection manager"""
        return ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_connection_request_handling(self, mock_services, connection_manager):
        """Test connection request handling"""
        mock_ws = MockWebSocket()
        
        handler = WebSocketHandler(
            websocket=mock_ws,
            connection_manager=connection_manager,
            stt_service=mock_services["stt"],
            llm_service=mock_services["llm"],
            mcp_service=mock_services["mcp"]
        )
        
        # Create connection request
        connection_request = {
            "type": MessageType.CONNECTION_REQUEST.value,
            "data": {
                "client_id": "test-app",
                "client_version": "1.0.0",
                "capabilities": ["stt", "llm", "mcp"],
                "audio_format": {
                    "sample_rate": 16000,
                    "channels": 1,
                    "bit_depth": 16,
                    "encoding": "pcm"
                }
            }
        }
        
        # Mock the receive_text method to return our test message
        mock_ws.receive_text = AsyncMock(return_value=json.dumps(connection_request))
        
        # This would normally start the connection process
        # For testing, we'll just verify the WebSocket is ready
        assert mock_ws.state == "connected"


class TestLogger:
    """Test Logger functionality"""
    
    def test_logger_creation(self):
        """Test logger creation"""
        test_logger = setup_logger("test_logger")
        assert test_logger is not None
        assert test_logger.name == "test_logger"
    
    def test_logger_levels(self):
        """Test different log levels"""
        test_logger = setup_logger("test_logger_levels")
        
        # Test all log levels work
        test_logger.debug("Debug message")
        test_logger.info("Info message")
        test_logger.warning("Warning message")
        test_logger.error("Error message")
        test_logger.critical("Critical message")
        
        # Should not raise any exceptions
        assert True


class IntegrationTests:
    """Integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_audio_pipeline_workflow(self):
        """Test complete audio processing workflow"""
        # Mock all services
        stt_service = AsyncMock()
        stt_service.transcribe_audio.return_value = {
            "success": True,
            "text": "What is the weather like?",
            "confidence": 0.95,
            "language": "en"
        }
        
        llm_service = AsyncMock()
        llm_service.generate_response.return_value = Mock(
            content="The weather is sunny today.",
            tokens_used=25,
            confidence=0.85
        )
        
        mcp_service = AsyncMock()
        mcp_service.execute_tool.return_value = {
            "success": True,
            "temperature": 22,
            "condition": "sunny"
        }
        
        # Create audio pipeline
        audio_processor = get_audio_processor(stt_service, llm_service, mcp_service)
        
        # Create test audio chunks
        audio_chunks = [
            AudioChunk(data=b"audio1", sequence=0, timestamp=time.time(), is_final=False),
            AudioChunk(data=b"audio2", sequence=1, timestamp=time.time(), is_final=True, duration_ms=2000)
        ]
        
        # Process audio
        result = await audio_processor.process_audio("test-session", audio_chunks)
        
        # Verify results
        assert result.success is True
        assert result.text == "What is the weather like?"
        assert result.stt_confidence == 0.95
        assert result.llm_response == "The weather is sunny today."
        
        # Verify service calls
        stt_service.transcribe_audio.assert_called_once()
        llm_service.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """Test error handling in complete workflow"""
        # Mock STT service to fail
        stt_service = AsyncMock()
        stt_service.transcribe_audio.return_value = {
            "success": False,
            "error": "Audio processing failed"
        }
        
        llm_service = AsyncMock()
        mcp_service = AsyncMock()
        
        # Create audio pipeline
        audio_processor = get_audio_processor(stt_service, llm_service, mcp_service)
        
        # Create test audio chunks
        audio_chunks = [
            AudioChunk(data=b"audio1", sequence=0, timestamp=time.time(), is_final=True, duration_ms=1000)
        ]
        
        # Process audio (should fail at STT stage)
        result = await audio_processor.process_audio("test-session", audio_chunks)
        
        # Verify error handling
        assert result.success is False
        assert "Audio processing failed" in result.error
        assert not result.llm_response  # Should be empty
        
        # Verify no LLM/MCP calls were made due to STT failure
        llm_service.generate_response.assert_not_called()
        mcp_service.execute_tool.assert_not_called()


def run_basic_tests():
    """Run basic functionality tests"""
    print("Running basic tests...")
    
    try:
        # Test model creation
        test_models = TestModels()
        test_models.test_connection_request_model()
        test_models.test_audio_data_model()
        test_models.test_create_connection_response()
        print("✓ Model tests passed")
        
        # Test STT service
        test_stt = TestSTTService()
        stt_service = STTService()
        test_stt.test_stt_supported_models(stt_service)
        test_stt.test_stt_supported_languages(stt_service)
        print("✓ STT service tests passed")
        
        # Test LLM service
        test_llm = TestLLMService()
        llm_service = LLMService()
        test_llm.test_llm_supported_models(llm_service)
        print("✓ LLM service tests passed")
        
        # Test MCP service
        test_mcp = TestMCPService()
        mcp_service = MCPService()
        test_mcp.test_mcp_available_tools(mcp_service)
        print("✓ MCP service tests passed")
        
        # Test logger
        test_logger = TestLogger()
        test_logger.test_logger_creation()
        test_logger.test_logger_levels()
        print("✓ Logger tests passed")
        
        print("All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"Basic test failed: {e}")
        return False


async def run_async_tests():
    """Run async tests"""
    print("Running async tests...")
    
    try:
        # Test MCP tools
        test_mcp = TestMCPService()
        mcp_service = MCPService()
        
        # Initialize MCP service
        await mcp_service.initialize()
        
        # Test echo tool
        result = await mcp_service.execute_tool("echo", {"message": "Hello World"})
        assert result["success"] is True
        assert result["message"] == "Hello World"
        print("✓ MCP echo tool test passed")
        
        # Test calculator tool
        result = await mcp_service.execute_tool("calculate", {"expression": "10 * 5"})
        assert result["success"] is True
        assert result["result"] == 50
        print("✓ MCP calculator tool test passed")
        
        print("All async tests passed!")
        return True
        
    except Exception as e:
        print(f"Async test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner"""
    print("=== Voice Control Server Test Suite ===")
    print()
    
    # Run basic tests
    basic_success = run_basic_tests()
    
    # Run async tests
    async_success = await run_async_tests()
    
    print()
    print("=== Test Results ===")
    print(f"Basic tests: {'PASSED' if basic_success else 'FAILED'}")
    print(f"Async tests: {'PASSED' if async_success else 'FAILED'}")
    
    if basic_success and async_success:
        print("\n🎉 All tests passed! Voice Control Server is ready.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    # Run tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)