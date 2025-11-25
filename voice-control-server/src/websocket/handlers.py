"""
WebSocket Handlers

Handles all WebSocket message processing for the voice control server.
Manages the complete audio processing pipeline from recording to response.
"""

import asyncio
import base64
import json
import time
import uuid
from typing import Dict, Any, Optional, List, Deque
from collections import deque
from datetime import datetime
import traceback

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from src.models.schemas import (
    WebSocketMessage, MessageType, ConnectionRequest, AudioData, AudioStart, AudioStop,
    STTRequest, LLMRequest, MCPRequest, STTResponse, LLMResponse, MCPResponse,
    create_connection_response, create_error_message, create_status_update,
    AudioFormat, ProcessingOptions
)
from src.websocket.connection_manager import ConnectionManager
from src.services.stt_service import STTService
from src.services.llm_service import LLMService
from src.services.mcp_service import MCPService
from src.services.audio_pipeline import AudioChunk, get_audio_processor
from src.utils.logger import get_logger, log_performance, get_audit_logger
from src.config.settings import get_settings

logger = get_logger(__name__)
audit_logger = get_audit_logger()
settings = get_settings()


class AudioBuffer:
    """Manages audio buffer for streaming"""
    
    def __init__(self, max_size: int = 100):
        self.buffer: Deque[bytes] = deque(maxlen=max_size)
        self.total_size = 0
        self.sequence = 0
        self.start_time = None
        self.is_final = False
    
    def add_chunk(self, audio_data: bytes, sequence: int, is_final: bool = False):
        """Add audio chunk to buffer"""
        if self.start_time is None:
            self.start_time = time.time()
        
        self.buffer.append(audio_data)
        self.total_size += len(audio_data)
        self.sequence = sequence
        self.is_final = is_final
    
    def get_audio_data(self) -> bytes:
        """Get combined audio data"""
        return b''.join(self.buffer)
    
    def get_duration_ms(self) -> int:
        """Get total duration in milliseconds"""
        if self.start_time is None:
            return 0
        return int((time.time() - self.start_time) * 1000)
    
    def clear(self):
        """Clear the buffer"""
        self.buffer.clear()
        self.total_size = 0
        self.sequence = 0
        self.start_time = None
        self.is_final = False


