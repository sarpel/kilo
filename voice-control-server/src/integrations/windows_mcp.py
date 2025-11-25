"""
Windows MCP Integration

Provides Windows-specific MCP tools for system-level operations including
file management, window management, process control, and system information.
"""

import asyncio
import os
import sys
import json
import time
import psutil
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path
import winreg
import ctypes
from ctypes import wintypes

from src.utils.logger import get_logger, log_performance
from src.services.mcp_service import MCPTool

logger = get_logger(__name__)


class WindowsAPI:
    """Windows API integration using ctypes"""
    
    def __init__(self):
        # Load Windows DLLs
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.shell32 = ctypes.windll.shell32
        self.ole32 = ctypes.windll.ole32
        
        # Define common Windows constants
        self.SW_RESTORE = 9
        self.SW_MINIMIZE = 6
        self.SW_MAXIMIZE = 3
        self.SW_SHOW = 5
    
    def get_window_by_title(self, title: str) -> Optional[int]:
        """Get window handle by title"""
        try:
            hwnd = self.user32.FindWindowW(None, title)
            return hwnd if hwnd != 0 else None
        except Exception as e:
            logger.error(f"Failed to get window by title: {e}")
            return None
    
    def set_window_position(self, hwnd: int, x: int, y: int, width: int, height: int) -> bool:
        """Set window position and size"""
        try:
            return bool(self.user32.SetWindowPos(
                hwnd, 0, x, y, width, height, 0x0040  # SWP_SHOWWINDOW
            ))
        except Exception as e:
            logger.error(f"Failed to set window position: {e}")
            return False
    
    def get_window_rect(self, hwnd: int) -> Optional[Dict[str, int]]:
        """Get window rectangle"""
        try:
            rect = wintypes.RECT()
            if self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return {
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get window rect: {e}")
            return None
    
    def show_window(self, hwnd: int, cmd_show: int) -> bool:
        """Show window with specified command"""
        try:
            return bool(self.user32.ShowWindow(hwnd, cmd_show))
        except Exception as e:
            logger.error(f"Failed to show window: {e}")
            return False
    
    def get_window_text(self, hwnd: int) -> str:
        """Get window title text"""
        try:
            buffer_size = 256
            buffer = ctypes.create_unicode_buffer(buffer_size)
            length = self.user32.GetWindowTextW(hwnd, buffer, buffer_size)
            return buffer.value[:length] if length > 0 else ""
        except Exception as e:
            logger.error(f"Failed to get window text: {e}")
            return ""
    
    def set_window_text(self, hwnd: int, text: str) -> bool:
        """Set window title text"""
        try:
            return bool(self.user32.SetWindowTextW(hwnd, text))
        except Exception as e:
            logger.error(f"Failed to set window text: {e}")
            return False
    
    def get_process_name_by_window(self, hwnd: int) -> str:
        """Get process name by window handle"""
        try:
            _, pid = self.user32.GetWindowThreadProcessId(hwnd, None)
            if pid:
                process = psutil.Process(pid)
                return process.name()
            return ""
        except Exception as e:
            logger.error(f"Failed to get process name: {e}")
            return ""


class WindowsRegistry:
    """Windows Registry operations"""
    
    @staticmethod
    def get_reg_value(key_path: str, value_name: str, value_type: str = "REG_SZ") -> Any:
        """Get registry value"""
        try:
            # Parse registry path
            parts = key_path.split('\\')
            if len(parts) < 2:
                raise ValueError("Invalid registry path")
            
            root_key_name = parts[0].upper()
            sub_key_path = '\\'.join(parts[1:])
            
            # Map root keys
            root_keys = {
                'HKEY_CLASSES_ROOT': winreg.HKEY_CLASSES_ROOT,
                'HKEY_CURRENT_USER': winreg.HKEY_CURRENT_USER,
                'HKEY_LOCAL_MACHINE': winreg.HKEY_LOCAL_MACHINE,
                'HKEY_USERS': winreg.HKEY_USERS,
                'HKEY_CURRENT_CONFIG': winreg.HKEY_CURRENT_CONFIG
            }
            
            root_key = root_keys.get(root_key_name)
            if not root_key:
                raise ValueError(f"Unknown root key: {root_key_name}")
            
            with winreg.OpenKey(root_key, sub_key_path) as key:
                value, reg_type = winreg.QueryValueEx(key, value_name)
                return value
                
        except Exception as e:
            logger.error(f"Failed to get registry value: {e}")
            return None
    
    @staticmethod
    def set_reg_value(key_path: str, value_name: str, value: Any, value_type: str = "REG_SZ") -> bool:
        """Set registry value"""
        try:
            # Implementation would require admin privileges
            # and proper value type handling
            logger.warning("Registry write operations require admin privileges")
            return False
        except Exception as e:
            logger.error(f"Failed to set registry value: {e}")
            return False


class WindowsTools:
    """Windows-specific MCP tools"""
    
    def __init__(self):
        self.api = WindowsAPI()
        self.registry = WindowsRegistry()
    
    async def list_processes(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """List running processes"""
        try:
            limit = arguments.get("limit", 100)
            include_children = arguments.get("include_children", False)
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'create_time']):
                try:
                    proc_info = proc.info
                    processes.append({
                        "pid": proc_info['pid'],
                        "name": proc_info['name'],
                        "cpu_percent": proc_info.get('cpu_percent', 0),
                        "memory_mb": round(proc_info['memory_info'].rss / 1024 / 1024, 2) if proc_info.get('memory_info') else 0,
                        "create_time": proc_info.get('create_time', 0),
                        "status": proc.status() if include_children else "running"
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            return {
                "success": True,
                "processes": processes[:limit],
                "total_processes": len(processes),
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to list processes: {e}")
            return {"success": False, "error": str(e)}
    
    async def kill_process(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Kill a process by PID or name"""
        try:
            pid = arguments.get("pid")
            name = arguments.get("name")
            force = arguments.get("force", False)
            
            if not pid and not name:
                return {"success": False, "error": "Either pid or name must be provided"}
            
            killed_processes = []
            
            if pid:
                try:
                    process = psutil.Process(pid)
                    process.terminate()
                    killed_processes.append({"pid": pid, "name": process.name()})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return {"success": False, "error": f"Cannot kill process {pid}"}
            
            if name:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'].lower() == name.lower():
                            proc.terminate()
                            killed_processes.append({"pid": proc.info['pid'], "name": name})
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            return {
                "success": True,
                "killed_processes": killed_processes,
                "count": len(killed_processes)
            }
            
        except Exception as e:
            logger.error(f"Failed to kill process: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_process(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start a new process"""
        try:
            command = arguments.get("command")
            args = arguments.get("args", [])
            cwd = arguments.get("cwd")
            shell = arguments.get("shell", False)
            
            if not command:
                return {"success": False, "error": "Command is required"}
            
            # Build command
            if isinstance(args, str):
                args = args.split()
            
            full_command = [command] + args
            
            # Start process
            process = subprocess.Popen(
                full_command,
                cwd=cwd,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            return {
                "success": True,
                "pid": process.pid,
                "command": command,
                "args": args,
                "returncode": process.returncode
            }
            
        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_system_info(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            import platform
            
            # CPU info
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory info
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk info
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network info
            network_io = psutil.net_io_counters()
            
            # System info
            boot_time = psutil.boot_time()
            
            return {
                "success": True,
                "system": {
                    "platform": platform.platform(),
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "boot_time": boot_time,
                    "boot_time_formatted": time.ctime(boot_time)
                },
                "cpu": {
                    "count": cpu_count,
                    "usage_percent": cpu_usage,
                    "frequency": {
                        "current": cpu_freq.current if cpu_freq else 0,
                        "min": cpu_freq.min if cpu_freq else 0,
                        "max": cpu_freq.max if cpu_freq else 0
                    } if cpu_freq else {}
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "usage_percent": memory.percent,
                    "swap": {
                        "total_gb": round(swap.total / (1024**3), 2),
                        "used_gb": round(swap.used / (1024**3), 2),
                        "usage_percent": swap.percent
                    }
                },
                "disk": {
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                    "used_gb": round(disk_usage.used / (1024**3), 2),
                    "free_gb": round(disk_usage.free / (1024**3), 2),
                    "usage_percent": round((disk_usage.used / disk_usage.total) * 100, 2),
                    "io": {
                        "read_count": disk_io.read_count if disk_io else 0,
                        "write_count": disk_io.write_count if disk_io else 0,
                        "read_bytes": disk_io.read_bytes if disk_io else 0,
                        "write_bytes": disk_io.write_bytes if disk_io else 0
                    } if disk_io else {}
                },
                "network": {
                    "bytes_sent": network_io.bytes_sent if network_io else 0,
                    "bytes_recv": network_io.bytes_recv if network_io else 0,
                    "packets_sent": network_io.packets_sent if network_io else 0,
                    "packets_recv": network_io.packets_recv if network_io else 0
                } if network_io else {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_files(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """List files in a directory"""
        try:
            directory = arguments.get("directory", ".")
            pattern = arguments.get("pattern", "*")
            recursive = arguments.get("recursive", False)
            include_hidden = arguments.get("include_hidden", False)
            
            path = Path(directory)
            if not path.exists():
                return {"success": False, "error": f"Directory does not exist: {directory}"}
            
            files = []
            try:
                if recursive:
                    file_paths = path.rglob(pattern)
                else:
                    file_paths = path.glob(pattern)
                
                for file_path in file_paths:
                    if not include_hidden and file_path.name.startswith('.'):
                        continue
                    
                    stat = file_path.stat()
                    files.append({
                        "name": file_path.name,
                        "path": str(file_path),
                        "is_directory": file_path.is_dir(),
                        "size_bytes": stat.st_size if file_path.is_file() else 0,
                        "size_mb": round(stat.st_size / (1024*1024), 2) if file_path.is_file() else 0,
                        "modified_time": stat.st_mtime,
                        "modified_time_formatted": time.ctime(stat.st_mtime)
                    })
            except PermissionError:
                return {"success": False, "error": f"Permission denied: {directory}"}
            
            # Sort by name
            files.sort(key=lambda x: x['name'].lower())
            
            return {
                "success": True,
                "directory": str(path.absolute()),
                "files": files,
                "count": len(files),
                "pattern": pattern,
                "recursive": recursive
            }
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return {"success": False, "error": str(e)}
    
    async def read_file(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Read file contents"""
        try:
            file_path = arguments.get("file_path")
            encoding = arguments.get("encoding", "utf-8")
            
            if not file_path:
                return {"success": False, "error": "file_path is required"}
            
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File does not exist: {file_path}"}
            
            if not path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}
            
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return {
                "success": True,
                "file_path": str(path.absolute()),
                "content": content,
                "size_bytes": len(content.encode(encoding)),
                "lines": len(content.splitlines())
            }
            
        except UnicodeDecodeError as e:
            return {"success": False, "error": f"Encoding error: {e}"}
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return {"success": False, "error": str(e)}
    
    async def write_file(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Write file contents"""
        try:
            file_path = arguments.get("file_path")
            content = arguments.get("content", "")
            encoding = arguments.get("encoding", "utf-8")
            append = arguments.get("append", False)
            
            if not file_path:
                return {"success": False, "error": "file_path is required"}
            
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = 'a' if append else 'w'
            with open(path, mode, encoding=encoding) as f:
                written = f.write(content)
            
            return {
                "success": True,
                "file_path": str(path.absolute()),
                "bytes_written": written,
                "lines_written": len(content.splitlines())
            }
            
        except Exception as e:
            logger.error(f"Failed to write file: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_windows(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """List open windows"""
        try:
            include_hidden = arguments.get("include_hidden", False)
            
            windows = []
            
            def enum_windows_callback(hwnd, windows_list):
                if not include_hidden:
                    if not self.api.user32.IsWindowVisible(hwnd):
                        return True
                
                window_text = self.api.get_window_text(hwnd)
                if window_text:
                    process_name = self.api.get_process_name_by_window(hwnd)
                    rect = self.api.get_window_rect(hwnd)
                    
                    windows_list.append({
                        "hwnd": hwnd,
                        "title": window_text,
                        "process": process_name,
                        "rect": rect,
                        "width": rect['right'] - rect['left'] if rect else 0,
                        "height": rect['bottom'] - rect['top'] if rect else 0
                    })
                
                return True
            
            # Callback function for EnumWindows
            enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))
            enum_windows_callback_ctypes = enum_windows_proc(enum_windows_callback)
            
            # Call EnumWindows
            windows_list = []
            self.api.user32.EnumWindows(enum_windows_callback_ctypes, ctypes.cast(ctypes.pointer(windows_list), ctypes.c_void_p))
            
            return {
                "success": True,
                "windows": windows_list,
                "count": len(windows_list)
            }
            
        except Exception as e:
            logger.error(f"Failed to list windows: {e}")
            return {"success": False, "error": str(e)}
    
    async def focus_window(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Focus a window by title or handle"""
        try:
            title = arguments.get("title")
            hwnd = arguments.get("hwnd")
            
            if not title and not hwnd:
                return {"success": False, "error": "Either title or hwnd is required"}
            
            window_handle = None
            
            if hwnd:
                window_handle = int(hwnd)
            else:
                window_handle = self.api.get_window_by_title(title)
            
            if not window_handle:
                return {"success": False, "error": f"Window not found: {title or hwnd}"}
            
            # Bring window to foreground
            self.api.user32.SetForegroundWindow(window_handle)
            
            return {
                "success": True,
                "hwnd": window_handle,
                "title": self.api.get_window_text(window_handle)
            }
            
        except Exception as e:
            logger.error(f"Failed to focus window: {e}")
            return {"success": False, "error": str(e)}
    
    async def resize_window(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Resize and move a window"""
        try:
            title = arguments.get("title")
            hwnd = arguments.get("hwnd")
            x = arguments.get("x", 100)
            y = arguments.get("y", 100)
            width = arguments.get("width", 800)
            height = arguments.get("height", 600)
            
            if not title and not hwnd:
                return {"success": False, "error": "Either title or hwnd is required"}
            
            window_handle = None
            
            if hwnd:
                window_handle = int(hwnd)
            else:
                window_handle = self.api.get_window_by_title(title)
            
            if not window_handle:
                return {"success": False, "error": f"Window not found: {title or hwnd}"}
            
            # Set window position
            success = self.api.set_window_position(window_handle, x, y, width, height)
            
            if success:
                return {
                    "success": True,
                    "hwnd": window_handle,
                    "position": {"x": x, "y": y},
                    "size": {"width": width, "height": height}
                }
            else:
                return {"success": False, "error": "Failed to resize window"}
            
        except Exception as e:
            logger.error(f"Failed to resize window: {e}")
            return {"success": False, "error": str(e)}
    
    async def minimize_window(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Minimize a window"""
        try:
            title = arguments.get("title")
            hwnd = arguments.get("hwnd")
            
            if not title and not hwnd:
                return {"success": False, "error": "Either title or hwnd is required"}
            
            window_handle = None
            
            if hwnd:
                window_handle = int(hwnd)
            else:
                window_handle = self.api.get_window_by_title(title)
            
            if not window_handle:
                return {"success": False, "error": f"Window not found: {title or hwnd}"}
            
            success = self.api.show_window(window_handle, self.api.SW_MINIMIZE)
            
            return {"success": success, "hwnd": window_handle}
            
        except Exception as e:
            logger.error(f"Failed to minimize window: {e}")
            return {"success": False, "error": str(e)}
    
    async def maximize_window(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Maximize a window"""
        try:
            title = arguments.get("title")
            hwnd = arguments.get("hwnd")
            
            if not title and not hwnd:
                return {"success": False, "error": "Either title or hwnd is required"}
            
            window_handle = None
            
            if hwnd:
                window_handle = int(hwnd)
            else:
                window_handle = self.api.get_window_by_title(title)
            
            if not window_handle:
                return {"success": False, "error": f"Window not found: {title or hwnd}"}
            
            success = self.api.show_window(window_handle, self.api.SW_MAXIMIZE)
            
            return {"success": success, "hwnd": window_handle}
            
        except Exception as e:
            logger.error(f"Failed to maximize window: {e}")
            return {"success": False, "error": str(e)}
    
    async def restore_window(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Restore a window from minimized state"""
        try:
            title = arguments.get("title")
            hwnd = arguments.get("hwnd")
            
            if not title and not hwnd:
                return {"success": False, "error": "Either title or hwnd is required"}
            
            window_handle = None
            
            if hwnd:
                window_handle = int(hwnd)
            else:
                window_handle = self.api.get_window_by_title(title)
            
            if not window_handle:
                return {"success": False, "error": f"Window not found: {title or hwnd}"}
            
            success = self.api.show_window(window_handle, self.api.SW_RESTORE)
            
            return {"success": success, "hwnd": window_handle}
            
        except Exception as e:
            logger.error(f"Failed to restore window: {e}")
            return {"success": False, "error": str(e)}
    
    async def run_command(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run a shell command"""
        try:
            command = arguments.get("command")
            args = arguments.get("args", [])
            cwd = arguments.get("cwd")
            timeout = arguments.get("timeout", 30)
            
            if not command:
                return {"success": False, "error": "Command is required"}
            
            # Build command
            if isinstance(args, str):
                args = args.split()
            
            full_command = [command] + args
            
            # Run command
            process = await asyncio.create_subprocess_exec(
                *full_command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                return {
                    "success": True,
                    "returncode": process.returncode,
                    "stdout": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace'),
                    "command": command,
                    "args": args
                }
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {"success": False, "error": "Command timed out"}
            
        except Exception as e:
            logger.error(f"Failed to run command: {e}")
            return {"success": False, "error": str(e)}


def create_windows_tools() -> List[MCPTool]:
    """Create list of Windows MCP tools"""
    tools = [
        MCPTool(
            name="list_processes",
            description="List running processes with CPU and memory usage",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of processes to return"},
                    "include_children": {"type": "boolean", "description": "Include child process information"}
                }
            }
        ),
        MCPTool(
            name="kill_process",
            description="Kill a process by PID or name",
            input_schema={
                "type": "object",
                "properties": {
                    "pid": {"type": "integer", "description": "Process ID to kill"},
                    "name": {"type": "string", "description": "Process name to kill"},
                    "force": {"type": "boolean", "description": "Force kill if normal termination fails"}
                },
                "required": ["pid", "name"]
            }
        ),
        MCPTool(
            name="start_process",
            description="Start a new process",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "args": {"type": "array", "items": {"type": "string"}, "description": "Command arguments"},
                    "cwd": {"type": "string", "description": "Working directory"},
                    "shell": {"type": "boolean", "description": "Use shell to execute command"}
                },
                "required": ["command"]
            }
        ),
        MCPTool(
            name="get_system_info",
            description="Get comprehensive system information including CPU, memory, disk, and network usage",
            input_schema={
                "type": "object",
                "properties": {}
            }
        ),
        MCPTool(
            name="list_files",
            description="List files in a directory with filtering options",
            input_schema={
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory to list (default: current directory)"},
                    "pattern": {"type": "string", "description": "File pattern to match (default: *)"},
                    "recursive": {"type": "boolean", "description": "Search recursively"},
                    "include_hidden": {"type": "boolean", "description": "Include hidden files"}
                }
            }
        ),
        MCPTool(
            name="read_file",
            description="Read file contents",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file to read"},
                    "encoding": {"type": "string", "description": "File encoding (default: utf-8)"}
                },
                "required": ["file_path"]
            }
        ),
        MCPTool(
            name="write_file",
            description="Write file contents",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file to write"},
                    "content": {"type": "string", "description": "Content to write"},
                    "encoding": {"type": "string", "description": "File encoding (default: utf-8)"},
                    "append": {"type": "boolean", "description": "Append to file instead of overwriting"}
                },
                "required": ["file_path", "content"]
            }
        ),
        MCPTool(
            name="list_windows",
            description="List all open windows",
            input_schema={
                "type": "object",
                "properties": {
                    "include_hidden": {"type": "boolean", "description": "Include hidden windows"}
                }
            }
        ),
        MCPTool(
            name="focus_window",
            description="Bring a window to the foreground",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Window title to focus"},
                    "hwnd": {"type": "integer", "description": "Window handle to focus"}
                },
                "required": ["title", "hwnd"]
            }
        ),
        MCPTool(
            name="resize_window",
            description="Resize and move a window",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Window title to resize"},
                    "hwnd": {"type": "integer", "description": "Window handle to resize"},
                    "x": {"type": "integer", "description": "X position"},
                    "y": {"type": "integer", "description": "Y position"},
                    "width": {"type": "integer", "description": "Window width"},
                    "height": {"type": "integer", "description": "Window height"}
                },
                "required": ["title", "hwnd"]
            }
        ),
        MCPTool(
            name="minimize_window",
            description="Minimize a window",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Window title to minimize"},
                    "hwnd": {"type": "integer", "description": "Window handle to minimize"}
                },
                "required": ["title", "hwnd"]
            }
        ),
        MCPTool(
            name="maximize_window",
            description="Maximize a window",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Window title to maximize"},
                    "hwnd": {"type": "integer", "description": "Window handle to maximize"}
                },
                "required": ["title", "hwnd"]
            }
        ),
        MCPTool(
            name="restore_window",
            description="Restore a minimized window",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Window title to restore"},
                    "hwnd": {"type": "integer", "description": "Window handle to restore"}
                },
                "required": ["title", "hwnd"]
            }
        ),
        MCPTool(
            name="run_command",
            description="Run a shell command and return output",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "args": {"type": "array", "items": {"type": "string"}, "description": "Command arguments"},
                    "cwd": {"type": "string", "description": "Working directory"},
                    "timeout": {"type": "integer", "description": "Command timeout in seconds"}
                },
                "required": ["command"]
            }
        )
    ]
    
    return tools


# Global Windows tools instance
_windows_tools: Optional[WindowsTools] = None


def get_windows_tools() -> WindowsTools:
    """Get global Windows tools instance"""
    global _windows_tools
    if _windows_tools is None:
        _windows_tools = WindowsTools()
    return _windows_tools