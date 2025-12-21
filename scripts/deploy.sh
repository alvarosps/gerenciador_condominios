#!/bin/bash
# ==================================================================
# Condomínios Manager - Production Deployment Script
# ==================================================================
# This script handles deployment of the application to production
# ==================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check if .env.production exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error ".env.production file not found!"
        log_info "Please copy .env.production.example to .env.production and configure it."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Backup database before deployment
backup_database() {
    log_info "Creating database backup..."

    mkdir -p "$BACKUP_DIR"

    # Check if postgres container is running
    if docker-compose -f $COMPOSE_FILE ps postgres | grep -q "Up"; then
        source $ENV_FILE
        docker-compose -f $COMPOSE_FILE exec -T postgres pg_dump -U $DB_USER $DB_NAME | gzip > "$BACKUP_DIR/db_backup_${TIMESTAMP}.sql.gz"
        log_success "Database backup created: $BACKUP_DIR/db_backup_${TIMESTAMP}.sql.gz"
    else
        log_warning "Postgres container is not running. Skipping backup."
    fi
}

# Pull latest code
pull_code() {
    log_info "Pulling latest code from repository..."

    if [ -d ".git" ]; then
        git pull origin master
        log_success "Code updated"
    else
        log_warning "Not a git repository. Skipping code pull."
    fi
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    docker-compose -f $COMPOSE_FILE build --no-cache
    log_success "Docker images built"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    docker-compose -f $COMPOSE_FILE run --rm web python manage.py migrate --noinput
    log_success "Migrations completed"
}

# Collect static files
collect_static() {
    log_info "Collecting static files..."
    docker-compose -f $COMPOSE_FILE run --rm web python manage.py collectstatic --noinput --clear
    log_success "Static files collected"
}

# Start services
start_services() {
    log_info "Starting services..."
    docker-compose -f $COMPOSE_FILE up -d
    log_success "Services started"
}

# Stop services
stop_services() {
    log_info "Stopping services..."
    docker-compose -f $COMPOSE_FILE down
    log_success "Services stopped"
}

# Restart services
restart_services() {
    log_info "Restarting services..."
    docker-compose -f $COMPOSE_FILE restart
    log_success "Services restarted"
}

# Check service health
check_health() {
    log_info "Checking service health..."

    sleep 10  # Wait for services to start

    # Check web service
    if docker-compose -f $COMPOSE_FILE ps web | grep -q "Up"; then
        log_success "Web service is running"
    else
        log_error "Web service is not running!"
        docker-compose -f $COMPOSE_FILE logs web
        exit 1
    fi

    # Check database
    if docker-compose -f $COMPOSE_FILE ps postgres | grep -q "Up"; then
        log_success "Database service is running"
    else
        log_error "Database service is not running!"
        exit 1
    fi

    # Check Redis
    if docker-compose -f $COMPOSE_FILE ps redis | grep -q "Up"; then
        log_success "Redis service is running"
    else
        log_error "Redis service is not running!"
        exit 1
    fi
}

# View logs
view_logs() {
    log_info "Viewing logs..."
    docker-compose -f $COMPOSE_FILE logs -f --tail=100
}

# Show status
show_status() {
    log_info "Service Status:"
    docker-compose -f $COMPOSE_FILE ps
}

# Main deployment function
deploy() {
    log_info "🚀 Starting deployment process..."

    check_prerequisites
    backup_database
    pull_code
    build_images
    stop_services
    run_migrations
    collect_static
    start_services
    check_health

    log_success "🎉 Deployment completed successfully!"
    log_info "View logs with: ./scripts/deploy.sh logs"
}

# Rollback function
rollback() {
    log_warning "Rolling back to previous version..."

    # Find latest backup
    LATEST_BACKUP=$(ls -t $BACKUP_DIR/db_backup_*.sql.gz | head -1)

    if [ -z "$LATEST_BACKUP" ]; then
        log_error "No backup found for rollback!"
        exit 1
    fi

    log_info "Restoring database from: $LATEST_BACKUP"

    source $ENV_FILE
    gunzip -c "$LATEST_BACKUP" | docker-compose -f $COMPOSE_FILE exec -T postgres psql -U $DB_USER $DB_NAME

    restart_services
    check_health

    log_success "Rollback completed"
}

# Parse command line arguments
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    backup)
        check_prerequisites
        backup_database
        ;;
    start)
        check_prerequisites
        start_services
        check_health
        ;;
    stop)
        check_prerequisites
        stop_services
        ;;
    restart)
        check_prerequisites
        restart_services
        check_health
        ;;
    logs)
        check_prerequisites
        view_logs
        ;;
    status)
        check_prerequisites
        show_status
        ;;
    rollback)
        check_prerequisites
        rollback
        ;;
    health)
        check_prerequisites
        check_health
        ;;
    *)
        echo "Usage: $0 {deploy|backup|start|stop|restart|logs|status|rollback|health}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Full deployment (backup, build, migrate, start)"
        echo "  backup   - Create database backup"
        echo "  start    - Start all services"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - View service logs"
        echo "  status   - Show service status"
        echo "  rollback - Rollback to previous database backup"
        echo "  health   - Check service health"
        exit 1
        ;;
esac
