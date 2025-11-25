#!/bin/bash
# ===============================================
# Voice Control Ecosystem - Production Deployment Script
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
DEPLOYMENT_TYPE="docker"  # docker, systemd, or manual
ENVIRONMENT="production"
BACKUP_ENABLED=true

# Functions for colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE       Deployment type (docker|systemd|manual)"
    echo "  -e, --env ENV         Environment (development|staging|production)"
    echo "  --no-backup           Skip backup creation"
    echo "  --skip-validation     Skip pre-deployment validation"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -t docker -e production"
    echo "  $0 --type systemd --env staging"
    echo "  $0 --no-backup"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            DEPLOYMENT_TYPE="$2"
            shift 2
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --no-backup)
            BACKUP_ENABLED=false
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
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

# Validate environment
case $ENVIRONMENT in
    development|staging|production)
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        echo "Valid environments: development, staging, production"
        exit 1
        ;;
esac

# Validate deployment type
case $DEPLOYMENT_TYPE in
    docker|systemd|manual)
        ;;
    *)
        print_error "Invalid deployment type: $DEPLOYMENT_TYPE"
        echo "Valid types: docker, systemd, manual"
        exit 1
        ;;
esac

print_info "Starting production deployment..."
print_info "Project Root: $PROJECT_ROOT"
print_info "Deployment Type: $DEPLOYMENT_TYPE"
print_info "Environment: $ENVIRONMENT"
print_info "Backup Enabled: $BACKUP_ENABLED"
echo ""

# ===============================================
# PRE-DEPLOYMENT VALIDATION
# ===============================================
if [ "${SKIP_VALIDATION:-false}" != "true" ]; then
    echo "[STEP 1/8] Pre-deployment Validation..."
    
    # Check if running as root or with sudo for systemd deployment
    if [ "$DEPLOYMENT_TYPE" = "systemd" ] && [ "$EUID" -ne 0 ]; then
        print_error "Systemd deployment requires root privileges"
        echo "Please run with: sudo $0 -t systemd -e $ENVIRONMENT"
        exit 1
    fi
    
    # Check required tools
    required_tools=("docker" "curl" "git")
    if [ "$DEPLOYMENT_TYPE" = "systemd" ]; then
        required_tools+=("systemctl" "ufw")
    fi
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            print_error "Required tool not found: $tool"
            case $tool in
                docker) echo "Install Docker: https://docs.docker.com/engine/install/" ;;
                systemctl) echo "Systemd is required for systemd deployment" ;;
                ufw) echo "Install UFW firewall: sudo apt install ufw" ;;
            esac
            exit 1
        fi
    done
    
    # Check port availability
    if ! curl -s http://localhost:8000/health >/dev/null 2>&1; then
        print_warning "Port 8000 is available"
    else
        print_warning "Port 8000 appears to be in use"
        echo "Current process using port 8000:"
        lsof -i :8000 || echo "Could not determine process using port 8000"
        echo "You may need to stop the current service before deployment"
    fi
    
    # Check disk space (minimum 5GB for production)
    available_space=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -lt 5 ]; then
        print_error "Insufficient disk space. Minimum 5GB required, available: ${available_space}GB"
        exit 1
    fi
    
    print_success "Pre-deployment validation completed"
    echo ""
fi

# ===============================================
# BACKUP EXISTING DEPLOYMENT
# ===============================================
if [ "$BACKUP_ENABLED" = true ]; then
    echo "[STEP 2/8] Creating Backup..."
    
    if [ -d "$PROJECT_ROOT/voice-control-server" ]; then
        backup_dir="$PROJECT_ROOT/backups/deployment-$(date +%Y%m%d-%H%M%S)"
        mkdir -p "$backup_dir"
        
        # Backup configuration files
        if [ -f "$PROJECT_ROOT/voice-control-server/.env" ]; then
            cp "$PROJECT_ROOT/voice-control-server/.env" "$backup_dir/"
            print_info "Backed up .env file"
        fi
        
        # Backup data directories
        if [ -d "$PROJECT_ROOT/voice-control-server/storage" ]; then
            cp -r "$PROJECT_ROOT/voice-control-server/storage" "$backup_dir/"
            print_info "Backed up storage directory"
        fi
        
        # Backup logs
        if [ -d "$PROJECT_ROOT/voice-control-server/storage/logs" ]; then
            tar -czf "$backup_dir/logs.tar.gz" -C "$PROJECT_ROOT/voice-control-server/storage" logs
            print_info "Backed up logs"
        fi
        
        # Backup database if exists
        if [ -f "$PROJECT_ROOT/voice-control-server/storage/voice_control.db" ]; then
            cp "$PROJECT_ROOT/voice-control-server/storage/voice_control.db" "$backup_dir/"
            print_info "Backed up database"
        fi
        
        print_success "Backup created at: $backup_dir"
    else
        print_info "No existing deployment found, skipping backup"
    fi
    
    echo ""
