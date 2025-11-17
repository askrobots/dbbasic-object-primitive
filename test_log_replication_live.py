#!/usr/bin/env python3
"""
Test log replication in live cluster
"""
from dbbasic_object_core.core.self_logger import SelfLogger
from cluster_config import get_config
import time

# Create logger with replication enabled
logger = SelfLogger('test_replication', base_dir='data', enable_replication=True)

print("Creating log entries with replication enabled...")
logger.info("First log entry from station1", test_number=1)
time.sleep(1)

logger.info("Second log entry from station1", test_number=2)
time.sleep(1)

logger.warning("Third entry - warning level", test_number=3)
time.sleep(1)

logger.error("Fourth entry - error level", test_number=4, extra_data="testing")
time.sleep(1)

logger.info("Fifth and final entry", test_number=5)

print("✓ Created 5 log entries with replication")
print("Waiting 3 seconds for replication to complete...")
time.sleep(3)

# Show local logs
logs = logger.get_logs()
print(f"\n✓ Local logs on station1: {len(logs)} entries")
for log in logs:
    print(f"  - {log['timestamp'][:19]} [{log['level']}] {log['message']} (entry_id: {log['entry_id'][:8]}...)")

print("\nNow check logs on worker stations:")
config = get_config()
for worker in config.get_workers():
    url = config.get_url(worker['station_id'], '/objects/test_replication?logs=true')
    print(f"  curl -s {url}")
