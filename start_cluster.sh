#!/bin/bash
# Start the entire cluster
# Run this from the master station
# Reads configuration from cluster.tsv

# Load cluster configuration
eval "$(python cluster_shell_helper.py)"

echo "=== Starting ${WORKER_COUNT}-Station Cluster ==="
echo

echo "Starting master ($MASTER_ID - this machine)..."
echo "Run manually in separate terminal:"
echo "  cd /Users/danq/multiplexing && source .venv/bin/activate && python run_server.py"
echo

echo "Starting workers..."
echo

# Start worker 1 (station2)
if [ -n "$WORKER1_ID" ]; then
    echo "Starting $WORKER1_ID ($WORKER1_HOST)..."
    ssh "$WORKER1_SSH" "cd ~/multiplexing && source .venv/bin/activate && STATION_ID=$WORKER1_ID nohup .venv/bin/python run_server.py > server.log 2>&1 &"
    sleep 2
    ssh "$WORKER1_SSH" "cd ~/multiplexing && source .venv/bin/activate && nohup .venv/bin/python cluster_heartbeat_daemon.py $MASTER_HOST --station-id $WORKER1_ID > heartbeat.log 2>&1 &"
    echo "✓ $WORKER1_ID started"
    echo
fi

# Start worker 2 (station3)
if [ -n "$WORKER2_ID" ]; then
    echo "Starting $WORKER2_ID ($WORKER2_HOST)..."
    ssh "$WORKER2_SSH" "cd ~/multiplexing && source .venv/bin/activate && STATION_ID=$WORKER2_ID nohup .venv/bin/python run_server.py > server.log 2>&1 &"
    sleep 2
    ssh "$WORKER2_SSH" "cd ~/multiplexing && source .venv/bin/activate && nohup .venv/bin/python cluster_heartbeat_daemon.py $MASTER_HOST --station-id $WORKER2_ID > heartbeat.log 2>&1 &"
    echo "✓ $WORKER2_ID started"
    echo
fi

echo "Waiting for stations to register..."
sleep 3
echo

echo "=== Cluster Status ==="
curl -s http://localhost:${MASTER_PORT}/cluster/stations | python3 -m json.tool

echo
echo "=== Cluster Ready ==="
echo "Master: http://localhost:${MASTER_PORT}/dashboard"
[ -n "$WORKER1_HOST" ] && echo "Worker 1: http://${WORKER1_HOST}:${WORKER1_PORT}/dashboard"
[ -n "$WORKER2_HOST" ] && echo "Worker 2: http://${WORKER2_HOST}:${WORKER2_PORT}/dashboard"
