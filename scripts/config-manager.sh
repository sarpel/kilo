#!/bin/bash
# ===============================================
# Voice Control Ecosystem - Configuration Management
# ===============================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups/config"
CONFIG_DIR="$PROJECT_ROOT/configs"
SERVER_DIR="$PROJECT_ROOT/voice-control-server"
APP_DIR="$PROJECT_ROOT/voice-control-app"

# Functions for colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create necessary directories
mkdir -p "$BACKUP_DIR"

# Usage information
usage() {
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  backup              Create configuration backup"
    echo "  restore             Restore configuration from backup"
    echo "  validate            Validate current configuration"
    echo "  migrate             Migrate configuration between environments"
    echo "  encrypt             Encrypt sensitive configuration"
    echo "  decrypt             Decrypt sensitive configuration"
    echo "  secrets             Manage secrets securely"
    echo ""
    echo "Options:"
    echo "  -e, --env ENV       Environment (development|staging|production)"
    echo "  -b, --backup FILE   Backup file path"
    echo "  --dry-run          Show what would be done without executing"
    echo "  --force            Skip confirmation prompts"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 backup -e production"
    echo "  $0 restore -b backup-20231125.tar.gz -e production"
    echo "  $0 validate -e staging"
    echo "  $0 migrate -e staging --to production"
}

# Parse command line arguments
COMMAND=""
ENVIRONMENT="development"
BACKUP_FILE=""
TO_ENVIRONMENT=""
DRY_RUN=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        backup|restore|validate|migrate|encrypt|decrypt|secrets)
            COMMAND="$1"
            shift
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -b|--backup)
            BACKUP_FILE="$2"
            shift 2
            ;;
        --to)
            TO_ENVIRONMENT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
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

# Check if command is provided
if [ -z "$COMMAND" ]; then
    print_error "No command specified"
    usage
    exit 1
fi

# ===============================================
# BACKUP CONFIGURATION
# ===============================================
backup_config() {
    local backup_name="config-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    print_info "Creating configuration backup..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would create backup at $backup_path"
        return 0
    fi
    
    # Create temporary directory for backup contents
    local temp_dir=$(mktemp -d)
    
    # Backup server configuration
    if [ -f "$SERVER_DIR/.env" ]; then
        mkdir -p "$temp_dir/server"
        cp "$SERVER_DIR/.env" "$temp_dir/server/"
        print_success "Backed up server configuration"
    fi
    
    # Backup app configuration
    if [ -f "$APP_DIR/.env" ]; then
        mkdir -p "$temp_dir/app"
        cp "$APP_DIR/.env" "$temp_dir/app/"
        print_success "Backed up app configuration"
    fi
    
    # Backup environment-specific configs
    if [ -f "$CONFIG_DIR/.env.$ENVIRONMENT" ]; then
        mkdir -p "$temp_dir/environments"
        cp "$CONFIG_DIR/.env.$ENVIRONMENT" "$temp_dir/environments/"
        print_success "Backed up $ENVIRONMENT environment configuration"
    fi
    
    # Backup docker configurations
    if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        cp "$PROJECT_ROOT/docker-compose.yml" "$temp_dir/"
        print_success "Backed up Docker Compose configuration"
    fi
    
    # Backup scripts
    if [ -d "$PROJECT_ROOT/scripts" ]; then
        mkdir -p "$temp_dir/scripts"
        cp -r "$PROJECT_ROOT/scripts" "$temp_dir/"
        print_success "Backed up deployment scripts"
    fi
    
    # Create metadata file
    cat > "$temp_dir/metadata.json" << EOF
{
    "backup_date": "$(date -Iseconds)",
    "environment": "$ENVIRONMENT",
    "project_version": "$(git describe --tags --always 2>/dev/null || echo 'unknown')",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "backup_path": "$backup_path"
}
EOF
    
    # Create backup archive
    cd "$temp_dir"
    tar -czf "$backup_path" .
    cd - >/dev/null
    
    # Cleanup temporary directory
    rm -rf "$temp_dir"
    
    print_success "Configuration backup created: $backup_path"
    
    # Show backup info
    if [ -f "$backup_path" ]; then
        local backup_size=$(du -h "$backup_path" | cut -f1)
        print_info "Backup size: $backup_size"
        echo ""
        
        # Verify backup integrity
        if tar -tzf "$backup_path" >/dev/null 2>&1; then
            print_success "Backup integrity verified"
        else
            print_error "Backup integrity check failed"
            return 1
        fi
    fi
}

