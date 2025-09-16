#!/bin/bash
# Health Check Script for Hybrid Search System
# 
# This script provides comprehensive health checks for the hybrid search system.
# It can be used for monitoring, alerting, and troubleshooting.

set -e

# Configuration
ES_URL="${ES_URL:-http://localhost:9200}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
SEARCH_SERVICE_URL="${SEARCH_SERVICE_URL:-http://localhost:8080}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Health check results
HEALTH_STATUS="healthy"
ISSUES=()

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ISSUES+=("$1")
    HEALTH_STATUS="unhealthy"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    ISSUES+=("$1")
    if [[ "$HEALTH_STATUS" == "healthy" ]]; then
        HEALTH_STATUS="degraded"
    fi
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if URL is accessible
check_url() {
    local url="$1"
    local name="$2"
    local timeout="${3:-10}"
    
    if curl -s --max-time "$timeout" "$url" >/dev/null 2>&1; then
        success "$name is accessible at $url"
        return 0
    else
        error "$name is not accessible at $url"
        return 1
    fi
}

# Check Elasticsearch health
check_elasticsearch_health() {
    log "Checking Elasticsearch health..."
    
    if ! check_url "${ES_URL}/_cluster/health" "Elasticsearch"; then
        return 1
    fi
    
    # Get cluster health
    local health_response=$(curl -s "${ES_URL}/_cluster/health" 2>/dev/null)
    if [[ $? -ne 0 ]]; then
        error "Failed to get Elasticsearch cluster health"
        return 1
    fi
    
    # Parse health status
    local status=$(echo "$health_response" | jq -r '.status' 2>/dev/null)
    local nodes=$(echo "$health_response" | jq -r '.number_of_nodes' 2>/dev/null)
    local active_shards=$(echo "$health_response" | jq -r '.active_shards' 2>/dev/null)
    local unassigned_shards=$(echo "$health_response" | jq -r '.unassigned_shards' 2>/dev/null)
    
    case $status in
        "green")
            success "Elasticsearch cluster is healthy (green) - $nodes nodes, $active_shards active shards"
            ;;
        "yellow")
            warning "Elasticsearch cluster is in yellow state - $nodes nodes, $active_shards active shards, $unassigned_shards unassigned shards"
            ;;
        "red")
            error "Elasticsearch cluster is in red state - $nodes nodes, $active_shards active shards, $unassigned_shards unassigned shards"
            ;;
        *)
            error "Unknown Elasticsearch status: $status"
            ;;
    esac
    
    # Check for unassigned shards
    if [[ "$unassigned_shards" -gt 0 ]]; then
        warning "Found $unassigned_shards unassigned shards"
    fi
    
    return 0
}

# Check Elasticsearch indices
check_elasticsearch_indices() {
    log "Checking Elasticsearch indices..."
    
    # Get indices
    local indices_response=$(curl -s "${ES_URL}/_cat/indices?format=json" 2>/dev/null)
    if [[ $? -ne 0 ]]; then
        error "Failed to get Elasticsearch indices"
        return 1
    fi
    
    # Check for required indices
    local required_indices=("watchlist_persons_current" "watchlist_orgs_current")
    local found_indices=()
    
    while IFS= read -r line; do
        local index_name=$(echo "$line" | jq -r '.index' 2>/dev/null)
        if [[ -n "$index_name" ]]; then
            found_indices+=("$index_name")
        fi
    done <<< "$indices_response"
    
    for required in "${required_indices[@]}"; do
        local found=false
        for found_index in "${found_indices[@]}"; do
            if [[ "$found_index" == "$required" ]] || [[ "$found_index" == *"$required"* ]]; then
                found=true
                break
            fi
        done
        
        if $found; then
            success "Required index found: $required"
        else
            error "Required index not found: $required"
        fi
    done
    
    # Check index health
    local unhealthy_indices=$(echo "$indices_response" | jq -r '.[] | select(.health != "green") | .index' 2>/dev/null)
    if [[ -n "$unhealthy_indices" ]]; then
        warning "Found unhealthy indices: $unhealthy_indices"
    fi
    
    return 0
}

