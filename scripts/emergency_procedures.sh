#!/bin/bash
# Emergency Procedures Script for Hybrid Search System
# 
# This script provides emergency procedures for SRE and developers
# to quickly respond to critical issues with the hybrid search system.

set -e

# Configuration
ES_URL="${ES_URL:-http://localhost:9200}"
DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-monitoring/docker-compose.monitoring.yml}"
LOG_DIR="${LOG_DIR:-./logs}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command_exists docker; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    if ! command_exists curl; then
        error "curl is not installed or not in PATH"
        exit 1
    fi
    
    success "All prerequisites met"
}

# Check Elasticsearch health
check_elasticsearch_health() {
    log "Checking Elasticsearch health..."
    
    if curl -s "${ES_URL}/_cluster/health" >/dev/null 2>&1; then
        local health=$(curl -s "${ES_URL}/_cluster/health" | jq -r '.status')
        case $health in
            "green")
                success "Elasticsearch is healthy (green)"
                return 0
                ;;
            "yellow")
                warning "Elasticsearch is in yellow state"
                return 1
                ;;
            "red")
                error "Elasticsearch is in red state"
                return 2
                ;;
            *)
                error "Unknown Elasticsearch status: $health"
                return 3
                ;;
        esac
    else
        error "Cannot connect to Elasticsearch at $ES_URL"
        return 4
    fi
}

# Check service status
check_service_status() {
    log "Checking service status..."
    
    local services=("search-elasticsearch" "search-prometheus" "search-grafana" "search-alertmanager")
    local all_healthy=true
    
    for service in "${services[@]}"; do
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$service.*Up"; then
            success "$service is running"
        else
            error "$service is not running"
            all_healthy=false
        fi
    done
    
    if $all_healthy; then
        success "All services are running"
        return 0
    else
        error "Some services are not running"
        return 1
    fi
}

# Emergency restart
emergency_restart() {
    log "Starting emergency restart procedure..."
    
    warning "This will restart all services and may cause temporary downtime"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Emergency restart cancelled"
        return 1
    fi
    
    # Stop all services
    log "Stopping all services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Wait for services to stop
    sleep 10
    
    # Start services
    log "Starting services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Check health
    if check_elasticsearch_health; then
        success "Emergency restart completed successfully"
        return 0
    else
        error "Emergency restart failed - services are not healthy"
        return 1
    fi
}

# Fallback to local index
enable_fallback() {
    log "Enabling fallback to local index..."
    
    # Set environment variable
    export ELASTICSEARCH_ENABLED=false
    
    # Restart search service
    log "Restarting search service with fallback enabled..."
    docker restart search-service 2>/dev/null || warning "Search service container not found"
    
    # Wait for service to be ready
    sleep 10
    
    # Test fallback
    if curl -s "http://localhost:8080/health" >/dev/null 2>&1; then
        success "Fallback to local index enabled successfully"
        return 0
    else
        error "Failed to enable fallback to local index"
        return 1
    fi
}

# Disable vector search
disable_vector_search() {
    log "Disabling vector search..."
    
    # Set environment variable
    export DISABLE_VECTOR_SEARCH=true
    
    # Restart search service
    log "Restarting search service with vector search disabled..."
    docker restart search-service 2>/dev/null || warning "Search service container not found"
    
    # Wait for service to be ready
    sleep 10
    
    success "Vector search disabled"
    return 0
}

# Clear Elasticsearch caches
clear_elasticsearch_caches() {
    log "Clearing Elasticsearch caches..."
    
    if curl -s -X POST "${ES_URL}/_cache/clear" >/dev/null 2>&1; then
        success "Elasticsearch caches cleared"
        return 0
    else
        error "Failed to clear Elasticsearch caches"
        return 1
    fi
}

# Force merge indices
force_merge_indices() {
    log "Force merging indices..."
    
    local indices=("watchlist_persons_current" "watchlist_orgs_current")
    
    for index in "${indices[@]}"; do
        log "Force merging $index..."
        if curl -s -X POST "${ES_URL}/$index/_forcemerge?max_num_segments=1" >/dev/null 2>&1; then
            success "$index force merged successfully"
        else
            error "Failed to force merge $index"
        fi
    done
}

# Create emergency backup
create_emergency_backup() {
    log "Creating emergency backup..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup Elasticsearch data
    log "Backing up Elasticsearch data..."
    docker exec search-elasticsearch tar -czf /tmp/elasticsearch_backup.tar.gz /usr/share/elasticsearch/data
    docker cp search-elasticsearch:/tmp/elasticsearch_backup.tar.gz "$BACKUP_DIR/elasticsearch_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    # Backup configuration files
    log "Backing up configuration files..."
    tar -czf "$BACKUP_DIR/config_backup_$(date +%Y%m%d_%H%M%S).tar.gz" \
        templates/elasticsearch/ \
        monitoring/ \
        scripts/ \
        docker-compose*.yml 2>/dev/null || true
    
    success "Emergency backup created in $BACKUP_DIR"
    return 0
}

