"""
WebSocket Connection Manager

Manages WebSocket connections, handles connection lifecycle,
and provides utilities for broadcasting messages to connected clients.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Set, Optional, Any, List
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection"""
    websocket: WebSocket
    session_id: str
    client_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    audio_chunks_received: int = 0
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_authenticated: bool = False


class ConnectionManager:
    """Manages WebSocket connections and sessions"""
    
    def __init__(self):
        # Active connections organized by session ID
        self.active_connections: Dict[str, ConnectionInfo] = {}
        
        # Client ID to session ID mapping
        self.client_to_session: Dict[str, str] = {}
        
        # Connection statistics
        self.connection_stats: Dict[str, Any] = {
            "total_connections": 0,
            "active_connections": 0,
            "max_concurrent": 0,
            "connection_attempts": 0,
            "disconnections": 0,
        }
        
        # Rate limiting per IP
        self.rate_limiter: Dict[str, deque] = defaultdict(lambda: deque(maxlen=60))
        
        # Heartbeat tracking
        self.last_heartbeat: Dict[str, datetime] = {}
        
        # Cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None
        self.cleanup_interval = 60  # seconds
        
        # Start background cleanup task
        self._start_cleanup_task()
    
    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """Accept a new WebSocket connection and create a session"""
        
        # Rate limiting check
        client_ip = self._get_client_ip(websocket)
        if not await self._check_rate_limit(client_ip):
            await websocket.close(code=1008, reason="Rate limit exceeded")
            raise ConnectionError("Rate limit exceeded")
        
        # Accept the connection
        await websocket.accept()
        
        # Generate session ID
        session_id = self._generate_session_id()
        
        # Create connection info
        connection_info = ConnectionInfo(
            websocket=websocket,
            session_id=session_id,
            client_id=client_id or f"client_{len(self.active_connections)}",
            ip_address=client_ip
        )
        
        # Store connection
        self.active_connections[session_id] = connection_info
        if client_id:
            self.client_to_session[client_id] = session_id
        
        # Update statistics
        self.connection_stats["total_connections"] += 1
        self.connection_stats["connection_attempts"] += 1
        self.connection_stats["active_connections"] = len(self.active_connections)
        self.connection_stats["max_concurrent"] = max(
            self.connection_stats["max_concurrent"],
            len(self.active_connections)
        )
        
        logger.info(f"WebSocket connected: {session_id} from {client_ip}")
        
        return session_id
    
    async def disconnect(self, session_id: str):
        """Disconnect a WebSocket session"""
        
        connection_info = self.active_connections.get(session_id)
        if not connection_info:
            return
        
        try:
            # Close the WebSocket connection
            if connection_info.websocket.application_state == WebSocketState.CONNECTED:
                await connection_info.websocket.close()
        except Exception as e:
            logger.warning(f"Error closing WebSocket for {session_id}: {e}")
        
        # Remove from active connections
        self.active_connections.pop(session_id, None)
        
        # Remove client mapping
        if connection_info.client_id:
            self.client_to_session.pop(connection_info.client_id, None)
        
        # Remove heartbeat tracking
        self.last_heartbeat.pop(session_id, None)
        
        # Update statistics
        self.connection_stats["active_connections"] = len(self.active_connections)
        self.connection_stats["disconnections"] += 1
        
        logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific session"""
        
        connection_info = self.active_connections.get(session_id)
        if not connection_info:
            logger.warning(f"Attempted to send message to non-existent session: {session_id}")
            return False
        
        try:
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.utcnow().isoformat()
            
            # Send message
            await connection_info.websocket.send_text(json.dumps(message))
            
            # Update connection stats
            connection_info.message_count += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {session_id}: {e}")
            # Connection might be dead, disconnect
            await self.disconnect(session_id)
            return False
    
    async def broadcast_message(self, message: Dict[str, Any], exclude_sessions: Set[str] = None) -> int:
        """Broadcast a message to all connected sessions"""
        
        if exclude_sessions is None:
            exclude_sessions = set()
        
        success_count = 0
        
        for session_id in list(self.active_connections.keys()):
            if session_id in exclude_sessions:
                continue
                
            if await self.send_message(session_id, message):
                success_count += 1
        
        return success_count
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific client ID"""
        
        session_id = self.client_to_session.get(client_id)
        if not session_id:
            logger.warning(f"Attempted to send message to non-existent client: {client_id}")
            return False
        
        return await self.send_message(session_id, message)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
    
    def get_connection_info(self, session_id: str) -> Optional[ConnectionInfo]:
        """Get connection information for a session"""
        return self.active_connections.get(session_id)
    
    def get_all_connections(self) -> Dict[str, ConnectionInfo]:
        """Get all active connections"""
        return self.active_connections.copy()
    
    def get_client_sessions(self) -> Dict[str, str]:
        """Get client ID to session ID mapping"""
        return self.client_to_session.copy()
    
    async def update_heartbeat(self, session_id: str):
        """Update the last heartbeat time for a session"""
        
        if session_id in self.active_connections:
            self.last_heartbeat[session_id] = datetime.utcnow()
            self.active_connections[session_id].last_ping = datetime.utcnow()
    
    async def check_heartbeats(self) -> List[str]:
        """Check for stale connections and return session IDs to disconnect"""
        
        current_time = datetime.utcnow()
        stale_sessions = []
        
        for session_id, last_heartbeat in list(self.last_heartbeat.items()):
            if current_time - last_heartbeat > timedelta(seconds=settings.websocket_ping_timeout):
                stale_sessions.append(session_id)
        
        return stale_sessions
    
    async def cleanup_stale_connections(self):
        """Clean up stale connections"""
        
        stale_sessions = await self.check_heartbeats()
        
        for session_id in stale_sessions:
            logger.warning(f"Cleaning up stale connection: {session_id}")
            await self.disconnect(session_id)
        
        if stale_sessions:
            logger.info(f"Cleaned up {len(stale_sessions)} stale connections")
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        
        active_connections = len(self.active_connections)
        current_time = datetime.utcnow()
        
        # Calculate average session duration
        durations = []
        for conn_info in self.active_connections.values():
            duration = (current_time - conn_info.connected_at).total_seconds()
            durations.append(duration)
        
        avg_session_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            **self.connection_stats,
            "active_connections": active_connections,
            "avg_session_duration_seconds": avg_session_duration,
            "stale_connections": len(await self.check_heartbeats())
        }
    
    def _get_client_ip(self, websocket: WebSocket) -> str:
        """Get client IP address from WebSocket"""
        try:
            # Try to get from headers first (for proxied connections)
            if hasattr(websocket, 'headers'):
                x_forwarded_for = websocket.headers.get('x-forwarded-for')
                if x_forwarded_for:
                    return x_forwarded_for.split(',')[0].strip()
            
            # Fallback to direct connection info
            if hasattr(websocket, 'client') and websocket.client:
                return websocket.client.host
                
        except Exception as e:
            logger.warning(f"Could not determine client IP: {e}")
        
        return "unknown"
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        timestamp = str(int(time.time() * 1000))
        import random
        random_suffix = ''.join(random.choices('0123456789abcdef', k=8))
        return f"session_{timestamp}_{random_suffix}"
    
    async def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if client IP is within rate limits"""
        
        current_time = time.time()
        requests = self.rate_limiter[client_ip]
        
        # Remove old requests (older than 1 minute)
        while requests and current_time - requests[0] > 60:
            requests.popleft()
        
        # Check if under limit
        if len(requests) >= settings.websocket_max_connections:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return False
        
        # Add current request
        requests.append(current_time)
        return True
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval)
                    await self.cleanup_stale_connections()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        self.cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def cleanup(self):
        """Clean up the connection manager"""
        
        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all active connections
        for session_id in list(self.active_connections.keys()):
            await self.disconnect(session_id)
        
        # Clear data structures
        self.active_connections.clear()
        self.client_to_session.clear()
        self.rate_limiter.clear()
        self.last_heartbeat.clear()
        
        logger.info("Connection manager cleaned up")