# Check Elasticsearch templates
check_elasticsearch_templates() {
    log "Checking Elasticsearch templates..."
    
    # Check component templates
    local component_templates=$(curl -s "${ES_URL}/_component_template" 2>/dev/null)
    if [[ $? -eq 0 ]]; then
        local template_count=$(echo "$component_templates" | jq -r '.component_templates | length' 2>/dev/null)
        if [[ "$template_count" -gt 0 ]]; then
            success "Found $template_count component templates"
        else
            warning "No component templates found"
        fi
    else
        error "Failed to get component templates"
    fi
    
    # Check index templates
    local index_templates=$(curl -s "${ES_URL}/_index_template" 2>/dev/null)
    if [[ $? -eq 0 ]]; then
        local template_count=$(echo "$index_templates" | jq -r '.index_templates | length' 2>/dev/null)
        if [[ "$template_count" -gt 0 ]]; then
            success "Found $template_count index templates"
        else
            warning "No index templates found"
        fi
    else
        error "Failed to get index templates"
    fi
    
    return 0
}

# Check Prometheus health
check_prometheus_health() {
    log "Checking Prometheus health..."
    
    if ! check_url "${PROMETHEUS_URL}/api/v1/query?query=up" "Prometheus"; then
        return 1
    fi
    
    # Check if Prometheus is scraping metrics
    local query_response=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=up" 2>/dev/null)
    if [[ $? -eq 0 ]]; then
        local result_count=$(echo "$query_response" | jq -r '.data.result | length' 2>/dev/null)
        if [[ "$result_count" -gt 0 ]]; then
            success "Prometheus is scraping $result_count targets"
        else
            warning "Prometheus is not scraping any targets"
        fi
    else
        error "Failed to query Prometheus"
    fi
    
    return 0
}

# Check Grafana health
check_grafana_health() {
    log "Checking Grafana health..."
    
    if check_url "${GRAFANA_URL}/api/health" "Grafana"; then
        success "Grafana is accessible"
    else
        warning "Grafana is not accessible"
    fi
    
    return 0
}

# Check search service health
check_search_service_health() {
    log "Checking search service health..."
    
    if check_url "${SEARCH_SERVICE_URL}/health" "Search Service"; then
        success "Search service is accessible"
    else
        warning "Search service is not accessible"
    fi
    
    return 0
}

# Check Docker containers
check_docker_containers() {
    log "Checking Docker containers..."
    
    local required_containers=("search-elasticsearch" "search-prometheus" "search-grafana" "search-alertmanager")
    local all_running=true
    
    for container in "${required_containers[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            local status=$(docker ps --format "{{.Names}}\t{{.Status}}" | grep "^${container}" | awk '{print $2}')
            if [[ "$status" == *"Up"* ]]; then
                success "Container $container is running ($status)"
            else
                error "Container $container is not running ($status)"
                all_running=false
            fi
        else
            error "Container $container is not found"
            all_running=false
        fi
    done
    
    if $all_running; then
        success "All required containers are running"
    fi
    
    return 0
}

# Check system resources
check_system_resources() {
    log "Checking system resources..."
    
    # Check disk space
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -gt 90 ]]; then
        error "Disk usage is critical: ${disk_usage}%"
    elif [[ $disk_usage -gt 80 ]]; then
        warning "Disk usage is high: ${disk_usage}%"
    else
        success "Disk usage is normal: ${disk_usage}%"
    fi
    
    # Check memory usage
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [[ $memory_usage -gt 90 ]]; then
        error "Memory usage is critical: ${memory_usage}%"
    elif [[ $memory_usage -gt 80 ]]; then
        warning "Memory usage is high: ${memory_usage}%"
    else
        success "Memory usage is normal: ${memory_usage}%"
    fi
    
    # Check Docker disk usage
    local docker_usage=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}" | grep -v "TYPE" | awk '{sum+=$3} END {print sum}' 2>/dev/null || echo "0")
    if [[ $docker_usage -gt 10000 ]]; then  # 10GB
        warning "Docker disk usage is high: ${docker_usage}MB"
    else
        success "Docker disk usage is normal: ${docker_usage}MB"
    fi
    
    return 0
}

