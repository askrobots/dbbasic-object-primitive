#!/bin/bash
# Deploy code to all stations
# Run this from the master station
# Reads configuration from cluster.tsv

# Load cluster configuration
eval "$(python cluster_shell_helper.py)"

echo "=== Deploying to All Stations ==="
echo

# Deploy to worker 1
if [ -n "$WORKER1_SSH" ]; then
    echo "Deploying to $WORKER1_ID ($WORKER1_HOST)..."
    rsync -av --exclude='.venv' --exclude='data' --exclude='__pycache__' --exclude='.git' --exclude='_to_move' --exclude='cluster.tsv' \
      ./ ${WORKER1_SSH}:~/multiplexing/
    echo "✓ $WORKER1_ID deployed"
    echo
fi

# Deploy to worker 2
if [ -n "$WORKER2_SSH" ]; then
    echo "Deploying to $WORKER2_ID ($WORKER2_HOST)..."
    rsync -av --exclude='.venv' --exclude='data' --exclude='__pycache__' --exclude='.git' --exclude='_to_move' --exclude='cluster.tsv' \
      ./ ${WORKER2_SSH}:~/multiplexing/
    echo "✓ $WORKER2_ID deployed"
    echo
fi

echo "=== Deployment Complete ==="
echo "Servers will auto-reload (uvicorn --reload=True)"
echo "Run ./restart_cluster.sh to restart heartbeat daemons with new version"