# ===============================================
# RESTORE CONFIGURATION
# ===============================================
restore_config() {
    if [ -z "$BACKUP_FILE" ]; then
        # Find latest backup for environment
        BACKUP_FILE="$BACKUP_DIR/config-backup-$(date +%Y%m%d)*-$ENVIRONMENT.tar.gz"
        
        # If no environment-specific backup, use latest general backup
        if [ ! -f "$BACKUP_FILE" ]; then
            BACKUP_FILE="$BACKUP_DIR/config-backup-$(date +%Y%m%d)*-*.tar.gz"
        fi
        
        # Use latest backup if multiple exist
        BACKUP_FILE=$(ls -t $BACKUP_FILE 2>/dev/null | head -n1)
    fi
    
    if [ ! -f "$BACKUP_FILE" ]; then
        print_error "Backup file not found: $BACKUP_FILE"
        echo "Available backups:"
        ls -la "$BACKUP_DIR"/*.tar.gz 2>/dev/null || echo "No backups found"
        return 1
    fi
    
    print_info "Restoring configuration from: $BACKUP_FILE"
    
    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would restore from $BACKUP_FILE"
        return 0
    fi
    
    # Verify backup integrity
    if ! tar -tzf "$BACKUP_FILE" >/dev/null 2>&1; then
        print_error "Invalid backup file"
        return 1
    fi
    
    # Extract backup to temporary directory
    local temp_dir=$(mktemp -d)
    tar -xzf "$BACKUP_FILE" -C "$temp_dir"
    
    # Show backup metadata if available
    if [ -f "$temp_dir/metadata.json" ]; then
        print_info "Backup metadata:"
        cat "$temp_dir/metadata.json" | jq '.' 2>/dev/null || cat "$temp_dir/metadata.json"
        echo ""
    fi
    
    # Restore configuration files
    if [ -d "$temp_dir/server" ] && [ -f "$temp_dir/server/.env" ]; then
        if [ "$FORCE" = true ] || confirm "Overwrite server configuration?"; then
            cp "$temp_dir/server/.env" "$SERVER_DIR/.env"
            print_success "Restored server configuration"
        fi
    fi
    
    if [ -d "$temp_dir/app" ] && [ -f "$temp_dir/app/.env" ]; then
        if [ "$FORCE" = true ] || confirm "Overwrite app configuration?"; then
            cp "$temp_dir/app/.env" "$APP_DIR/.env"
            print_success "Restored app configuration"
        fi
    fi
    
    if [ -d "$temp_dir/environments" ] && [ -f "$temp_dir/environments/.env.$ENVIRONMENT" ]; then
        if [ "$FORCE" = true ] || confirm "Overwrite environment configuration?"; then
            cp "$temp_dir/environments/.env.$ENVIRONMENT" "$CONFIG_DIR/.env.$ENVIRONMENT"
            print_success "Restored $ENVIRONMENT environment configuration"
        fi
    fi
    
    if [ -f "$temp_dir/docker-compose.yml" ]; then
        if [ "$FORCE" = true ] || confirm "Overwrite Docker Compose configuration?"; then
            cp "$temp_dir/docker-compose.yml" "$PROJECT_ROOT/docker-compose.yml"
            print_success "Restored Docker Compose configuration"
        fi
    fi
    
    if [ -d "$temp_dir/scripts" ]; then
        if [ "$FORCE" = true ] || confirm "Overwrite deployment scripts?"; then
            cp -r "$temp_dir/scripts"/* "$PROJECT_ROOT/scripts/"
            print_success "Restored deployment scripts"
        fi
    fi
    
    # Cleanup
    rm -rf "$temp_dir"
    
    print_success "Configuration restore completed"
}

# ===============================================
# VALIDATE CONFIGURATION
# ===============================================
validate_config() {
    print_info "Validating configuration for environment: $ENVIRONMENT"
    
    local validation_passed=true
    
    # Check environment configuration file
    local env_config="$CONFIG_DIR/.env.$ENVIRONMENT"
    if [ ! -f "$env_config" ]; then
        print_error "Environment configuration file not found: $env_config"
        validation_passed=false
    else
        print_success "Environment configuration found"
        
        # Validate required variables
        local required_vars=("ENVIRONMENT" "HOST" "PORT" "SECRET_KEY")
        
        for var in "${required_vars[@]}"; do
            if ! grep -q "^${var}=" "$env_config"; then
                print_error "Missing required variable: $var"
                validation_passed=false
            fi
        done
        
        # Check for placeholder values
        if grep -q "your-super-secure" "$env_config"; then
            print_warning "Placeholder values detected in configuration"
            validation_passed=false
        fi
        
        # Validate URL formats
        if grep -q "OLLAMA_BASE_URL=" "$env_config"; then
            local ollama_url=$(grep "OLLAMA_BASE_URL=" "$env_config" | cut -d'=' -f2)
            if [[ ! "$ollama_url" =~ ^https?:// ]]; then
                print_error "Invalid Ollama URL format: $ollama_url"
                validation_passed=false
            fi
        fi
        
        # Check database URLs
        if grep -q "DATABASE_URL=" "$env_config"; then
            local db_url=$(grep "DATABASE_URL=" "$env_config" | cut -d'=' -f2)
            if [[ ! "$db_url" =~ ^(sqlite|postgresql|mysql):// ]]; then
                print_error "Invalid database URL format: $db_url"
                validation_passed=false
            fi
        fi
    fi
    
    # Check server configuration
    local server_config="$SERVER_DIR/.env"
    if [ -f "$server_config" ]; then
        print_success "Server configuration found"
        
        # Validate WebSocket URL
        if grep -q "WEBSOCKET_URL=" "$server_config"; then
            local ws_url=$(grep "WEBSOCKET_URL=" "$server_config" | cut -d'=' -f2)
            if [[ ! "$ws_url" =~ ^wss?:// ]]; then
                print_error "Invalid WebSocket URL format: $ws_url"
                validation_passed=false
            fi
        fi
    else
        print_warning "Server configuration file not found: $server_config"
    fi
    
    # Check app configuration
    local app_config="$APP_DIR/.env"
    if [ -f "$app_config" ]; then
        print_success "App configuration found"
    else
        print_warning "App configuration file not found: $app_config"
    fi
    
    # Validate Docker Compose configuration
    local docker_compose="$PROJECT_ROOT/docker-compose.yml"
    if [ -f "$docker_compose" ]; then
        if command -v docker-compose >/dev/null; then
            if docker-compose -f "$docker_compose" config >/dev/null 2>&1; then
                print_success "Docker Compose configuration is valid"
            else
                print_error "Docker Compose configuration is invalid"
                validation_passed=false
            fi
        fi
    fi
    
    # Summary
    echo ""
    if [ "$validation_passed" = true ]; then
        print_success "Configuration validation passed"
    else
        print_error "Configuration validation failed"
        echo ""
        print_info "Common issues:"
        echo "  1. Check that all required environment variables are set"
        echo "  2. Replace placeholder values with actual secrets"
        echo "  3. Verify URL formats are correct"
        echo "  4. Ensure configuration files exist"
    fi
    
    return $([ "$validation_passed" = true ] && echo 0 || echo 1)
}

# ===============================================
# MIGRATE CONFIGURATION
# ===============================================
migrate_config() {
    if [ -z "$TO_ENVIRONMENT" ]; then
        print_error "Target environment not specified"
        echo "Usage: $0 migrate --to ENVIRONMENT"
        return 1
    fi
    
    if [ "$ENVIRONMENT" = "$TO_ENVIRONMENT" ]; then
        print_error "Source and target environments are the same"
        return 1
    fi
    
    print_info "Migrating configuration from $ENVIRONMENT to $TO_ENVIRONMENT"
    
    local source_config="$CONFIG_DIR/.env.$ENVIRONMENT"
    local target_config="$CONFIG_DIR/.env.$TO_ENVIRONMENT"
    
    if [ ! -f "$source_config" ]; then
        print_error "Source configuration not found: $source_config"
        return 1
    fi
    
    # Create target environment configuration based on source
    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would migrate $source_config to $target_config"
        return 0
    fi
    
    # Create backup of target if it exists
    if [ -f "$target_config" ]; then
        local backup_file="$target_config.backup.$(date +%Y%m%d-%H%M%S)"
        cp "$target_config" "$backup_file"
        print_success "Created backup of target configuration: $backup_file"
    fi
    
    # Copy source to target with environment-specific modifications
    cp "$source_config" "$target_config"
    
    # Update environment-specific values
    sed -i "s/ENVIRONMENT=.*/ENVIRONMENT=$TO_ENVIRONMENT/" "$target_config"
    
    # Add environment-specific modifications
    case $TO_ENVIRONMENT in
        production)
            # Production-specific hardening
            sed -i 's/DEBUG=.*/DEBUG=false/' "$target_config"
            sed -i 's/LOG_LEVEL=.*/LOG_LEVEL=INFO/' "$target_config"
            # Remove development-specific settings
            sed -i '/HOT_RELOAD=/d' "$target_config"
            sed -i '/AUTO_RELOAD=/d' "$target_config"
            ;;
        staging)
            # Staging-specific settings
            sed -i 's/DEBUG=.*/DEBUG=false/' "$target_config"
            sed -i 's/LOG_LEVEL=.*/LOG_LEVEL=INFO/' "$target_config"
            ;;
        development)
            # Development-specific settings
            sed -i 's/DEBUG=.*/DEBUG=true/' "$target_config"
            sed -i 's/LOG_LEVEL=.*/LOG_LEVEL=DEBUG/' "$target_config"
            # Add development features
            echo "HOT_RELOAD=true" >> "$target_config"
            echo "AUTO_RELOAD=true" >> "$target_config"
            ;;
    esac
    
    print_success "Configuration migrated to $TO_ENVIRONMENT"
    
    # Update server and app configurations if they exist
    if [ -f "$SERVER_DIR/.env" ]; then
        cp "$target_config" "$SERVER_DIR/.env"
        print_success "Updated server configuration"
    fi
    
    if [ -f "$APP_DIR/.env" ]; then
        # Update app config with environment-specific WebSocket URL
        local app_target_config="$target_config"
        local app_config="$APP_DIR/.env"
        cp "$app_target_config" "$app_config"
        print_success "Updated app configuration"
    fi
}

