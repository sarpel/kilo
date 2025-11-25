"""
MCP (Model Context Protocol) Service

Comprehensive MCP client infrastructure that manages connections to MCP servers,
handles tool discovery, execution, and provides integration with various MCP servers
including Windows and Chrome DevTools.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import aiohttp
import websockets
from enum import Enum

from src.config.settings import get_settings
from src.utils.logger import get_logger, log_performance, get_audit_logger

logger = get_logger(__name__)
audit_logger = get_audit_logger()
settings = get_settings()


class MCPMessageType(str, Enum):
    """MCP message types"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MCPServerStatus(str, Enum):
    """MCP server connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class MCPTool:
    """MCP tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    annotations: Dict[str, Any] = field(default_factory=dict)
    server_name: str = ""


@dataclass
class MCPResource:
    """MCP resource definition"""
    uri: str
    name: str
    description: str = ""
    mime_type: str = ""
    server_name: str = ""


@dataclass
class MCPPrompt:
    """MCP prompt definition"""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    server_name: str = ""


@dataclass
class MCPRequest:
    """MCP request structure"""
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    jsonrpc: str = "2.0"


@dataclass
class MCPResponse:
    """MCP response structure"""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: str = ""
    jsonrpc: str = "2.0"


class MCPServerConnection:
    """Manages connection to a single MCP server"""
    
    def __init__(self, name: str, uri: str, server_type: str = "unknown"):
        self.name = name
        self.uri = uri
        self.server_type = server_type
        self.status = MCPServerStatus.DISCONNECTED
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Capabilities and features
        self.capabilities: Dict[str, Any] = {}
        self.tools: List[MCPTool] = []
        self.resources: List[MCPResource] = []
        self.prompts: List[MCPPrompt] = []
        
        # Request tracking
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.request_timeout = 30.0
        
        # Reconnection settings
        self.max_retries = 5
        self.retry_delay = 5.0
        self.current_retry = 0
        
        # Statistics
        self.stats = {
            "requests_sent": 0,
            "requests_received": 0,
            "errors": 0,
            "last_activity": None,
            "uptime": 0
        }
    
    async def connect(self) -> bool:
        """Connect to MCP server"""
        if self.status in [MCPServerStatus.CONNECTING, MCPServerStatus.CONNECTED]:
            return True
        
        self.status = MCPServerStatus.CONNECTING
        logger.info(f"Connecting to MCP server: {self.name} at {self.uri}")
        
        try:
            # Create WebSocket connection
            self.websocket = await websockets.connect(
                self.uri,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5
            )
            
            self.status = MCPServerStatus.CONNECTED
            self.current_retry = 0
            
            # Initialize server capabilities
            await self._initialize_server()
            
            # Start message handling
            asyncio.create_task(self._handle_messages())
            
            logger.info(f"Connected to MCP server: {self.name}")
            audit_logger.log_system_event(
                event="mcp_server_connected",
                source=self.name,
                details={"uri": self.uri, "type": self.server_type}
            )
            
            return True
            
        except Exception as e:
            self.status = MCPServerStatus.ERROR
            logger.error(f"Failed to connect to MCP server {self.name}: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.status = MCPServerStatus.DISCONNECTED
        logger.info(f"Disconnected from MCP server: {self.name}")
    
    async def _initialize_server(self):
        """Initialize server capabilities and tools"""
        try:
            # Initialize (some servers require this)
            init_request = MCPRequest(
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "roots": {"listChanged": True},
                        "sampling": {}
                    },
                    "clientInfo": {
                        "name": "voice-control-server",
                        "version": "1.0.0"
                    }
                }
            )
            
            init_response = await self._send_request(init_request)
            
            # List available tools
            tools_request = MCPRequest(method="tools/list")
            tools_response = await self._send_request(tools_request)
            
            if tools_response.result and "tools" in tools_response.result:
                for tool_data in tools_response.result["tools"]:
                    tool = MCPTool(
                        name=tool_data["name"],
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                        annotations=tool_data.get("annotations", {}),
                        server_name=self.name
                    )
                    self.tools.append(tool)
            
            # List resources if supported
            try:
                resources_request = MCPRequest(method="resources/list")
                resources_response = await self._send_request(resources_request)
                
                if resources_response.result and "resources" in resources_response.result:
                    for resource_data in resources_response.result["resources"]:
                        resource = MCPResource(
                            uri=resource_data["uri"],
                            name=resource_data["name"],
                            description=resource_data.get("description", ""),
                            mime_type=resource_data.get("mimeType", ""),
                            server_name=self.name
                        )
                        self.resources.append(resource)
            except Exception:
                # Resources not supported
                pass
            
            logger.info(f"MCP server {self.name} initialized with {len(self.tools)} tools, {len(self.resources)} resources")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server {self.name}: {e}")
            raise
    
    async def _handle_messages(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from {self.name}: {e}")
                except Exception as e:
                    logger.error(f"Message handling error from {self.name}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Connection closed for {self.name}")
            self.status = MCPServerStatus.DISCONNECTED
        except Exception as e:
            logger.error(f"WebSocket error for {self.name}: {e}")
            self.status = MCPServerStatus.ERROR
    
    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming MCP message"""
        message_id = data.get("id")
        
        # Handle response
        if "result" in data or "error" in data:
            if message_id in self.pending_requests:
                future = self.pending_requests.pop(message_id)
                
                response = MCPResponse(
                    result=data.get("result"),
                    error=data.get("error"),
                    id=message_id
                )
                
                if not future.done():
                    future.set_result(response)
            
            self.stats["requests_received"] += 1
        
        # Handle notification
        elif data.get("method"):
            await self._handle_notification(data)
        
        self.stats["last_activity"] = datetime.utcnow()
    
    async def _handle_notification(self, data: Dict[str, Any]):
        """Handle MCP notification"""
        method = data.get("method")
        params = data.get("params", {})
        
        # Handle server notifications
        if method == "notifications/resources/updated":
            # Resources updated, refresh if needed
            logger.debug(f"Resources updated on {self.name}")
        
        elif method == "notifications/tools/listChanged":
            # Tools list changed, refresh if needed
            logger.debug(f"Tools list changed on {self.name}")
        
        else:
            logger.debug(f"Unknown notification from {self.name}: {method}")
    
    async def _send_request(self, request: MCPRequest) -> MCPResponse:
        """Send MCP request and wait for response"""
        if self.status != MCPServerStatus.CONNECTED or not self.websocket:
            raise ConnectionError(f"MCP server {self.name} is not connected")
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request.id] = future
        
        try:
            # Send request
            message = {
                "jsonrpc": "2.0",
                "id": request.id,
                "method": request.method,
                "params": request.params
            }
            
            await self.websocket.send(json.dumps(message))
            self.stats["requests_sent"] += 1
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=self.request_timeout)
            return response
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(request.id, None)
            raise TimeoutError(f"Request to {self.name} timed out")
        except Exception as e:
            self.pending_requests.pop(request.id, None)
            self.stats["errors"] += 1
            raise e
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        arguments = arguments or {}
        
        request = MCPRequest(
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments
            }
        )
        
        try:
            response = await self._send_request(request)
            
            if response.error:
                return {
                    "success": False,
                    "error": response.error.get("message", "Unknown error"),
                    "error_code": response.error.get("code", -1)
                }
            
            return {
                "success": True,
                "result": response.result,
                "content": response.result.get("content", []) if response.result else []
            }
            
        except Exception as e:
            logger.error(f"Tool call failed on {self.name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def read_resource(self, resource_uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        request = MCPRequest(
            method="resources/read",
            params={
                "uri": resource_uri
            }
        )
        
        try:
            response = await self._send_request(request)
            
            if response.error:
                return {
                    "success": False,
                    "error": response.error.get("message", "Unknown error")
                }
            
            return {
                "success": True,
                "contents": response.result.get("contents", []) if response.result else []
            }
            
        except Exception as e:
            logger.error(f"Resource read failed on {self.name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            **self.stats,
            "name": self.name,
            "uri": self.uri,
            "status": self.status.value,
            "server_type": self.server_type,
            "tools_count": len(self.tools),
            "resources_count": len(self.resources),
            "pending_requests": len(self.pending_requests)
        }


class MCPService:
    """Main MCP service that manages multiple server connections"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConnection] = {}
        self.server_configs: Dict[str, Dict[str, Any]] = {}
        self.is_initialized = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Built-in tool handlers for common operations
        self.builtin_tools: Dict[str, Callable] = {}
        
        # Registry for tool execution
        self.tool_registry: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        """Initialize MCP service"""
        try:
            logger.info("Initializing MCP service...")
            
            # Load server configurations
            await self._load_server_configs()
            
            # Register built-in tools
            self._register_builtin_tools()
            
            # Connect to configured servers
            await self._connect_servers()
            
            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.is_initialized = True
            logger.info("MCP service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP service: {e}")
            raise
    
    async def _load_server_configs(self):
        """Load MCP server configurations"""
        # Define known server configurations
        self.server_configs = {
            "windows": {
                "uri": "ws://localhost:3000/mcp",  # Windows MCP server
                "server_type": "windows",
                "auto_connect": False,  # These will use built-in tools
                "description": "Windows System Control"
            },
            "chrome_devtools": {
                "uri": "ws://localhost:9222/devtools/browser",  # Chrome DevTools
                "server_type": "chrome_devtools", 
                "auto_connect": False,  # Requires Chrome to be running with DevTools
                "description": "Chrome Browser Automation"
            },
            "calculator": {
                "uri": "ws://localhost:3001/mcp",  # Calculator MCP server
                "server_type": "calculator",
                "auto_connect": False,
                "description": "Calculator Service"
            },
            "weather": {
                "uri": "ws://localhost:3002/mcp",  # Weather MCP server
                "server_type": "weather",
                "auto_connect": False,
                "description": "Weather Information"
            }
        }
        
        logger.info(f"Loaded {len(self.server_configs)} MCP server configurations")
    
    def _register_builtin_tools(self):
        """Register built-in tools that don't require external MCP servers"""
        
        # Import built-in tool integrations
        try:
            from src.integrations.windows_mcp import get_windows_tools
            from src.integrations.chrome_devtools_mcp import get_chrome_tools
        except ImportError as e:
            logger.warning(f"Could not import built-in tool integrations: {e}")
            return
        
        self.builtin_tools = {
            "get_time": self._builtin_get_time,
            "get_system_info": self._builtin_get_system_info,
            "calculate": self._builtin_calculate,
            "echo": self._builtin_echo,
        }
        
        # Register Windows tools
        try:
            windows_tools = get_windows_tools()
            windows_tool_methods = {
                "list_processes": windows_tools.list_processes,
                "kill_process": windows_tools.kill_process,
                "start_process": windows_tools.start_process,
                "get_system_info": windows_tools.get_system_info,  # Enhanced version
                "list_files": windows_tools.list_files,
                "read_file": windows_tools.read_file,
                "write_file": windows_tools.write_file,
                "list_windows": windows_tools.list_windows,
                "focus_window": windows_tools.focus_window,
                "resize_window": windows_tools.resize_window,
                "minimize_window": windows_tools.minimize_window,
                "maximize_window": windows_tools.maximize_window,
                "restore_window": windows_tools.restore_window,
                "run_command": windows_tools.run_command,
            }
            self.builtin_tools.update(windows_tool_methods)
            logger.info(f"Registered {len(windows_tool_methods)} Windows tools")
        except Exception as e:
            logger.error(f"Failed to register Windows tools: {e}")
        
        # Register Chrome DevTools tools
        try:
            chrome_tools = get_chrome_tools()
            chrome_tool_methods = {
                "chrome_connect": chrome_tools.connect,
                "chrome_disconnect": chrome_tools.disconnect,
                "chrome_navigate": chrome_tools.navigate_to_url,
                "chrome_get_page": chrome_tools.get_current_page,
                "chrome_screenshot": chrome_tools.take_screenshot,
                "chrome_click": chrome_tools.click_element,
                "chrome_type": chrome_tools.type_text,
                "chrome_get_text": chrome_tools.get_element_text,
                "chrome_get_html": chrome_tools.get_page_html,
                "chrome_scroll": chrome_tools.scroll_page,
                "chrome_reload": chrome_tools.reload_page,
                "chrome_back": chrome_tools.navigate_back,
                "chrome_forward": chrome_tools.navigate_forward,
                "chrome_execute_script": chrome_tools.execute_javascript,
                "chrome_wait_for_element": chrome_tools.wait_for_element,
                "chrome_fill_form": chrome_tools.fill_form,
            }
            self.builtin_tools.update(chrome_tool_methods)
            logger.info(f"Registered {len(chrome_tool_methods)} Chrome DevTools tools")
        except Exception as e:
            logger.error(f"Failed to register Chrome DevTools tools: {e}")
    
    async def _connect_servers(self):
        """Connect to configured MCP servers"""
        for server_name, config in self.server_configs.items():
            if config.get("auto_connect", False):
                try:
                    connection = MCPServerConnection(
                        name=server_name,
                        uri=config["uri"],
                        server_type=config["server_type"]
                    )
                    
                    if await connection.connect():
                        self.servers[server_name] = connection
                        logger.info(f"Connected to MCP server: {server_name}")
                    else:
                        logger.warning(f"Failed to connect to MCP server: {server_name}")
                        
                except Exception as e:
                    logger.error(f"Error connecting to MCP server {server_name}: {e}")
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(30)  # Run every 30 seconds
                
                # Check for stale connections
                for server_name, connection in list(self.servers.items()):
                    if connection.status == MCPServerStatus.ERROR:
                        logger.warning(f"Attempting to reconnect to {server_name}")
                        await connection.connect()
                
                # Update server statistics
                for connection in self.servers.values():
                    if connection.status == MCPServerStatus.CONNECTED:
                        if connection.stats["last_activity"]:
                            idle_time = (datetime.utcnow() - connection.stats["last_activity"]).total_seconds()
                            if idle_time > 300:  # 5 minutes idle
                                logger.debug(f"Connection {connection.name} has been idle for {idle_time:.0f} seconds")
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a tool across available MCP servers"""
        arguments = arguments or {}
        
        start_time = time.time()
        
        try:
            # Check built-in tools first
            if tool_name in self.builtin_tools:
                logger.info(f"Executing built-in tool: {tool_name}")
                result = await self.builtin_tools[tool_name](arguments)
                return result
            
            # Find tool across MCP servers
            for server_name, connection in self.servers.items():
                if connection.status == MCPServerStatus.CONNECTED:
                    # Check if server has this tool
                    if any(tool.name == tool_name for tool in connection.tools):
                        logger.info(f"Executing tool {tool_name} on server {server_name}")
                        result = await connection.call_tool(tool_name, arguments)
                        
                        # Add server info to result
                        if isinstance(result, dict):
                            result["server"] = server_name
                            result["execution_time_ms"] = int((time.time() - start_time) * 1000)
                        
                        return result
            
            # Tool not found
            logger.warning(f"Tool {tool_name} not found on any connected server")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
                "available_tools": self.get_available_tools()
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }
    
    async def _builtin_get_time(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in tool to get current time"""
        import datetime as dt
        
        timezone = arguments.get("timezone", "UTC")
        format_str = arguments.get("format", "%Y-%m-%d %H:%M:%S")
        
        try:
            if timezone.upper() == "UTC":
                now = dt.datetime.utcnow()
            else:
                import pytz
                tz = pytz.timezone(timezone)
                now = dt.datetime.now(tz)
            
            return {
                "success": True,
                "current_time": now.strftime(format_str),
                "timezone": timezone,
                "iso_format": now.isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Time formatting error: {e}"
            }
    
    async def _builtin_get_system_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in tool to get system information"""
        try:
            import platform
            import psutil
            
            return {
                "success": True,
                "system": {
                    "platform": platform.platform(),
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor()
                },
                "cpu": {
                    "count": psutil.cpu_count(),
                    "usage_percent": psutil.cpu_percent(interval=1)
                },
                "memory": {
                    "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                    "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                    "usage_percent": psutil.virtual_memory().percent
                },
                "disk": {
                    "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                    "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
                    "usage_percent": psutil.disk_usage('/').percent
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"System info error: {e}"
            }
    
    async def _builtin_calculate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in calculator tool"""
        try:
            expression = arguments.get("expression", "")
            if not expression:
                return {
                    "success": False,
                    "error": "No expression provided"
                }
            
            # Safe evaluation (basic implementation)
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                return {
                    "success": False,
                    "error": "Invalid characters in expression"
                }
            
            result = eval(expression)
            
            return {
                "success": True,
                "expression": expression,
                "result": result,
                "type": type(result).__name__
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Calculation error: {e}"
            }
    
    async def _builtin_echo(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in echo tool for testing"""
        message = arguments.get("message", "Hello from voice control!")
        
        return {
            "success": True,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "echo_type": "builtin"
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools"""
        tools = []
        
        # Add built-in tools
        for tool_name in self.builtin_tools.keys():
            tools.append({
                "name": tool_name,
                "description": f"Built-in {tool_name} tool",
                "server": "builtin",
                "type": "builtin"
            })
        
        # Add MCP server tools
        for server_name, connection in self.servers.items():
            if connection.status == MCPServerStatus.CONNECTED:
                for tool in connection.tools:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "server": server_name,
                        "type": "mcp",
                        "input_schema": tool.input_schema
                    })
        
        return tools
    
    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names"""
        return [name for name, conn in self.servers.items() 
                if conn.status == MCPServerStatus.CONNECTED]
    
    async def connect_server(self, server_name: str) -> bool:
        """Connect to a specific MCP server"""
        if server_name not in self.server_configs:
            logger.error(f"Unknown server: {server_name}")
            return False
        
        if server_name in self.servers:
            logger.info(f"Server {server_name} already connected")
            return True
        
        config = self.server_configs[server_name]
        connection = MCPServerConnection(
            name=server_name,
            uri=config["uri"],
            server_type=config["server_type"]
        )
        
        try:
            if await connection.connect():
                self.servers[server_name] = connection
                logger.info(f"Connected to MCP server: {server_name}")
                return True
            else:
                logger.error(f"Failed to connect to {server_name}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to {server_name}: {e}")
            return False
    
    async def disconnect_server(self, server_name: str):
        """Disconnect from a specific MCP server"""
        if server_name in self.servers:
            await self.servers[server_name].disconnect()
            del self.servers[server_name]
            logger.info(f"Disconnected from MCP server: {server_name}")
    
    async def get_server_stats(self) -> Dict[str, Any]:
        """Get statistics for all connected servers"""
        stats = {}
        for server_name, connection in self.servers.items():
            stats[server_name] = connection.get_stats()
        return stats
    
    async def cleanup(self):
        """Clean up MCP service"""
        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all servers
        for server_name in list(self.servers.keys()):
            await self.disconnect_server(server_name)
        
        logger.info("MCP service cleaned up")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for MCP service"""
        connected_servers = self.get_connected_servers()
        
        return {
            "status": "healthy" if connected_servers else "degraded",
            "initialized": self.is_initialized,
            "connected_servers": len(connected_servers),
            "available_tools": len(self.get_available_tools()),
            "servers": connected_servers
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get detailed MCP service status"""
        return {
            "initialized": self.is_initialized,
            "servers": {name: conn.get_stats() for name, conn in self.servers.items()},
            "available_tools": self.get_available_tools(),
            "builtin_tools": list(self.builtin_tools.keys()),
            "configs": self.server_configs
        }
    
    async def reload_models(self):
        """Reload MCP connections"""
        try:
            logger.info("Reloading MCP connections...")
            
            # Disconnect all servers
            for server_name in list(self.servers.keys()):
                await self.disconnect_server(server_name)
            
            # Reconnect auto-connect servers
            await self._connect_servers()
            
            logger.info("MCP connections reloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload MCP connections: {e}")
            raise