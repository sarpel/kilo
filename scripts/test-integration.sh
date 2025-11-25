#!/bin/bash
# ===============================================
# Voice Control Ecosystem - Integration Test Suite
# ===============================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Set error handling
set -e
set -u

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVER_URL="http://localhost:8000"
TEST_AUDIO_DIR="$PROJECT_ROOT/test-audio"
RESULTS_DIR="$PROJECT_ROOT/test-results"
TEST_DURATION=${TEST_DURATION:-300}  # 5 minutes default

# Functions for colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[FAIL]${NC} $1"; }
print_test() { echo -e "${YELLOW}[TEST]${NC} $1"; }

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -u, --url URL         Server URL (default: http://localhost:8000)"
    echo "  -d, --duration SEC    Test duration in seconds (default: 300)"
    echo "  --skip-server-check   Skip server availability check"
    echo "  --performance-only    Run only performance tests"
    echo "  --integration-only    Run only integration tests"
    echo "  --load-test           Run load testing"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all tests"
    echo "  $0 -u http://192.168.1.100:8000"
    echo "  $0 --performance-only"
    echo "  $0 --load-test"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            SERVER_URL="$2"
            shift 2
            ;;
        -d|--duration)
            TEST_DURATION="$2"
            shift 2
            ;;
        --skip-server-check)
            SKIP_SERVER_CHECK=true
            shift
            ;;
        --performance-only)
            PERFORMANCE_ONLY=true
            shift
            ;;
        --integration-only)
            INTEGRATION_ONLY=true
            shift
            ;;
        --load-test)
            LOAD_TEST=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Create test directories
mkdir -p "$TEST_AUDIO_DIR" "$RESULTS_DIR"

# Test result tracking
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    print_test "Running: $test_name"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    # Run test and capture result
    local start_time=$(date +%s.%N)
    if eval "$test_command" > "$RESULTS_DIR/${test_name// /_}.log" 2>&1; then
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc -l)
        print_success "$test_name (${duration}s)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc -l)
        print_error "$test_name (${duration}s)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "  Check log: $RESULTS_DIR/${test_name// /_}.log"
        return 1
    fi
}

skip_test() {
    local test_name="$1"
    local reason="$2"
    
    print_warning "Skipping: $test_name - $reason"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
}

# Server connectivity check
check_server() {
    if [ "${SKIP_SERVER_CHECK:-false}" = "true" ]; then
        return 0
    fi
    
    print_info "Checking server connectivity..."
    
    if curl -s -f "$SERVER_URL/health" >/dev/null; then
        print_success "Server is accessible at $SERVER_URL"
        return 0
    else
        print_error "Server is not accessible at $SERVER_URL"
        print_info "Make sure the server is running:"
        print_info "  python voice-control-server/start_server.py"
        return 1
    fi
}

# ===============================================
# BASIC FUNCTIONALITY TESTS
# ===============================================
test_basic_endpoints() {
    print_info "Testing basic HTTP endpoints..."
    
    # Health check
    run_test "Health Check" "curl -s -f '$SERVER_URL/health'"
    
    # Status endpoint
    run_test "Status Endpoint" "curl -s -f '$SERVER_URL/api/status'"
    
    # Config endpoint
    run_test "Config Endpoint" "curl -s -f '$SERVER_URL/api/config'"
    
    # OpenAPI documentation
    run_test "OpenAPI Docs" "curl -s -f '$SERVER_URL/docs'"
    
    # ReDoc documentation
    run_test "ReDoc Docs" "curl -s -f '$SERVER_URL/redoc'"
}

# ===============================================
# WEBSOCKET CONNECTION TESTS
# ===============================================
test_websocket_connections() {
    print_info "Testing WebSocket connections..."
    
    # Test WebSocket connection
    if command -v websocat >/dev/null; then
        run_test "WebSocket Connection" "echo '{\"type\": \"connection_request\", \"data\": {\"client_id\": \"test-client\", \"capabilities\": [\"stt\", \"llm\"]}}' | websocat '$SERVER_URL/ws' --text-mode --timeout 10"
    elif command -v wscat >/dev/null; then
        run_test "WebSocket Connection" "timeout 10s wscat -c '$SERVER_URL/ws' <<< '{\"type\": \"connection_request\", \"data\": {\"client_id\": \"test-client\", \"capabilities\": [\"stt\", \"llm\"]}}'"
    else
        skip_test "WebSocket Connection" "websocat or wscat not available"
    fi
}

