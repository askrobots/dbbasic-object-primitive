#!/usr/bin/env python3
"""
Helper script to output cluster configuration in shell-friendly format
Usage: eval "$(python cluster_shell_helper.py)"
"""

import sys
from cluster_config import get_config


def main():
    config = get_config()

    # Output bash arrays and variables
    master = config.get_master()
    workers = config.get_workers()

    if not master:
        print("echo 'ERROR: No master station configured'", file=sys.stderr)
        sys.exit(1)

    # Master info
    print(f"export MASTER_ID='{master['station_id']}'")
    print(f"export MASTER_HOST='{master['host']}'")
    print(f"export MASTER_PORT='{master['port']}'")
    print(f"export MASTER_USER='{master['user']}'")
    print(f"export MASTER_SSH='{master['user']}@{master['host']}'")
    print()

    # Worker arrays (bash doesn't handle complex data structures well)
    # Output each worker's info as separate variables
    for i, worker in enumerate(workers, 1):
        print(f"export WORKER{i}_ID='{worker['station_id']}'")
        print(f"export WORKER{i}_HOST='{worker['host']}'")
        print(f"export WORKER{i}_PORT='{worker['port']}'")
        print(f"export WORKER{i}_USER='{worker['user']}'")
        print(f"export WORKER{i}_SSH='{worker['user']}@{worker['host']}'")
        print()

    print(f"export WORKER_COUNT={len(workers)}")


if __name__ == "__main__":
    main()
