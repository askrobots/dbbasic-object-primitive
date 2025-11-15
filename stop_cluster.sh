#!/bin/bash
# Stop the entire cluster
# Run this from station1 (master)

# Configure for your setup
STATION2_HOST="station2.local"
STATION3_HOST="station3.local"

echo "=== Stopping 3-Station Cluster ==="
echo

echo "Stopping workers..."
ssh $STATION2_HOST 'killall python' && echo "✓ station2 stopped" || echo "⚠ station2 not running"
ssh $STATION3_HOST 'killall python' && echo "✓ station3 stopped" || echo "⚠ station3 not running"
echo

echo "Master (station1) still running on this machine"
echo "Stop manually with Ctrl+C in terminal or: killall python"
echo

echo "=== Cluster Stopped ==="