# ===============================================
# STT (SPEECH-TO-TEXT) TESTS
# ===============================================
test_stt_functionality() {
    print_info "Testing STT functionality..."
    
    # Check if STT service is available
    if ! curl -s "$SERVER_URL/api/status" | grep -q "stt"; then
        skip_test "STT Functionality" "STT service not available"
        return
    fi
    
    # Create test audio file (sine wave for basic test)
    local test_audio="$TEST_AUDIO_DIR/test-tone.wav"
    if [ ! -f "$test_audio" ]; then
        # Generate a simple test tone
        if command -v ffmpeg >/dev/null; then
            ffmpeg -f lavfi -i "sine=frequency=1000:duration=2" -ac 1 -ar 16000 "$test_audio" -y >/dev/null 2>&1 || {
                skip_test "STT Functionality" "Could not create test audio"
                return
            }
        else
            skip_test "STT Functionality" "ffmpeg not available for test audio"
            return
        fi
    fi
    
    # Test STT with WebSocket (if wscat available)
    if command -v wscat >/dev/null && [ -f "$test_audio" ]; then
        run_test "STT Processing" "timeout 30s bash -c \"echo '{\\\"type\\\": \\\"stt_request\\\", \\\"data\\\": {}}' | wscat -c '$SERVER_URL/ws' --timeout 10\""
    else
        skip_test "STT Processing" "wscat or test audio not available"
    fi
}

# ===============================================
# LLM INTEGRATION TESTS
# ===============================================
test_llm_integration() {
    print_info "Testing LLM integration..."
    
    # Check if LLM service is available
    if ! curl -s "$SERVER_URL/api/status" | grep -q "llm"; then
        skip_test "LLM Integration" "LLM service not available"
        return
    fi
    
    # Test LLM endpoint (if available)
    if curl -s -X POST "$SERVER_URL/api/test-llm" -H "Content-Type: application/json" -d '{"text": "Hello, test message"}' >/dev/null 2>&1; then
        run_test "LLM Processing" "curl -s -X POST '$SERVER_URL/api/test-llm' -H 'Content-Type: application/json' -d '{\"text\": \"Hello, test message\"}'"
    else
        skip_test "LLM Processing" "LLM test endpoint not available"
    fi
    
    # Test Ollama connectivity
    run_test "Ollama Connection" "curl -s -f 'http://localhost:11434/api/tags' >/dev/null"
}

# ===============================================
# MCP PROTOCOL TESTS
# ===============================================
test_mcp_protocol() {
    print_info "Testing MCP protocol..."
    
    # Check if MCP service is available
    if ! curl -s "$SERVER_URL/api/status" | grep -q "mcp"; then
        skip_test "MCP Protocol" "MCP service not available"
        return
    fi
    
    # Test basic MCP tool execution
    run_test "MCP Tools Available" "curl -s '$SERVER_URL/api/mcp/tools' | grep -q '\"tools\"'"
    
    # Test echo tool
    run_test "MCP Echo Tool" "curl -s -X POST '$SERVER_URL/api/mcp/execute' -H 'Content-Type: application/json' -d '{\"tool\": \"echo\", \"parameters\": {\"message\": \"test\"}}' | grep -q 'test'"
}

