# Voice Control Ecosystem - Performance Tuning Guide

This comprehensive guide covers performance optimization techniques for the Voice Control Ecosystem, including server optimization, model tuning, resource management, and monitoring.

## Table of Contents

1. [Performance Overview](#performance-overview)
2. [Hardware Requirements](#hardware-requirements)
3. [Server Performance Optimization](#server-performance-optimization)
4. [Model Optimization](#model-optimization)
5. [Memory Management](#memory-management)
6. [Network Performance](#network-performance)
7. [Audio Processing Optimization](#audio-processing-optimization)
8. [Database Performance](#database-performance)
9. [Monitoring and Metrics](#monitoring-and-metrics)
10. [Scaling Strategies](#scaling-strategies)
11. [Benchmarking](#benchmarking)

## Performance Overview

The Voice Control Ecosystem consists of multiple components that can be optimized:

- **FastAPI Server**: Handles WebSocket connections and API requests
- **Speech-to-Text (Whisper)**: Audio transcription processing
- **Language Model (Ollama)**: LLM inference and response generation
- **MCP Servers**: Tool execution and system automation
- **React Native App**: Mobile client for voice recording

### Performance Targets

| Component | Target Response Time | Throughput | Resource Usage |
|-----------|---------------------|------------|----------------|
| Server | < 100ms | 100+ concurrent users | 2-4GB RAM, 2-4 CPU cores |
| STT Processing | < 500ms | 50+ requests/minute | 1-2GB RAM, GPU optional |
| LLM Processing | < 2s | 30+ requests/minute | 4-8GB RAM, GPU recommended |
| WebSocket Connection | < 50ms | 100+ simultaneous | Minimal CPU/Memory |
| Overall System | < 3s end-to-end | 50+ concurrent sessions | 8-16GB RAM total |

## Hardware Requirements

### Minimum Requirements
- **CPU**: Intel i5/AMD Ryzen 5 (4+ cores)
- **RAM**: 8GB
- **Storage**: 50GB SSD
- **Network**: 100Mbps stable connection
- **GPU**: Optional (for acceleration)

### Recommended Requirements
- **CPU**: Intel i7/AMD Ryzen 7 (8+ cores)
- **RAM**: 16GB+
- **Storage**: 100GB+ NVMe SSD
- **Network**: 1Gbps stable connection
- **GPU**: NVIDIA GTX 1060+ (6GB+ VRAM) or modern equivalent

### Production Requirements
- **CPU**: Intel Xeon/AMD EPYC (16+ cores)
- **RAM**: 32GB+
- **Storage**: 500GB+ NVMe SSD with redundancy
- **Network**: 10Gbps connection with redundancy
- **GPU**: NVIDIA RTX 3080+ (10GB+ VRAM) for LLM acceleration

### Hardware Optimization Tips

#### CPU Optimization
```bash
# Set CPU governor for performance
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Disable CPU idle states for low latency
echo 1 | sudo tee /sys/devices/system/cpu/cpu*/cpuidle/state*/disable

# Set process priority for voice control server
nice -n -10 python start_server.py
```

#### Memory Optimization
```bash
# Configure memory overcommit
echo 1 | sudo tee /proc/sys/vm/overcommit_memory

# Set swappiness to minimize swap usage
echo 10 | sudo tee /proc/sys/vm/swappiness

# Configure huge pages for large models
echo 512 | sudo tee /proc/sys/vm/nr_hugepages
```

#### Storage Optimization
```bash
# Set I/O scheduler for SSD
echo noop | sudo tee /sys/block/sda/queue/scheduler

# Optimize for low latency
echo 1 | sudo tee /sys/block/sda/queue/nomerges
echo 1 | sudo tee /sys/block/sda/queue/rotational
echo 1 | sudo tee /sys/block/sda/queue/rq_affinity
```

## Server Performance Optimization

### FastAPI Configuration

#### Production Settings
```bash
# In production configuration (.env.production)
WORKERS=4                    # CPU cores or CPU cores * 2
WORKER_CONNECTIONS=1000      # Concurrent connections per worker
MAX_REQUESTS=1000           # Restart worker after requests
MAX_REQUESTS_JITTER=100     # Random jitter for restarts
TIMEOUT=120                 # Request timeout
KEEPALIVE=2                 # Keep-alive timeout

# Optimize for your hardware
WORKERS=$(nproc)            # Number of CPU cores
WORKER_CONNECTIONS=1000     # 1000 * WORKERS = max concurrent connections
```

#### Gunicorn Optimization
```bash
# Advanced Gunicorn configuration
gunicorn src.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 120 \
    --keep-alive 2 \
    --preload-app \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

### Connection Management

#### WebSocket Optimization
```bash
# In configuration file
WEBSOCKET_MAX_CONNECTIONS=100      # Concurrent WebSocket connections
WEBSOCKET_PING_INTERVAL=30         # Ping interval in seconds
WEBSOCKET_CLOSE_TIMEOUT=60         # Connection close timeout
WEBSOCKET_MAX_MESSAGE_SIZE=10485760 # 10MB max message size

# WebSocket buffer optimization
WEBSOCKET_SEND_BUFFER_SIZE=65536   # Send buffer size
WEBSOCKET_RECV_BUFFER_SIZE=65536   # Receive buffer size
```

#### Rate Limiting
```bash
# Configure rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100          # Requests per minute per IP
RATE_LIMIT_PER_HOUR=1000           # Requests per hour per IP
RATE_LIMIT_BURST_SIZE=10           # Burst allowance
```

### Async/Await Optimization

#### Process Pool Configuration
```python
# In main.py or service configuration
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# Configure process pools for CPU-intensive tasks
PROCESS_POOL_SIZE = 2  # For STT processing
THREAD_POOL_SIZE = 10  # For I/O operations

# Configure async event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Optimize for your workload
loop.set_default_executor(ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE))
```

## Model Optimization

### Speech-to-Text (Whisper) Optimization

#### Model Selection
```bash
# Performance vs Accuracy trade-offs
WHISPER_MODEL=tiny      # Fastest, lowest accuracy
WHISPER_MODEL=base      # Balanced (recommended)
WHISPER_MODEL=small     # Better accuracy, slower
WHISPER_MODEL=medium    # Good accuracy
WHISPER_MODEL=large     # Best accuracy, slowest
```

#### Compute Optimization
```bash
# Device selection
WHISPER_DEVICE=cpu      # CPU only (most compatible)
WHISPER_DEVICE=cuda     # GPU acceleration (NVIDIA)
WHISPER_DEVICE=opencl   # OpenCL GPU acceleration
WHISPER_DEVICE=mps      # Apple Silicon GPU

# Compute type optimization
WHISPER_COMPUTE_TYPE=int8       # Fastest, smallest memory
WHISPER_COMPUTE_TYPE=float16    # Good balance (recommended)
WHISPER_COMPUTE_TYPE=float32    # Highest accuracy
```

#### Batch Processing
```bash
# Optimize for batch processing
STT_BATCH_SIZE=8              # Process multiple audio chunks
STT_BATCH_TIMEOUT=100         # Milliseconds to wait for batch
STT_CONCURRENT_REQUESTS=2     # Parallel STT processing
```

#### Memory Management
```bash
# Whisper memory optimization
WHISPER_VRAM_OPTIMIZATION=true
WHISPER_CPU_THREADS=4         # CPU threads for inference
WHISPER_CHUNK_LENGTH=30       # Process audio in chunks
WHISPER_FLASH_ATTENTION=true  # Use flash attention if available
```

### Language Model (Ollama) Optimization

#### Model Selection Strategy
```bash
# Hardware-based model selection
# 4GB RAM: Use 7B parameter models
# 8GB RAM: Use 13B parameter models
# 16GB+ RAM: Use 34B+ parameter models

OLLAMA_MODEL=llama2:7b        # Good for 8GB+ systems
OLLAMA_MODEL=llama2:13b       # Requires 16GB+ RAM
OLLAMA_MODEL=mistral:7b       # Efficient alternative
OLLAMA_MODEL=codellama:7b     # For code tasks
```

#### Performance Settings
```bash
# Generation parameters
LLM_MAX_TOKENS=512           # Response length limit
LLM_TEMPERATURE=0.7          # Creativity balance
LLM_TOP_P=0.9                # Nucleus sampling
LLM_TOP_K=40                 # Top-k sampling

# Performance optimization
LLM_CONTEXT_SIZE=2048        # Context window size
LLM_GPU_LAYERS=35            # GPU layers (0 for CPU only)
LLM_NUM_PARALLEL=2           # Parallel requests
OLLAMA_NUM_PARALLEL=2        # Ollama parallel processing
```

#### Caching Strategy
```bash
# Enable response caching
CACHE_ENABLED=true
CACHE_TTL=3600               # Cache TTL in seconds
CACHE_MAX_SIZE=1000          # Maximum cache entries
CACHE_COMPRESSION=true       # Compress cached responses
```

#### Model Switching
```bash
# Dynamic model switching based on task
SPECIALIZED_MODELS=true
TASK_MODEL_MAPPING='{"coding": "codellama", "conversation": "llama2", "analysis": "mistral"}'
```

## Memory Management

### Process Memory Optimization

#### Python Memory Settings
```bash
# Set Python memory limits
PYTHONMALLOC=malloc          # Use jemalloc if available
PYTHONHASHSEED=random        # Randomized hash seeding
PYTHONDONTWRITEBYTECODE=1    # Don't write .pyc files

# Garbage collection optimization
PYTHONGC=1                   # Enable generational GC
PYTHONTRACEBACK=1            # Detailed tracebacks
```

#### Application Memory Limits
```bash
# In configuration
MAX_MEMORY_USAGE=8192        # MB limit for server
MAX_CPU_USAGE=80             # CPU percentage limit
MEMORY_MONITORING_ENABLED=true
AUTO_RESTART_ON_OOM=true
```

### Model Memory Management

#### Lazy Loading
```python
# Implement lazy model loading
class LazyModel:
    def __init__(self, model_name, device):
        self.model_name = model_name
        self.device = device
        self.model = None
        self._lock = asyncio.Lock()
    
    async def load(self):
        async with self._lock:
            if self.model is None:
                self.model = load_model(self.model_name, self.device)
    
    async def inference(self, input_data):
        await self.load()
        return self.model.inference(input_data)
```

#### Model Unloading
```python
# Implement model unloading for low-memory situations
class MemoryAwareModelManager:
    def __init__(self, max_memory_mb=4096):
        self.max_memory_mb = max_memory_mb
        self.loaded_models = {}
        self.last_access = {}
    
    async def load_model(self, model_name):
        # Check memory before loading
        current_memory = psutil.virtual_memory().percent
        if current_memory > 80:
            await self.unload_least_recently_used()
        
        # Load model
        self.loaded_models[model_name] = load_model(model_name)
        self.last_access[model_name] = time.time()
    
    async def unload_least_recently_used(self):
        if not self.loaded_models:
            return
        
        lru_model = min(self.last_access, key=self.last_access.get)
        del self.loaded_models[lru_model]
        del self.last_access[lru_model]
```

## Network Performance

### WebSocket Optimization

#### Connection Pooling
```python
# Implement WebSocket connection pooling
class OptimizedConnectionManager:
    def __init__(self, max_connections=100):
        self.max_connections = max_connections
        self.connections = {}
        self.connection_pool = asyncio.Queue(maxsize=max_connections)
    
    async def get_connection(self):
        try:
            return await asyncio.wait_for(self.connection_pool.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None
    
    async def return_connection(self, connection):
        try:
            self.connection_pool.put_nowait(connection)
        except asyncio.QueueFull:
            await connection.close()
```

#### Message Compression
```python
# Enable message compression
import zlib

def compress_message(message: str) -> bytes:
    return zlib.compress(message.encode('utf-8'), level=6)

def decompress_message(compressed: bytes) -> str:
    return zlib.decompress(compressed).decode('utf-8')
```

### HTTP Optimization

#### Response Compression
```python
# In main.py
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Enable response caching
from fastapi.responses import JSONResponse
from cachetools import TTLCache

cache = TTLCache(maxsize=1000, ttl=300)

@app.get("/api/cacheable-endpoint")
async def cacheable_endpoint():
    cache_key = "some_key"
    if cache_key in cache:
        return cache[cache_key]
    
    result = await expensive_computation()
    cache[cache_key] = result
    return result
```

## Audio Processing Optimization

### Audio Buffer Management

#### Optimized Buffer Sizes
```python
# Audio buffer optimization
AUDIO_CHUNK_SIZE = 1024      # 1024 samples = 64ms at 16kHz
AUDIO_BUFFER_SIZE = 4096     # 4 chunks buffer
AUDIO_OVERLAP_SIZE = 256     # 25% overlap for continuity

# Dynamic buffer sizing
class DynamicAudioBuffer:
    def __init__(self, base_size=1024, max_size=4096):
        self.base_size = base_size
        self.max_size = max_size
        self.current_size = base_size
        self.silence_threshold = 0.01
    
    def adjust_buffer_size(self, audio_level, processing_time):
        if processing_time > 0.1:  # 100ms processing time
            self.current_size = min(self.current_size * 2, self.max_size)
        elif audio_level < self.silence_threshold:
            self.current_size = max(self.current_size // 2, self.base_size)
```

#### Audio Processing Pipeline
```python
# Optimized audio processing pipeline
import numpy as np
from concurrent.futures import ThreadPoolExecutor

class OptimizedAudioProcessor:
    def __init__(self, num_workers=2):
        self.thread_pool = ThreadPoolExecutor(max_workers=num_workers)
        self.preprocessing_queue = asyncio.Queue(maxsize=100)
        
    async def process_audio_async(self, audio_data):
        # Preprocess in thread pool
        loop = asyncio.get_event_loop()
        processed_audio = await loop.run_in_executor(
            self.thread_pool, 
            self.preprocess_audio, 
            audio_data
        )
        
        # Add to processing queue
        await self.preprocessing_queue.put(processed_audio)
        
        # Process in background
        asyncio.create_task(self.process_queue())
    
    def preprocess_audio(self, audio_data):
        # Optimized preprocessing
        # - Noise reduction
        # - Normalization
        # - Voice activity detection
        return processed_audio
```

## Database Performance

### SQLite Optimization (Development)

```sql
-- SQLite performance optimization
PRAGMA journal_mode=WAL;        -- Write-Ahead Logging
PRAGMA synchronous=NORMAL;      -- Balance safety and speed
PRAGMA cache_size=10000;        -- Cache size in pages
PRAGMA temp_store=MEMORY;       -- Store temp tables in memory
PRAGMA mmap_size=268435456;     -- Memory-mapped I/O (256MB)

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_conversation_timestamp ON conversations(timestamp);
CREATE INDEX IF NOT EXISTS idx_session_user ON sessions(user_id);
```

### PostgreSQL Optimization (Production)

```sql
-- PostgreSQL performance tuning
-- In postgresql.conf
shared_buffers = 256MB              -- 25% of RAM
effective_cache_size = 1GB          -- 75% of RAM
maintenance_work_mem = 64MB         -- For maintenance operations
work_mem = 4MB                      -- Per operation
random_page_cost = 1.1              -- For SSD storage
max_connections = 100

-- Connection pooling configuration
-- In .env
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
```

## Monitoring and Metrics

### Performance Monitoring Setup

#### Prometheus Metrics
```python
# Add to main.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import psutil

# Define metrics
REQUEST_COUNT = Counter('voice_control_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('voice_control_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('voice_control_active_connections', 'Active WebSocket connections')
MEMORY_USAGE = Gauge('voice_control_memory_usage_bytes', 'Memory usage in bytes')
CPU_USAGE = Gauge('voice_control_cpu_usage_percent', 'CPU usage percentage')

# Add monitoring to endpoints
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)
    
    return response

# Update metrics periodically
async def update_system_metrics():
    while True:
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        
        MEMORY_USAGE.set(memory.used)
        CPU_USAGE.set(cpu)
        
        await asyncio.sleep(30)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_system_metrics())
```

#### Grafana Dashboard Configuration
```yaml
# monitoring/grafana/dashboards/voice-control-overview.json
{
  "dashboard": {
    "title": "Voice Control Performance",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(voice_control_requests_total[1m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(voice_control_request_duration_seconds_bucket[1m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "voice_control_memory_usage_bytes / 1024 / 1024",
            "legendFormat": "Memory (MB)"
          }
        ]
      }
    ]
  }
}
```

### Health Checks and Alerts

#### Custom Health Check Endpoint
```python
@app.get("/health/detailed")
async def detailed_health_check():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Check memory usage
    memory = psutil.virtual_memory()
    health_status["components"]["memory"] = {
        "status": "healthy" if memory.percent < 80 else "degraded",
        "usage_percent": memory.percent,
        "available_gb": memory.available / (1024**3)
    }
    
    # Check CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    health_status["components"]["cpu"] = {
        "status": "healthy" if cpu_percent < 80 else "degraded",
        "usage_percent": cpu_percent
    }
    
    # Check database connection
    try:
        # Test database connection
        db_status = "healthy" if test_db_connection() else "unhealthy"
    except Exception:
        db_status = "unhealthy"
    
    health_status["components"]["database"] = {"status": db_status}
    
    # Determine overall status
    if any(comp["status"] == "unhealthy" for comp in health_status["components"].values()):
        health_status["status"] = "unhealthy"
        return JSONResponse(content=health_status, status_code=503)
    elif any(comp["status"] == "degraded" for comp in health_status["components"].values()):
        health_status["status"] = "degraded"
        return JSONResponse(content=health_status, status_code=200)
    
    return health_status
```

## Scaling Strategies

### Horizontal Scaling

#### Load Balancer Configuration
```yaml
# haproxy/haproxy.cfg
global
    daemon
    maxconn 4096
    
defaults
    mode http
    timeout connect 5s
    timeout client 30s
    timeout server 30s
    
frontend voice_control_frontend
    bind *:8000
    default_backend voice_control_servers
    
backend voice_control_servers
    balance roundrobin
    option httpchk GET /health
    server server1 127.0.0.1:8001 check
    server server2 127.0.0.1:8002 check
    server server3 127.0.0.1:8003 check
```

#### Docker Swarm Setup
```bash
# Deploy as Docker Swarm service
docker service create \
  --name voice-control-server \
  --replicas 3 \
  --network voice-control-net \
  --publish 8000:8000 \
  voice-control-server:latest

# Scale service
docker service scale voice-control-server=5
```

### Vertical Scaling

#### Resource Allocation
```bash
# Docker resource limits
docker run \
  --cpus="4.0" \
  --memory="8g" \
  --memory-swap="8g" \
  --memory-reservation="6g" \
  voice-control-server:latest

# Kubernetes resource limits
resources:
  requests:
    memory: "4Gi"
    cpu: "2"
  limits:
    memory: "8Gi"
    cpu: "4"
```

### Database Scaling

#### Read Replicas
```python
# Configure read replicas
DATABASE_CONFIG = {
    "primary": "postgresql://user:pass@primary-db:5432/voice_control",
    "replicas": [
        "postgresql://user:pass@replica1-db:5432/voice_control",
        "postgresql://user:pass@replica2-db:5432/voice_control"
    ]
}

# Read/write splitting
class DatabaseRouter:
    def db_for_read(self, model, **hints):
        # Route reads to replicas
        return random.choice(DATABASE_CONFIG["replicas"])
    
    def db_for_write(self, model, **hints):
        # Route writes to primary
        return DATABASE_CONFIG["primary"]
```

## Benchmarking

### Performance Testing Script

```python
# scripts/benchmark.py
import asyncio
import time
import statistics
import aiohttp
import json

class PerformanceBenchmark:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
    
    async def benchmark_health_check(self, num_requests=100):
        """Benchmark health check endpoint"""
        print(f"Benchmarking health check ({num_requests} requests)...")
        
        latencies = []
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            for _ in range(num_requests):
                request_start = time.time()
                async with session.get(f"{self.base_url}/health") as response:
                    await response.text()
                    request_end = time.time()
                    latencies.append(request_end - request_start)
        
        total_time = time.time() - start_time
        self.results["health_check"] = {
            "total_requests": num_requests,
            "total_time": total_time,
            "requests_per_second": num_requests / total_time,
            "avg_latency": statistics.mean(latencies),
            "min_latency": min(latencies),
            "max_latency": max(latencies),
            "p95_latency": statistics.quantiles(latencies, n=20)[18],
            "p99_latency": statistics.quantiles(latencies, n=100)[98]
        }
        
        print(f"  RPS: {self.results['health_check']['requests_per_second']:.2f}")
        print(f"  Avg latency: {self.results['health_check']['avg_latency']*1000:.2f}ms")
    
    async def benchmark_websocket(self, num_connections=10, duration=30):
        """Benchmark WebSocket connections"""
        print(f"Benchmarking WebSocket ({num_connections} connections, {duration}s)...")
        
        connection_results = []
        
        async def single_connection_test():
            try:
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(f"{self.base_url.replace('http', 'ws')}/ws") as ws:
                        connection_start = time.time()
                        
                        # Send connection request
                        await ws.send_json({
                            "type": "connection_request",
                            "data": {
                                "client_id": f"benchmark_{int(time.time())}",
                                "capabilities": ["stt", "llm"]
                            }
                        })
                        
                        # Keep connection alive
                        end_time = time.time() + duration
                        message_count = 0
                        
                        async for msg in ws:
                            message_count += 1
                            if time.time() >= end_time:
                                break
                        
                        connection_end = time.time()
                        return {
                            "connection_time": connection_start - connection_start,
                            "messages_processed": message_count,
                            "duration": connection_end - connection_start
                        }
            except Exception as e:
                return {"error": str(e)}
        
        # Run multiple connections concurrently
        tasks = [single_connection_test() for _ in range(num_connections)]
        results = await asyncio.gather(*tasks)
        
        successful_connections = [r for r in results if "error" not in r]
        
        self.results["websocket"] = {
            "total_connections": num_connections,
            "successful_connections": len(successful_connections),
            "avg_duration": statistics.mean([r["duration"] for r in successful_connections]),
            "total_messages": sum(r["messages_processed"] for r in successful_connections),
            "messages_per_second": sum(r["messages_processed"] for r in successful_connections) / duration
        }
        
        print(f"  Successful connections: {len(successful_connections)}/{num_connections}")
        print(f"  Messages/second: {self.results['websocket']['messages_per_second']:.2f}")
    
    async def benchmark_load(self, concurrent_users=50, requests_per_user=10):
        """Benchmark system under load"""
        print(f"Running load test ({concurrent_users} users, {requests_per_user} requests each)...")
        
        async def user_session(user_id):
            async with aiohttp.ClientSession() as session:
                latencies = []
                for i in range(requests_per_user):
                    start = time.time()
                    try:
                        async with session.get(f"{self.base_url}/api/status") as response:
                            await response.text()
                            latency = time.time() - start
                            latencies.append(latency)
                    except Exception as e:
                        print(f"User {user_id}, request {i} failed: {e}")
                
                return latencies
        
        start_time = time.time()
        tasks = [user_session(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        all_latencies = []
        for user_latencies in results:
            all_latencies.extend(user_latencies)
        
        self.results["load_test"] = {
            "concurrent_users": concurrent_users,
            "total_requests": len(all_latencies),
            "total_time": total_time,
            "requests_per_second": len(all_latencies) / total_time,
            "avg_latency": statistics.mean(all_latencies),
            "p95_latency": statistics.quantiles(all_latencies, n=20)[18],
            "error_rate": (len(tasks) * requests_per_user - len(all_latencies)) / (len(tasks) * requests_per_user)
        }
        
        print(f"  RPS: {self.results['load_test']['requests_per_second']:.2f}")
        print(f"  Error rate: {self.results['load_test']['error_rate']*100:.2f}%")
    
    def generate_report(self):
        """Generate performance report"""
        print("\n" + "="*50)
        print("PERFORMANCE BENCHMARK REPORT")
        print("="*50)
        
        for test_name, results in self.results.items():
            print(f"\n{test_name.upper().replace('_', ' ')}:")
            for metric, value in results.items():
                if isinstance(value, float):
                    print(f"  {metric}: {value:.3f}")
                else:
                    print(f"  {metric}: {value}")
        
        # Performance score calculation
        if "health_check" in self.results:
            rps_score = min(self.results["health_check"]["requests_per_second"] / 100, 1.0) * 100
            latency_score = max(0, (1000 - self.results["health_check"]["avg_latency"] * 1000) / 1000) * 100
            
            overall_score = (rps_score + latency_score) / 2
            print(f"\nPERFORMANCE SCORE: {overall_score:.1f}/100")
            
            if overall_score >= 90:
                print("RATING: Excellent ⚡")
            elif overall_score >= 80:
                print("RATING: Very Good ✅")
            elif overall_score >= 70:
                print("RATING: Good ⚠️")
            else:
                print("RATING: Needs Optimization 🔧")

async def main():
    benchmark = PerformanceBenchmark()
    
    # Run benchmarks
    await benchmark.benchmark_health_check(200)
    await asyncio.sleep(1)
    await benchmark.benchmark_websocket(20, 15)
    await asyncio.sleep(1)
    await benchmark.benchmark_load(100, 20)
    
    # Generate report
    benchmark.generate_report()

if __name__ == "__main__":
    asyncio.run(main())
```

### Running Benchmarks

```bash
# Run all benchmarks
python scripts/benchmark.py

# Run specific benchmarks
python scripts/benchmark.py --test health_check
python scripts/benchmark.py --test websocket
python scripts/benchmark.py --test load

# Custom parameters
python scripts/benchmark.py --url http://your-server:8000 --concurrent-users 100
```

This comprehensive performance tuning guide provides strategies for optimizing every aspect of the Voice Control Ecosystem. Regular benchmarking and monitoring will help maintain optimal performance as your system scales and usage patterns evolve.