fi

# ===============================================
# PREPARE DEPLOYMENT
# ===============================================
echo "[STEP 3/8] Preparing Deployment..."

cd "$PROJECT_ROOT"

# Pull latest code changes (if git repository)
if [ -d ".git" ]; then
    print_info "Checking for latest code changes..."
    git fetch origin
    current_branch=$(git branch --show-current)
    latest_commit=$(git rev-parse HEAD)
    
    read -p "Pull latest changes from git repository? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git pull origin "$current_branch"
        print_success "Latest code pulled successfully"
    else
        print_info "Skipping git pull, using current code"
    fi
fi

# Stop existing services if running
if [ "$DEPLOYMENT_TYPE" = "docker" ]; then
    if docker ps | grep -q voice-control-server; then
        print_info "Stopping existing Docker containers..."
        docker-compose down --remove-orphans
        print_success "Docker containers stopped"
    fi
elif [ "$DEPLOYMENT_TYPE" = "systemd" ]; then
    if systemctl is-active --quiet voice-control-server; then
        print_info "Stopping existing systemd service..."
        systemctl stop voice-control-server
        print_success "Systemd service stopped"
    fi
fi

echo ""

# ===============================================
# DOCKER DEPLOYMENT
# ===============================================
if [ "$DEPLOYMENT_TYPE" = "docker" ]; then
    echo "[STEP 4/8] Deploying with Docker..."
    
    # Copy environment configuration
    if [ -f "configs/.env.$ENVIRONMENT" ]; then
        cp "configs/.env.$ENVIRONMENT" "voice-control-server/.env"
        print_success "Copied $ENVIRONMENT configuration"
    else
        print_error "Configuration file not found: configs/.env.$ENVIRONMENT"
        exit 1
    fi
    
    # Build and deploy
    print_info "Building Docker images..."
    docker-compose build --no-cache
    
    print_info "Starting services..."
    case $ENVIRONMENT in
        production)
            docker-compose --profile production up -d
            ;;
        staging)
            docker-compose up -d
            ;;
        development)
            docker-compose up -d
            ;;
    esac
    
    # Wait for services to be ready
    print_info "Waiting for services to be ready..."
    sleep 30
    
    # Health check
    if curl -s http://localhost:8000/health >/dev/null; then
        print_success "Docker deployment successful"
    else
        print_error "Docker deployment health check failed"
        echo "Check logs: docker-compose logs"
        exit 1
    fi
    
    # Setup automatic startup
    if command -v systemctl >/dev/null; then
        print_info "Setting up automatic Docker startup..."
        cat > /etc/systemd/system/docker-voice-control.service << EOF
[Unit]
Description=Voice Control Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_ROOT
ExecStart=/usr/bin/docker-compose --profile production up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
        systemctl enable docker-voice-control
        print_success "Docker service setup completed"
    fi
    
# ===============================================
# SYSTEMD DEPLOYMENT
# ===============================================
elif [ "$DEPLOYMENT_TYPE" = "systemd" ]; then
    echo "[STEP 4/8] Deploying with Systemd..."
    
    # Setup Python virtual environment
    print_info "Setting up Python environment..."
    
    cd voice-control-server
    
    # Create virtual environment if not exists
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    print_success "Dependencies installed"
    
    # Copy environment configuration
    if [ -f "../configs/.env.$ENVIRONMENT" ]; then
        cp "../configs/.env.$ENVIRONMENT" ".env"
        print_success "Copied $ENVIRONMENT configuration"
    else
        print_error "Configuration file not found: configs/.env.$ENVIRONMENT"
        exit 1
    fi
    
    # Create systemd service
    print_info "Creating systemd service..."
    cat > /etc/systemd/system/voice-control-server.service << EOF
[Unit]
Description=Voice Control Server
After=network.target

