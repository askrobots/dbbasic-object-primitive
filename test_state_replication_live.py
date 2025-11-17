#!/usr/bin/env python3
"""
Test state replication in live cluster
"""
import json
import requests
import time
from cluster_config import get_config

def create_counter_object():
    """Create a simple counter object on station1"""
    print("Creating counter object on station1...")

    code = '''
import json
from pathlib import Path

# Initialize counter state
state_file = Path('data/state/test_counter/state.tsv')
state_file.parent.mkdir(parents=True, exist_ok=True)

# Create initial state
state = {
    'count': 0,
    'last_update': '2025-11-16T00:00:00'
}

# Write state
with open(state_file, 'w') as f:
    f.write('timestamp\\tdata\\n')
    f.write(f'2025-11-16T00:00:00\\t{json.dumps(state)}\\n')

print(f"Created counter with state: {state}")
'''

    response = requests.post(
        'http://localhost:8001/objects/test_counter/execute',
        json={'code': code},
        timeout=10
    )

    if response.status_code == 200:
        print("✓ Counter object created")
        return True
    else:
        print(f"✗ Failed to create counter: {response.text}")
        return False

def update_counter_state(count_value):
    """Update counter state on station1"""
    print(f"\nUpdating counter to {count_value}...")

    code = f'''
import json
import time
from pathlib import Path

# Update counter state
state_file = Path('data/state/test_counter/state.tsv')

state = {{
    'count': {count_value},
    'last_update': time.strftime('%Y-%m-%dT%H:%M:%S')
}}

# Write state (this should trigger replication)
timestamp = time.time()
with open(state_file, 'w') as f:
    f.write('timestamp\\tdata\\n')
    f.write(f'{{timestamp}}\\t{{json.dumps(state)}}\\n')

print(f"Updated counter to {{state}}")

# Trigger replication manually
import os
import threading

def replicate():
    try:
        import requests

        # Get cluster stations
        stations_response = requests.get('http://localhost:8001/cluster/stations', timeout=2)
        stations_data = stations_response.json()

        for station in stations_data.get('stations', []):
            if station['station_id'] == os.environ.get('STATION_ID', 'station1'):
                continue
            if not station.get('is_active', False):
                continue

            # Replicate state to this station
            url = f"{{station['url']}}/cluster/replicate"
            payload = {{
                'object_id': 'test_counter',
                'timestamp': timestamp,
                'state': state,
                'source_station': os.environ.get('STATION_ID', 'station1')
            }}
            requests.post(url, json=payload, timeout=0.5)
    except:
        pass

thread = threading.Thread(target=replicate, daemon=True)
thread.start()
'''

    response = requests.post(
        'http://localhost:8001/objects/test_counter/execute',
        json={'code': code},
        timeout=10
    )

    if response.status_code == 200:
        print(f"✓ Counter updated to {count_value}")
        return True
    else:
        print(f"✗ Failed to update counter: {response.text}")
        return False

def check_state_on_station(station_url, station_name):
    """Check state file on a station"""
    print(f"\nChecking state on {station_name}...")

    try:
        response = requests.get(
            f"{station_url}/objects/test_counter",
            params={'state': 'true'},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            state = data.get('state')
            if state:
                print(f"  State: count={state.get('count')}, last_update={state.get('last_update')}")
                return state
            else:
                print("  No state found")
                return None
        else:
            print(f"  Error: {response.text}")
            return None
    except Exception as e:
        print(f"  Error: {e}")
        return None

def main():
    print("=== Testing State Replication ===\n")

    # Create counter
    if not create_counter_object():
        return

    time.sleep(2)

    # Update counter several times
    for i in [1, 5, 10, 15]:
        if not update_counter_state(i):
            return
        time.sleep(2)

    print("\n" + "="*50)
    print("Waiting 5 seconds for replication to complete...")
    print("="*50)
    time.sleep(5)

    # Check state on all stations
    print("\n=== Checking State Across Cluster ===")

    config = get_config()
    master = config.get_master()
    workers = config.get_workers()

    # Check master
    master_url = config.get_url(master['station_id'])
    state_master = check_state_on_station(master_url, master['station_id'])

    # Check workers
    states = [state_master]
    for worker in workers:
        worker_url = config.get_url(worker['station_id'])
        state = check_state_on_station(worker_url, worker['station_id'])
        states.append(state)

    print("\n=== Results ===")

    if all(states):
        counts = [s.get('count') for s in states]
        if all(c == 15 for c in counts):
            print("✓ State replication PASSED")
            print(f"✓ All {len(states)} stations have count=15 (latest state)")
            print("✓ Replace-based replication working correctly")
        else:
            print("✗ State mismatch across stations")
            print(f"  {master['station_id']}: {counts[0]}")
            for i, worker in enumerate(workers, 1):
                print(f"  {worker['station_id']}: {counts[i]}")
    else:
        print("✗ Some stations missing state")
        print(f"  {master['station_id']}: {'found' if states[0] else 'missing'}")
        for i, worker in enumerate(workers, 1):
            print(f"  {worker['station_id']}: {'found' if states[i] else 'missing'}")

if __name__ == '__main__':
    main()