# Restore from backup
restore_from_backup() {
    log "Restoring from backup..."
    
    # List available backups
    log "Available backups:"
    ls -la "$BACKUP_DIR"/*.tar.gz 2>/dev/null || {
        error "No backups found in $BACKUP_DIR"
        return 1
    }
    
    # Get backup file
    read -p "Enter backup filename: " backup_file
    
    if [[ ! -f "$BACKUP_DIR/$backup_file" ]]; then
        error "Backup file not found: $BACKUP_DIR/$backup_file"
        return 1
    fi
    
    warning "This will restore from backup and may overwrite current data"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Restore cancelled"
        return 1
    fi
    
    # Stop services
    log "Stopping services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Restore Elasticsearch data
    if [[ $backup_file == elasticsearch_backup_* ]]; then
        log "Restoring Elasticsearch data..."
        docker cp "$BACKUP_DIR/$backup_file" search-elasticsearch:/tmp/
        docker exec search-elasticsearch tar -xzf /tmp/$(basename "$backup_file") -C /
    fi
    
    # Start services
    log "Starting services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    # Wait for services to be ready
    sleep 30
    
    if check_elasticsearch_health; then
        success "Restore completed successfully"
        return 0
    else
        error "Restore failed - services are not healthy"
        return 1
    fi
}

# Collect diagnostic information
collect_diagnostics() {
    log "Collecting diagnostic information..."
    
    # Create diagnostics directory
    local diag_dir="$LOG_DIR/diagnostics_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$diag_dir"
    
    # System information
    log "Collecting system information..."
    {
        echo "=== System Information ==="
        uname -a
        echo
        echo "=== Docker Version ==="
        docker --version
        echo
        echo "=== Docker Compose Version ==="
        docker-compose --version
        echo
        echo "=== Disk Usage ==="
        df -h
        echo
        echo "=== Memory Usage ==="
        free -h
        echo
        echo "=== CPU Info ==="
        lscpu | head -20
    } > "$diag_dir/system_info.txt"
    
    # Docker information
    log "Collecting Docker information..."
    {
        echo "=== Docker Containers ==="
        docker ps -a
        echo
        echo "=== Docker Images ==="
        docker images
        echo
        echo "=== Docker Volumes ==="
        docker volume ls
        echo
        echo "=== Docker Networks ==="
        docker network ls
    } > "$diag_dir/docker_info.txt"
    
    # Elasticsearch information
    log "Collecting Elasticsearch information..."
    {
        echo "=== Elasticsearch Cluster Health ==="
        curl -s "${ES_URL}/_cluster/health?pretty" || echo "Failed to get cluster health"
        echo
        echo "=== Elasticsearch Indices ==="
        curl -s "${ES_URL}/_cat/indices?v" || echo "Failed to get indices"
        echo
        echo "=== Elasticsearch Nodes ==="
        curl -s "${ES_URL}/_cat/nodes?v" || echo "Failed to get nodes"
        echo
        echo "=== Elasticsearch Shards ==="
        curl -s "${ES_URL}/_cat/shards?v" || echo "Failed to get shards"
    } > "$diag_dir/elasticsearch_info.txt"
    
    # Service logs
    log "Collecting service logs..."
    local services=("search-elasticsearch" "search-prometheus" "search-grafana" "search-alertmanager" "search-service")
    
    for service in "${services[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "$service"; then
            log "Collecting logs for $service..."
            docker logs "$service" --tail 1000 > "$diag_dir/${service}_logs.txt" 2>&1 || true
        fi
    done
    
    # Create archive
    log "Creating diagnostics archive..."
    tar -czf "$diag_dir.tar.gz" -C "$LOG_DIR" "$(basename "$diag_dir")"
    rm -rf "$diag_dir"
    
    success "Diagnostics collected: $diag_dir.tar.gz"
    return 0
}

# Show usage
show_usage() {
    echo "Emergency Procedures Script for Hybrid Search System"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  health          Check Elasticsearch health"
    echo "  status          Check service status"
    echo "  restart         Emergency restart all services"
    echo "  fallback        Enable fallback to local index"
    echo "  disable-vector  Disable vector search"
    echo "  clear-cache     Clear Elasticsearch caches"
    echo "  force-merge     Force merge indices"
    echo "  backup          Create emergency backup"
    echo "  restore         Restore from backup"
    echo "  diagnostics     Collect diagnostic information"
    echo "  help            Show this help message"
    echo
    echo "Environment Variables:"
    echo "  ES_URL                    Elasticsearch URL (default: http://localhost:9200)"
    echo "  DOCKER_COMPOSE_FILE       Docker Compose file (default: monitoring/docker-compose.monitoring.yml)"
    echo "  LOG_DIR                   Log directory (default: ./logs)"
    echo "  BACKUP_DIR                Backup directory (default: ./backups)"
}

# Main function
main() {
    # Check prerequisites
    check_prerequisites
    
    # Parse command
    case "${1:-help}" in
        "health")
            check_elasticsearch_health
            ;;
        "status")
            check_service_status
            ;;
        "restart")
            emergency_restart
            ;;
        "fallback")
            enable_fallback
            ;;
        "disable-vector")
            disable_vector_search
            ;;
        "clear-cache")
            clear_elasticsearch_caches
            ;;
        "force-merge")
            force_merge_indices
            ;;
        "backup")
            create_emergency_backup
            ;;
        "restore")
            restore_from_backup
            ;;
        "diagnostics")
            collect_diagnostics
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
