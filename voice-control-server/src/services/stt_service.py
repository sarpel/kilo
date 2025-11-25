"""
Speech-to-Text Service

Handles speech-to-text conversion using faster-whisper.
Supports multiple languages, models, and real-time transcription.
"""

import asyncio
import base64
import io
import logging
import tempfile
import time
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from pathlib import Path

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from pydub import AudioSegment
from pydub.silence import split_on_silence
import librosa
import soundfile as sf

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class STTService:
    """Speech-to-Text service using faster-whisper"""
    
    def __init__(self):
        self.model = None
        self.model_name = settings.whisper_model
        self.device = settings.whisper_device
        self.compute_type = settings.whisper_compute_type
        self.confidence_threshold = settings.stt_confidence_threshold
        self.is_initialized = False
        self.supported_models = [
            "tiny", "base", "small", "medium", "large", "large-v2", "large-v3"
        ]
        
    async def initialize(self):
        """Initialize the STT service and load the model"""
        if WhisperModel is None:
            logger.error("faster-whisper not installed. Please install it with: pip install faster-whisper")
            return False
            
        try:
            logger.info(f"Loading Whisper model: {self.model_name}")
            
            # Load model in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                self._load_model,
                self.model_name,
                self.device,
                self.compute_type
            )
            
            self.is_initialized = True
            logger.info(f"STT service initialized successfully with model: {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize STT service: {e}")
            self.is_initialized = False
            return False
    
    def _load_model(self, model_name: str, device: str, compute_type: str):
        """Load Whisper model (blocking operation)"""
        return WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type
        )
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = "en",
        task: str = "transcribe",
        temperature: float = 0.0,
        word_timestamps: bool = False
    ) -> Dict[str, Any]:
        """Transcribe audio data to text"""
        
        if not self.is_initialized or self.model is None:
            raise RuntimeError("STT service not initialized")
        
        start_time = time.time()
        
        try:
            # Convert bytes to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Transcribe in a separate thread
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._transcribe_file,
                temp_file_path,
                language,
                task,
                temperature,
                word_timestamps
            )
            
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Format result
            return {
                "text": result["text"].strip(),
                "segments": result["segments"],
                "language": result["language"],
                "confidence": self._calculate_confidence(result),
                "processing_time_ms": int(processing_time),
                "model_used": self.model_name,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "text": "",
                "segments": [],
                "language": language,
                "confidence": 0.0,
                "processing_time_ms": 0,
                "model_used": self.model_name,
                "error": str(e),
                "success": False
            }
    
    def _transcribe_file(
        self,
        file_path: str,
        language: str,
        task: str,
        temperature: float,
        word_timestamps: bool
    ) -> Dict[str, Any]:
        """Transcribe file (blocking operation)"""
        
        segments, info = self.model.transcribe(
            file_path,
            language=language if language != "auto" else None,
            task=task,
            temperature=temperature,
            word_timestamps=word_timestamps,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500
            )
        )
        
        # Convert segments to list and collect text
        segments_list = []
        text_parts = []
        
        for segment in segments:
            segments_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": getattr(segment, 'avg_logprob', 0.0)
            })
            text_parts.append(segment.text.strip())
        
        return {
            "text": " ".join(text_parts),
            "segments": segments_list,
            "language": info.language,
            "duration": info.duration,
            "duration_after_vad": info.duration_after_vad
        }
    
    async def transcribe_base64_audio(
        self,
        base64_audio: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Transcribe base64 encoded audio"""
        
        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(base64_audio)
            
            # Convert to standard audio format if needed
            audio_bytes = await self._convert_audio_format(audio_bytes)
            
            # Transcribe
            return await self.transcribe_audio(audio_bytes, language)
            
        except Exception as e:
            logger.error(f"Base64 audio transcription failed: {e}")
            return {
                "text": "",
                "segments": [],
                "language": language,
                "confidence": 0.0,
                "processing_time_ms": 0,
                "error": str(e),
                "success": False
            }
    
    async def _convert_audio_format(self, audio_bytes: bytes) -> bytes:
        """Convert audio to standard format (16kHz mono WAV)"""
        
        try:
            # Load audio with librosa
            audio_data, sample_rate = librosa.load(
                io.BytesIO(audio_bytes),
                sr=settings.audio_sample_rate,
                mono=True
            )
            
            # Convert to 16-bit PCM
            audio_data = (audio_data * 32767).astype(np.int16)
            
            # Convert to bytes
            output_buffer = io.BytesIO()
            sf.write(output_buffer, audio_data, settings.audio_sample_rate, format='WAV')
            
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.warning(f"Audio conversion failed: {e}. Returning original audio.")
            return audio_bytes
    
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate overall confidence score from segments"""
        
        if not result["segments"]:
            return 0.0
        
        # Calculate average confidence from segments
        confidences = [
            segment.get("confidence", 0.0) 
            for segment in result["segments"]
        ]
        
        if not confidences:
            return 0.0
        
        # Convert log probabilities to confidence scores
        confidence_scores = [
            max(0, min(1, 1 - abs(conf)))  # Convert to 0-1 scale
            for conf in confidences
        ]
        
        return sum(confidence_scores) / len(confidence_scores)
    
    async def process_audio_stream(
        self,
        audio_chunks: List[bytes],
        language: str = "en"
    ) -> Dict[str, Any]:
        """Process streaming audio data"""
        
        try:
            # Combine audio chunks
            combined_audio = b''.join(audio_chunks)
            
            # Transcribe combined audio
            return await self.transcribe_audio(combined_audio, language)
            
        except Exception as e:
            logger.error(f"Audio stream processing failed: {e}")
            return {
                "text": "",
                "segments": [],
                "language": language,
                "confidence": 0.0,
                "processing_time_ms": 0,
                "error": str(e),
                "success": False
            }
    
    async def detect_language(self, audio_data: bytes) -> Dict[str, Any]:
        """Detect language from audio data"""
        
        if not self.is_initialized or self.model is None:
            raise RuntimeError("STT service not initialized")
        
        try:
            # Convert bytes to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Detect language in a separate thread
            loop = asyncio.get_event_loop()
            language_probs = await loop.run_in_executor(
                None,
                self._detect_language,
                temp_file_path
            )
            
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)
            
            # Get most likely language
            detected_language = max(language_probs, key=language_probs.get)
            confidence = language_probs.get(detected_language, 0.0)
            
            return {
                "detected_language": detected_language,
                "confidence": confidence,
                "language_probabilities": language_probs,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return {
                "detected_language": "en",
                "confidence": 0.0,
                "language_probabilities": {},
                "error": str(e),
                "success": False
            }
    
    def _detect_language(self, file_path: str) -> Dict[str, float]:
        """Detect language from file (blocking operation)"""
        
        _, info = self.model.transcribe(
            file_path,
            task="detect_language"
        )
        
        return {"language": info.language, "language_prob": info.language_prob}
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported STT models"""
        return self.supported_models
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return [
            "auto", "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "tr", "nl", "sv", "da", "no", "fi", "pl", "cs", "sk", "hu", "ro", "bg", "hr", "sl", "et", "lv", "lt", "mt", "ga", "eu", "ca", "gl", "is", "mk", "sq", "sr", "bs", "me", "al", "mk"
        ]
    
    async def reload_models(self):
        """Reload STT models"""
        try:
            if self.model:
                del self.model
                self.model = None
            
            await self.initialize()
            logger.info("STT models reloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload STT models: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.model:
                del self.model
                self.model = None
            
            self.is_initialized = False
            logger.info("STT service cleaned up")
            
        except Exception as e:
            logger.error(f"Error during STT cleanup: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for STT service"""
        
        return {
            "status": "healthy" if self.is_initialized else "unhealthy",
            "model_loaded": self.model_name if self.is_initialized else None,
            "device": self.device,
            "confidence_threshold": self.confidence_threshold,
            "supported_languages": len(self.get_supported_languages())
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get detailed STT service status"""
        
        return {
            "initialized": self.is_initialized,
            "model": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "supported_models": self.supported_models,
            "confidence_threshold": self.confidence_threshold,
            "memory_usage": self._get_memory_usage() if self.is_initialized else None
        }
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            import psutil
            process = psutil.Process()
            return {
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent()
            }
        except ImportError:
            return {"memory_mb": "unknown", "cpu_percent": "unknown"}