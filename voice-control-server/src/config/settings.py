"""
Application settings and configuration management
"""

from typing import List, Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings configuration"""
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://10.0.2.2:3000"],
        description="CORS allowed origins"
    )
    
    # Security Configuration
    secret_key: str = Field(default="your-secret-key-change-in-production", description="Secret key for JWT")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="JWT token expiration time")
    
    # WebSocket Configuration
    websocket_max_connections: int = Field(default=10, description="Maximum WebSocket connections per IP")
    websocket_ping_interval: int = Field(default=30, description="WebSocket ping interval in seconds")
    websocket_ping_timeout: int = Field(default=10, description="WebSocket ping timeout in seconds")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    # STT (Speech-to-Text) Configuration
    whisper_model: str = Field(default="base", description="Whisper model to use")
    whisper_device: str = Field(default="cpu", description="Device for Whisper (cpu, cuda)")
    whisper_compute_type: str = Field(default="int8", description="Compute type for Whisper")
    stt_confidence_threshold: float = Field(default=0.7, description="Minimum confidence for STT results")
    stt_max_duration: int = Field(default=300, description="Maximum audio duration in seconds")
    stt_supported_formats: List[str] = Field(
        default=["pcm", "wav", "mp3", "webm"],
        description="Supported audio formats"
    )
    
    # LLM Configuration
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    ollama_model: str = Field(default="llama2", description="Default LLM model")
    ollama_timeout: int = Field(default=30, description="Ollama request timeout in seconds")
    llm_max_tokens: int = Field(default=150, description="Maximum tokens for LLM responses")
    llm_temperature: float = Field(default=0.7, description="LLM temperature parameter")
    llm_system_prompt: str = Field(
        default="You are a helpful voice assistant. Respond concisely and accurately.",
        description="System prompt for LLM"
    )
    
    # MCP (Model Context Protocol) Configuration
    mcp_timeout: int = Field(default=10, description="MCP timeout in seconds")
    mcp_max_results: int = Field(default=100, description="Maximum MCP results")
    mcp_enabled_tools: List[str] = Field(
        default=["weather", "calculator", "calendar", "reminder"],
        description="Enabled MCP tools"
    )
    
    # Audio Processing Configuration
    audio_sample_rate: int = Field(default=16000, description="Audio sample rate")
    audio_channels: int = Field(default=1, description="Audio channels (1=mono, 2=stereo)")
    audio_bit_depth: int = Field(default=16, description="Audio bit depth")
    audio_chunk_size: int = Field(default=4096, description="Audio chunk size for processing")
    audio_max_buffer_size: int = Field(default=10485760, description="Maximum audio buffer size (10MB)")
    
    # Database Configuration
    database_url: Optional[str] = Field(default=None, description="Database connection URL")
    database_echo: bool = Field(default=False, description="Echo SQL queries")
    database_pool_size: int = Field(default=5, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Database max overflow connections")
    
    # Cache Configuration
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    cache_max_size: int = Field(default=1000, description="Maximum cache entries")
    
    # File Storage Configuration
    storage_path: str = Field(default="./storage", description="File storage directory")
    max_file_size: int = Field(default=104857600, description="Maximum file size (100MB)")
    allowed_file_extensions: List[str] = Field(
        default=[".mp3", ".wav", ".webm", ".m4a", ".ogg"],
        description="Allowed file extensions"
    )
    
    # Performance Configuration
    max_workers: int = Field(default=4, description="Maximum worker processes")
    async_semaphore_limit: int = Field(default=100, description="Async operation semaphore limit")
    request_timeout: int = Field(default=60, description="Request timeout in seconds")
    rate_limit_requests: int = Field(default=60, description="Rate limit requests per minute")
    
    # Monitoring and Metrics
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Metrics port")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    
    # Development and Testing
    hot_reload: bool = Field(default=False, description="Enable hot reload")
    auto_reload_models: bool = Field(default=False, description="Auto-reload models on changes")
    mock_services: bool = Field(default=False, description="Use mock services for testing")
    
    # Feature Flags
    enable_stt: bool = Field(default=True, description="Enable STT service")
    enable_llm: bool = Field(default=True, description="Enable LLM service")
    enable_mcp: bool = Field(default=True, description="Enable MCP service")
    enable_audio_processing: bool = Field(default=True, description="Enable audio processing")
    enable_transcription: bool = Field(default=True, description="Enable live transcription")
    enable_streaming: bool = Field(default=True, description="Enable response streaming")
    
    # Model Loading Configuration
    model_cache_size: int = Field(default=3, description="Number of models to keep in memory")
    model_preload: bool = Field(default=False, description="Preload models on startup")
    model_unload_timeout: int = Field(default=300, description="Model unload timeout in seconds")
    
    # Security and Validation
    max_audio_duration: int = Field(default=600, description="Maximum audio duration (10 minutes)")
    allowed_audio_formats: List[str] = Field(
        default=["audio/wav", "audio/mpeg", "audio/webm", "audio/ogg"],
        description="Allowed MIME types for audio"
    )
    sanitize_input: bool = Field(default=True, description="Sanitize user input")
    
    # Integration Configuration
    external_api_timeout: int = Field(default=30, description="External API timeout")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for events")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
        _create_directories(_settings)
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment"""
    global _settings
    _settings = Settings()
    return _settings


def _create_directories(settings: Settings) -> None:
    """Create necessary directories"""
    directories = [
        Path(settings.storage_path),
        Path(settings.storage_path) / "audio",
        Path(settings.storage_path) / "logs",
        Path(settings.storage_path) / "cache",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_database_url() -> str:
    """Get database URL for SQLAlchemy"""
    settings = get_settings()
    if settings.database_url:
        return settings.database_url
    
    # Default to SQLite if no database URL provided
    return f"sqlite:///./{settings.storage_path}/voice_control.db"


def get_redis_url() -> str:
    """Get Redis URL"""
    settings = get_settings()
    return settings.redis_url or "redis://localhost:6379/0"


# Environment-specific configurations
ENV_CONFIGS = {
    "development": {
        "debug": True,
        "log_level": "DEBUG",
        "hot_reload": True,
        "cors_origins": ["http://localhost:3000", "http://localhost:19006"],
    },
    "staging": {
        "debug": False,
        "log_level": "INFO",
        "cors_origins": ["https://staging.example.com"],
    },
    "production": {
        "debug": False,
        "log_level": "WARNING",
        "hot_reload": False,
        "cors_origins": ["https://example.com"],
    },
}