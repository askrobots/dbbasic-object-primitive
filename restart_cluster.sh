#!/bin/bash
# Restart heartbeat daemons on worker stations
# Run this from the master station after deploying new code
# Reads configuration from cluster.tsv

# Load cluster configuration
eval "$(python cluster_shell_helper.py)"

echo "=== Restarting Cluster Heartbeat Daemons ==="
echo

# Restart worker 1
if [ -n "$WORKER1_SSH" ]; then
    echo "Restarting $WORKER1_ID ($WORKER1_HOST)..."
    ssh "$WORKER1_SSH" "pkill -f cluster_heartbeat_daemon.py; sleep 1; cd ~/multiplexing && source .venv/bin/activate && nohup python cluster_heartbeat_daemon.py $MASTER_HOST --station-id $WORKER1_ID > heartbeat.log 2>&1 &"
    echo "✓ $WORKER1_ID heartbeat restarted"
    sleep 2
    echo
fi

# Restart worker 2
if [ -n "$WORKER2_SSH" ]; then
    echo "Restarting $WORKER2_ID ($WORKER2_HOST)..."
    ssh "$WORKER2_SSH" "pkill -f cluster_heartbeat_daemon.py; sleep 1; cd ~/multiplexing && source .venv/bin/activate && nohup python cluster_heartbeat_daemon.py $MASTER_HOST --station-id $WORKER2_ID > heartbeat.log 2>&1 &"
    echo "✓ $WORKER2_ID heartbeat restarted"
    sleep 2
    echo
fi

echo "=== Heartbeat Daemons Restarted ==="
echo

echo "Waiting 5 seconds for heartbeats to register..."
sleep 5
echo

echo "Cluster status:"
curl -s http://localhost:${MASTER_PORT}/cluster/stations | python3 -m json.tool | grep -E "station_id|version|is_active" | head -20
echo
echo "✓ Check dashboard: http://localhost:${MASTER_PORT}/dashboard"