# Check search functionality
check_search_functionality() {
    log "Checking search functionality..."
    
    # Test AC search
    local ac_query='{
        "query": {
            "bool": {
                "must": [
                    {"term": {"entity_type": "person"}},
                    {"match_all": {}}
                ]
            }
        },
        "size": 1
    }'
    
    local ac_response=$(curl -s -X GET "${ES_URL}/watchlist_persons_current/_search" \
        -H "Content-Type: application/json" \
        -d "$ac_query" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        local ac_hits=$(echo "$ac_response" | jq -r '.hits.total.value' 2>/dev/null)
        if [[ "$ac_hits" -gt 0 ]]; then
            success "AC search is working ($ac_hits hits found)"
        else
            warning "AC search returned no hits"
        fi
    else
        error "AC search test failed"
    fi
    
    # Test Vector search
    local vector_query='{
        "knn": {
            "field": "name_vector",
            "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
            "k": 5,
            "similarity": "cosine"
        },
        "size": 1
    }'
    
    local vector_response=$(curl -s -X GET "${ES_URL}/watchlist_persons_current/_search" \
        -H "Content-Type: application/json" \
        -d "$vector_query" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        local vector_hits=$(echo "$vector_response" | jq -r '.hits.total.value' 2>/dev/null)
        if [[ "$vector_hits" -gt 0 ]]; then
            success "Vector search is working ($vector_hits hits found)"
        else
            warning "Vector search returned no hits"
        fi
    else
        error "Vector search test failed"
    fi
    
    return 0
}

# Generate health report
generate_health_report() {
    log "Generating health report..."
    
    local report_file="health_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "=== Hybrid Search System Health Report ==="
        echo "Generated: $(date)"
        echo "Status: $HEALTH_STATUS"
        echo
        
        if [[ ${#ISSUES[@]} -gt 0 ]]; then
            echo "=== Issues Found ==="
            for issue in "${ISSUES[@]}"; do
                echo "- $issue"
            done
            echo
        fi
        
        echo "=== System Information ==="
        echo "Hostname: $(hostname)"
        echo "Uptime: $(uptime)"
        echo "Load Average: $(cat /proc/loadavg 2>/dev/null || echo 'N/A')"
        echo
        
        echo "=== Docker Information ==="
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker not available"
        echo
        
        echo "=== Elasticsearch Information ==="
        curl -s "${ES_URL}/_cluster/health?pretty" 2>/dev/null || echo "Elasticsearch not accessible"
        echo
        
        echo "=== Disk Usage ==="
        df -h 2>/dev/null || echo "Disk usage not available"
        echo
        
        echo "=== Memory Usage ==="
        free -h 2>/dev/null || echo "Memory usage not available"
        
    } > "$report_file"
    
    success "Health report generated: $report_file"
    return 0
}

# Main health check function
run_health_check() {
    log "Starting comprehensive health check..."
    
    # Check prerequisites
    if ! command_exists curl; then
        error "curl is not installed"
        exit 1
    fi
    
    if ! command_exists docker; then
        error "Docker is not installed"
        exit 1
    fi
    
    if ! command_exists jq; then
        warning "jq is not installed - some checks may not work properly"
    fi
    
    # Run all health checks
    check_elasticsearch_health
    check_elasticsearch_indices
    check_elasticsearch_templates
    check_prometheus_health
    check_grafana_health
    check_search_service_health
    check_docker_containers
    check_system_resources
    check_search_functionality
    
    # Generate report
    generate_health_report
    
    # Print summary
    echo
    echo "=========================================="
    echo "Health Check Summary"
    echo "=========================================="
    echo "Overall Status: $HEALTH_STATUS"
    echo "Issues Found: ${#ISSUES[@]}"
    
    if [[ ${#ISSUES[@]} -gt 0 ]]; then
        echo
        echo "Issues:"
        for issue in "${ISSUES[@]}"; do
            echo "  - $issue"
        done
    fi
    
    echo "=========================================="
    
    # Exit with appropriate code
    case $HEALTH_STATUS in
        "healthy")
            success "System is healthy"
            exit 0
            ;;
        "degraded")
            warning "System is degraded"
            exit 1
            ;;
        "unhealthy")
            error "System is unhealthy"
            exit 2
            ;;
    esac
}

# Show usage
show_usage() {
    echo "Health Check Script for Hybrid Search System"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -q, --quiet    Quiet mode (minimal output)"
    echo "  -j, --json     Output in JSON format"
    echo
    echo "Environment Variables:"
    echo "  ES_URL              Elasticsearch URL (default: http://localhost:9200)"
    echo "  PROMETHEUS_URL      Prometheus URL (default: http://localhost:9090)"
    echo "  GRAFANA_URL         Grafana URL (default: http://localhost:3000)"
    echo "  SEARCH_SERVICE_URL  Search Service URL (default: http://localhost:8080)"
}

# Parse command line arguments
QUIET=false
JSON_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -j|--json)
            JSON_OUTPUT=true
            shift
            ;;
        *)
            error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Run health check
run_health_check