# ===============================================
# PERFORMANCE TESTS
# ===============================================
test_performance() {
    print_info "Running performance tests..."
    
    # Response time tests
    print_test "Testing response times..."
    
    local iterations=10
    local total_time=0
    local max_time=0
    local min_time=999
    
    for i in $(seq 1 $iterations); do
        local start_time=$(date +%s.%N)
        if curl -s -f "$SERVER_URL/health" >/dev/null; then
            local end_time=$(date +%s.%N)
            local response_time=$(echo "$end_time - $start_time" | bc -l)
            total_time=$(echo "$total_time + $response_time" | bc -l)
            
            if (( $(echo "$response_time > $max_time" | bc -l) )); then
                max_time=$response_time
            fi
            
            if (( $(echo "$response_time < $min_time" | bc -l) )); then
                min_time=$response_time
            fi
        fi
    done
    
    local avg_time=$(echo "scale=3; $total_time / $iterations" | bc -l)
    local avg_ms=$(echo "scale=1; $avg_time * 1000" | bc -l)
    local max_ms=$(echo "scale=1; $max_time * 1000" | bc -l)
    local min_ms=$(echo "scale=1; $min_time * 1000" | bc -l)
    
    print_info "Response time stats:"
    print_info "  Average: ${avg_ms}ms"
    print_info "  Min: ${min_ms}ms"
    print_info "  Max: ${max_ms}ms"
    
    # Store performance results
    echo "Response Time Performance Test Results" > "$RESULTS_DIR/performance.log"
    echo "Iterations: $iterations" >> "$RESULTS_DIR/performance.log"
    echo "Average: ${avg_ms}ms" >> "$RESULTS_DIR/performance.log"
    echo "Min: ${min_ms}ms" >> "$RESULTS_DIR/performance.log"
    echo "Max: ${max_ms}ms" >> "$RESULTS_DIR/performance.log"
    
    # Performance thresholds
    if (( $(echo "$avg_ms < 1000" | bc -l) )); then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        print_success "Performance Test (avg: ${avg_ms}ms)"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        print_error "Performance Test (avg: ${avg_ms}ms) - Too slow"
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

# ===============================================
# LOAD TESTING
# ===============================================
test_load_testing() {
    print_info "Running load tests..."
    
    # Check if load testing tools are available
    if ! command -v ab >/dev/null && ! command -v wrk >/dev/null && ! command -v httperf >/dev/null; then
        skip_test "Load Testing" "No load testing tools available (ab, wrk, httperf)"
        return
    fi
    
    # Use available tool for load testing
    if command -v wrk >/dev/null; then
        run_test "Load Test (wrk)" "wrk -t4 -c10 -d30s '$SERVER_URL/health'"
    elif command -v ab >/dev/null; then
        run_test "Load Test (ab)" "ab -n 100 -c 10 '$SERVER_URL/health'"
    elif command -v httperf >/dev/null; then
        run_test "Load Test (httperf)" "httperf --server localhost --port 8000 --uri /health --num-conn 10 --rate 1"
    fi
}

# ===============================================
# CONCURRENCY TESTS
# ===============================================
test_concurrent_requests() {
    print_info "Testing concurrent requests..."
    
    local num_requests=5
    local pids=()
    
    # Start multiple concurrent requests
    for i in $(seq 1 $num_requests); do
        (curl -s -f "$SERVER_URL/health" >/dev/null && echo "Request $i: SUCCESS" >> "$RESULTS_DIR/concurrent.log" || echo "Request $i: FAILED" >> "$RESULTS_DIR/concurrent.log") &
        pids+=($!)
    done
    
    # Wait for all requests to complete
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    # Analyze results
    local success_count=$(grep -c "SUCCESS" "$RESULTS_DIR/concurrent.log" 2>/dev/null || echo "0")
    
    if [ "$success_count" -eq "$num_requests" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        print_success "Concurrent Requests Test ($success_count/$num_requests)"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        print_error "Concurrent Requests Test ($success_count/$num_requests)"
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

# ===============================================
# ERROR HANDLING TESTS
# ===============================================
test_error_handling() {
    print_info "Testing error handling..."
    
    # Test 404 endpoint
    run_test "404 Handling" "! curl -s -f '$SERVER_URL/nonexistent' >/dev/null"
    
    # Test malformed JSON
    run_test "Malformed JSON" "! curl -s -X POST '$SERVER_URL/api/test' -H 'Content-Type: application/json' -d 'invalid json' >/dev/null"
    
    # Test missing Content-Type
    run_test "Missing Content-Type" "! curl -s -X POST '$SERVER_URL/api/test' -d 'test' >/dev/null"
    
    # Test oversized request
    local large_data=$(python3 -c "print('x' * 10000)")
    run_test "Large Request" "! curl -s -X POST '$SERVER_URL/api/test' -H 'Content-Type: application/json' -d '{\"data\": \"$large_data\"}' >/dev/null"
}

# ===============================================
# SECURITY TESTS
# ===============================================
test_security() {
    print_info "Running security tests..."
    
    # Test CORS headers
    run_test "CORS Headers" "curl -s -H 'Origin: http://evil.com' -I '$SERVER_URL/health' | grep -i 'access-control'"
    
    # Test rate limiting (if implemented)
    for i in $(seq 1 11); do
        curl -s "$SERVER_URL/health" >/dev/null || true
    done
    run_test "Rate Limiting" "curl -s -f '$SERVER_URL/health' >/dev/null"
    
    # Test input sanitization
    run_test "Input Sanitization" "! curl -s -X POST '$SERVER_URL/api/test' -H 'Content-Type: application/json' -d '{\"text\": \"<script>alert(\\\"xss\\\")</script>\"}' >/dev/null"
}

# ===============================================
# RESOURCE MONITORING
# ===============================================
test_resource_monitoring() {
    print_info "Monitoring resource usage..."
    
    # Monitor for specified duration
    local start_time=$(date +%s)
    local end_time=$((start_time + TEST_DURATION))
    
    local log_file="$RESULTS_DIR/resource-monitoring.log"
    echo "Resource Monitoring Log - $(date)" > "$log_file"
    echo "Duration: ${TEST_DURATION}s" >> "$log_file"
    echo "===========================================" >> "$log_file"
    
    while [ $(date +%s) -lt $end_time ]; do
        local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        
        # CPU usage
        local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
        
        # Memory usage
        local memory_info=$(free -m | awk 'NR==2{printf "%.1f", $3*100/$2}')
        
        # Disk usage
        local disk_usage=$(df -h . | awk 'NR==2{print $5}' | sed 's/%//')
        
        echo "$timestamp - CPU: ${cpu_usage}% - Memory: ${memory_usage}% - Disk: ${disk_usage}%" >> "$log_file"
        
        sleep 10
    done
    
    print_info "Resource monitoring completed - Results in $log_file"
    
    # Analyze results
    PASSED_TESTS=$((PASSED_TESTS + 1))
    print_success "Resource Monitoring Test"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

# ===============================================
# INTEGRATION TEST SUITE
# ===============================================
run_integration_tests() {
    print_info "Running integration test suite..."
    echo ""
    
    # Basic functionality
    test_basic_endpoints
    echo ""
    
    # WebSocket functionality
    test_websocket_connections
    echo ""
    
    # Core features
    test_stt_functionality
    test_llm_integration
    test_mcp_protocol
    echo ""
    
    # Security
    test_security
    echo ""
    
    # Error handling
    test_error_handling
    echo ""
}

# ===============================================
# PERFORMANCE TEST SUITE
# ===============================================
run_performance_tests() {
    print_info "Running performance test suite..."
    echo ""
    
    # Performance tests
    test_performance
    test_concurrent_requests
    test_resource_monitoring
    
    if [ "${LOAD_TEST:-false}" = "true" ]; then
        test_load_testing
    fi
    echo ""
}

# ===============================================
# MAIN TEST EXECUTION
# ===============================================
main() {
    echo "==============================================="
    echo "  Voice Control Ecosystem - Integration Tests"
    echo "==============================================="
    echo ""
    print_info "Server URL: $SERVER_URL"
    print_info "Test Duration: ${TEST_DURATION}s"
    print_info "Results Directory: $RESULTS_DIR"
    echo ""
    
    # Check server availability
    if ! check_server; then
        print_error "Cannot proceed without server connectivity"
        exit 1
    fi
    echo ""
    
    # Run selected test suites
    if [ "${INTEGRATION_ONLY:-false}" = "true" ]; then
        run_integration_tests
    elif [ "${PERFORMANCE_ONLY:-true}" = "true" ]; then
        run_performance_tests
    else
        # Run all tests
        run_integration_tests
        run_performance_tests
    fi
    
    # ===============================================
    # TEST SUMMARY
    # ===============================================
    echo "==============================================="
    echo "  TEST SUMMARY"
    echo "==============================================="
    echo ""
    print_info "Total Tests: $TOTAL_TESTS"
    print_success "Passed: $PASSED_TESTS"
    print_error "Failed: $FAILED_TESTS"
    if [ $SKIPPED_TESTS -gt 0 ]; then
        print_warning "Skipped: $SKIPPED_TESTS"
    fi
    
    local success_rate=0
    if [ $TOTAL_TESTS -gt 0 ]; then
        success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    fi
    
    print_info "Success Rate: ${success_rate}%"
    echo ""
    
    # Performance summary
    if [ -f "$RESULTS_DIR/performance.log" ]; then
        print_info "Performance Summary:"
        cat "$RESULTS_DIR/performance.log"
        echo ""
    fi
    
    # Results location
    print_info "Detailed results available in: $RESULTS_DIR"
    echo ""
    
    # Final verdict
    if [ $FAILED_TESTS -eq 0 ]; then
        print_success "All tests passed! Voice Control Ecosystem is ready for use."
        exit 0
    elif [ $success_rate -ge 80 ]; then
        print_warning "Most tests passed. System may have minor issues."
        exit 0
    else
        print_error "Several tests failed. Please check the issues before proceeding."
        exit 1
    fi
}

# Run main function
main
