"""
LLM (Language Model) Service

Handles language model interactions using Ollama.
Supports multiple models, streaming responses, and context management.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from dataclasses import dataclass
from datetime import datetime

import httpx
import ollama

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


@dataclass
class LLMMessage:
    """A message in the LLM conversation"""
    role: str  # 'system', 'user', 'assistant'
    content: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class LLMResponse:
    """Response from the LLM service"""
    content: str
    model: str
    tokens_used: int
    processing_time_ms: int
    confidence: float
    timestamp: datetime = None
    conversation_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class LLMService:
    """Language Model service using Ollama"""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.default_model = settings.ollama_model
        self.timeout = settings.ollama_timeout
        self.is_initialized = False
        self.available_models: List[str] = []
        self.conversations: Dict[str, List[LLMMessage]] = {}
        self.model_loaded = False
        
        # Initialize Ollama client
        self.client = ollama.AsyncClient(host=self.base_url)
        
    async def initialize(self):
        """Initialize the LLM service and check Ollama connection"""
        
        try:
            # Test connection to Ollama
            await self._test_connection()
            
            # Get available models (but don't load yet - that happens on first request)
            await self._refresh_model_list()
            
            # Check if default model is available, but don't load it yet
            if self.available_models:
                if self.default_model in self.available_models or any(self.default_model in m for m in self.available_models):
                    self.model_loaded = True  # Mark as available (lazy load on first use)
                else:
                    logger.warning(f"Default model {self.default_model} not found. Available: {self.available_models}")
                    # Use first available model
                    if self.available_models:
                        self.default_model = self.available_models[0]
                        self.model_loaded = True
            
            self.is_initialized = True
            logger.info(f"LLM service initialized, default model: {self.default_model}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            self.is_initialized = False
            return False
    
    async def _test_connection(self):
        """Test connection to Ollama server"""
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Ollama at {self.base_url}: {e}")
    
    async def _load_model(self, model_name: str):
        """Load a specific model"""
        
        try:
            logger.info(f"Loading model: {model_name}")
            
            # Pull model if not exists
            try:
                await self.client.pull(model_name)
            except Exception as e:
                logger.warning(f"Model pull failed (may already exist): {e}")
            
            # Generate a test request to ensure model is loaded
            test_response = await self.client.generate(
                model=model_name,
                prompt="Hello",
                options={'num_predict': 1}
            )
            
            self.model_loaded = True
            logger.info(f"Model {model_name} loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise
    
    async def _refresh_model_list(self):
        """Refresh the list of available models"""
        
        try:
            response = await self.client.list()
            models = response.get('models', [])
            # Handle both dict and object-like responses from different Ollama versions
            self.available_models = []
            for model in models:
                if isinstance(model, dict):
                    model_name = model.get('name') or model.get('model')
                else:
                    model_name = getattr(model, 'name', None) or getattr(model, 'model', None)
                if model_name:
                    self.available_models.append(model_name)
            logger.info(f"Available models: {self.available_models}")
            
        except Exception as e:
            logger.error(f"Failed to refresh model list: {e}")
            self.available_models = [self.default_model]
    
    async def generate_response(
        self,
        prompt: str,
        model: str = None,
        context: str = "user_query",
        conversation_id: str = None,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
        stream: bool = False,
        conversation_history: List[Dict[str, str]] = None
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """
        Generate a response from the LLM
        
        Args:
            prompt: The input prompt
            model: Model to use (defaults to configured model)
            context: Context of the request
            conversation_id: Conversation ID for maintaining context
            system_prompt: Custom system prompt
            temperature: Model temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            conversation_history: Previous conversation messages
        
        Returns:
            LLMResponse object or async generator if streaming
        """
        
        if not self.is_initialized or not self.model_loaded:
            raise RuntimeError("LLM service not initialized")
        
        # Use defaults
        model = model or self.default_model
        temperature = temperature if temperature is not None else settings.llm_temperature
        max_tokens = max_tokens or settings.llm_max_tokens
        system_prompt = system_prompt or settings.llm_system_prompt
        
        start_time = time.time()
        
        try:
            # Prepare messages
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append(LLMMessage(role="system", content=system_prompt))
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    messages.append(LLMMessage(
                        role=msg['role'],
                        content=msg['content']
                    ))
            
            # Add current user message
            messages.append(LLMMessage(role="user", content=prompt))
            
            # Convert to Ollama format
            ollama_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Generate response
            if stream:
                return self._stream_response(
                    ollama_messages, model, temperature, max_tokens, start_time
                )
            else:
                return await self._generate_single_response(
                    ollama_messages, model, temperature, max_tokens, start_time
                )
                
        except Exception as e:
            logger.error(f"LLM response generation failed: {e}")
            
            processing_time = (time.time() - start_time) * 1000
            
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=model,
                tokens_used=0,
                processing_time_ms=int(processing_time),
                confidence=0.0,
                conversation_id=conversation_id
            )
    
    async def _generate_single_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        start_time: float
    ) -> LLMResponse:
        """Generate a single response (non-streaming)"""
        
        response = await self.client.chat(
            model=model,
            messages=messages,
            options={
                'temperature': temperature,
                'num_predict': max_tokens,
                'stop': ['User:', 'Assistant:'],
            }
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Extract content and metadata
        content = response['message']['content']
        model_used = response.get('model', model)
        prompt_eval_count = response.get('prompt_eval_count', 0)
        eval_count = response.get('eval_count', 0)
        tokens_used = prompt_eval_count + eval_count
        
        return LLMResponse(
            content=content.strip(),
            model=model_used,
            tokens_used=tokens_used,
            processing_time_ms=int(processing_time),
            confidence=self._calculate_confidence(response),
            conversation_id=None
        )
    
    async def _stream_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        start_time: float
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response"""
        
        response_stream = await self.client.chat(
            model=model,
            messages=messages,
            options={
                'temperature': temperature,
                'num_predict': max_tokens,
                'stop': ['User:', 'Assistant:'],
            },
            stream=True
        )
        
        collected_content = []
        token_count = 0
        
        try:
            async for chunk in response_stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    content_chunk = chunk['message']['content']
                    collected_content.append(content_chunk)
                    
                    # Estimate token count
                    token_count += len(content_chunk.split())
                    
                    yield content_chunk
            
            # Update conversation history if needed
            # This would require conversation management logic
            
        except Exception as e:
            logger.error(f"Streaming response error: {e}")
            yield f"Error: {str(e)}"
    
    def _calculate_confidence(self, response: Dict[str, Any]) -> float:
        """Calculate confidence score from Ollama response"""
        
        # Ollama doesn't directly provide confidence scores
        # This is a placeholder for implementing confidence estimation
        
        # Could use factors like:
        # - Response length
        # - Model evaluation metrics
        # - Content analysis
        
        # For now, return a reasonable default
        return 0.85
    
    async def generate_summary(
        self,
        text: str,
        max_length: int = 150,
        model: str = None
    ) -> str:
        """Generate a summary of the given text"""
        
        prompt = f"Please provide a concise summary of the following text (max {max_length} words):\n\n{text}"
        
        response = await self.generate_response(
            prompt=prompt,
            model=model,
            context="summarization",
            max_tokens=max_length
        )
        
        return response.content
    
    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
        model: str = None
    ) -> str:
        """Translate text to target language"""
        
        prompt = f"Translate the following text from {'auto-detected' if source_language == 'auto' else source_language} to {target_language}:\n\n{text}"
        
        response = await self.generate_response(
            prompt=prompt,
            model=model,
            context="translation",
            max_tokens=len(text.split()) * 2  # Rough estimate for translation
        )
        
        return response.content
    
    async def extract_entities(
        self,
        text: str,
        model: str = None
    ) -> List[Dict[str, Any]]:
        """Extract named entities from text"""
        
        prompt = f"""Extract named entities (people, organizations, locations, dates, etc.) from the following text. 
Return them in JSON format with type and value.

Text: {text}"""
        
        response = await self.generate_response(
            prompt=prompt,
            model=model,
            context="entity_extraction",
            max_tokens=200
        )
        
        try:
            # Try to parse JSON response
            entities = json.loads(response.content)
            return entities
        except json.JSONDecodeError:
            # Fallback: return structured text
            return [{"raw_response": response.content}]
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported LLM models"""
        return self.available_models if self.available_models else [self.default_model]
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific model"""
        
        # This would typically query the model registry
        # For now, return basic info
        return {
            "name": model,
            "type": "ollama",
            "context_length": 4096,  # Default for most models
            "supports_streaming": True,
            "supports_function_calling": False
        }
    
    async def reload_models(self):
        """Reload LLM models"""
        try:
            await self._refresh_model_list()
            if self.default_model not in self.available_models:
                await self._load_model(self.default_model)
            logger.info("LLM models reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload LLM models: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            # Clear conversations
            self.conversations.clear()
            
            # The Ollama client doesn't need explicit cleanup
            self.is_initialized = False
            self.model_loaded = False
            
            logger.info("LLM service cleaned up")
        except Exception as e:
            logger.error(f"Error during LLM cleanup: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for LLM service"""
        
        return {
            "status": "healthy" if self.is_initialized else "unhealthy",
            "model_loaded": self.default_model if self.model_loaded else None,
            "base_url": self.base_url,
            "available_models": len(self.available_models),
            "timeout": self.timeout
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get detailed LLM service status"""
        
        return {
            "initialized": self.is_initialized,
            "model_loaded": self.model_loaded,
            "default_model": self.default_model,
            "available_models": self.available_models,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "conversation_count": len(self.conversations)
        }