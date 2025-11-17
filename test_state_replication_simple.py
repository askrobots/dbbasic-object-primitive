#!/usr/bin/env python3
"""
Simple test: Use existing counter object to verify state replication
"""
import requests
import time
import json
from cluster_config import get_config

print("=== Testing State Replication with Counter Object ===\n")

# Step 1: Reset counter on station1
print("Step 1: Resetting counter to 0 on station1...")
response = requests.post('http://localhost:8001/objects/basics_counter', json={'value': 0})
print(f"  Response: {response.json()}")
time.sleep(1)

# Step 2: Increment counter multiple times on station1
print("\nStep 2: Incrementing counter 5 times on station1...")
for i in range(5):
    response = requests.get('http://localhost:8001/objects/basics_counter')
    data = response.json()
    print(f"  Increment {i+1}: count={data.get('count')}")
    time.sleep(0.5)

# Step 3: Wait for replication
print("\nStep 3: Waiting 5 seconds for state replication...")
time.sleep(5)

# Step 4: Check state on all stations
print("\nStep 4: Checking counter state across cluster...")

def get_counter_state(url, name):
    try:
        response = requests.get(f"{url}/objects/basics_counter", params={'state': 'true'}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            state = data.get('state', {})
            count = state.get('count', 'N/A')
            print(f"  {name}: count={count}")
            return count
        else:
            print(f"  {name}: Error - {response.status_code}")
            return None
    except Exception as e:
        print(f"  {name}: Error - {e}")
        return None

config = get_config()
master = config.get_master()
workers = config.get_workers()

# Get state from all stations
master_url = config.get_url(master['station_id'])
count_master = get_counter_state(master_url, master['station_id'])

counts = [count_master]
for worker in workers:
    worker_url = config.get_url(worker['station_id'])
    count = get_counter_state(worker_url, worker['station_id'])
    counts.append(count)

# Step 5: Verify
print("\n" + "="*60)
print("RESULTS:")
print("="*60)

if all(c == 5 for c in counts):
    print("✓ STATE REPLICATION WORKING")
    print(f"✓ All {len(counts)} stations have count=5")
    print("✓ Replace-based replication confirmed")
else:
    print("✗ STATE MISMATCH")
    print(f"  {master['station_id']}: {counts[0]}")
    for i, worker in enumerate(workers, 1):
        print(f"  {worker['station_id']}: {counts[i]}")
    print("\nNote: State replication may require manual triggering")
    print("      Objects need to explicitly call replication endpoint")

# Check state files directly via SSH on worker stations
print("\n" + "="*60)
print("Checking state files directly on workers:")
print("="*60)

import subprocess

for worker in workers:
    ssh_target = config.get_ssh_target(worker['station_id'])
    try:
        result = subprocess.run(
            ['ssh', ssh_target, 'cat ~/multiplexing/data/state/basics_counter/state.tsv 2>&1'],
            capture_output=True, text=True, timeout=5
        )
        print(f"{worker['station_id']} state file:")
        print(f"  {result.stdout.strip()}")
    except Exception as e:
        print(f"  Error reading {worker['station_id']}: {e}")
