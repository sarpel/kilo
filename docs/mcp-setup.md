# MCP Server Setup Guide

This guide provides comprehensive instructions for setting up and configuring Model Context Protocol (MCP) servers for the Voice Control Ecosystem.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Windows MCP Server Setup](#windows-mcp-server-setup)
4. [Chrome DevTools MCP Server Setup](#chrome-devtools-mcp-server-setup)
5. [Ollama Installation and Configuration](#ollama-installation-and-configuration)
6. [Testing MCP Server Connectivity](#testing-mcp-server-connectivity)
7. [Troubleshooting](#troubleshooting)
8. [Security Considerations](#security-considerations)
9. [Advanced Configuration](#advanced-configuration)

## Overview

The Voice Control Ecosystem uses multiple MCP servers to enable:

- **Windows MCP Server**: System-level control for Windows operations
- **Chrome DevTools MCP Server**: Browser automation and control
- **Ollama MCP Server**: Local language model integration

These servers work together to provide comprehensive voice control capabilities.

## Prerequisites

### System Requirements

- **Windows 10/11** (for Windows MCP server)
- **Google Chrome** (for Chrome DevTools MCP server)
- **Python 3.10+** (for custom MCP servers)
- **4GB+ RAM** (8GB recommended for LLM models)
- **Network access** for server communication

### Required Software

- **Ollama**: For LLM model serving
- **Git**: For cloning repositories
- **Python pip**: For Python package management
- **Node.js**: For development tools (optional)

## Windows MCP Server Setup

The Windows MCP server provides system-level control capabilities including:

- File and folder operations
- Process management
- Window management
- System information retrieval
- Shell command execution

### Installation Steps

#### 1. Install Prerequisites

```powershell
# Run PowerShell as Administrator

# Install Python 3.10+ from Microsoft Store or python.org
# Verify installation
python --version

# Install Git if not already installed
winget install --id Git.Git -e --source winget

# Verify Git installation
git --version
```

#### 2. Download and Setup Windows MCP Server

```powershell
# Navigate to project directory
cd "C:\path\to\voice-control-ecosystem"

# The Windows MCP server is already integrated in the Python FastAPI server
# No additional setup required for the basic functionality

# For custom Windows MCP server (optional)
git clone https://github.com/modelcontextprotocol/servers.git
cd servers\src\windows-system
pip install -r requirements.txt
```

#### 3. Configuration

The Windows MCP server is automatically configured through the main server's `.env` file:

```bash
# In voice-control-server/.env
# Windows MCP is enabled by default
FEATURE_SYSTEM_CONTROL=true
MCP_TIMEOUT=30
MCP_MAX_CONCURRENT_REQUESTS=5
```

#### 4. Permissions Setup

The server runs with the permissions of the logged-in user. For advanced system operations:

```powershell
# Run as Administrator for full system access
# The server will request elevated permissions as needed
```

### Available Windows MCP Tools

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `list_processes` | List running processes | "Show me running processes" |
| `kill_process` | Terminate a process | "Close Chrome browser" |
| `start_process` | Launch application | "Open Notepad" |
| `list_files` | Browse file system | "Show me my Documents folder" |
| `read_file` / `write_file` | File operations | "Read my todo.txt file" |
| `list_windows` | List open windows | "Show me open applications" |
| `focus_window` | Switch to window | "Switch to Notepad" |
| `resize_window` | Window management | "Maximize the browser window" |
| `run_command` | Execute shell commands | "Run ipconfig command" |
| `get_system_info` | System information | "Show me system information" |

## Chrome DevTools MCP Server Setup

The Chrome DevTools MCP server enables browser automation and control.

### Installation Steps

#### 1. Install Google Chrome

```powershell
# Download and install Google Chrome from https://www.google.com/chrome/
# Or install via command line:
winget install Google.Chrome
```

#### 2. Enable Chrome DevTools Protocol

**Option A: Start Chrome with Remote Debugging**

```powershell
# Create a shortcut for Chrome with remote debugging
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$arguments = "--remote-debugging-port=9222 --user-data-dir=C:\chrome-dev-session"
Start-Process -FilePath $chromePath -ArgumentList $arguments
```

**Option B: Use Chrome Settings**

1. Open Chrome
2. Go to `chrome://settings/`
3. Search for "remote debugging"
4. Enable "Remote debugging"

#### 3. Verify Chrome DevTools Connection

```powershell
# Test the connection
curl http://localhost:9222/json

# Should return JSON with active tabs
```

### Configuration

The Chrome DevTools MCP server is configured through the main server:

```bash
# In voice-control-server/.env
FEATURE_BROWSER_AUTOMATION=true
CHROME_DEBUG_PORT=9222
CHROME_TIMEOUT=30
```

### Available Chrome MCP Tools

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `chrome_connect` | Connect to Chrome DevTools | Automatic connection |
| `chrome_navigate` | Navigate to URLs | "Go to google.com" |
| `chrome_screenshot` | Capture page screenshots | "Take a screenshot" |
| `chrome_click` | Click elements | "Click the search button" |
| `chrome_type` | Type text | "Type 'Hello World' in the search box" |
| `chrome_get_text` | Extract page text | "What does this page say?" |
| `chrome_get_html` | Get page source | "Get the page HTML" |
| `chrome_scroll` | Scroll page | "Scroll down the page" |
| `chrome_reload` | Reload page | "Refresh the page" |
| `chrome_execute_script` | Run JavaScript | "Execute alert('Hello')" |

### Security Considerations for Chrome

1. **Local Network Only**: Chrome DevTools only accepts connections from localhost
2. **Port Security**: Use firewall rules to restrict port 9222 access
3. **User Data Security**: Use dedicated user data directories

```powershell
# Restrict Chrome DevTools to localhost
netsh advfirewall firewall add rule name="Chrome DevTools Local" dir=in action=allow protocol=TCP localport=9222
```

## Ollama Installation and Configuration

Ollama provides local language model serving for the voice control system.

### Installation Methods

#### 1. Windows Installation (Recommended)

**Option A: Direct Download**

1. Download Ollama from [https://ollama.ai](https://ollama.ai)
2. Run the installer
3. Ollama will be installed to `C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\`

**Option B: PowerShell Installation**

```powershell
# Download Ollama installer
$ollamaUrl = "https://ollama.com/download/ollama-windows-amd64.exe"
$ollamaExe = "$env:TEMP\ollama.exe"
Invoke-WebRequest -Uri $ollamaUrl -OutFile $ollamaExe

# Install Ollama
Start-Process -FilePath $ollamaExe -ArgumentList "/S" -Wait

# Add to PATH (optional)
$env:PATH += ";$env:LOCALAPPDATA\Programs\Ollama"
```

#### 2. Manual Installation

```powershell
# Create installation directory
$installDir = "$env:LOCALAPPDATA\Programs\Ollama"
New-Item -ItemType Directory -Force -Path $installDir

# Download Ollama binary
$ollamaUrl = "https://ollama.com/download/ollama-windows-amd64.exe"
$ollamaExe = "$installDir\ollama.exe"
Invoke-WebRequest -Uri $ollamaUrl -OutFile $ollamaExe

# Create Ollama service
$serviceName = "Ollama"
$serviceDescription = "Ollama Language Model Server"

sc.exe create $serviceName binPath= "$ollamaExe serve" start= auto
sc.exe description $serviceName $serviceDescription
sc.exe start $serviceName

# Set PATH
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$newPath = "$installDir;$currentPath"
[Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
```

### Model Installation

#### 1. Basic Models (Recommended for testing)

```powershell
# Start Ollama service
ollama serve

# In another terminal, install models
ollama pull llama2:7b        # 3.8GB - Good for testing
ollama pull mistral:7b       # 4.1GB - Alternative
ollama pull codellama:7b     # 3.8GB - Code-focused
```

#### 2. Production Models (Recommended for production)

```powershell
# High-quality models
ollama pull llama2:70b       # 39GB - Best quality
ollama pull codellama:34b    # 20GB - Advanced coding
ollama pull mistral:7b       # 4.1GB - Fast and capable
```

#### 3. Specialized Models

```powershell
# Specialized models for specific tasks
ollama pull starling-lm:7b   # Text generation
ollama pull dolphin-mistral  # Conversational AI
ollama pull qwen:14b         # Multilingual support
```

### Configuration

#### Ollama Server Configuration

```bash
# Set environment variables for Ollama
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_ORIGINS=["http://localhost:3000", "http://your-voice-control-server:8000"]

# Custom model directories (optional)
OLLAMA_MODELS=/path/to/custom/models
```

#### Voice Control Integration

Update the main server configuration:

```bash
# In voice-control-server/.env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:7b
LLM_MAX_TOKENS=512
LLM_TEMPERATURE=0.7
LLM_TIMEOUT=60
LLM_SYSTEM_PROMPT="You are a helpful voice assistant that can control computer systems safely."
```

### Performance Optimization

#### 1. GPU Acceleration (CUDA)

```powershell
# Check for NVIDIA GPU
nvidia-smi

# If GPU is available, Ollama will automatically use it
# Verify GPU usage
ollama ps
```

#### 2. Memory Management

```bash
# Monitor memory usage
# Recommended: 8GB+ RAM for larger models
# 4GB RAM: Use models up to 7B parameters
# 8GB RAM: Use models up to 13B parameters
# 16GB+ RAM: Use models 34B+ parameters
```

#### 3. Model Switching

```bash
# Switch between models based on task
ollama cp llama2:7b voice-assistant
ollama cp mistral:7b coding-assistant

# Use specific model
OLLAMA_MODEL=voice-assistant
```

## Testing MCP Server Connectivity

### 1. Windows MCP Server Test

```powershell
# Test Windows system integration
python -c "
import sys
sys.path.append('voice-control-server/src')
from integrations.windows_mcp import WindowsMCPServer
server = WindowsMCPServer()
print('Available tools:', list(server.tools.keys()))
result = server.execute_tool('get_system_info', {})
print('System info:', result)
"
```

### 2. Chrome DevTools MCP Test

```powershell
# Test Chrome DevTools connection
curl http://localhost:9222/json/version

# Test MCP tools
python -c "
from integrations.chrome_devtools_mcp import ChromeDevToolsMCP
chrome = ChromeDevToolsMCP()
print('Available tools:', list(chrome.tools.keys()))
"
```

### 3. Ollama Test

```powershell
# Test Ollama API
curl http://localhost:11434/api/tags

# Test model generation
curl http://localhost:11434/api/generate -d '{
  \"model\": \"llama2:7b\",
  \"prompt\": \"Hello, how are you?\",
  \"stream\": false
}'
```

### 4. Integration Test

Run the comprehensive test suite:

```bash
# Test all MCP integrations
./scripts/test-integration.sh --integration-only

# Test specific components
curl http://localhost:8000/api/status | jq '.mcp_servers'
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Windows MCP Server Issues

**Problem**: "Access Denied" errors

**Solutions**:
- Run as Administrator
- Check Windows UAC settings
- Verify file permissions
- Check antivirus software blocking

**Problem**: Commands not executing

**Solutions**:
- Verify path permissions
- Check Windows version compatibility
- Ensure PowerShell execution policy allows scripts

#### 2. Chrome DevTools Issues

**Problem**: Cannot connect to Chrome

**Solutions**:
```powershell
# Check if Chrome is running with DevTools
netstat -an | findstr :9222

# Restart Chrome with DevTools
taskkill /f /im chrome.exe
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" "--remote-debugging-port=9222"
```

**Problem**: Tab manipulation fails

**Solutions**:
- Ensure Chrome is fully loaded
- Check for pop-up blockers
- Verify page is accessible
- Check JavaScript execution permissions

#### 3. Ollama Issues

**Problem**: "Connection refused" to Ollama

**Solutions**:
```powershell
# Check Ollama service status
ollama ps

# Start Ollama service
ollama serve

# Check port availability
netstat -an | findstr :11434

# Restart Ollama
taskkill /f /im ollama.exe
ollama serve
```

**Problem**: Model loading failures

**Solutions**:
- Check available disk space
- Verify model files integrity
- Reduce model size if memory limited
- Check GPU drivers (for CUDA acceleration)

**Problem**: Slow inference

**Solutions**:
- Use smaller models for faster response
- Enable GPU acceleration if available
- Increase system RAM
- Close unnecessary applications

#### 4. General Connectivity Issues

**Problem**: MCP servers not communicating

**Solutions**:
```powershell
# Check network connectivity
ping localhost

# Verify firewall settings
netsh advfirewall show allprofiles

# Test WebSocket connections
curl http://localhost:8000/api/status
```

### Debug Mode

Enable debug logging:

```bash
# In voice-control-server/.env
DEBUG=true
LOG_LEVEL=DEBUG
MCP_DEBUG=true
```

Check logs:

```powershell
# Server logs
tail -f voice-control-server/storage/logs/production.log

# Windows event logs
Get-EventLog -LogName Application -Source "*Voice Control*" -Newest 10
```

### Log Analysis

Common log patterns and meanings:

| Pattern | Meaning | Action |
|---------|---------|---------|
| `Connection timeout` | Network connectivity issue | Check firewall, restart services |
| `Permission denied` | Access control issue | Run as administrator, check permissions |
| `Model not found` | Ollama model missing | Install model: `ollama pull <model>` |
| `Device not found` | Hardware issue | Check Chrome/ChromeDriver, GPU drivers |

## Security Considerations

### 1. Access Control

```powershell
# Limit network access to localhost only
netsh advfirewall firewall add rule name="Voice Control Local" dir=in action=allow protocol=TCP localport=8000

# Restrict Ollama to localhost
netsh advfirewall firewall add rule name="Ollama Local" dir=in action=allow protocol=TCP localport=11434
```

### 2. File System Security

- Limit file system access to necessary directories only
- Use dedicated user accounts for services
- Enable file system auditing
- Regularly backup configuration files

### 3. Network Security

- Use HTTPS for production deployments
- Implement proper authentication
- Monitor network traffic
- Use VPNs for remote access

### 4. Input Validation

- Sanitize all user inputs
- Validate file paths to prevent directory traversal
- Implement rate limiting
- Log security events

## Advanced Configuration

### 1. Custom MCP Tools

Create custom MCP tools for specific functionality:

```python
# In voice-control-server/src/integrations/custom_mcp.py
class CustomMCPServer:
    tools = {
        "custom_operation": {
            "description": "Custom tool description",
            "parameters": {
                "param1": {"type": "string", "description": "Parameter description"}
            }
        }
    }
    
    def execute_tool(self, tool_name: str, parameters: dict):
        if tool_name == "custom_operation":
            # Implementation
            pass
```

### 2. Performance Tuning

#### Windows MCP Performance

```bash
# Increase worker processes
WORKERS=4

# Optimize memory usage
MAX_MEMORY_USAGE=4096

# Tune connection limits
WEBSOCKET_MAX_CONNECTIONS=100
```

#### Chrome DevTools Performance

```bash
# Increase timeout for complex operations
CHROME_TIMEOUT=60

# Enable concurrent operations
CHROME_MAX_CONCURRENT=3
```

#### Ollama Performance

```bash
# Optimize for your hardware
OLLAMA_NUM_PARALLEL=2
OLLAMA_CONTEXT_SIZE=4096

# Enable GPU acceleration
OLLAMA_GPU_LAYERS=35
```

### 3. Monitoring and Metrics

Enable comprehensive monitoring:

```bash
# Enable metrics collection
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
METRICS_RETENTION_DAYS=30

# Monitor MCP performance
MCP_METRICS_ENABLED=true
PERFORMANCE_MONITORING=true
```

### 4. Backup and Recovery

```bash
# Backup MCP configurations
./scripts/config-manager.sh backup -e production

# Schedule regular backups
# Add to Windows Task Scheduler:
schtasks /Create /SC DAILY /TN "Voice Control MCP Backup" /TR "powershell -File C:\path\to\scripts\backup-mcp.ps1"
```

This comprehensive guide should enable you to successfully set up and configure all MCP servers for the Voice Control Ecosystem. For additional support, consult the main documentation or check the troubleshooting section.
