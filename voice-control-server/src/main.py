"""
FastAPI Voice Control Server

Main application entry point for the voice control ecosystem.
Handles WebSocket connections, speech-to-text, LLM processing, and MCP protocol.
"""

import logging
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Dict, Any
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os

from src.websocket.connection_manager import ConnectionManager
from src.websocket.handlers import WebSocketHandler
from src.config.settings import get_settings
from src.models.schemas import (
    ConnectionRequest,
    ConnectionResponse,
    AudioStart,
    AudioData,
    AudioStop,
    STTRequest,
    LLMRequest,
    MCPRequest
)
from src.services.stt_service import STTService
from src.services.llm_service import LLMService
from src.services.mcp_service import MCPService
from src.utils.logger import setup_logger

# Initialize settings and logger
settings = get_settings()
logger = setup_logger(__name__)

# Global services
stt_service: STTService = None
llm_service: LLMService = None
mcp_service: MCPService = None
connection_manager: ConnectionManager = None

# Application start time for uptime calculation
APP_START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global stt_service, llm_service, mcp_service, connection_manager
    
    # Startup
    logger.info("Starting Voice Control Server...")
    
    try:
        # Initialize connection manager
        connection_manager = ConnectionManager()
        
        # Initialize services
        stt_service = STTService()
        llm_service = LLMService()
        mcp_service = MCPService()
        
        # Start services
        await stt_service.initialize()
        await llm_service.initialize()
        await mcp_service.initialize()
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Voice Control Server...")
    
    try:
        # Cleanup services
        await stt_service.cleanup()
        await llm_service.cleanup()
        await mcp_service.cleanup()
        
        logger.info("Services cleaned up successfully")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Create FastAPI application
app = FastAPI(
    title="Voice Control Server",
    description="FastAPI server for voice control ecosystem with STT, LLM, and MCP support",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "version": "1.0.0",
            "services": {
                "stt": await stt_service.health_check() if stt_service else "not_initialized",
                "llm": await llm_service.health_check() if llm_service else "not_initialized",
                "mcp": await mcp_service.health_check() if mcp_service else "not_initialized",
            }
        }
    )

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time voice control communication"""
    session_id = None
    
    try:
        await connection_manager.connect(websocket)
        
        # Create WebSocket handler for this connection
        handler = WebSocketHandler(
            websocket=websocket,
            connection_manager=connection_manager,
            stt_service=stt_service,
            llm_service=llm_service,
            mcp_service=mcp_service
        )
        
        # Handle the connection
        session_id = await handler.handle_connection()
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass
    finally:
        if session_id:
            await connection_manager.disconnect(session_id)

# API endpoints for configuration and status
@app.get("/api/config")
async def get_config():
    """Get server configuration information"""
    return JSONResponse(
        content={
            "stt_models": stt_service.get_supported_models() if stt_service else [],
            "llm_models": llm_service.get_supported_models() if llm_service else [],
            "capabilities": ["stt", "llm", "mcp"],
            "audio_formats": ["pcm", "wav", "mp3"],
            "websocket_url": "/ws"
        }
    )

@app.get("/api/status")
async def get_status():
    """Get detailed server status"""
    return JSONResponse(
        content={
            "server": {
                "version": "1.0.0",
                "uptime": await get_uptime(),
                "active_connections": connection_manager.get_active_connection_count() if connection_manager else 0
            },
            "services": {
                "stt": await stt_service.get_status() if stt_service else {"status": "not_initialized"},
                "llm": await llm_service.get_status() if llm_service else {"status": "not_initialized"},
                "mcp": await mcp_service.get_status() if mcp_service else {"status": "not_initialized"}
            }
        }
    )

@app.post("/api/reload-models")
async def reload_models():
    """Reload STT and LLM models (admin endpoint)"""
    try:
        await stt_service.reload_models()
        await llm_service.reload_models()
        return JSONResponse(
            status_code=200,
            content={"status": "Models reloaded successfully"}
        )
    except Exception as e:
        logger.error(f"Failed to reload models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload models: {str(e)}")

# Static file serving (for serving audio files, logs, etc.)
@app.get("/files/{file_path:path}")
async def serve_file(file_path: str):
    """Serve static files"""
    from pathlib import Path
    import os
    
    # Define allowed directories for security
    allowed_dirs = [
        settings.storage_path,
        os.path.join(settings.storage_path, "audio"),
        os.path.join(settings.storage_path, "logs"),
    ]
    
    # Construct full file path
    file_path = Path(file_path)
    
    # Security check: ensure file is within allowed directories
    full_path = None
    for allowed_dir in allowed_dirs:
        candidate_path = Path(allowed_dir) / file_path
        try:
            candidate_path.resolve().relative_to(Path(allowed_dir).resolve())
            if candidate_path.exists() and candidate_path.is_file():
                full_path = candidate_path
                break
        except (ValueError, OSError):
            continue
    
    if not full_path:
        raise HTTPException(status_code=403, detail="Access denied to file path")
    
    # Check file size limit
    if full_path.stat().st_size > settings.max_file_size:
        raise HTTPException(status_code=413, detail="File too large")
    
    # Determine content type
    content_type = "application/octet-stream"
    if full_path.suffix.lower() == ".wav":
        content_type = "audio/wav"
    elif full_path.suffix.lower() == ".log":
        content_type = "text/plain"
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(full_path),
        media_type=content_type,
        filename=file_path.name
    )

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "message": "The requested resource was not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "An internal server error occurred"}
    )

# Utility functions
async def get_uptime() -> int:
    """Get server uptime in seconds"""
    return int(time.time() - APP_START_TIME)

if __name__ == "__main__":
    # Run the server directly
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )