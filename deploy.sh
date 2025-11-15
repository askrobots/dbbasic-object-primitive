#!/bin/bash
# Deploy code to all stations
# Run this from station1 (master)

# Configure for your setup
STATION2_HOST="station2.local"
STATION3_HOST="station3.local"
INSTALL_DIR="~/dbbasic-object-primitive"

echo "=== Deploying to All Stations ==="
echo

echo "Deploying to station2..."
rsync -av --exclude='.venv' --exclude='data' --exclude='__pycache__' --exclude='.git' \
  ./ $STATION2_HOST:$INSTALL_DIR/
echo "✓ station2 deployed"
echo

echo "Deploying to station3..."
rsync -av --exclude='.venv' --exclude='data' --exclude='__pycache__' --exclude='.git' \
  ./ $STATION3_HOST:$INSTALL_DIR/
echo "✓ station3 deployed"
echo

echo "=== Deployment Complete ==="
echo "Servers will auto-reload (uvicorn --reload=True)"