# ===============================================
# ENCRYPT/DECRYPT SENSITIVE CONFIGURATION
# ===============================================
encrypt_config() {
    print_info "Encrypting sensitive configuration..."
    
    if ! command -v gpg >/dev/null; then
        print_error "GPG not found. Please install GPG for encryption."
        return 1
    fi
    
    local config_file="$CONFIG_DIR/.env.$ENVIRONMENT"
    if [ ! -f "$config_file" ]; then
        print_error "Configuration file not found: $config_file"
        return 1
    fi
    
    # Check if already encrypted
    if file "$config_file" | grep -q "gpg"; then
        print_warning "File already appears to be encrypted"
        return 0
    fi
    
    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would encrypt $config_file"
        return 0
    fi
    
    # Backup original
    local backup_file="$config_file.backup.$(date +%Y%m%d-%H%M%S)"
    cp "$config_file" "$backup_file"
    
    # Encrypt configuration
    gpg --symmetric --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 --s2k-digest-algo SHA512 --s2k-count 65536 --output "$config_file.gpg" "$config_file"
    
    if [ $? -eq 0 ]; then
        # Remove original file
        rm "$config_file"
        print_success "Configuration encrypted: $config_file.gpg"
        print_info "Original backed up as: $backup_file"
    else
        print_error "Encryption failed"
        return 1
    fi
}

