#!/bin/bash
# Start the entire cluster
# Run this from station1 (master)

# Configure for your setup
STATION1_HOST="station1.local"
STATION2_HOST="station2.local"
STATION3_HOST="station3.local"
INSTALL_DIR="~/dbbasic-object-primitive"

echo "=== Starting 3-Station Cluster ==="
echo

echo "Starting master (station1 - this machine)..."
echo "Run manually in separate terminal:"
echo "  cd $INSTALL_DIR && source .venv/bin/activate && python run_server.py"
echo

echo "Starting workers..."
echo

echo "Starting station2..."
ssh $STATION2_HOST "cd $INSTALL_DIR && source .venv/bin/activate && STATION_ID=station2 nohup python run_server.py > server.log 2>&1 &"
sleep 2
ssh $STATION2_HOST "cd $INSTALL_DIR && STATION_ID=station2 nohup python cluster_heartbeat_daemon.py $STATION1_HOST > heartbeat.log 2>&1 &"
echo "✓ station2 started"
echo

echo "Starting station3..."
ssh $STATION3_HOST "cd $INSTALL_DIR && source .venv/bin/activate && STATION_ID=station3 nohup python run_server.py > server.log 2>&1 &"
sleep 2
ssh $STATION3_HOST "cd $INSTALL_DIR && STATION_ID=station3 nohup python cluster_heartbeat_daemon.py $STATION1_HOST > heartbeat.log 2>&1 &"
echo "✓ station3 started"
echo

echo "Waiting for stations to register..."
sleep 3
echo

echo "=== Cluster Status ==="
curl -s http://localhost:8001/cluster/stations | python3 -m json.tool

echo
echo "=== Cluster Ready ==="
echo "Master: http://localhost:8001/dashboard"
echo "Worker 2: http://$STATION2_HOST:8001/dashboard"
echo "Worker 3: http://$STATION3_HOST:8001/dashboard"
