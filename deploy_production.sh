#!/bin/bash

# GPUDex Production Deployment Script
# Comprehensive deployment with safety checks, backups, and rollback capabilities

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="gpudex"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
BACKUP_DIR="./backups"
LOG_FILE="./deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

# Check if running as root
check_user() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "🔍 Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker first."
    fi
    
    # Check environment file
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Environment file $ENV_FILE not found. Please create it from env.production template."
    fi
    
    # Check Docker Compose file
    if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
        error "Docker Compose file $DOCKER_COMPOSE_FILE not found."
    fi
    
    log "✅ All prerequisites satisfied"
}

# Validate environment configuration
validate_environment() {
    log "🔧 Validating environment configuration..."
    
    source "$ENV_FILE"
    
    # Check critical environment variables
    critical_vars=(
        "DATABASE_URL"
        "POSTGRES_PASSWORD"
        "JWT_SECRET_KEY"
        "SECRET_KEY"
        "SENDGRID_API_KEY"
    )
    
    for var in "${critical_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Critical environment variable $var is not set in $ENV_FILE"
        fi
    done
    
    # Check for default/insecure values
    if [[ "$POSTGRES_PASSWORD" == "SECURE_PASSWORD_HERE" ]]; then
        error "Please change POSTGRES_PASSWORD from default value"
    fi
    
    if [[ "$JWT_SECRET_KEY" == "GENERATE_SECURE_JWT_SECRET_HERE" ]]; then
        error "Please generate a secure JWT_SECRET_KEY"
    fi
    
    log "✅ Environment configuration validated"
}

# Create backup
create_backup() {
    log "💾 Creating backup before deployment..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup current deployment if exists
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Up"; then
        BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE="$BACKUP_DIR/backup_pre_deploy_$BACKUP_TIMESTAMP.sql"
        
        info "Creating database backup: $BACKUP_FILE"
        docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres pg_dump \
            -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$BACKUP_FILE" || warn "Database backup failed"
        
        # Backup current images
        info "Saving current Docker images..."
        docker save "${PROJECT_NAME}_backend:latest" -o "$BACKUP_DIR/backend_image_$BACKUP_TIMESTAMP.tar" 2>/dev/null || warn "Backend image backup failed"
        docker save "${PROJECT_NAME}_frontend:latest" -o "$BACKUP_DIR/frontend_image_$BACKUP_TIMESTAMP.tar" 2>/dev/null || warn "Frontend image backup failed"
    fi
    
    log "✅ Backup completed"
}

# Build and test images
build_images() {
    log "🏗️  Building Docker images..."
    
    # Build with no cache for production
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache --parallel
    
    log "✅ Images built successfully"
}

# Run health checks
health_check() {
    log "🏥 Running health checks..."
    
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log "✅ Backend health check passed"
            break
        fi
        
        attempt=$((attempt + 1))
        if [[ $attempt -eq $max_attempts ]]; then
            error "Backend health check failed after $max_attempts attempts"
        fi
        
        info "Health check attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
    done
    
    # Check frontend
    if curl -f http://localhost:3000/ &> /dev/null; then
        log "✅ Frontend health check passed"
    else
        warn "Frontend health check failed"
    fi
}

# Deploy application
deploy() {
    log "🚀 Deploying GPUDex to production..."
    
    # Stop existing services gracefully
    info "Stopping existing services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans || true
    
    # Start database first
    info "Starting database..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d postgres redis
    
    # Wait for database to be ready
    info "Waiting for database to be ready..."
    while ! docker-compose -f "$DOCKER_COMPOSE_FILE" exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" &> /dev/null; do
        sleep 2
    done
    
    # Start all services
    info "Starting all services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    # Wait for services to start
    sleep 30
    
    log "✅ Deployment completed"
}

# Rollback function
rollback() {
    log "🔄 Rolling back deployment..."
    
    # Stop current deployment
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Restore from latest backup
    latest_backup=$(ls -t "$BACKUP_DIR"/backup_pre_deploy_*.sql 2>/dev/null | head -n1)
    if [[ -n "$latest_backup" ]]; then
        info "Restoring database from: $latest_backup"
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d postgres
        sleep 10
        docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$latest_backup"
    fi
    
    # Restore previous images if available
    latest_backend_image=$(ls -t "$BACKUP_DIR"/backend_image_*.tar 2>/dev/null | head -n1)
    if [[ -n "$latest_backend_image" ]]; then
        info "Restoring backend image from: $latest_backend_image"
        docker load -i "$latest_backend_image"
    fi
    
    log "✅ Rollback completed"
}

# Cleanup old backups
cleanup_backups() {
    log "🧹 Cleaning up old backups..."
    
    # Keep only last 7 days of backups
    find "$BACKUP_DIR" -name "backup_*.sql" -mtime +7 -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "*_image_*.tar" -mtime +7 -delete 2>/dev/null || true
    
    log "✅ Backup cleanup completed"
}

# Security check
security_check() {
    log "🔒 Running security checks..."
    
    # Check for exposed ports
    if netstat -tlnp 2>/dev/null | grep -q ":5432.*0.0.0.0"; then
        warn "PostgreSQL port 5432 is exposed to all interfaces"
    fi
    
    if netstat -tlnp 2>/dev/null | grep -q ":6379.*0.0.0.0"; then
        warn "Redis port 6379 is exposed to all interfaces"
    fi
    
    # Check Docker daemon security
    if docker version --format '{{.Server.Version}}' | grep -qE '^(1\.|18\.|19\.)'; then
        warn "Docker version may have known security vulnerabilities"
    fi
    
    log "✅ Security checks completed"
}

# Main deployment function
main() {
    log "🚀 Starting GPUDex Production Deployment"
    
    # Parse command line arguments
    case "${1:-deploy}" in
        "deploy")
            check_user
            check_prerequisites
            validate_environment
            create_backup
            build_images
            deploy
            health_check
            security_check
            cleanup_backups
            log "🎉 Deployment completed successfully!"
            ;;
        "rollback")
            log "🔄 Starting rollback process..."
            rollback
            log "🎉 Rollback completed successfully!"
            ;;
        "health")
            health_check
            ;;
        "backup")
            create_backup
            ;;
        "logs")
            docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
            ;;
        "status")
            docker-compose -f "$DOCKER_COMPOSE_FILE" ps
            ;;
        *)
            echo "Usage: $0 {deploy|rollback|health|backup|logs|status}"
            echo "  deploy   - Full production deployment"
            echo "  rollback - Rollback to previous version"
            echo "  health   - Run health checks"
            echo "  backup   - Create manual backup"
            echo "  logs     - View application logs"
            echo "  status   - Show service status"
            exit 1
            ;;
    esac
}

# Trap for cleanup on script exit
cleanup() {
    if [[ $? -ne 0 ]]; then
        error "Deployment failed! Check logs at $LOG_FILE"
        info "To rollback, run: $0 rollback"
    fi
}

trap cleanup EXIT

# Run main function
main "$@" 