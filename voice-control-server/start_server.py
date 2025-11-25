#!/usr/bin/env python3
"""
Voice Control Server Startup Script

Comprehensive startup script for the Voice Control Server with dependency checking,
configuration validation, and service initialization.
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    import uvicorn
    from fastapi import FastAPI
    from src.config.settings import get_settings
    from src.utils.logger import setup_logger, get_logger
    from src.services.stt_service import STTService
    from src.services.llm_service import LLMService
    from src.services.mcp_service import MCPService
    from src.main import app
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)

logger = get_logger(__name__)


class DependencyChecker:
    """Check system dependencies and configurations"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
    
    def check_python_version(self):
        """Check Python version compatibility"""
        if sys.version_info < (3, 8):
            self.issues.append("Python 3.8+ is required")
            return False
        return True
    
    def check_required_packages(self):
        """Check if required packages are installed"""
        required_packages = [
            "fastapi", "uvicorn", "websockets", "faster_whisper",
            "ollama", "aiohttp", "pydantic", "numpy", "psutil"
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self.issues.append(f"Missing packages: {', '.join(missing_packages)}")
            return False
        return True
    
    def check_ollama_service(self):
        """Check if Ollama service is running"""
        try:
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request("http://localhost:11434/api/tags", method='GET')
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    result = response.status == 200
            except (urllib.error.URLError, urllib.error.HTTPError):
                result = False
            
            if not result:
                self.warnings.append("Ollama service not accessible at localhost:11434")
                self.warnings.append("LLM features will be limited until Ollama is running")
            return result
        except Exception:
            self.warnings.append("Could not verify Ollama service status")
            return False
    
    def check_system_resources(self):
        """Check system resources"""
        try:
            import psutil
            
            # Check memory
            memory = psutil.virtual_memory()
            if memory.available < 2 * 1024 * 1024 * 1024:  # 2GB
                self.warnings.append("Low system memory detected. Consider closing other applications.")
            
            # Check disk space
            disk = psutil.disk_usage('/')
            if disk.free < 1 * 1024 * 1024 * 1024:  # 1GB
                self.warnings.append("Low disk space detected. Model downloads may fail.")
            
        except ImportError:
            self.warnings.append("psutil not available - resource checking disabled")
        except Exception as e:
            logger.warning(f"Resource check failed: {e}")
    
    def check_configuration(self):
        """Check configuration settings"""
        try:
            settings = get_settings()
            
            # Check port availability
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            port_available = sock.connect_ex(('localhost', settings.port)) != 0
            sock.close()
            
            if not port_available:
                self.issues.append(f"Port {settings.port} is already in use")
                return False
            
        except Exception as e:
            self.warnings.append(f"Configuration check failed: {e}")
        
        return True
    
    def run_all_checks(self):
        """Run all dependency checks"""
        print("🔍 Checking system dependencies...")
        
        checks = [
            ("Python version", self.check_python_version),
            ("Required packages", self.check_required_packages),
            ("Ollama service", self.check_ollama_service),
            ("System resources", self.check_system_resources),
            ("Configuration", self.check_configuration),
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            print(f"  Checking {check_name}...", end=" ")
            try:
                result = check_func()
                if result:
                    print("✓")
                else:
                    print("✗")
                    all_passed = False
            except Exception as e:
                print(f"⚠ ({e})")
                all_passed = False
        
        return all_passed
    
    def print_summary(self):
        """Print check summary"""
        if self.issues:
            print("\n❌ Issues found:")
            for issue in self.issues:
                print(f"  • {issue}")
        
        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if not self.issues and not self.warnings:
            print("\n✅ All checks passed!")
        elif not self.issues:
            print("\n✅ Core requirements met (warnings can be ignored for development)")


async def initialize_services():
    """Initialize server services"""
    print("\n🚀 Initializing server services...")
    
    try:
        # Initialize services
        print("  Starting STT service...", end=" ", flush=True)
        stt_service = STTService()
        try:
            stt_initialized = await asyncio.wait_for(stt_service.initialize(), timeout=60)
        except asyncio.TimeoutError:
            stt_initialized = False
            print("⚠ (timeout)")
        except Exception as e:
            stt_initialized = False
            print(f"⚠ ({e})")
        else:
            if stt_initialized:
                print("✓")
            else:
                print("⚠ (will retry on demand)")
        
        print("  Starting LLM service...", end=" ", flush=True)
        llm_service = LLMService()
        try:
            llm_initialized = await asyncio.wait_for(llm_service.initialize(), timeout=30)
        except asyncio.TimeoutError:
            llm_initialized = False
            print("⚠ (timeout - will retry on demand)")
        except Exception as e:
            llm_initialized = False
            print(f"⚠ ({e})")
        else:
            if llm_initialized:
                print("✓")
            else:
                print("⚠ (will retry on demand)")
        
        print("  Starting MCP service...", end=" ", flush=True)
        mcp_service = MCPService()
        try:
            mcp_initialized = await asyncio.wait_for(mcp_service.initialize(), timeout=30)
        except asyncio.TimeoutError:
            mcp_initialized = False
            print("⚠ (timeout)")
        except Exception as e:
            mcp_initialized = False
            print(f"⚠ ({e})")
        else:
            if mcp_initialized:
                print("✓")
            else:
                print("⚠ (will retry on demand)")
        
        return {
            "stt": stt_initialized,
            "llm": llm_initialized,
            "mcp": mcp_initialized
        }
        
    except Exception as e:
        print(f"\n❌ Service initialization failed: {e}")
        return None


def print_server_info():
    """Print server information"""
    print("\n📋 Voice Control Server Information")
    print("=" * 50)
    print("Server URL: http://localhost:8000")
    print("WebSocket URL: ws://localhost:8000/ws")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print()
    print("Features:")
    print("  • Real-time speech-to-text with faster-whisper")
    print("  • Language model integration with Ollama")
    print("  • MCP protocol support for system automation")
    print("  • Windows system control tools")
    print("  • Chrome browser automation")
    print()
    print("Controls:")
    print("  • Press Ctrl+C to stop the server")
    print("  • Monitor logs in the console output")
    print()


def create_run_script():
    """Create a simple run script"""
    script_content = '''#!/usr/bin/env python3
"""Simple run script for Voice Control Server"""

import sys
import uvicorn
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
'''
    
    script_path = Path(__file__).parent / "run_server.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make executable on Unix systems
    if os.name != 'nt':
        os.chmod(script_path, 0o755)
    
    print(f"📝 Created run script: {script_path}")


def main():
    """Main startup function"""
    print("🎤 Voice Control Server Startup")
    print("=" * 40)
    
    # Check dependencies
    checker = DependencyChecker()
    if not checker.run_all_checks():
        checker.print_summary()
        if checker.issues:
            print("\n❌ Please fix the issues above before starting the server.")
            sys.exit(1)
    
    checker.print_summary()
    
    # Create run script
    create_run_script()
    
    # Initialize services (run synchronously before starting server)
    services = asyncio.run(initialize_services())
    
    if services is None:
        print("\n❌ Failed to initialize services")
        sys.exit(1)
    
    # Print server information
    print_server_info()
    
    # Get settings
    settings = get_settings()
    
    # Start server
    print("🔥 Starting server...")
    print()
    
    try:
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info" if not settings.debug else "debug",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server failed to start: {e}")
        sys.exit(1)
    finally:
        # Cleanup (run synchronously)
        print("🧹 Cleaning up...")
        async def cleanup_services():
            for service_name, service in [("STT", STTService()), ("LLM", LLMService()), ("MCP", MCPService())]:
                try:
                    await service.cleanup()
                    print(f"  {service_name} service cleaned up")
                except Exception as e:
                    logger.warning(f"Cleanup failed for {service_name}: {e}")
        
        asyncio.run(cleanup_services())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)