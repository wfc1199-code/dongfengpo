#!/bin/bash

# Grayscale Rollout Management Script
# Manages feature flag rollout percentages for Phase 3
# Usage: ./grayscale_rollout.sh [command] [percentage]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config file path
CONFIG_FILE="config/grayscale-rollout.json"
FRONTEND_CONFIG="frontend/src/config/featureFlags.ts"

# Print colored message
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if config file exists
check_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Config file not found: $CONFIG_FILE"
        exit 1
    fi
}

# Get current rollout percentage
get_current_percentage() {
    check_config
    local percentage=$(cat "$CONFIG_FILE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['feature_flags']['anomalyDetection']['rolloutPercentage'])")
    echo "$percentage"
}

# Set rollout percentage
set_rollout_percentage() {
    local percentage=$1

    if [ -z "$percentage" ]; then
        log_error "Please provide a percentage (0-100)"
        exit 1
    fi

    if [ "$percentage" -lt 0 ] || [ "$percentage" -gt 100 ]; then
        log_error "Percentage must be between 0 and 100"
        exit 1
    fi

    check_config

    log_info "Setting rollout percentage to ${percentage}%..."

    # Update config file
    cat "$CONFIG_FILE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
data['feature_flags']['anomalyDetection']['rolloutPercentage'] = $percentage
data['feature_flags']['limitUpPrediction']['rolloutPercentage'] = $percentage
print(json.dumps(data, indent=2))
" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"

    log_success "Rollout percentage set to ${percentage}%"
    log_info "Note: Frontend users need to refresh their browser to see changes"
}

# Show current status
show_status() {
    check_config

    local percentage=$(get_current_percentage)
    local stage=$(get_current_stage)

    echo ""
    echo "========================================"
    echo "  Grayscale Rollout Status"
    echo "========================================"
    echo ""
    echo "Current Rollout: ${GREEN}${percentage}%${NC}"
    echo "Current Stage: ${BLUE}${stage}${NC}"
    echo ""

    # Check Signal API health
    log_info "Checking Signal API health..."
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Signal API: ${GREEN}✓ Healthy${NC}"
    else
        log_error "Signal API: ${RED}✗ Unhealthy${NC}"
    fi

    # Check Legacy API health
    log_info "Checking Legacy API health..."
    if curl -s -f http://localhost:9000/docs > /dev/null 2>&1; then
        log_success "Legacy API: ${GREEN}✓ Healthy${NC}"
    else
        log_warning "Legacy API: ${YELLOW}? Unknown${NC}"
    fi

    echo ""
    echo "Feature Flags:"
    echo "  - anomalyDetection: ${percentage}%"
    echo "  - limitUpPrediction: ${percentage}%"
    echo "  - fallbackToLegacy: enabled"
    echo ""
}

# Get current stage based on percentage
get_current_stage() {
    local percentage=$(get_current_percentage)

    if [ "$percentage" -eq 0 ]; then
        echo "Stage 0: Preparation"
    elif [ "$percentage" -le 10 ]; then
        echo "Stage 1: Initial Rollout (10%)"
    elif [ "$percentage" -le 30 ]; then
        echo "Stage 2: Expanded Rollout (30%)"
    elif [ "$percentage" -le 50 ]; then
        echo "Stage 3: Majority Rollout (50%)"
    elif [ "$percentage" -le 80 ]; then
        echo "Stage 4: Near Full Rollout (80%)"
    else
        echo "Stage 5: Full Rollout (100%)"
    fi
}

# Rollout to specific stage
rollout_to_stage() {
    local stage=$1

    case "$stage" in
        0) set_rollout_percentage 0 ;;
        1) set_rollout_percentage 10 ;;
        2) set_rollout_percentage 30 ;;
        3) set_rollout_percentage 50 ;;
        4) set_rollout_percentage 80 ;;
        5) set_rollout_percentage 100 ;;
        *)
            log_error "Invalid stage. Must be 0-5"
            exit 1
            ;;
    esac

    log_success "Rolled out to Stage $stage"
}

# Rollback to previous stage
rollback() {
    local current=$(get_current_percentage)
    local target=0

    if [ "$current" -eq 100 ]; then
        target=80
    elif [ "$current" -eq 80 ]; then
        target=50
    elif [ "$current" -eq 50 ]; then
        target=30
    elif [ "$current" -eq 30 ]; then
        target=10
    elif [ "$current" -eq 10 ]; then
        target=0
    fi

    log_warning "Rolling back from ${current}% to ${target}%..."
    set_rollout_percentage "$target"
    log_success "Rollback complete"
}

# Emergency rollback to 0%
emergency_rollback() {
    log_error "EMERGENCY ROLLBACK INITIATED"
    set_rollout_percentage 0
    log_success "Emergency rollback complete - All traffic routed to Legacy API"
}

# Run smoke tests
smoke_test() {
    log_info "Running smoke tests..."

    # Test Signal API
    log_info "Testing Signal API endpoints..."

    if ! curl -s -f http://localhost:8000/health > /dev/null; then
        log_error "Signal API health check failed"
        return 1
    fi
    log_success "✓ Health endpoint OK"

    if ! curl -s -f http://localhost:8000/signals?limit=10 > /dev/null; then
        log_error "Signal API /signals endpoint failed"
        return 1
    fi
    log_success "✓ Signals endpoint OK"

    if ! curl -s -f http://localhost:8000/signals/stats > /dev/null; then
        log_error "Signal API /signals/stats endpoint failed"
        return 1
    fi
    log_success "✓ Stats endpoint OK"

    log_success "All smoke tests passed"
    return 0
}

# Show help
show_help() {
    echo "Usage: $0 [command] [arguments]"
    echo ""
    echo "Commands:"
    echo "  status                    Show current rollout status"
    echo "  set <percentage>          Set rollout percentage (0-100)"
    echo "  stage <0-5>              Roll out to specific stage"
    echo "  rollback                  Roll back to previous stage"
    echo "  emergency                 Emergency rollback to 0%"
    echo "  test                      Run smoke tests"
    echo "  help                      Show this help message"
    echo ""
    echo "Stages:"
    echo "  0: Preparation (0%)"
    echo "  1: Initial Rollout (10%)"
    echo "  2: Expanded Rollout (30%)"
    echo "  3: Majority Rollout (50%)"
    echo "  4: Near Full Rollout (80%)"
    echo "  5: Full Rollout (100%)"
    echo ""
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 set 10"
    echo "  $0 stage 2"
    echo "  $0 rollback"
    echo ""
}

# Main
main() {
    local command=${1:-status}

    case "$command" in
        status)
            show_status
            ;;
        set)
            set_rollout_percentage "$2"
            show_status
            ;;
        stage)
            rollout_to_stage "$2"
            show_status
            ;;
        rollback)
            rollback
            show_status
            ;;
        emergency)
            emergency_rollback
            show_status
            ;;
        test)
            smoke_test
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
