#!/usr/bin/env python3
"""
Cluster Management - PID-based process control for distributed cluster

Usage:
    ./cluster.py start      # Start all cluster processes
    ./cluster.py stop       # Stop all cluster processes
    ./cluster.py restart    # Restart all cluster processes
    ./cluster.py status     # Show status of all processes
    ./cluster.py deploy     # Deploy code to all stations
"""
import sys
import subprocess
import time
from pathlib import Path
from process_manager import ProcessManager
from cluster_config import get_config


class ClusterManager:
    """Manage cluster processes with PID files"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.config = get_config()
        self.master = self.config.get_master()
        self.workers = self.config.get_workers()

    def start(self):
        """Start all cluster processes"""
        print("=== Starting Cluster ===\n")

        # Start master server
        print(f"Starting master ({self.master['station_id']})...")
        server_pm = ProcessManager(f"server_{self.master['station_id']}")

        if server_pm.is_running():
            print(f"✓ {self.master['station_id']} already running (PID {server_pm.get_pid()})")
        else:
            subprocess.Popen(
                ['python', 'run_server.py', '--port', str(self.master['port'])],
                env={**dict(subprocess.os.environ), 'STATION_ID': self.master['station_id']},
                stdout=open('server.log', 'w'),
                stderr=subprocess.STDOUT,
                cwd=self.base_dir,
            )
            time.sleep(2)

            # Get PID and write PID file
            result = subprocess.run(
                ['pgrep', '-f', 'python run_server.py'],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                pid = int(result.stdout.strip().split()[0])
                server_pm.write_pid(pid)
                print(f"✓ {self.master['station_id']} started (PID {pid})")
            else:
                print(f"✗ {self.master['station_id']} failed to start")

        # Start worker stations
        for worker in self.workers:
            self._start_worker(worker)

        print("\n=== Cluster Started ===")
        time.sleep(2)
        self.status()

    def _start_worker(self, worker: dict):
        """Start worker station server and heartbeat daemon"""
        station_id = worker['station_id']
        host = worker['host']
        port = worker['port']
        ssh_target = self.config.get_ssh_target(station_id)

        print(f"\nStarting {station_id} ({host})...")

        # Start server on worker
        server_cmd = f"cd ~/multiplexing && STATION_ID={station_id} nohup .venv/bin/python run_server.py --port {port} > server.log 2>&1 < /dev/null & echo $!"
        result = subprocess.run(
            ['ssh', ssh_target, server_cmd],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            server_pid = result.stdout.strip()
            print(f"  Server: PID {server_pid}")
        else:
            print(f"  Server: Failed to start")

        time.sleep(2)

        # Start heartbeat daemon on worker
        master_host = self.master['host']
        hb_cmd = f"cd ~/multiplexing && STATION_ID={station_id} nohup .venv/bin/python cluster_heartbeat_daemon.py {master_host} > heartbeat.log 2>&1 < /dev/null & echo $!"
        result = subprocess.run(
            ['ssh', ssh_target, hb_cmd],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            hb_pid = result.stdout.strip()
            print(f"  Heartbeat: PID {hb_pid}")
            print(f"✓ {station_id} started")
        else:
            print(f"  Heartbeat: Failed to start")

    def stop(self):
        """Stop all cluster processes"""
        print("=== Stopping Cluster ===\n")

        # Stop workers first
        for worker in self.workers:
            self._stop_worker(worker)

        # Stop master
        print(f"\nStopping master ({self.master['station_id']})...")
        server_pm = ProcessManager(f"server_{self.master['station_id']}")
        server_pm.stop()

        print("\n=== Cluster Stopped ===")

    def _stop_worker(self, worker: dict):
        """Stop worker station processes"""
        station_id = worker['station_id']
        host = worker['host']
        ssh_target = self.config.get_ssh_target(station_id)

        print(f"Stopping {station_id} ({host})...")

        # Kill all Python processes (servers and heartbeat daemons)
        cmd = "pkill -f 'python.*run_server.py' && pkill -f 'python.*cluster_heartbeat_daemon.py'"
        subprocess.run(['ssh', ssh_target, cmd], capture_output=True)

        print(f"✓ {station_id} stopped")

    def restart(self):
        """Restart all cluster processes"""
        self.stop()
        time.sleep(2)
        self.start()

    def status(self):
        """Show status of all cluster processes"""
        print("=== Cluster Status ===\n")

        # Check master
        server_pm = ProcessManager(f"server_{self.master['station_id']}")
        status = server_pm.status()

        if status['running']:
            print(f"{self.master['station_id']} (master): RUNNING (PID {status['pid']})")
        else:
            print(f"{self.master['station_id']} (master): NOT RUNNING")

        # Check workers via curl
        for worker in self.workers:
            station_id = worker['station_id']
            url = self.config.get_url(station_id, '/cluster/stations')

            try:
                result = subprocess.run(
                    ['curl', '-s', '--max-time', '2', url],
                    capture_output=True,
                    text=True,
                    timeout=3
                )

                if result.returncode == 0 and 'station_id' in result.stdout:
                    print(f"{station_id}: RUNNING")
                else:
                    print(f"{station_id}: NOT RESPONDING")
            except subprocess.TimeoutExpired:
                print(f"{station_id}: TIMEOUT")

    def deploy(self):
        """Deploy code to all stations"""
        print("=== Deploying to All Stations ===\n")

        for worker in self.workers:
            station_id = worker['station_id']
            host = worker['host']
            ssh_target = self.config.get_ssh_target(station_id)

            print(f"Deploying to {station_id} ({host})...")

            cmd = [
                'rsync', '-av', '--delete',
                '--exclude', '.git',
                '--exclude', '.venv',
                '--exclude', '__pycache__',
                '--exclude', '*.pyc',
                '--exclude', 'pids/',
                '--exclude', '*.pid',
                '--exclude', '_to_move/',
                '--exclude', 'cluster.tsv',
                f'{self.base_dir}/',
                f'{ssh_target}:~/multiplexing/'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✓ {station_id} deployed")
            else:
                print(f"✗ {station_id} deployment failed")
                print(result.stderr)

        print("\n=== Deployment Complete ===")


def main():
    if len(sys.argv) < 2:
        print("Usage: ./cluster.py {start|stop|restart|status|deploy}")
        sys.exit(1)

    command = sys.argv[1]
    manager = ClusterManager()

    if command == 'start':
        manager.start()
    elif command == 'stop':
        manager.stop()
    elif command == 'restart':
        manager.restart()
    elif command == 'status':
        manager.status()
    elif command == 'deploy':
        manager.deploy()
    else:
        print(f"Unknown command: {command}")
        print("Usage: ./cluster.py {start|stop|restart|status|deploy}")
        sys.exit(1)


if __name__ == '__main__':
    main()