decrypt_config() {
    print_info "Decrypting sensitive configuration..."
    
    local encrypted_file="$CONFIG_DIR/.env.$ENVIRONMENT.gpg"
    if [ ! -f "$encrypted_file" ]; then
        print_error "Encrypted file not found: $encrypted_file"
        return 1
    fi
    
    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would decrypt $encrypted_file"
        return 0
    fi
    
    # Decrypt configuration
    gpg --decrypt --output "$CONFIG_DIR/.env.$ENVIRONMENT" "$encrypted_file"
    
    if [ $? -eq 0 ]; then
        print_success "Configuration decrypted: $CONFIG_DIR/.env.$ENVIRONMENT"
        
        # Set secure permissions
        chmod 600 "$CONFIG_DIR/.env.$ENVIRONMENT"
        print_info "Set secure file permissions (600)"
    else
        print_error "Decryption failed"
        return 1
    fi
}

# ===============================================
# SECRETS MANAGEMENT
# ===============================================
manage_secrets() {
    print_info "Managing secrets..."
    
    echo "Available secrets management options:"
    echo "  1. Generate new secret key"
    echo "  2. Generate database password"
    echo "  3. Generate API key"
    echo "  4. Show current secrets"
    echo "  5. Update secrets in configuration"
    echo ""
    
    read -p "Select option (1-5): " -r
    echo
    
    case $REPLY in
        1)
            local secret_key=$(openssl rand -hex 32)
            print_info "Generated secret key: $secret_key"
            
            if [ "$DRY_RUN" = false ] && [ "$FORCE" = true ]; then
                sed -i "s/SECRET_KEY=.*/SECRET_KEY=$secret_key/" "$CONFIG_DIR/.env.$ENVIRONMENT"
                print_success "Updated secret key in configuration"
            fi
            ;;
        2)
            local db_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
            print_info "Generated database password: $db_password"
            
            if [ "$DRY_RUN" = false ] && [ "$FORCE" = true ]; then
                sed -i "s/password=.*/password=$db_password/" "$CONFIG_DIR/.env.$ENVIRONMENT"
                print_success "Updated database password in configuration"
            fi
            ;;
        3)
            local api_key=$(openssl rand -hex 16)
            print_info "Generated API key: $api_key"
            ;;
        4)
            if [ -f "$CONFIG_DIR/.env.$ENVIRONMENT" ]; then
                print_info "Current secrets (masked):"
                grep -E "(SECRET_KEY|PASSWORD|API_KEY)" "$CONFIG_DIR" | sed 's/=.*/=***HIDDEN***/' || echo "No secrets found"
            else
                print_warning "Configuration file not found"
            fi
            ;;
        5)
            print_info "Updating secrets in configuration..."
            # Implementation would update all placeholder values
            if grep -q "placeholder" "$CONFIG_DIR/.env.$ENVIRONMENT" 2>/dev/null; then
                print_warning "Placeholder values found in configuration"
                print_info "Please manually update sensitive values"
            else
                print_success "All secrets appear to be properly configured"
            fi
            ;;
        *)
            print_error "Invalid option"
            return 1
            ;;
    esac
}

# ===============================================
# HELPER FUNCTIONS
# ===============================================
confirm() {
    local message="$1"
    
    if [ "$FORCE" = true ]; then
        return 0
    fi
    
    echo -n "$message [y/N]: "
    read -r response
    
    [[ "$response" =~ ^[Yy]$ ]]
    return $?
}

# ===============================================
# MAIN EXECUTION
# ===============================================
main() {
    case $COMMAND in
        backup)
            backup_config
            ;;
        restore)
            restore_config
            ;;
        validate)
            validate_config
            ;;
        migrate)
            migrate_config
            ;;
        encrypt)
            encrypt_config
            ;;
        decrypt)
            decrypt_config
            ;;
        secrets)
            manage_secrets
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main
