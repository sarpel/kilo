"""
Chrome DevTools MCP Integration

Provides Chrome browser automation capabilities including tab management,
DOM interaction, navigation, form filling, and browser control.
"""

import asyncio
import json
import time
import base64
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import websockets
import aiohttp

from src.utils.logger import get_logger, log_performance
from src.services.mcp_service import MCPTool

logger = get_logger(__name__)


class ChromeDevToolsAPI:
    """Chrome DevTools Protocol API client"""
    
    def __init__(self, debugger_url: str = "http://localhost:9222"):
        self.debugger_url = debugger_url.rstrip('/')
        self.ws_url = debugger_url.replace('http', 'ws') + '/devtools/browser'
        self.target_id: Optional[str] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.session_id: Optional[str] = None
        self.message_id = 0
        self.pending_messages: Dict[int, asyncio.Future] = {}
        
    async def connect(self) -> bool:
        """Connect to Chrome DevTools"""
        try:
            # Get list of targets
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.debugger_url}/json") as response:
                    if response.status != 200:
                        logger.error(f"Failed to get Chrome targets: {response.status}")
                        return False
                    
                    targets = await response.json()
                    
                    # Find the main page target
                    main_target = None
                    for target in targets:
                        if target.get('type') == 'page' and target.get('title'):
                            main_target = target
                            break
                    
                    if not main_target:
                        logger.error("No suitable Chrome target found")
                        return False
                    
                    self.target_id = main_target['id']
                    self.session_id = main_target.get('webSocketDebuggerUrl', '').split('/')[-1]
                    
                    # Connect WebSocket
                    if self.session_id:
                        ws_url = f"{self.debugger_url.replace('http', 'ws')}/devtools/page/{self.session_id}"
                        self.websocket = await websockets.connect(ws_url)
                        
                        # Enable domains
                        await self._enable_domains()
                        
                        logger.info(f"Connected to Chrome DevTools: {self.target_id}")
                        return True
                    else:
                        logger.error("Failed to get session ID")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to connect to Chrome DevTools: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Chrome DevTools"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.target_id = None
        self.session_id = None
        logger.info("Disconnected from Chrome DevTools")
    
    async def _enable_domains(self):
        """Enable required DevTools domains"""
        await self._send_command("Runtime.enable", {})
        await self._send_command("Page.enable", {})
        await self._send_command("DOM.enable", {})
        await self._send_command("Network.enable", {})
        await self._send_command("Console.enable", {})
    
    async def _send_command(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command and wait for response"""
        if not self.websocket:
            raise ConnectionError("Not connected to Chrome DevTools")
        
        params = params or {}
        self.message_id += 1
        
        command = {
            "id": self.message_id,
            "method": method,
            "params": params
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_messages[self.message_id] = future
        
        try:
            await self.websocket.send(json.dumps(command))
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
            
        except asyncio.TimeoutError:
            self.pending_messages.pop(self.message_id, None)
            raise TimeoutError(f"Command {method} timed out")
        except Exception as e:
            self.pending_messages.pop(self.message_id, None)
            raise e
    
    async def _handle_messages(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    if "id" in data and data["id"] in self.pending_messages:
                        future = self.pending_messages.pop(data["id"])
                        if not future.done():
                            future.set_result(data)
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from Chrome: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Chrome DevTools connection closed")
        except Exception as e:
            logger.error(f"Chrome DevTools message error: {e}")
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        try:
            response = await self._send_command("Page.navigate", {"url": url})
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            return {
                "success": True,
                "url": url,
                "frame_id": response.get("result", {}).get("frameId")
            }
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_page_title(self) -> Dict[str, Any]:
        """Get current page title"""
        try:
            response = await self._send_command("Page.getResourceContent", {
                "frameId": await self._get_main_frame_id()
            })
            
            # Fallback to simpler method
            response = await self._send_command("Runtime.evaluate", {
                "expression": "document.title"
            })
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            title = response.get("result", {}).get("value", "")
            return {"success": True, "title": title}
            
        except Exception as e:
            logger.error(f"Failed to get page title: {e}")
            return {"success": False, "error": str(e)}
    
    async def take_screenshot(self, full_page: bool = False) -> Dict[str, Any]:
        """Take a screenshot"""
        try:
            params = {
                "format": "png",
                "fromSurface": True
            }
            
            if full_page:
                # Get page dimensions first
                dimensions_response = await self._send_command("Runtime.evaluate", {
                    "expression": "{ width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight }"
                })
                
                if "result" in dimensions_response:
                    dimensions = dimensions_response["result"]["value"]
                    params["captureBeyondViewport"] = True
                    params["clip"] = {
                        "x": 0,
                        "y": 0,
                        "width": dimensions["width"],
                        "height": dimensions["height"],
                        "scale": 1
                    }
            
            response = await self._send_command("Page.captureScreenshot", params)
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            image_data = response.get("result", {}).get("data", "")
            
            return {
                "success": True,
                "image_data": image_data,
                "format": "png",
                "full_page": full_page
            }
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return {"success": False, "error": str(e)}
    
    async def click_element(self, selector: str) -> Dict[str, Any]:
        """Click an element by CSS selector"""
        try:
            # Query for element
            response = await self._send_command("Runtime.evaluate", {
                "expression": f'document.querySelector("{selector}")'
            })
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            element = response.get("result", {}).get("value")
            if not element:
                return {"success": False, "error": f"Element not found: {selector}"}
            
            # Click element
            click_response = await self._send_command("Runtime.evaluate", {
                "expression": f'document.querySelector("{selector}").click()'
            })
            
            if "error" in click_response:
                return {"success": False, "error": click_response["error"]["message"]}
            
            return {"success": True, "selector": selector}
            
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return {"success": False, "error": str(e)}
    
    async def type_text(self, selector: str, text: str, clear_first: bool = True) -> Dict[str, Any]:
        """Type text into an element"""
        try:
            # Focus element first
            focus_response = await self._send_command("Runtime.evaluate", {
                "expression": f'document.querySelector("{selector}").focus()'
            })
            
            if "error" in focus_response:
                return {"success": False, "error": focus_response["error"]["message"]}
            
            # Clear existing content if requested
            if clear_first:
                clear_response = await self._send_command("Runtime.evaluate", {
                    "expression": f'''
                        const element = document.querySelector("{selector}");
                        element.value = "";
                        element.dispatchEvent(new Event("input", {{bubbles: true}}));
                        element.dispatchEvent(new Event("change", {{bubbles: true}}));
                    '''
                })
            
            # Type text
            type_response = await self._send_command("Runtime.evaluate", {
                "expression": f'''
                    const element = document.querySelector("{selector}");
                    element.value = "{text}";
                    element.dispatchEvent(new Event("input", {{bubbles: true}}));
                    element.dispatchEvent(new Event("change", {{bubbles: true}}));
                '''
            })
            
            if "error" in type_response:
                return {"success": False, "error": type_response["error"]["message"]}
            
            return {"success": True, "selector": selector, "text": text}
            
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_element_text(self, selector: str) -> Dict[str, Any]:
        """Get text content of an element"""
        try:
            response = await self._send_command("Runtime.evaluate", {
                "expression": f'document.querySelector("{selector}").textContent'
            })
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            text = response.get("result", {}).get("value", "")
            
            return {"success": True, "selector": selector, "text": text}
            
        except Exception as e:
            logger.error(f"Failed to get element text: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_page_content(self) -> Dict[str, Any]:
        """Get current page HTML content"""
        try:
            response = await self._send_command("Runtime.evaluate", {
                "expression": "document.documentElement.outerHTML"
            })
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            content = response.get("result", {}).get("value", "")
            
            return {"success": True, "content": content}
            
        except Exception as e:
            logger.error(f"Failed to get page content: {e}")
            return {"success": False, "error": str(e)}
    
    async def scroll_page(self, x: int = 0, y: int = 500) -> Dict[str, Any]:
        """Scroll the page"""
        try:
            response = await self._send_command("Runtime.evaluate", {
                "expression": f"window.scrollBy({x}, {y})"
            })
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            return {"success": True, "x": x, "y": y}
            
        except Exception as e:
            logger.error(f"Failed to scroll page: {e}")
            return {"success": False, "error": str(e)}
    
    async def reload_page(self) -> Dict[str, Any]:
        """Reload the current page"""
        try:
            response = await self._send_command("Page.reload", {})
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to reload page: {e}")
            return {"success": False, "error": str(e)}
    
    async def go_back(self) -> Dict[str, Any]:
        """Go back in browser history"""
        try:
            response = await self._send_command("Page.goBack", {})
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to go back: {e}")
            return {"success": False, "error": str(e)}
    
    async def go_forward(self) -> Dict[str, Any]:
        """Go forward in browser history"""
        try:
            response = await self._send_command("Page.goForward", {})
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to go forward: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_page_info(self) -> Dict[str, Any]:
        """Get current page information"""
        try:
            # Get URL
            url_response = await self._send_command("Runtime.evaluate", {
                "expression": "window.location.href"
            })
            
            # Get title
            title_response = await self._send_command("Runtime.evaluate", {
                "expression": "document.title"
            })
            
            # Get dimensions
            dimensions_response = await self._send_command("Runtime.evaluate", {
                "expression": "{ width: window.innerWidth, height: window.innerHeight }"
            })
            
            url = url_response.get("result", {}).get("value", "") if "result" in url_response else ""
            title = title_response.get("result", {}).get("value", "") if "result" in title_response else ""
            dimensions = dimensions_response.get("result", {}).get("value", {}) if "result" in dimensions_response else {}
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "dimensions": dimensions
            }
            
        except Exception as e:
            logger.error(f"Failed to get page info: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_script(self, script: str) -> Dict[str, Any]:
        """Execute JavaScript code"""
        try:
            response = await self._send_command("Runtime.evaluate", {
                "expression": script
            })
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            result = response.get("result", {})
            
            return {
                "success": True,
                "result": result,
                "value": result.get("value")
            }
            
        except Exception as e:
            logger.error(f"Failed to execute script: {e}")
            return {"success": False, "error": str(e)}
    
    async def wait_for_element(self, selector: str, timeout: int = 10) -> Dict[str, Any]:
        """Wait for an element to appear"""
        try:
            # Simple polling approach
            start_time = time.time()
            while time.time() - start_time < timeout:
                response = await self._send_command("Runtime.evaluate", {
                    "expression": f'document.querySelector("{selector}") !== null'
                })
                
                if "result" in response and response["result"].get("value"):
                    return {"success": True, "selector": selector, "found": True}
                
                await asyncio.sleep(0.5)
            
            return {"success": False, "error": f"Element {selector} not found within {timeout} seconds"}
            
        except Exception as e:
            logger.error(f"Failed to wait for element: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_main_frame_id(self) -> str:
        """Get main frame ID"""
        try:
            response = await self._send_command("Page.getResourceContent", {})
            if "result" in response and "frameId" in response["result"]:
                return response["result"]["frameId"]
            
            # Fallback: try to get from navigation response
            return "main_frame"
            
        except Exception as e:
            logger.error(f"Failed to get main frame ID: {e}")
            return "main_frame"


class ChromeDevToolsTools:
    """Chrome DevTools MCP tools"""
    
    def __init__(self):
        self.api = ChromeDevToolsAPI()
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Connect to Chrome DevTools"""
        try:
            self.is_connected = await self.api.connect()
            return self.is_connected
        except Exception as e:
            logger.error(f"Failed to connect Chrome DevTools: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Chrome DevTools"""
        await self.api.disconnect()
        self.is_connected = False
    
    async def navigate_to_url(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Navigate to a URL"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            url = arguments.get("url")
            if not url:
                return {"success": False, "error": "URL is required"}
            
            result = await self.api.navigate(url)
            
            # Add small delay for page load
            await asyncio.sleep(1)
            
            return result
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_current_page(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get current page information"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            return await self.api.get_page_info()
            
        except Exception as e:
            logger.error(f"Failed to get current page: {e}")
            return {"success": False, "error": str(e)}
    
    async def take_screenshot(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Take a screenshot"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            full_page = arguments.get("full_page", False)
            return await self.api.take_screenshot(full_page=full_page)
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return {"success": False, "error": str(e)}
    
    async def click_element(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Click an element by CSS selector"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            selector = arguments.get("selector")
            if not selector:
                return {"success": False, "error": "Selector is required"}
            
            return await self.api.click_element(selector)
            
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return {"success": False, "error": str(e)}
    
    async def type_text(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Type text into an element"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            selector = arguments.get("selector")
            text = arguments.get("text", "")
            
            if not selector:
                return {"success": False, "error": "Selector is required"}
            
            return await self.api.type_text(selector, text)
            
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_element_text(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get text content of an element"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            selector = arguments.get("selector")
            if not selector:
                return {"success": False, "error": "Selector is required"}
            
            return await self.api.get_element_text(selector)
            
        except Exception as e:
            logger.error(f"Failed to get element text: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_page_html(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get current page HTML"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            return await self.api.get_page_content()
            
        except Exception as e:
            logger.error(f"Failed to get page HTML: {e}")
            return {"success": False, "error": str(e)}
    
    async def scroll_page(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Scroll the page"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            x = arguments.get("x", 0)
            y = arguments.get("y", 500)
            
            return await self.api.scroll_page(x, y)
            
        except Exception as e:
            logger.error(f"Failed to scroll page: {e}")
            return {"success": False, "error": str(e)}
    
    async def reload_page(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Reload the current page"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            return await self.api.reload_page()
            
        except Exception as e:
            logger.error(f"Failed to reload page: {e}")
            return {"success": False, "error": str(e)}
    
    async def navigate_back(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Go back in browser history"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            return await self.api.go_back()
            
        except Exception as e:
            logger.error(f"Failed to go back: {e}")
            return {"success": False, "error": str(e)}
    
    async def navigate_forward(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Go forward in browser history"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            return await self.api.go_forward()
            
        except Exception as e:
            logger.error(f"Failed to go forward: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_javascript(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute JavaScript code"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            script = arguments.get("script")
            if not script:
                return {"success": False, "error": "Script is required"}
            
            return await self.api.execute_script(script)
            
        except Exception as e:
            logger.error(f"Failed to execute JavaScript: {e}")
            return {"success": False, "error": str(e)}
    
    async def wait_for_element(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Wait for an element to appear"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            selector = arguments.get("selector")
            timeout = arguments.get("timeout", 10)
            
            if not selector:
                return {"success": False, "error": "Selector is required"}
            
            return await self.api.wait_for_element(selector, timeout)
            
        except Exception as e:
            logger.error(f"Failed to wait for element: {e}")
            return {"success": False, "error": str(e)}
    
    async def fill_form(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fill a form with multiple fields"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to Chrome DevTools"}
        
        try:
            fields = arguments.get("fields", {})
            if not fields:
                return {"success": False, "error": "Fields dictionary is required"}
            
            results = []
            for selector, value in fields.items():
                try:
                    result = await self.api.type_text(selector, str(value))
                    results.append({"selector": selector, "value": value, "success": result["success"]})
                    if not result["success"]:
                        logger.warning(f"Failed to fill field {selector}: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    results.append({"selector": selector, "value": value, "success": False, "error": str(e)})
            
            successful = sum(1 for r in results if r["success"])
            
            return {
                "success": successful > 0,
                "results": results,
                "successful": successful,
                "total": len(fields)
            }
            
        except Exception as e:
            logger.error(f"Failed to fill form: {e}")
            return {"success": False, "error": str(e)}


def create_chrome_devtools_tools() -> List[MCPTool]:
    """Create list of Chrome DevTools MCP tools"""
    tools = [
        MCPTool(
            name="connect",
            description="Connect to Chrome DevTools for browser automation",
            input_schema={
                "type": "object",
                "properties": {}
            }
        ),
        MCPTool(
            name="disconnect",
            description="Disconnect from Chrome DevTools",
            input_schema={
                "type": "object",
                "properties": {}
            }
        ),
        MCPTool(
            name="navigate",
            description="Navigate to a URL",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"}
                },
                "required": ["url"]
            }
        ),
        MCPTool(
            name="get_current_page",
            description="Get current page information (URL, title, dimensions)",
            input_schema={
                "type": "object",
                "properties": {}
            }
        ),
        MCPTool(
            name="take_screenshot",
            description="Take a screenshot of the current page",
            input_schema={
                "type": "object",
                "properties": {
                    "full_page": {"type": "boolean", "description": "Take full page screenshot"}
                }
            }
        ),
        MCPTool(
            name="click_element",
            description="Click an element by CSS selector",
            input_schema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the element"}
                },
                "required": ["selector"]
            }
        ),
        MCPTool(
            name="type_text",
            description="Type text into an element",
            input_schema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the element"},
                    "text": {"type": "string", "description": "Text to type"}
                },
                "required": ["selector", "text"]
            }
        ),
        MCPTool(
            name="get_element_text",
            description="Get text content of an element",
            input_schema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the element"}
                },
                "required": ["selector"]
            }
        ),
        MCPTool(
            name="get_page_html",
            description="Get current page HTML content",
            input_schema={
                "type": "object",
                "properties": {}
            }
        ),
        MCPTool(
            name="scroll_page",
            description="Scroll the page",
            input_schema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Horizontal scroll amount"},
                    "y": {"type": "integer", "description": "Vertical scroll amount"}
                }
            }
        ),
        MCPTool(
            name="reload_page",
            description="Reload the current page",
            input_schema={
                "type": "object",
                "properties": {}
            }
        ),
        MCPTool(
            name="navigate_back",
            description="Go back in browser history",
            input_schema={
                "type": "object",
                "properties": {}
            }
        ),
        MCPTool(
            name="navigate_forward",
            description="Go forward in browser history",
            input_schema={
                "type": "object",
                "properties": {}
            }
        ),
        MCPTool(
            name="execute_javascript",
            description="Execute JavaScript code",
            input_schema={
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "JavaScript code to execute"}
                },
                "required": ["script"]
            }
        ),
        MCPTool(
            name="wait_for_element",
            description="Wait for an element to appear",
            input_schema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the element"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 10}
                },
                "required": ["selector"]
            }
        ),
        MCPTool(
            name="fill_form",
            description="Fill multiple form fields at once",
            input_schema={
                "type": "object",
                "properties": {
                    "fields": {
                        "type": "object",
                        "description": "Dictionary of selector -> value pairs",
                        "additionalProperties": {"type": "string"}
                    }
                },
                "required": ["fields"]
            }
        )
    ]
    
    return tools


# Global Chrome DevTools tools instance
_chrome_tools: Optional[ChromeDevToolsTools] = None


def get_chrome_tools() -> ChromeDevToolsTools:
    """Get global Chrome DevTools tools instance"""
    global _chrome_tools
    if _chrome_tools is None:
        _chrome_tools = ChromeDevToolsTools()
    return _chrome_tools