class ProcessingPipeline:
    """Handles the complete audio processing pipeline"""
    
    def __init__(self, session_id: str, stt_service: STTService, llm_service: LLMService, mcp_service: MCPService):
        self.session_id = session_id
        self.stt_service = stt_service
        self.llm_service = llm_service
        self.mcp_service = mcp_service
        self.audio_buffer = AudioBuffer()
        self.is_processing = False
        self.current_task: Optional[asyncio.Task] = None
        
    async def process_audio_stream(self, audio_data: bytes, language: str = "en") -> Dict[str, Any]:
        """Process complete audio stream through STT -> LLM -> MCP pipeline"""
        if self.is_processing:
            logger.warning(f"Pipeline already processing for session {self.session_id}")
            return {"error": "Pipeline busy", "success": False}
        
        self.is_processing = True
        
        try:
            # Step 1: Speech-to-Text
            stt_result = await self._process_stt(audio_data, language)
            
            if not stt_result.get("success") or not stt_result.get("text"):
                return stt_result
            
            # Step 2: Language Model Processing
            llm_result = await self._process_llm(stt_result["text"])
            
            if not llm_result.get("success"):
                return llm_result
            
            # Step 3: MCP Tool Execution (if needed)
            mcp_result = await self._process_mcp(llm_result["response"])
            
            return {
                "success": True,
                "stt": stt_result,
                "llm": llm_result,
                "mcp": mcp_result
            }
            
        except Exception as e:
            logger.error(f"Pipeline processing failed for {self.session_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": "pipeline_processing_error"
            }
        finally:
            self.is_processing = False
    
    async def _process_stt(self, audio_data: bytes, language: str) -> Dict[str, Any]:
        """Process speech-to-text"""
        try:
            # Convert base64 to bytes if needed
            if isinstance(audio_data, str):
                audio_data = base64.b64decode(audio_data)
            
            result = await self.stt_service.transcribe_audio(audio_data, language=language)
            result["success"] = result.get("success", True)
            return result
            
        except Exception as e:
            logger.error(f"STT processing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": "stt_processing_error"
            }
    
    async def _process_llm(self, text: str) -> Dict[str, Any]:
        """Process language model"""
        try:
            # Create system prompt for voice assistant
            system_prompt = """You are a helpful voice assistant that can control computer systems, 
            interact with applications, and provide information. Keep responses concise and actionable.
            If the user asks for system operations, respond with specific instructions."""
            
            response = await self.llm_service.generate_response(
                prompt=text,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=150
            )
            
            return {
                "success": True,
                "response": response.content,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "processing_time_ms": response.processing_time_ms,
                "confidence": response.confidence
            }
            
        except Exception as e:
            logger.error(f"LLM processing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": "llm_processing_error"
            }
    
    async def _process_mcp(self, llm_response: str) -> Dict[str, Any]:
        """Process MCP tool execution based on LLM response"""
        try:
            # Extract potential tool calls from LLM response
            tool_calls = await self._extract_tool_calls(llm_response)
            
            if not tool_calls:
                return {"success": True, "result": "No tool calls extracted"}
            
            results = []
            for tool_call in tool_calls:
                try:
                    result = await self.mcp_service.execute_tool(
                        tool_name=tool_call["tool"],
                        arguments=tool_call["arguments"]
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"MCP tool execution failed: {e}", exc_info=True)
                    results.append({"error": str(e), "success": False})
            
            return {
                "success": True,
                "results": results,
                "tool_calls": tool_calls
            }
            
        except Exception as e:
            logger.error(f"MCP processing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": "mcp_processing_error"
            }
    
    async def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract potential tool calls from LLM response"""
        # Simple implementation - could be enhanced with more sophisticated parsing
        import re
        
        # Look for JSON tool calls in response
        json_pattern = r'\{[^{}]*"tool"[^{}]*\}'
        matches = re.findall(json_pattern, response)
        
        tool_calls = []
        for match in matches:
            try:
                tool_call = json.loads(match)
                if "tool" in tool_call and "arguments" in tool_call:
                    tool_calls.append(tool_call)
            except json.JSONDecodeError:
                continue
        
        return tool_calls


class WebSocketHandler:
    """Main WebSocket handler for voice control"""
    
    def __init__(self, websocket: WebSocket, connection_manager: ConnectionManager,
                 stt_service: STTService, llm_service: LLMService, mcp_service: MCPService):
        self.websocket = websocket
        self.connection_manager = connection_manager
        self.stt_service = stt_service
        self.llm_service = llm_service
        self.mcp_service = mcp_service
        self.session_id: Optional[str] = None
        self.client_id: Optional[str] = None
        self.audio_buffer: Optional[AudioBuffer] = None
        self.pipeline: Optional[ProcessingPipeline] = None
        self.is_authenticated = False
        self.connection_start_time = time.time()
        
    async def handle_connection(self) -> str:
        """Handle WebSocket connection lifecycle"""
        try:
            # Wait for connection request
            message = await self._receive_message()
            
            if not message or message["type"] != MessageType.CONNECTION_REQUEST:
                await self._send_error("INVALID_MESSAGE", "Expected connection_request")
                return None
            
            # Process connection request
            connection_data = message["data"]
            self.client_id = connection_data.get("client_id")
            
            # Create session
            self.session_id = await self.connection_manager.connect(self.websocket, self.client_id)
            
            # Send connection response
            await self._send_connection_response()
            
            # Audit log connection
            audit_logger.log_user_action(
                user_id=self.client_id or "anonymous",
                action="websocket_connected",
                session_id=self.session_id,
                details={"client_version": connection_data.get("client_version")}
            )
            
            # Set up audio buffer and pipeline
            self.audio_buffer = AudioBuffer()
            self.pipeline = ProcessingPipeline(
                self.session_id, self.stt_service, self.llm_service, self.mcp_service
            )
            
            self.is_authenticated = True
            
            # Handle messages
            await self._handle_messages()
            
            return self.session_id
            
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}", exc_info=True)
            await self._send_error("HANDLER_ERROR", str(e))
            return None
    
    async def _handle_messages(self):
        """Handle incoming WebSocket messages"""
        while True:
            try:
                message = await self._receive_message()
                
                if not message:
                    break  # Connection closed
                
                # Handle heartbeat messages
                if message["type"] == MessageType.HEARTBEAT:
                    await self._handle_heartbeat()
                    continue
                
                # Route message to appropriate handler
                await self._route_message(message)
                
            except Exception as e:
                logger.error(f"Message handling error: {e}", exc_info=True)
                await self._send_error("MESSAGE_HANDLING_ERROR", str(e))
                break
    
    async def _route_message(self, message: Dict[str, Any]):
        """Route message to appropriate handler"""
        message_type = message["type"]
        
        handlers = {
            MessageType.AUDIO_START: self._handle_audio_start,
            MessageType.AUDIO_DATA: self._handle_audio_data,
            MessageType.AUDIO_STOP: self._handle_audio_stop,
            MessageType.STT_REQUEST: self._handle_stt_request,
            MessageType.LLM_REQUEST: self._handle_llm_request,
            MessageType.MCP_REQUEST: self._handle_mcp_request,
            MessageType.HEARTBEAT_RESPONSE: self._handle_heartbeat_response,
        }
        
        handler = handlers.get(message_type)
        if handler:
            await handler(message)
        else:
            await self._send_error("UNKNOWN_MESSAGE_TYPE", f"Unknown message type: {message_type}")
    
    async def _receive_message(self) -> Optional[Dict[str, Any]]:
        """Receive and parse WebSocket message"""
        try:
            data = await self.websocket.receive_text()
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            await self._send_error("INVALID_JSON", "Invalid JSON in message")
            return None
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
            return None
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send WebSocket message"""
        try:
            await self.websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            raise
    
    async def _send_connection_response(self):
        """Send connection response"""
        from src.models.schemas import ServerInfo
        
        server_info = ServerInfo(
            version="1.0.0",
            capabilities=["stt", "llm", "mcp"],
            supported_models=[
                "tiny", "base", "small", "medium",
                "llama2", "mistral", "codellama"
            ]
        )
        
        response = create_connection_response(
            status="connected",
            server_info=server_info,
            session_id=self.session_id
        )
        
        await self._send_message(response.dict())
        logger.log_websocket_event("connection_established", self.session_id)
    
    async def _handle_audio_start(self, message: Dict[str, Any]):
        """Handle audio start message"""
        try:
            data = message["data"]
            session_id = data.get("session_id")
            
            if session_id != self.session_id:
                await self._send_error("SESSION_MISMATCH", "Session ID mismatch")
                return
            
            # Initialize audio processing
            self.audio_buffer = AudioBuffer()
            
            # Update processing pipeline with new session
            if self.pipeline:
                self.pipeline.session_id = session_id
            
            await self._send_status("audio_recording_started", 0, "Ready to receive audio")
            
            audit_logger.log_user_action(
                user_id=self.client_id or "anonymous",
                action="audio_recording_started",
                session_id=self.session_id,
                details={"session_id": session_id}
            )
            
        except Exception as e:
            logger.error(f"Audio start handling failed: {e}", exc_info=True)
            await self._send_error("AUDIO_START_ERROR", str(e))
    
    async def _handle_audio_data(self, message: Dict[str, Any]):
        """Handle audio data message"""
        try:
            data = message["data"]
            session_id = data.get("session_id")
            
            if session_id != self.session_id:
                await self._send_error("SESSION_MISMATCH", "Session ID mismatch")
                return
            
            # Extract audio data
            audio_chunk = data.get("audio_chunk")
            sequence = data.get("sequence", 0)
            is_final = data.get("is_final", False)
            
            if not audio_chunk:
                await self._send_error("NO_AUDIO_DATA", "No audio data provided")
                return
            
            # Decode base64 audio
            try:
                audio_bytes = base64.b64decode(audio_chunk)
            except Exception as e:
                await self._send_error("INVALID_AUDIO_FORMAT", f"Invalid base64 audio: {e}")
                return
            
            # Add to buffer
            self.audio_buffer.add_chunk(audio_bytes, sequence, is_final)
            
            # Send acknowledgment
            await self._send_status("audio_data_received", min(90, (sequence % 100)), 
                                  f"Received chunk {sequence}")
            
        except Exception as e:
            logger.error(f"Audio data handling failed: {e}", exc_info=True)
            await self._send_error("AUDIO_DATA_ERROR", str(e))
    
    async def _handle_audio_stop(self, message: Dict[str, Any]):
        """Handle audio stop message and process complete audio"""
        try:
            data = message["data"]
            session_id = data.get("session_id")
            
            if session_id != self.session_id:
                await self._send_error("SESSION_MISMATCH", "Session ID mismatch")
                return
            
            # Mark final chunk
            self.audio_buffer.is_final = True
            
            await self._send_status("processing_audio", 10, "Processing audio...")
            
            # Get audio data
            audio_data = self.audio_buffer.get_audio_data()
            duration_ms = self.audio_buffer.get_duration_ms()
            
            if not audio_data:
                await self._send_error("NO_AUDIO_DATA", "No audio data received")
                return
            
            # Check audio size limit
            if len(audio_data) > settings.audio_max_buffer_size:
                await self._send_error("AUDIO_TOO_LARGE", "Audio data exceeds size limit")
                return
            
            audit_logger.log_user_action(
                user_id=self.client_id or "anonymous",
                action="audio_processing_started",
                session_id=self.session_id,
                details={"duration_ms": duration_ms, "size_bytes": len(audio_data)}
            )
            
            # Start processing pipeline
            if self.current_task and not self.current_task.done():
                self.current_task.cancel()
            
            self.current_task = asyncio.create_task(self._process_audio_pipeline())
            
        except Exception as e:
            logger.error(f"Audio stop handling failed: {e}", exc_info=True)
            await self._send_error("AUDIO_STOP_ERROR", str(e))
    
    async def _process_audio_pipeline(self):
        """Process complete audio through STT -> LLM -> MCP pipeline"""
        try:
            await self._send_status("processing_stt", 20, "Converting speech to text...")
            
            # Get processing options (default to English for now)
            language = "en"
            
            # Process through pipeline
            result = await self.pipeline.process_audio_stream(
                self.audio_buffer.get_audio_data(),
                language=language
            )
            
            if result.get("success"):
                # Send STT result
                await self._send_stt_response(result["stt"])
                
                await self._send_status("processing_llm", 60, "Generating response...")
                
                # Send LLM result
                await self._send_llm_response(result["llm"])
                
                await self._send_status("processing_complete", 100, "Processing complete")
                
                # Send MCP result if available
                if "mcp" in result and result["mcp"].get("success"):
                    await self._send_mcp_response(result["mcp"])
                
                audit_logger.log_user_action(
                    user_id=self.client_id or "anonymous",
                    action="audio_processing_complete",
                    session_id=self.session_id,
                    details={
                        "stt_confidence": result["stt"].get("confidence", 0),
                        "llm_tokens": result["llm"].get("tokens_used", 0)
                    }
                )
            else:
                # Send error
                error_type = result.get("error_type", "PROCESSING_ERROR")
                await self._send_error(error_type, result.get("error", "Processing failed"))
            
            # Clear audio buffer
            self.audio_buffer.clear()
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}", exc_info=True)
            await self._send_error("PIPELINE_ERROR", str(e))
    
    async def _handle_stt_request(self, message: Dict[str, Any]):
        """Handle standalone STT request"""
        try:
            data = message["data"]
            session_id = data.get("session_id")
            
            if session_id != self.session_id:
                await self._send_error("SESSION_MISMATCH", "Session ID mismatch")
                return
            
            # Process STT request (similar to pipeline STT step)
            audio_data = self.audio_buffer.get_audio_data() if self.audio_buffer else None
            
            if not audio_data:
                await self._send_error("NO_AUDIO_DATA", "No audio data available")
                return
            
            result = await self.stt_service.transcribe_audio(
                audio_data,
                language=data.get("language", "en")
            )
            
            await self._send_stt_response(result)
            
        except Exception as e:
            logger.error(f"STT request handling failed: {e}", exc_info=True)
            await self._send_error("STT_REQUEST_ERROR", str(e))
    
    async def _handle_llm_request(self, message: Dict[str, Any]):
        """Handle standalone LLM request"""
        try:
            data = message["data"]
            session_id = data.get("session_id")
            
            if session_id != self.session_id:
                await self._send_error("SESSION_MISMATCH", "Session ID mismatch")
                return
            
            text = data.get("text")
            if not text:
                await self._send_error("NO_TEXT", "No text provided")
                return
            
            # Generate LLM response
            response = await self.llm_service.generate_response(
                prompt=text,
                model=data.get("model", "llama2"),
                temperature=data.get("options", {}).get("temperature", 0.7),
                max_tokens=data.get("options", {}).get("max_tokens", 150)
            )
            
            await self._send_llm_response({
                "success": True,
                "response": response.content,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "processing_time_ms": response.processing_time_ms,
                "confidence": response.confidence
            })
            
        except Exception as e:
            logger.error(f"LLM request handling failed: {e}", exc_info=True)
            await self._send_error("LLM_REQUEST_ERROR", str(e))
    
    async def _handle_mcp_request(self, message: Dict[str, Any]):
        """Handle MCP tool request"""
        try:
            data = message["data"]
            session_id = data.get("session_id")
            
            if session_id != self.session_id:
                await self._send_error("SESSION_MISMATCH", "Session ID mismatch")
                return
            
            tool_name = data.get("tool")
            arguments = data.get("arguments", {})
            
            if not tool_name:
                await self._send_error("NO_TOOL", "No tool specified")
                return
            
            # Execute MCP tool
            result = await self.mcp_service.execute_tool(tool_name, arguments)
            
            await self._send_mcp_response({
                "success": True,
                "result": result
            })
            
        except Exception as e:
            logger.error(f"MCP request handling failed: {e}", exc_info=True)
            await self._send_error("MCP_REQUEST_ERROR", str(e))
    
    async def _handle_heartbeat(self):
        """Handle heartbeat message"""
        heartbeat_data = {
            "server_time": datetime.utcnow().isoformat(),
            "uptime": int(time.time() - self.connection_start_time)
        }
        
        await self._send_message({
            "type": MessageType.HEARTBEAT,
            "timestamp": datetime.utcnow().isoformat(),
            "data": heartbeat_data,
            "message_id": f"heartbeat_{int(time.time() * 1000)}"
        })
    
    async def _handle_heartbeat_response(self, message: Dict[str, Any]):
        """Handle heartbeat response"""
        await self.connection_manager.update_heartbeat(self.session_id)
    
    async def _send_status(self, status: str, progress: int, message: str):
        """Send status update"""
        status_message = create_status_update(self.session_id, status, progress, message)
        await self._send_message(status_message.dict())
    
    async def _send_error(self, error_type: str, message: str):
        """Send error message"""
        error_message = create_error_message(error_type, message, error_type.upper(), self.session_id)
        await self._send_message(error_message.dict())
        
        audit_logger.log_user_action(
            user_id=self.client_id or "anonymous",
            action="error_sent",
            session_id=self.session_id,
            details={"error_type": error_type, "message": message}
        )
    
    async def _send_stt_response(self, result: Dict[str, Any]):
        """Send STT response"""
        response_data = {
            "session_id": self.session_id,
            "text": result.get("text", ""),
            "confidence": result.get("confidence", 0.0),
            "language": result.get("language", "en"),
            "processing_time_ms": result.get("processing_time_ms", 0),
            "audio_duration_ms": self.audio_buffer.get_duration_ms() if self.audio_buffer else 0,
            "segments": result.get("segments", [])
        }
        
        await self._send_message({
            "type": MessageType.STT_RESPONSE,
            "timestamp": datetime.utcnow().isoformat(),
            "data": response_data,
            "message_id": f"stt_{int(time.time() * 1000)}"
        })
    
    async def _send_llm_response(self, result: Dict[str, Any]):
        """Send LLM response"""
        response_data = {
            "session_id": self.session_id,
            "response": result.get("response", ""),
            "model": result.get("model", "unknown"),
            "processing_time_ms": result.get("processing_time_ms", 0),
            "tokens_used": result.get("tokens_used", 0),
            "confidence": result.get("confidence", 0.0)
        }
        
        await self._send_message({
            "type": MessageType.LLM_RESPONSE,
            "timestamp": datetime.utcnow().isoformat(),
            "data": response_data,
            "message_id": f"llm_{int(time.time() * 1000)}"
        })
    
    async def _send_mcp_response(self, result: Dict[str, Any]):
        """Send MCP response"""
        response_data = {
            "session_id": self.session_id,
            "result": result.get("result", {}),
            "success": result.get("success", False)
        }
        
        await self._send_message({
            "type": MessageType.MCP_RESPONSE,
            "timestamp": datetime.utcnow().isoformat(),
            "data": response_data,
            "message_id": f"mcp_{int(time.time() * 1000)}"
        })