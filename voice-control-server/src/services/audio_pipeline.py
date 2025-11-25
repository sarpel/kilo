"""
Audio Processing Pipeline Service

Comprehensive audio processing pipeline that manages the complete flow from
audio recording through STT, LLM, and MCP tool execution with non-blocking execution.
"""

import asyncio
import base64
import io
import time
import wave
import tempfile
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from pathlib import Path

from src.config.settings import get_settings
from src.services.stt_service import STTService
from src.services.llm_service import LLMService
from src.services.mcp_service import MCPService
from src.utils.logger import get_logger, log_performance, get_audit_logger, get_performance_monitor

logger = get_logger(__name__)
audit_logger = get_audit_logger()
performance_monitor = get_performance_monitor()
settings = get_settings()


@dataclass
class AudioChunk:
    """Audio chunk data structure"""
    data: bytes
    sequence: int
    timestamp: float
    is_final: bool = False
    duration_ms: int = 0


@dataclass
class ProcessingResult:
    """Result of audio processing pipeline"""
    session_id: str
    success: bool
    text: str = ""
    llm_response: str = ""
    mcp_results: List[Dict[str, Any]] = field(default_factory=list)
    stt_confidence: float = 0.0
    processing_time_ms: int = 0
    audio_duration_ms: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class FunctionCallExtractor:
    """Extracts and parses function calls from LLM responses"""
    
    def __init__(self):
        self.function_patterns = {
            # JSON function calls
            "json": r'\{[^{}]*"function"[^{}]*\}|\{[^{}]*"tool"[^{}]*\}',
            # Simple function calls
            "simple": r'(\w+)\(([^)]*)\)',
            # Tool mentions
            "tool": r'[\"\']([\w_]+)[\"\'][::]\s*([\w_]+)',
        }
    
    def extract_function_calls(self, text: str) -> List[Dict[str, Any]]:
        """Extract function calls from LLM response text"""
        import re
        import json
        
        calls = []
        
        # Try to extract JSON function calls
        json_matches = re.findall(self.function_patterns["json"], text, re.IGNORECASE)
        for match in json_matches:
            try:
                # Parse as JSON
                call_data = json.loads(match)
                if isinstance(call_data, dict):
                    # Handle different formats
                    if "function" in call_data:
                        calls.append({
                            "type": "json",
                            "function": call_data["function"],
                            "arguments": call_data.get("arguments", {}),
                            "raw": match
                        })
                    elif "tool" in call_data:
                        calls.append({
                            "type": "json",
                            "tool": call_data["tool"],
                            "arguments": call_data.get("arguments", {}),
                            "raw": match
                        })
            except json.JSONDecodeError:
                continue
        
        # Try to extract simple function calls
        simple_matches = re.findall(self.function_patterns["simple"], text, re.IGNORECASE)
        for func_name, args_str in simple_matches:
            if func_name.lower() in ["run", "execute", "call"]:
                continue  # Skip generic terms
            
            calls.append({
                "type": "simple",
                "function": func_name,
                "arguments": self._parse_arguments(args_str),
                "raw": f"{func_name}({args_str})"
            })
        
        # Try to extract tool mentions
        tool_matches = re.findall(self.function_patterns["tool"], text, re.IGNORECASE)
        for tool_name, method in tool_matches:
            calls.append({
                "type": "tool",
                "tool": tool_name,
                "method": method,
                "arguments": {},
                "raw": f'"{tool_name}"::{method}'
            })
        
        return calls
    
    def _parse_arguments(self, args_str: str) -> Dict[str, Any]:
        """Parse function arguments from string"""
        import re
        
        args = {}
        if not args_str.strip():
            return args
        
        # Simple key=value parsing
        pairs = re.findall(r'(\w+)\s*=\s*([\'\"][^\'\"]*[\'\"]|\w+)', args_str)
        for key, value in pairs:
            # Remove quotes if present
            if value.startswith(('"', "'")) and value.endswith(('"', "'")):
                value = value[1:-1]
            
            # Try to convert to appropriate type
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif self._is_float(value):
                value = float(value)
            
            args[key] = value
        
        return args
    
    def _is_float(self, value: str) -> bool:
        """Check if string represents a float"""
        try:
            float(value)
            return True
        except ValueError:
            return False