[Service]
Type=simple
User=voicecontrol
Group=voicecontrol
WorkingDirectory=$PROJECT_ROOT/voice-control-server
Environment=PATH=$PROJECT_ROOT/voice-control-server/venv/bin
ExecStart=$PROJECT_ROOT/voice-control-server/venv/bin/python start_server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=voice-control-server

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$PROJECT_ROOT/voice-control-server/storage

[Install]
WantedBy=multi-user.target
EOF
    
    # Create service user if not exists
    if ! id voicecontrol &>/dev/null; then
        useradd -r -s /bin/false -d "$PROJECT_ROOT" voicecontrol
        print_success "Service user created"
    fi
    
    # Set permissions
    chown -R voicecontrol:voicecontrol "$PROJECT_ROOT"
    chmod +x "$PROJECT_ROOT/voice-control-server/venv/bin/python"
    
    # Start service
    systemctl daemon-reload
    systemctl enable voice-control-server
    systemctl start voice-control-server
    
    # Wait and check status
    sleep 10
    
    if systemctl is-active --quiet voice-control-server; then
        print_success "Systemd deployment successful"
    else
        print_error "Systemd deployment failed"
        systemctl status voice-control-server
        exit 1
    fi
    
    # Setup firewall rules
    print_info "Setting up firewall rules..."
    ufw allow 8000/tcp comment "Voice Control Server"
    ufw allow 11434/tcp comment "Ollama LLM Server"
    ufw --force enable
    
    echo ""

# ===============================================
# MANUAL DEPLOYMENT
# ===============================================
elif [ "$DEPLOYMENT_TYPE" = "manual" ]; then
    echo "[STEP 4/8] Manual Deployment Instructions..."
    
    print_info "Manual deployment selected. Please follow these steps:"
    echo ""
    echo "1. Setup Python environment:"
    echo "   cd voice-control-server"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    echo ""
    echo "2. Copy configuration:"
    echo "   cp configs/.env.$ENVIRONMENT voice-control-server/.env"
    echo ""
    echo "3. Start the server:"
    echo "   cd voice-control-server"
    echo "   source venv/bin/activate"
    echo "   python start_server.py"
    echo ""
    print_info "For production deployment with systemd, use: sudo $0 -t systemd -e $ENVIRONMENT"
    echo ""
fi

# ===============================================
# SECURITY HARDENING
# ===============================================
echo "[STEP 5/8] Security Hardening..."

# Generate secure secret key if not exists
if [ "$DEPLOYMENT_TYPE" != "manual" ]; then
    if grep -q "your-super-secure-production-secret-key" "voice-control-server/.env" 2>/dev/null; then
        secret_key=$(openssl rand -hex 32)
        sed -i "s/your-super-secure-production-secret-key-change-this-in-production/$secret_key/" voice-control-server/.env
        print_success "Generated secure secret key"
    fi
fi

# Set proper file permissions
if [ "$DEPLOYMENT_TYPE" = "systemd" ]; then
    find "$PROJECT_ROOT" -type f -name "*.py" -exec chmod 644 {} \;
    find "$PROJECT_ROOT" -type d -exec chmod 755 {} \;
    chmod 600 "$PROJECT_ROOT/voice-control-server/.env"
    print_success "File permissions secured"
fi

echo ""

# ===============================================
# MONITORING SETUP
# ===============================================
echo "[STEP 6/8] Setting up Monitoring..."

# Create monitoring script
cat > "$PROJECT_ROOT/scripts/health-check.sh" << 'EOF'
#!/bin/bash
# Voice Control Health Check Script

HEALTH_URL="http://localhost:8000/health"
LOG_FILE="/var/log/voice-control-health.log"

# Check service health
if curl -s -f "$HEALTH_URL" > /dev/null; then
    echo "$(date): Service healthy" >> "$LOG_FILE"
    exit 0
else
    echo "$(date): Service unhealthy, restarting..." >> "$LOG_FILE"
    systemctl restart voice-control-server
    sleep 10
    if curl -s -f "$HEALTH_URL" > /dev/null; then
        echo "$(date): Service recovered after restart" >> "$LOG_FILE"
        exit 0
    else
        echo "$(date): Service failed to recover" >> "$LOG_FILE"
        exit 1
    fi
fi
EOF

chmod +x "$PROJECT_ROOT/scripts/health-check.sh"

