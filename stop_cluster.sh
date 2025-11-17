#!/bin/bash
# Stop the entire cluster
# Run this from the master station
# Reads configuration from cluster.tsv

# Load cluster configuration
eval "$(python cluster_shell_helper.py)"

echo "=== Stopping ${WORKER_COUNT}-Station Cluster ==="
echo

echo "Stopping workers..."

# Stop worker 1
if [ -n "$WORKER1_SSH" ]; then
    ssh "$WORKER1_SSH" 'killall python3' && echo "✓ $WORKER1_ID stopped" || echo "⚠ $WORKER1_ID not running"
fi

# Stop worker 2
if [ -n "$WORKER2_SSH" ]; then
    ssh "$WORKER2_SSH" 'killall python3' && echo "✓ $WORKER2_ID stopped" || echo "⚠ $WORKER2_ID not running"
fi

echo

echo "Master ($MASTER_ID) still running on this machine"
echo "Stop manually with Ctrl+C in terminal or: killall python"
echo

echo "=== Cluster Stopped ==="