class AudioProcessingPipeline:
    """Main audio processing pipeline orchestrator"""
    
    def __init__(self, session_id: str, stt_service: STTService, 
                 llm_service: LLMService, mcp_service: MCPService):
        self.session_id = session_id
        self.stt_service = stt_service
        self.llm_service = llm_service
        self.mcp_service = mcp_service
        
        # Pipeline state
        self.is_processing = False
        self.current_task: Optional[asyncio.Task] = None
        self.processing_cancelled = False
        
        # Audio buffer
        self.audio_chunks: List[AudioChunk] = []
        self.total_audio_duration_ms = 0
        
        # Configuration
        self.confidence_threshold = settings.stt_confidence_threshold
        self.max_audio_duration_ms = settings.max_audio_duration * 1000
        
        # Function call extraction
        self.function_extractor = FunctionCallExtractor()
        
        logger.info(f"Audio processing pipeline initialized for session {session_id}")
    
    async def process_audio_stream(self, audio_chunks: List[AudioChunk]) -> ProcessingResult:
        """Process complete audio stream through the pipeline"""
        if self.is_processing:
            logger.warning(f"Pipeline already processing for session {self.session_id}")
            return ProcessingResult(
                session_id=self.session_id,
                success=False,
                error="Pipeline busy"
            )
        
        self.is_processing = True
        self.processing_cancelled = False
        self.audio_chunks = audio_chunks
        
        start_time = time.time()
        result = ProcessingResult(session_id=self.session_id, success=False)
        
        try:
            logger.info(f"Starting audio processing for session {self.session_id} "
                       f"with {len(audio_chunks)} chunks")
            
            # Calculate total duration
            self.total_audio_duration_ms = sum(chunk.duration_ms for chunk in audio_chunks)
            
            if self.total_audio_duration_ms > self.max_audio_duration_ms:
                raise ValueError(f"Audio duration ({self.total_audio_duration_ms}ms) "
                               f"exceeds maximum allowed ({self.max_audio_duration_ms}ms)")
            
            # Step 1: Combine audio chunks
            combined_audio = await self._combine_audio_chunks()
            
            # Step 2: Speech-to-Text processing
            stt_result = await self._process_speech_to_text(combined_audio)
            
            if not stt_result.get("success") or not stt_result.get("text"):
                result.text = stt_result.get("text", "")
                result.stt_confidence = stt_result.get("confidence", 0.0)
                result.error = stt_result.get("error", "Speech-to-text processing failed")
                return result
            
            result.text = stt_result["text"]
            result.stt_confidence = stt_result.get("confidence", 0.0)
            result.audio_duration_ms = self.total_audio_duration_ms
            
            # Check confidence threshold
            if result.stt_confidence < self.confidence_threshold:
                logger.warning(f"STT confidence {result.stt_confidence} below threshold "
                             f"{self.confidence_threshold}")
                result.error = f"Low confidence transcription: {result.stt_confidence:.2f}"
                return result
            
            # Step 3: Language Model processing
            llm_result = await self._process_language_model(result.text)
            
            if not llm_result.get("success"):
                result.error = llm_result.get("error", "Language model processing failed")
                return result
            
            result.llm_response = llm_result["response"]
            result.metadata["llm_tokens"] = llm_result.get("tokens_used", 0)
            
            # Step 4: Extract and execute function calls
            function_calls = self.function_extractor.extract_function_calls(result.llm_response)
            
            if function_calls:
                mcp_results = await self._execute_function_calls(function_calls)
                result.mcp_results = mcp_results
                result.metadata["function_calls"] = function_calls
            
            # All steps completed successfully
            result.success = True
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Performance monitoring
            performance_monitor.record_metric(
                "audio_processing_time_ms", 
                result.processing_time_ms,
                {"session_id": self.session_id}
            )
            
            performance_monitor.record_metric(
                "audio_duration_ms", 
                result.audio_duration_ms,
                {"session_id": self.session_id}
            )
            
            # Audit logging
            audit_logger.log_user_action(
                user_id=f"session_{self.session_id}",
                action="audio_processing_complete",
                session_id=self.session_id,
                details={
                    "text_length": len(result.text),
                    "stt_confidence": result.stt_confidence,
                    "processing_time_ms": result.processing_time_ms,
                    "function_calls_count": len(function_calls)
                }
            )
            
            logger.info(f"Audio processing completed for session {self.session_id} "
                       f"in {result.processing_time_ms}ms")
            
            return result
            
        except asyncio.CancelledError:
            self.processing_cancelled = True
            result.error = "Processing cancelled"
            logger.info(f"Audio processing cancelled for session {self.session_id}")
            return result
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Audio processing failed for session {self.session_id}: {e}", 
                        exc_info=True)
            
            audit_logger.log_user_action(
                user_id=f"session_{self.session_id}",
                action="audio_processing_error",
                session_id=self.session_id,
                details={"error": str(e)}
            )
            
            return result
            
        finally:
            self.is_processing = False
            # Clear audio chunks to free memory
            self.audio_chunks.clear()
    
    async def _combine_audio_chunks(self) -> bytes:
        """Combine audio chunks into a single audio buffer"""
        try:
            if not self.audio_chunks:
                return b""
            
            # For PCM audio, simply concatenate chunks
            combined_audio = b"".join(chunk.data for chunk in self.audio_chunks)
            
            logger.debug(f"Combined {len(self.audio_chunks)} audio chunks "
                        f"into {len(combined_audio)} bytes")
            
            return combined_audio
            
        except Exception as e:
            logger.error(f"Failed to combine audio chunks: {e}")
            raise
    
    async def _process_speech_to_text(self, audio_data: bytes) -> Dict[str, Any]:
        """Process speech-to-text conversion"""
        try:
            start_time = time.time()
            
            # Use STT service to transcribe
            result = await self.stt_service.transcribe_audio(
                audio_data,
                language="en"  # Could be made configurable
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            # Log performance
            performance_monitor.record_metric(
                "stt_processing_time_ms",
                processing_time,
                {"session_id": self.session_id}
            )
            
            if result.get("success"):
                logger.info(f"STT completed: '{result['text']}' "
                           f"(confidence: {result.get('confidence', 0):.2f})")
            else:
                logger.warning(f"STT failed: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"STT processing error: {e}")
            return {
                "success": False,
                "error": str(e),
                "confidence": 0.0
            }
    
    async def _process_language_model(self, text: str) -> Dict[str, Any]:
        """Process language model generation"""
        try:
            start_time = time.time()
            
            # Enhanced system prompt for computer automation
            system_prompt = """You are a helpful voice assistant for computer automation. 
            You can control Windows systems, interact with applications, browse websites, 
            and perform various tasks through voice commands. 
            
            When users ask for system operations, provide specific, actionable responses.
            If you need to perform system tasks, you can call appropriate tools.
            
            Keep responses concise but informative. If a task requires multiple steps,
            provide a clear sequence of actions."""
            
            # Generate response using LLM service
            response = await self.llm_service.generate_response(
                prompt=text,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=150
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            # Log performance
            performance_monitor.record_metric(
                "llm_processing_time_ms",
                processing_time,
                {"session_id": self.session_id}
            )
            
            logger.info(f"LLM response generated: '{response.content[:100]}...' "
                       f"({response.tokens_used} tokens)")
            
            return {
                "success": True,
                "response": response.content,
                "tokens_used": response.tokens_used,
                "processing_time_ms": int(processing_time),
                "confidence": response.confidence
            }
            
        except Exception as e:
            logger.error(f"LLM processing error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_function_calls(self, function_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute extracted function calls via MCP service"""
        results = []
        
        for call in function_calls:
            try:
                start_time = time.time()
                
                # Determine tool name and arguments
                if call["type"] == "json":
                    if "function" in call:
                        tool_name = call["function"]
                    else:
                        tool_name = call["tool"]
                    arguments = call["arguments"]
                elif call["type"] == "simple":
                    tool_name = call["function"]
                    arguments = call["arguments"]
                elif call["type"] == "tool":
                    # Convert tool::method format
                    tool_name = f"{call['tool']}_{call['method']}"
                    arguments = call["arguments"]
                else:
                    continue
                
                # Execute tool via MCP service
                result = await self.mcp_service.execute_tool(tool_name, arguments)
                
                execution_time = (time.time() - start_time) * 1000
                
                results.append({
                    "call": call,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": result,
                    "execution_time_ms": int(execution_time),
                    "success": result.get("success", False)
                })
                
                # Log performance
                performance_monitor.record_metric(
                    "mcp_execution_time_ms",
                    execution_time,
                    {"session_id": self.session_id, "tool": tool_name}
                )
                
                logger.info(f"MCP tool {tool_name} executed "
                           f"({'success' if result.get('success') else 'failed'}): "
                           f"{execution_time:.0f}ms")
                
            except Exception as e:
                logger.error(f"MCP tool execution failed: {e}")
                results.append({
                    "call": call,
                    "error": str(e),
                    "success": False
                })
        
        return results
    
    async def cancel_processing(self):
        """Cancel current processing operation"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        
        self.processing_cancelled = True
        self.is_processing = False
        
        logger.info(f"Cancelled audio processing for session {self.session_id}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status"""
        return {
            "session_id": self.session_id,
            "is_processing": self.is_processing,
            "processing_cancelled": self.processing_cancelled,
            "audio_chunks_count": len(self.audio_chunks),
            "total_audio_duration_ms": self.total_audio_duration_ms,
            "confidence_threshold": self.confidence_threshold,
            "max_audio_duration_ms": self.max_audio_duration_ms
        }


class AudioProcessor:
    """Main audio processor that manages multiple pipeline instances"""
    
    def __init__(self, stt_service: STTService, llm_service: LLMService, mcp_service: MCPService):
        self.stt_service = stt_service
        self.llm_service = llm_service
        self.mcp_service = mcp_service
        
        # Active pipelines
        self.pipelines: Dict[str, AudioProcessingPipeline] = {}
        
        logger.info("Audio processor initialized")
    
    async def create_pipeline(self, session_id: str) -> AudioProcessingPipeline:
        """Create a new processing pipeline for a session"""
        if session_id in self.pipelines:
            logger.warning(f"Pipeline already exists for session {session_id}")
            return self.pipelines[session_id]
        
        pipeline = AudioProcessingPipeline(
            session_id=session_id,
            stt_service=self.stt_service,
            llm_service=self.llm_service,
            mcp_service=self.mcp_service
        )
        
        self.pipelines[session_id] = pipeline
        logger.info(f"Created audio pipeline for session {session_id}")
        
        return pipeline
    
    async def process_audio(self, session_id: str, audio_chunks: List[AudioChunk]) -> ProcessingResult:
        """Process audio for a specific session"""
        try:
            # Get or create pipeline
            pipeline = self.pipelines.get(session_id)
            if not pipeline:
                pipeline = await self.create_pipeline(session_id)
            
            # Process audio through pipeline
            result = await pipeline.process_audio_stream(audio_chunks)
            
            return result
            
        except Exception as e:
            logger.error(f"Audio processing failed for session {session_id}: {e}")
            return ProcessingResult(
                session_id=session_id,
                success=False,
                error=str(e)
            )
    
    async def cancel_session_processing(self, session_id: str):
        """Cancel processing for a specific session"""
        pipeline = self.pipelines.get(session_id)
        if pipeline:
            await pipeline.cancel_processing()
    
    def remove_pipeline(self, session_id: str):
        """Remove pipeline for a session"""
        if session_id in self.pipelines:
            del self.pipelines[session_id]
            logger.info(f"Removed audio pipeline for session {session_id}")
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.pipelines.keys())
    
    def get_pipeline_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific pipeline"""
        pipeline = self.pipelines.get(session_id)
        if pipeline:
            return pipeline.get_status()
        return None
    
    def get_all_pipeline_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all pipelines"""
        return {session_id: pipeline.get_status() 
                for session_id, pipeline in self.pipelines.items()}
    
    async def cleanup(self):
        """Clean up all pipelines"""
        for session_id, pipeline in list(self.pipelines.items()):
            await pipeline.cancel_processing()
            self.remove_pipeline(session_id)
        
        logger.info("Audio processor cleaned up")


# Global audio processor instance
_audio_processor: Optional[AudioProcessor] = None


def get_audio_processor(stt_service: STTService = None, 
                       llm_service: LLMService = None, 
                       mcp_service: MCPService = None) -> AudioProcessor:
    """Get global audio processor instance"""
    global _audio_processor
    
    if _audio_processor is None:
        if stt_service and llm_service and mcp_service:
            _audio_processor = AudioProcessor(stt_service, llm_service, mcp_service)
        else:
            raise ValueError("Services must be provided when creating audio processor")
    
    return _audio_processor