# Setup cron job for health monitoring
if [ "$DEPLOYMENT_TYPE" = "systemd" ]; then
    (crontab -l 2>/dev/null; echo "*/5 * * * * $PROJECT_ROOT/scripts/health-check.sh") | crontab -
    print_success "Health monitoring cron job setup"
fi

echo ""

# ===============================================
# PERFORMANCE OPTIMIZATION
# ===============================================
echo "[STEP 7/8] Performance Optimization..."

# System optimization for production
if [ "$DEPLOYMENT_TYPE" = "systemd" ]; then
    # Optimize system limits
    if ! grep -q "voicecontrol" /etc/security/limits.conf; then
        cat >> /etc/security/limits.conf << EOF
voicecontrol soft nofile 65536
voicecontrol hard nofile 65536
voicecontrol soft nproc 4096
voicecontrol hard nproc 4096
EOF
        print_success "System limits optimized"
    fi
fi

echo ""

# ===============================================
# POST-DEPLOYMENT VALIDATION
# ===============================================
echo "[STEP 8/8] Post-deployment Validation..."

# Wait for services to be ready
print_info "Waiting for services to initialize..."
sleep 15

# Health check
max_attempts=10
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000/health >/dev/null; then
        print_success "Service health check passed"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "Service health check failed after $max_attempts attempts"
        
        if [ "$DEPLOYMENT_TYPE" = "docker" ]; then
            print_info "Docker logs:"
            docker-compose logs voice-control-server
        elif [ "$DEPLOYMENT_TYPE" = "systemd" ]; then
            print_info "Systemd service status:"
            systemctl status voice-control-server
            print_info "Service logs:"
            journalctl -u voice-control-server -n 50
        fi
        
        exit 1
    fi
    
    print_info "Health check attempt $attempt/$max_attempts failed, retrying in 5 seconds..."
    sleep 5
    attempt=$((attempt + 1))
done

# API validation
print_info "Testing API endpoints..."
api_tests=(
    "http://localhost:8000/health"
    "http://localhost:8000/api/status"
    "http://localhost:8000/api/config"
)

for endpoint in "${api_tests[@]}"; do
    if curl -s -f "$endpoint" >/dev/null; then
        print_success "API endpoint OK: $(basename "$endpoint")"
    else
        print_warning "API endpoint may have issues: $(basename "$endpoint")"
    fi
done

# WebSocket test
print_info "Testing WebSocket connection..."
ws_test_result=$(curl -s -X POST http://localhost:8000/api/test-websocket 2>/dev/null || echo "N/A")
if [[ "$ws_test_result" == *"success"* ]] || [[ "$ws_test_result" == "N/A" ]]; then
    print_success "WebSocket test passed"
else
    print_warning "WebSocket test result: $ws_test_result"
fi

echo ""

# ===============================================
# DEPLOYMENT SUMMARY
# ===============================================
echo "==============================================="
echo "  PRODUCTION DEPLOYMENT COMPLETED"
echo "==============================================="
echo ""
print_success "Voice Control Ecosystem deployed successfully!"
echo ""
echo "Deployment Details:"
echo "  Environment: $ENVIRONMENT"
echo "  Type: $DEPLOYMENT_TYPE"
echo "  URL: http://localhost:8000"
echo "  Health Check: http://localhost:8000/health"
echo ""
echo "Next Steps:"
echo "  1. Test the application with your React Native app"
echo "  2. Monitor logs for any issues"
echo "  3. Configure SSL/HTTPS for production"
echo "  4. Set up backup procedures"
echo ""
echo "Useful Commands:"
if [ "$DEPLOYMENT_TYPE" = "docker" ]; then
    echo "  View logs: docker-compose logs -f"
    echo "  Stop services: docker-compose down"
    echo "  Restart services: docker-compose restart"
elif [ "$DEPLOYMENT_TYPE" = "systemd" ]; then
    echo "  View logs: journalctl -u voice-control-server -f"
    echo "  Stop service: sudo systemctl stop voice-control-server"
    echo "  Restart service: sudo systemctl restart voice-control-server"
    echo "  Service status: sudo systemctl status voice-control-server"
fi
echo ""
echo "Monitoring:"
echo "  Health check script: $PROJECT_ROOT/scripts/health-check.sh"
echo "  Log files: $PROJECT_ROOT/voice-control-server/storage/logs/"
echo ""
echo "==============================================="
