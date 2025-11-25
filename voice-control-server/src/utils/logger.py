"""
Logger utility for the voice control server

Provides centralized logging configuration and utilities.
"""

import logging
import logging.handlers
import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json
from functools import wraps

from src.config.settings import get_settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for console"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'lineno', 
                          'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process',
                          'message', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class VoiceControlLogger:
    """Custom logger class for voice control server"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger configuration"""
        settings = get_settings()
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set level
        level = getattr(logging, settings.log_level.upper(), logging.INFO)
        self.logger.setLevel(level)
        
        # Create formatters
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(level)
        self.logger.addHandler(console_handler)
        
        # File handler
        if settings.log_file:
            log_file_path = Path(settings.log_file)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(level)
            self.logger.addHandler(file_handler)
        
        # Prevent duplicate logs
        self.logger.propagate = False
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        """Log error message"""
        self.logger.error(message, exc_info=exc_info, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, extra=kwargs)
    
    def log_function_call(self, func_name: str, args: tuple = None, kwargs: dict = None):
        """Log function call with parameters"""
        self.debug(f"Calling {func_name}", 
                  function=func_name, 
                  args=args or (), 
                  kwargs=kwargs or {})
    
    def log_response(self, response_data: Dict[str, Any], duration_ms: Optional[int] = None):
        """Log response data"""
        self.info(f"Response: {len(str(response_data))} bytes", 
                 response_size=len(str(response_data)),
                 duration_ms=duration_ms)
    
    def log_websocket_event(self, event: str, session_id: str, **kwargs):
        """Log WebSocket events"""
        self.info(f"WebSocket {event}: {session_id}",
                 event=event,
                 session_id=session_id,
                 **kwargs)
    
    def log_audio_processing(self, action: str, duration_ms: int, **kwargs):
        """Log audio processing events"""
        self.info(f"Audio {action} completed in {duration_ms}ms",
                 action=action,
                 duration_ms=duration_ms,
                 **kwargs)


# Global logger instances
_loggers: Dict[str, VoiceControlLogger] = {}


def setup_logger(name: str) -> VoiceControlLogger:
    """Setup and return a logger instance"""
    if name not in _loggers:
        _loggers[name] = VoiceControlLogger(name)
    return _loggers[name]


def get_logger(name: str) -> VoiceControlLogger:
    """Get existing logger instance"""
    return _loggers.get(name, setup_logger(name))


def log_performance(func):
    """Decorator to log function performance"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = datetime.utcnow()
        logger = get_logger(func.__module__)
        logger.log_function_call(func.__name__, args, kwargs)
        
        try:
            result = await func(*args, **kwargs)
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(f"{func.__name__} completed in {duration:.2f}ms",
                       function=func.__name__,
                       duration_ms=duration)
            return result
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"{func.__name__} failed after {duration:.2f}ms: {str(e)}",
                        function=func.__name__,
                        duration_ms=duration,
                        exc_info=True)
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = datetime.utcnow()
        logger = get_logger(func.__module__)
        logger.log_function_call(func.__name__, args, kwargs)
        
        try:
            result = func(*args, **kwargs)
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(f"{func.__name__} completed in {duration:.2f}ms",
                       function=func.__name__,
                       duration_ms=duration)
            return result
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"{func.__name__} failed after {duration:.2f}ms: {str(e)}",
                        function=func.__name__,
                        duration_ms=duration,
                        exc_info=True)
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


class AuditLogger:
    """Specialized logger for audit trail"""
    
    def __init__(self):
        self.logger = setup_logger("audit")
        self.audit_file = Path(get_settings().storage_path) / "audit.log"
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup file handler for audit log
        audit_handler = logging.handlers.RotatingFileHandler(
            self.audit_file,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        audit_handler.setFormatter(JSONFormatter())
        self.logger.logger.addHandler(audit_handler)
    
    def log_user_action(self, user_id: str, action: str, session_id: str, details: Dict[str, Any] = None):
        """Log user action for audit trail"""
        self.logger.info(f"User action: {action}",
                        user_id=user_id,
                        action=action,
                        session_id=session_id,
                        details=details or {},
                        audit_type="user_action")
    
    def log_system_event(self, event: str, source: str, details: Dict[str, Any] = None):
        """Log system event for audit trail"""
        self.logger.info(f"System event: {event}",
                        event=event,
                        source=source,
                        details=details or {},
                        audit_type="system_event")
    
    def log_security_event(self, event: str, ip_address: str, details: Dict[str, Any] = None):
        """Log security event for audit trail"""
        self.logger.warning(f"Security event: {event}",
                           event=event,
                           ip_address=ip_address,
                           details=details or {},
                           audit_type="security_event")
    
    def log_data_access(self, data_type: str, action: str, session_id: str, details: Dict[str, Any] = None):
        """Log data access for audit trail"""
        self.logger.info(f"Data access: {data_type} {action}",
                        data_type=data_type,
                        action=action,
                        session_id=session_id,
                        details=details or {},
                        audit_type="data_access")


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Performance monitoring
class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self):
        self.logger = get_logger("performance")
        self.metrics: Dict[str, list] = {}
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a performance metric"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            'value': value,
            'timestamp': datetime.utcnow(),
            'tags': tags or {}
        })
        
        # Keep only last 1000 entries per metric
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
    
    def get_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        values = [m['value'] for m in self.metrics[name]]
        values.sort()
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'p50': values[len(values) // 2],
            'p95': values[int(len(values) * 0.95)],
            'p99': values[int(len(values) * 0.99)]
        }
    
    def log_summary(self):
        """Log performance summary"""
        for name, stats in {k: self.get_stats(k) for k in self.metrics.keys()}.items():
            if stats:
                self.logger.info(f"Performance metrics for {name}", 
                               metric=name,
                               **stats)


# Global performance monitor
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# Initialize default loggers
setup_logger("voice_control_server")
setup_logger("stt_service")
setup_logger("llm_service")
setup_logger("mcp_service")
setup_logger("websocket")
setup_logger("audio_processing")