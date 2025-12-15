#!/bin/bash

# Performance Monitoring Script
# Collects and compares Signal API vs Legacy API metrics
# Usage: ./monitor_performance.sh [duration_seconds]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SIGNAL_API="http://localhost:8000"
LEGACY_API="http://localhost:9000"
DURATION=${1:-60}  # Default 60 seconds
SAMPLE_INTERVAL=5  # Sample every 5 seconds

# Metrics arrays
declare -a signal_response_times
declare -a legacy_response_times
signal_success=0
signal_failures=0
legacy_success=0
legacy_failures=0

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

# Test Signal API endpoint
test_signal_api() {
    local start_time=$(date +%s%N)
    local response=$(curl -s -w "\n%{http_code}" "${SIGNAL_API}/signals?limit=10" 2>/dev/null)
    local end_time=$(date +%s%N)
    local http_code=$(echo "$response" | tail -n1)
    local duration_ms=$(( (end_time - start_time) / 1000000 ))

    if [ "$http_code" = "200" ]; then
        signal_response_times+=($duration_ms)
        ((signal_success++))
        return 0
    else
        ((signal_failures++))
        return 1
    fi
}

# Calculate statistics
calculate_stats() {
    local arr=("$@")
    local count=${#arr[@]}

    if [ $count -eq 0 ]; then
        echo "0:0:0:0:0"
        return
    fi

    # Sort array
    IFS=$'\n' sorted=($(sort -n <<<"${arr[*]}"))
    unset IFS

    # Calculate metrics
    local sum=0
    for val in "${sorted[@]}"; do
        sum=$((sum + val))
    done
    local avg=$((sum / count))
    local min=${sorted[0]}
    local max=${sorted[-1]}
    local p50_idx=$((count / 2))
    local p95_idx=$((count * 95 / 100))
    local p50=${sorted[$p50_idx]}
    local p95=${sorted[$p95_idx]}

    echo "$avg:$min:$max:$p50:$p95"
}

# Main monitoring loop
run_monitoring() {
    log_info "Starting performance monitoring for ${DURATION} seconds..."
    log_info "Sampling every ${SAMPLE_INTERVAL} seconds"
    echo ""

    local elapsed=0
    while [ $elapsed -lt $DURATION ]; do
        # Test Signal API
        if test_signal_api; then
            echo -ne "\r${CYAN}[$(date +%H:%M:%S)]${NC} Signal API: ${GREEN}✓${NC} Success: $signal_success, Failures: $signal_failures"
        else
            echo -ne "\r${CYAN}[$(date +%H:%M:%S)]${NC} Signal API: ${RED}✗${NC} Success: $signal_success, Failures: $signal_failures"
        fi

        sleep $SAMPLE_INTERVAL
        elapsed=$((elapsed + SAMPLE_INTERVAL))
    done

    echo ""
    echo ""
}

# Generate report
generate_report() {
    echo ""
    echo "=========================================="
    echo "  Performance Monitoring Report"
    echo "=========================================="
    echo ""
    echo "Duration: ${DURATION}s"
    echo "Sample Interval: ${SAMPLE_INTERVAL}s"
    echo "Total Samples: $((signal_success + signal_failures))"
    echo ""

    # Signal API stats
    local signal_stats=$(calculate_stats "${signal_response_times[@]}")
    IFS=':' read -r sig_avg sig_min sig_max sig_p50 sig_p95 <<< "$signal_stats"

    echo "=== Signal API ($SIGNAL_API) ==="
    echo "Success Rate: ${signal_success}/$((signal_success + signal_failures)) ($(awk "BEGIN {printf \"%.1f\", $signal_success * 100 / ($signal_success + $signal_failures)}")%)"
    echo "Response Times (ms):"
    echo "  Average: ${sig_avg}ms"
    echo "  Min: ${sig_min}ms"
    echo "  Max: ${sig_max}ms"
    echo "  P50: ${sig_p50}ms"
    echo "  P95: ${sig_p95}ms"
    echo ""

    # Status indicators
    local status="✅ EXCELLENT"
    if [ $sig_avg -gt 200 ]; then
        status="⚠️  DEGRADED"
    fi
    if [ $sig_avg -gt 500 ]; then
        status="❌ POOR"
    fi

    echo "Overall Status: $status"
    echo ""

    # Success criteria check
    echo "=== Success Criteria Check ==="
    local criteria_met=0
    local criteria_total=3

    # Error rate < 1%
    local error_rate=$(awk "BEGIN {printf \"%.2f\", $signal_failures * 100 / ($signal_success + $signal_failures)}")
    if (( $(awk "BEGIN {print ($error_rate < 1)}") )); then
        echo "✅ Error Rate: ${error_rate}% (< 1%)"
        ((criteria_met++))
    else
        echo "❌ Error Rate: ${error_rate}% (>= 1%)"
    fi

    # P95 < 200ms
    if [ $sig_p95 -lt 200 ]; then
        echo "✅ P95 Latency: ${sig_p95}ms (< 200ms)"
        ((criteria_met++))
    else
        echo "❌ P95 Latency: ${sig_p95}ms (>= 200ms)"
    fi

    # Average < 100ms
    if [ $sig_avg -lt 100 ]; then
        echo "✅ Average Latency: ${sig_avg}ms (< 100ms)"
        ((criteria_met++))
    else
        echo "⚠️  Average Latency: ${sig_avg}ms (>= 100ms)"
    fi

    echo ""
    echo "Criteria Met: ${criteria_met}/${criteria_total}"

    if [ $criteria_met -eq $criteria_total ]; then
        log_success "All criteria met! Ready to proceed to next stage."
        return 0
    elif [ $criteria_met -ge 2 ]; then
        log_warning "Most criteria met. Consider proceeding with caution."
        return 1
    else
        log_error "Insufficient criteria met. Consider rollback or investigation."
        return 2
    fi
}

# Export metrics to JSON
export_metrics() {
    local output_file="monitoring_results_$(date +%Y%m%d_%H%M%S).json"

    cat > "$output_file" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "duration_seconds": $DURATION,
  "signal_api": {
    "url": "$SIGNAL_API",
    "success_count": $signal_success,
    "failure_count": $signal_failures,
    "success_rate": $(awk "BEGIN {printf \"%.2f\", $signal_success * 100 / ($signal_success + $signal_failures)}"),
    "response_times_ms": $(printf '%s\n' "${signal_response_times[@]}" | jq -s .)
  }
}
EOF

    log_success "Metrics exported to: $output_file"
}

# Main
main() {
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║  Performance Monitoring Tool           ║"
    echo "║  Signal API Grayscale Rollout          ║"
    echo "╚════════════════════════════════════════╝"
    echo ""

    # Check if Signal API is available
    if ! curl -s -f "${SIGNAL_API}/health" > /dev/null 2>&1; then
        log_error "Signal API is not available at $SIGNAL_API"
        exit 1
    fi

    log_success "Signal API is available"

    # Run monitoring
    run_monitoring

    # Generate report
    generate_report
    local result=$?

    # Export metrics
    export_metrics

    exit $result
}

main "$@"
