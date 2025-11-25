# Voice Control Ecosystem - Security Guidelines & Best Practices

This comprehensive security guide covers security best practices, hardening procedures, and protection measures for the Voice Control Ecosystem in production environments.

## Table of Contents

1. [Security Overview](#security-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Network Security](#network-security)
4. [Data Protection](#data-protection)
5. [Application Security](#application-security)
6. [System Hardening](#system-hardening)
7. [Monitoring & Incident Response](#monitoring--incident-response)
8. [Compliance & Privacy](#compliance--privacy)
9. [Security Configuration](#security-configuration)
10. [Emergency Procedures](#emergency-procedures)

## Security Overview

### Threat Model

The Voice Control Ecosystem faces several security challenges:

- **Voice Data Interception**: Audio data transmission vulnerabilities
- **System Access**: Unauthorized system control through voice commands
- **Network Attacks**: WebSocket and API endpoint exploitation
- **Privilege Escalation**: Exploiting system control capabilities
- **Data Exfiltration**: Unauthorized access to sensitive information

### Security Principles

- **Defense in Depth**: Multiple layers of security controls
- **Least Privilege**: Minimal required permissions for each component
- **Zero Trust**: Verify everything, trust nothing by default
- **Privacy by Design**: Minimize data collection and retention
- **Security by Default**: Secure configurations out of the box

## Authentication & Authorization

### API Key Authentication (Optional)

```python
# Implement API key authentication
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Verify API key against database
    if not verify_api_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return api_key

# Apply to sensitive endpoints
@app.post("/api/admin/reload-models")
async def reload_models(api_key: str = Security(get_api_key)):
    # Reload AI models
    pass
```

### JWT Token Authentication

```python
# JWT token implementation
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

### Role-Based Access Control

```python
# RBAC implementation
from enum import Enum
from typing import List, Set

class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class Permission(Enum):
    VOICE_CONTROL = "voice_control"
    SYSTEM_ADMIN = "system_admin"
    MODEL_MANAGEMENT = "model_management"

ROLE_PERMISSIONS = {
    UserRole.ADMIN: {
        Permission.VOICE_CONTROL,
        Permission.SYSTEM_ADMIN,
        Permission.MODEL_MANAGEMENT
    },
    UserRole.USER: {
        Permission.VOICE_CONTROL
    },
    UserRole.GUEST: set()
}

def require_permission(permission: Permission):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user = get_current_user()  # Get from context
            user_role = user.role
            required_permissions = ROLE_PERMISSIONS.get(user_role, set())
            
            if permission not in required_permissions:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Apply permission checks
@app.post("/api/admin/system-control")
@require_permission(Permission.SYSTEM_ADMIN)
async def system_control(command: str):
    # Execute system command
    pass
```

## Network Security

### WebSocket Security

```python
# Secure WebSocket implementation
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Secure WebSocket handler
async def websocket_endpoint(websocket: WebSocket):
    # Verify connection origin
    if not verify_origin(websocket.headers.get("origin")):
        await websocket.close(code=1008, reason="Invalid origin")
        return
    
    # Authentication
    api_key = websocket.headers.get("x-api-key")
    if not await verify_api_key(api_key):
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Rate limiting
    if not check_rate_limit(websocket.client.host):
        await websocket.close(code=1008, reason="Rate limit exceeded")
        return
    
    await websocket.accept()
    
    try:
        while True:
            # Message validation
            data = await websocket.receive_text()
            if not validate_message(data):
                await websocket.close(code=1003, reason="Invalid message format")
                break
            
            # Process message
            await process_websocket_message(websocket, data)
            
    except WebSocketDisconnect:
        pass
```

### TLS/SSL Configuration

```python
# HTTPS configuration
import ssl
import uvicorn

# SSL context
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(
    certfile="/path/to/cert.pem",
    keyfile="/path/to/key.pem"
)

# Server configuration
config = {
    "host": "0.0.0.0",
    "port": 8000,
    "ssl_keyfile": "/path/to/key.pem",
    "ssl_certfile": "/path/to/cert.pem",
    "ssl_reload": True,
    "log_config": {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["default"],
        },
    },
}

# Start with SSL
uvicorn.run(app, **config)
```

### Firewall Configuration

```bash
# Windows Firewall rules
netsh advfirewall firewall add rule name="Voice Control HTTPS" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="Voice Control WebSocket" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="Ollama Local" dir=in action=allow protocol=TCP localport=11434

# Restrict to local network only
netsh advfirewall firewall add rule name="Voice Control Local Network" dir=in action=allow protocol=TCP localport=8000 remoteip=192.168.0.0/16
```

```bash
# Linux Firewall (UFW) rules
sudo ufw allow from 192.168.0.0/16 to any port 8000
sudo ufw allow from 192.168.0.0/16 to any port 11434
sudo ufw deny from any to any port 8000
sudo ufw deny from any to any port 11434

# Rate limiting
sudo ufw limit 8000/tcp
sudo ufw limit 11434/tcp
```

## Data Protection

### Voice Data Encryption

```python
# Audio data encryption
from cryptography.fernet import Fernet
import base64

class AudioEncryption:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)
    
    def encrypt_audio(self, audio_data: bytes) -> str:
        encrypted_data = self.fernet.encrypt(audio_data)
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_audio(self, encrypted_b64: str) -> bytes:
        encrypted_data = base64.b64decode(encrypted_b64.encode('utf-8'))
        return self.fernet.decrypt(encrypted_data)

# Key management
class SecureKeyManager:
    @staticmethod
    def generate_key() -> bytes:
        return Fernet.generate_key()
    
    @staticmethod
    def derive_key_from_password(password: str, salt: bytes) -> bytes:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode('utf-8'))
```

### Configuration Encryption

```bash
# Encrypt sensitive configuration
./scripts/config-manager.sh encrypt -e production

# Decrypt for use
./scripts/config-manager.sh decrypt -e production
```

```python
# Encrypted configuration loader
import os
from cryptography.fernet import Fernet

class EncryptedConfig:
    def __init__(self, config_file: str, key_file: str):
        self.config_file = config_file
        self.key_file = key_file
        self.fernet = self._load_key()
    
    def _load_key(self) -> Fernet:
        with open(self.key_file, 'rb') as f:
            key = f.read()
        return Fernet(key)
    
    def load_config(self) -> dict:
        with open(self.config_file, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = self.fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode('utf-8'))
```

### Data Retention & Privacy

```python
# Data retention policies
class DataRetentionManager:
    def __init__(self):
        self.retention_policies = {
            "voice_recordings": 7,     # 7 days
            "transcripts": 30,         # 30 days
            "audit_logs": 90,          # 90 days
            "system_logs": 30,         # 30 days
        }
    
    async def cleanup_expired_data(self):
        from datetime import datetime, timedelta
        
        for data_type, retention_days in self.retention_policies.items():
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            if data_type == "voice_recordings":
                await self.cleanup_old_recordings(cutoff_date)
            elif data_type == "transcripts":
                await self.cleanup_old_transcripts(cutoff_date)
            # ... other data types
    
    async def cleanup_old_recordings(self, cutoff_date: datetime):
        # Remove audio files older than cutoff date
        pass
    
    async def cleanup_old_transcripts(self, cutoff_date: datetime):
        # Remove transcript entries older than cutoff date
        pass

# Automated cleanup task
@app.on_event("startup")
async def start_data_cleanup():
    import asyncio
    # Run cleanup every 24 hours
    asyncio.create_task(schedule_daily_cleanup())

async def schedule_daily_cleanup():
    from datetime import datetime, timedelta
    while True:
        # Run cleanup at 2 AM UTC
        now = datetime.now()
        if now.hour == 2:
            cleanup_manager = DataRetentionManager()
            await cleanup_manager.cleanup_expired_data()
        
        # Wait 1 hour
        await asyncio.sleep(3600)
```

## Application Security

### Input Validation

```python
# Comprehensive input validation
from pydantic import BaseModel, validator, Field
from typing import Optional, List
import re

class VoiceCommandRequest(BaseModel):
    session_id: str = Field(..., regex=r'^[a-zA-Z0-9_-]{1,64}$')
    audio_data: str = Field(..., regex=r'^[A-Za-z0-9+/]*={0,2}$')  # Base64
    client_id: str = Field(..., regex=r'^[a-zA-Z0-9_-]{1,32}$')
    
    @validator('audio_data')
    def validate_audio_data(cls, v):
        # Check audio data size (max 10MB)
        audio_bytes = base64.b64decode(v)
        if len(audio_bytes) > 10 * 1024 * 1024:
            raise ValueError('Audio data too large')
        
        # Check for malicious patterns
        if b'<script' in audio_bytes.lower():
            raise ValueError('Malicious content detected')
        
        return v

class SystemCommandRequest(BaseModel):
    command: str = Field(..., max_length=200)
    parameters: dict = Field(default_factory=dict)
    
    @validator('command')
    def validate_command(cls, v):
        # Whitelist allowed commands
        allowed_commands = [
            'echo', 'get_time', 'list_processes', 'get_system_info',
            'open_application', 'close_application', 'minimize_window'
        ]
        
        if v not in allowed_commands:
            raise ValueError(f'Command "{v}" not allowed')
        
        # Check for command injection
        dangerous_patterns = [';', '|', '&', '$(', '`', '$(', '${']
        if any(pattern in v.lower() for pattern in dangerous_patterns):
            raise ValueError('Command contains dangerous patterns')
        
        return v
    
    @validator('parameters')
    def validate_parameters(cls, v):
        # Sanitize parameter values
        sanitized = {}
        for key, value in v.items():
            # Validate key
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise ValueError(f'Invalid parameter key: {key}')
            
            # Sanitize value
            if isinstance(value, str):
                # Remove potentially dangerous characters
                sanitized_value = re.sub(r'[<>"\']', '', value)
                sanitized[key] = sanitized_value
            else:
                sanitized[key] = value
        
        return sanitized
```

### Secure Command Execution

```python
# Safe command execution
import subprocess
import shlex
from typing import List, Dict, Any

class SecureCommandExecutor:
    # Whitelist of safe commands and their parameters
    ALLOWED_COMMANDS = {
        'echo': {
            'params': ['message'],
            'max_length': 100
        },
        'list_processes': {
            'params': ['filter'],
            'max_length': 50
        },
        'get_time': {
            'params': ['format'],
            'max_length': 20
        }
    }
    
    def execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        # Validate command
        if command not in self.ALLOWED_COMMANDS:
            raise ValueError(f"Command '{command}' not allowed")
        
        config = self.ALLOWED_COMMANDS[command]
        
        # Validate parameters
        for param_name, param_value in parameters.items():
            if param_name not in config['params']:
                raise ValueError(f"Parameter '{param_name}' not allowed for command '{command}'")
            
            # Parameter length validation
            if isinstance(param_value, str) and len(param_value) > config['max_length']:
                raise ValueError(f"Parameter '{param_name}' too long")
        
        # Execute command safely
        try:
            if command == 'echo':
                message = parameters.get('message', '')
                return {'result': message, 'success': True}
            
            elif command == 'list_processes':
                filter_name = parameters.get('filter', 'all')
                processes = self._get_processes(filter_name)
                return {'result': processes, 'success': True}
            
            elif command == 'get_time':
                format_name = parameters.get('format', 'iso')
                current_time = datetime.now().isoformat()
                return {'result': current_time, 'success': True}
            
        except Exception as e:
            return {'error': str(e), 'success': False}
    
    def _get_processes(self, filter_name: str) -> List[Dict]:
        # Safe implementation to get running processes
        import psutil
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                process_info = proc.info
                
                if filter_name == 'chrome' and 'chrome' in process_info['name'].lower():
                    processes.append(process_info)
                elif filter_name == 'all':
                    processes.append(process_info)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
```

### SQL Injection Prevention

```python
# Secure database operations
from sqlalchemy import text
from typing import List, Dict, Any

class SecureDatabase:
    def __init__(self, engine):
        self.engine = engine
    
    async def execute_safe_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict]:
        # Use parameterized queries only
        with self.engine.connect() as connection:
            result = connection.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]
    
    async def get_user_sessions(self, user_id: str) -> List[Dict]:
        # Safe parameterized query
        query = """
            SELECT session_id, created_at, last_activity 
            FROM sessions 
            WHERE user_id = :user_id 
            AND last_activity > NOW() - INTERVAL '1 day'
            ORDER BY last_activity DESC
        """
        return await self.execute_safe_query(query, {"user_id": user_id})
    
    async def log_audit_event(self, user_id: str, action: str, details: str):
        # Safe audit logging
        query = """
            INSERT INTO audit_log (user_id, action, details, timestamp)
            VALUES (:user_id, :action, :details, NOW())
        """
        await self.execute_safe_query(query, {
            "user_id": user_id,
            "action": action,
            "details": details[:1000]  # Limit details length
        })
```

## System Hardening

### Operating System Security

```bash
# Linux system hardening
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install security updates automatically
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Configure automatic security updates
echo 'Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};' | sudo tee /etc/apt/apt.conf.d/50unattended-upgrades

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable cups

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.168.0.0/16 to any port 8000
sudo ufw allow from 192.168.0.0/16 to any port 11434
sudo ufw enable

# Set up fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban

# Configure fail2ban for SSH
sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF

sudo systemctl restart fail2ban
```

### Application Security

```python
# Secure application configuration
import os
from cryptography.fernet import Fernet

class SecurityConfig:
    def __init__(self):
        self.secret_key = self._get_or_create_secret_key()
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _get_or_create_secret_key(self) -> str:
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            secret_key = Fernet.generate_key().decode()
            os.environ['SECRET_KEY'] = secret_key
        return secret_key
    
    def _get_or_create_encryption_key(self) -> bytes:
        key_file = '/app/secure/.encryption_key'
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        
        # Generate new key
        key = Fernet.generate_key()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(key_file), mode=0o700)
        
        # Save key with restricted permissions
        with open(key_file, 'wb') as f:
            f.write(key)
        os.chmod(key_file, 0o600)
        
        return key
    
    def encrypt_sensitive_data(self, data: str) -> str:
        encrypted_data = self.fernet.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted_data = self.fernet.decrypt(encrypted_bytes)
        return decrypted_data.decode()
```

### Container Security

```dockerfile
# Secure Dockerfile
FROM python:3.11-slim

# Security: Create non-root user
RUN groupadd -r voicecontrol && useradd -r -g voicecontrol voicecontrol

# Security: Update packages and install only necessary ones
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Security: Set working directory and permissions
WORKDIR /app

# Security: Copy and install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# Security: Copy application code
COPY . .

# Security: Create necessary directories with proper permissions
RUN mkdir -p storage/logs storage/audio storage/temp \
    && chown -R voicecontrol:voicecontrol /app

# Security: Switch to non-root user
USER voicecontrol

# Security: Set resource limits
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Security: Use read-only filesystem where possible
# VOLUME ["/app/storage"]

EXPOSE 8000

CMD ["python", "start_server.py"]
```

## Monitoring & Incident Response

### Security Monitoring

```python
# Security event monitoring
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

class SecurityMonitor:
    def __init__(self):
        self.alert_thresholds = {
            "failed_auth_attempts": 5,
            "rate_limit_violations": 10,
            "suspicious_commands": 3,
            "large_file_uploads": 5
        }
        self.event_counts = {}
        self.last_cleanup = datetime.now()
    
    async def log_security_event(self, event_type: str, details: Dict[str, Any]):
        timestamp = datetime.utcnow()
        
        # Log to secure audit log
        await self._write_audit_log(timestamp, event_type, details)
        
        # Check for potential attacks
        await self._check_thresholds(event_type, details)
        
        # Send alerts if necessary
        await self._send_alerts_if_needed(event_type, details)
    
    async def _write_audit_log(self, timestamp: datetime, event_type: str, details: Dict[str, Any]):
        audit_entry = {
            "timestamp": timestamp.isoformat(),
            "event_type": event_type,
            "details": details,
            "severity": self._calculate_severity(event_type, details)
        }
        
        # Write to encrypted audit log
        with open("/app/storage/logs/security_audit.log", "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
    
    async def _check_thresholds(self, event_type: str, details: Dict[str, Any]):
        client_ip = details.get("client_ip", "unknown")
        key = f"{event_type}_{client_ip}"
        
        # Initialize counter
        if key not in self.event_counts:
            self.event_counts[key] = {
                "count": 0,
                "first_seen": datetime.now(),
                "last_seen": datetime.now()
            }
        
        # Update count
        self.event_counts[key]["count"] += 1
        self.event_counts[key]["last_seen"] = datetime.now()
        
        # Check threshold
        threshold = self.alert_thresholds.get(event_type, float('inf'))
        if self.event_counts[key]["count"] >= threshold:
            await self._trigger_alert(key, event_type, self.event_counts[key])
    
    async def _send_alerts_if_needed(self, event_type: str, details: Dict[str, Any]):
        severity = self._calculate_severity(event_type, details)
        
        if severity == "HIGH":
            # Send immediate alert
            await self._send_immediate_alert(event_type, details)
        elif severity == "MEDIUM":
            # Add to daily summary
            await self._add_to_daily_summary(event_type, details)
    
    def _calculate_severity(self, event_type: str, details: Dict[str, Any]) -> str:
        # Severity calculation logic
        if event_type in ["failed_auth_attempts", "command_injection_attempt"]:
            return "HIGH"
        elif event_type in ["rate_limit_violation", "large_file_upload"]:
            return "MEDIUM"
        else:
            return "LOW"

# Security middleware
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Check request for security threats
    client_ip = request.client.host
    
    # Rate limiting
    if not await check_rate_limit(client_ip):
        await security_monitor.log_security_event(
            "rate_limit_violation",
            {"client_ip": client_ip, "endpoint": str(request.url)}
        )
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})
    
    # Input validation
    if not await validate_request(request):
        await security_monitor.log_security_event(
            "invalid_request",
            {"client_ip": client_ip, "endpoint": str(request.url)}
        )
        return JSONResponse(status_code=400, content={"error": "Invalid request"})
    
    response = await call_next(request)
    
    # Log successful requests for auditing
    await security_monitor.log_security_event(
        "request_completed",
        {
            "client_ip": client_ip,
            "endpoint": str(request.url),
            "status_code": response.status_code
        }
    )
    
    return response
```

### Incident Response Plan

```bash
#!/bin/bash
# scripts/security-incident-response.sh

echo "Voice Control Ecosystem - Security Incident Response"
echo "=================================================="

# Immediate response steps
echo "Step 1: Stop all voice control services"
sudo systemctl stop voice-control-server
docker-compose down

echo "Step 2: Isolate the system"
sudo ufw deny 8000/tcp
sudo ufw deny 11434/tcp

echo "Step 3: Preserve evidence"
cp -r /app/storage/logs/ /tmp/security-evidence-$(date +%Y%m%d-%H%M%S)/
cp /var/log/auth.log /tmp/security-evidence-$(date +%Y%m%d-%H%M%S)/

echo "Step 4: Notify stakeholders"
# Send notifications (email, Slack, etc.)
# This would be implemented based on your notification system

echo "Step 5: Assess damage"
# Analyze logs for:
# - Unauthorized access attempts
# - Data exfiltration
# - System modifications

echo "Step 6: Recovery plan"
# 1. Restore from backup
# 2. Apply security patches
# 3. Update passwords
# 4. Monitor for ongoing threats
# 5. Gradually restore services

echo "For detailed procedures, see docs/security-incident-response.md"
```

## Compliance & Privacy

### Data Privacy Compliance

```python
# Privacy compliance features
class PrivacyManager:
    def __init__(self):
        self.data_categories = {
            "voice_data": {"sensitive": True, "retention_days": 7},
            "transcripts": {"sensitive": True, "retention_days": 30},
            "system_logs": {"sensitive": False, "retention_days": 30},
            "audit_logs": {"sensitive": True, "retention_days": 90}
        }
    
    async def handle_data_request(self, request_type: str, user_id: str, **kwargs):
        """Handle GDPR-style data subject requests"""
        if request_type == "access":
            return await self._export_user_data(user_id)
        elif request_type == "deletion":
            return await self._delete_user_data(user_id)
        elif request_type == "portability":
            return await self._export_portable_data(user_id)
        elif request_type == "rectification":
            return await self._update_user_data(user_id, kwargs)
    
    async def _export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export all user data"""
        user_data = {}
        
        for data_type in self.data_categories:
            data = await self._get_user_data(user_id, data_type)
            if data:
                user_data[data_type] = data
        
        return user_data
    
    async def _delete_user_data(self, user_id: str) -> Dict[str, Any]:
        """Delete all user data"""
        deleted_data = {}
        
        for data_type, config in self.data_categories.items():
            data = await self._get_user_data(user_id, data_type)
            if data:
                await self._delete_user_data_type(user_id, data_type)
                deleted_data[data_type] = {"deleted": True, "records": len(data)}
        
        return deleted_data
    
    async def _get_consent_status(self, user_id: str) -> Dict[str, Any]:
        """Check user consent status"""
        return await self._get_user_consent(user_id)
    
    async def _update_consent(self, user_id: str, consent_data: Dict[str, Any]) -> bool:
        """Update user consent preferences"""
        return await self._set_user_consent(user_id, consent_data)
```

### Audit Compliance

```python
# Audit logging for compliance
class AuditLogger:
    def __init__(self):
        self.audit_events = [
            "user_authentication",
            "voice_command_executed",
            "system_access",
            "data_access",
            "data_modification",
            "security_event",
            "configuration_change"
        ]
    
    async def log_audit_event(self, event_type: str, user_id: str, details: Dict[str, Any]):
        """Log event for audit trail"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "session_id": details.get("session_id"),
            "ip_address": details.get("client_ip"),
            "user_agent": details.get("user_agent"),
            "details": details,
            "hash": self._calculate_integrity_hash(event_type, user_id, details)
        }
        
        # Write to audit log with integrity protection
        await self._write_audit_log_entry(audit_entry)
    
    def _calculate_integrity_hash(self, event_type: str, user_id: str, details: Dict[str, Any]) -> str:
        """Calculate hash for log integrity"""
        import hashlib
        import hmac
        
        # Create integrity hash
        data = f"{event_type}:{user_id}:{json.dumps(details, sort_keys=True)}"
        return hmac.new(
            key=os.environ['AUDIT_LOG_SECRET'].encode(),
            msg=data.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
    
    async def verify_audit_integrity(self, log_file: str) -> Dict[str, bool]:
        """Verify audit log integrity"""
        integrity_results = {}
        
        with open(log_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    expected_hash = entry.get('hash')
                    
                    # Recalculate hash
                    data = f"{entry['event_type']}:{entry['user_id']}:{json.dumps(entry['details'], sort_keys=True)}"
                    calculated_hash = self._calculate_integrity_hash(
                        entry['event_type'],
                        entry['user_id'],
                        entry['details']
                    )
                    
                    integrity_results[f"line_{line_num}"] = (expected_hash == calculated_hash)
                    
                except (json.JSONDecodeError, KeyError) as e:
                    integrity_results[f"line_{line_num}"] = False
        
        return integrity_results
```

## Security Configuration

### Environment-Specific Security

```bash
# Production security configuration
# In .env.production
SECURITY_STRICT_MODE=true
ENFORCE_HTTPS=true
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST_SIZE=10

# Authentication
REQUIRE_API_KEY=true
REQUIRE_JWT_TOKEN=false
TOKEN_EXPIRY_MINUTES=15

# Encryption
ENCRYPT_SENSITIVE_DATA=true
AUDIO_DATA_ENCRYPTION=true
CONFIG_ENCRYPTION_KEY_FILE=/app/secure/.config_key

# Monitoring
ENABLE_SECURITY_MONITORING=true
AUDIT_LOG_RETENTION_DAYS=2555  # 7 years for compliance
SECURITY_ALERT_EMAIL=security@yourcompany.com

# Network security
RESTRICT_TO_LOCAL_NETWORK=true
ALLOWED_ORIGINS=https://yourdomain.com
CORS_STRICT_MODE=true
```

### Security Testing

```bash
#!/bin/bash
# Security test suite

echo "Running security tests..."

# Test 1: Input validation
echo "Testing input validation..."
python -c "
import requests
import json

# Test malicious input
malicious_inputs = [
    'echo $(whoami)',
    '<script>alert(\"xss\")</script>',
    '../../../etc/passwd',
    'SELECT * FROM users;'
]

for inp in malicious_inputs:
    response = requests.post('http://localhost:8000/api/voice-command', 
                           json={'command': inp, 'session_id': 'test'})
    if response.status_code == 200:
        print(f'WARNING: Malicious input accepted: {inp}')
    else:
        print(f'OK: Malicious input rejected: {inp}')
"

# Test 2: Authentication bypass
echo "Testing authentication bypass..."
python -c "
import requests

# Test without API key
response = requests.get('http://localhost:8000/api/admin/status')
if response.status_code == 200:
    print('WARNING: Admin endpoint accessible without authentication')
else:
    print('OK: Admin endpoint properly protected')
"

# Test 3: Rate limiting
echo "Testing rate limiting..."
python -c "
import requests
import time

for i in range(20):
    response = requests.get('http://localhost:8000/health')
    if response.status_code == 429:
        print('OK: Rate limiting working')
        break
    time.sleep(0.1)
else:
    print('WARNING: Rate limiting may not be working')
"

echo "Security tests completed"
```

## Emergency Procedures

### Incident Response Checklist

```bash
#!/bin/bash
# Emergency security response checklist

echo "EMERGENCY SECURITY RESPONSE CHECKLIST"
echo "===================================="
echo

echo "1. IMMEDIATE RESPONSE (0-5 minutes):"
echo "   [ ] Stop all voice control services"
echo "   [ ] Isolate the system from network"
echo "   [ ] Preserve system logs and evidence"
echo "   [ ] Notify security team"
echo

echo "2. ASSESSMENT (5-15 minutes):"
echo "   [ ] Analyze compromised systems"
echo "   [ ] Determine attack vector"
echo "   [ ] Assess data exposure"
echo "   [ ] Identify affected users"
echo

echo "3. CONTAINMENT (15-30 minutes):"
echo "   [ ] Block malicious IP addresses"
echo "   [ ] Reset all user passwords"
echo "   [ ] Revoke API keys and tokens"
echo "   [ ] Disable compromised accounts"
echo

echo "4. RECOVERY (30+ minutes):"
echo "   [ ] Restore from clean backup"
echo "   [ ] Apply security patches"
echo "   [ ] Update security configurations"
echo "   [ ] Gradually restore services"
echo

echo "5. POST-INCIDENT:"
echo "   [ ] Document incident response"
echo "   [ ] Conduct forensic analysis"
echo "   [ ] Update security procedures"
echo "   [ ] Train staff on lessons learned"
echo

echo "For detailed procedures, run:"
echo "  ./scripts/security-incident-response.sh"
```

This comprehensive security guide provides the framework for securing the Voice Control Ecosystem in production environments. Regular security audits, penetration testing, and compliance reviews should be conducted to maintain security posture over time.
