"""
Integration tests for 3-station cluster.

Runs a full 3-station cluster locally on high ports (9001-9003)
to test distributed features without requiring SSH or remote machines.

Tests:
- State replication across all 3 stations
- Log replication consistency
- Load balancing
- Failover scenarios
"""

import pytest
import subprocess
import time
import tempfile
import shutil
import os
import requests
from pathlib import Path


class LocalCluster:
    """Manages a 3-station cluster running locally on different ports."""

    def __init__(self):
        self.base_dir = None
        self.stations = []
        self.server_processes = []
        self.heartbeat_processes = []

    def setup(self):
        """Start a 3-station cluster locally."""
        # Create temp directory for cluster
        self.base_dir = Path(tempfile.mkdtemp(prefix="test_cluster_"))
        print(f"Test cluster base: {self.base_dir}")

        # Define stations
        self.stations = [
            {"id": "station1", "port": 9001, "is_master": True},
            {"id": "station2", "port": 9002, "is_master": False},
            {"id": "station3", "port": 9003, "is_master": False},
        ]

        # Get source directory (project root)
        source_dir = Path(__file__).parent.parent.parent

        # Create station directories with necessary files
        for station in self.stations:
            station_dir = self.base_dir / station["id"]
            station_dir.mkdir()

            # Create data directories
            (station_dir / "data" / "cluster").mkdir(parents=True)
            (station_dir / "data" / "state").mkdir(parents=True)
            (station_dir / "data" / "logs").mkdir(parents=True)
            (station_dir / "data" / "versions").mkdir(parents=True)

            # Copy entire src, api, examples directories (preserve structure)
            for dir_name in ["src", "api", "examples"]:
                src_path = source_dir / dir_name
                if src_path.exists():
                    shutil.copytree(src_path, station_dir / dir_name)

            # Copy scripts
            for script in ["run_server.py", "cluster_heartbeat_daemon.py"]:
                src_script = source_dir / script
                if src_script.exists():
                    shutil.copy(src_script, station_dir / script)

            station["dir"] = station_dir

        # Initialize cluster registry on master (station1)
        self._init_registry()

        # Start all servers
        for station in self.stations:
            self._start_server(station)

        # Wait for servers to start
        time.sleep(3)

        # Verify all servers are running
        for station in self.stations:
            url = f"http://localhost:{station['port']}/cluster/info"
            resp = requests.get(url, timeout=5)
            assert resp.status_code == 200, f"{station['id']} not responding"
            print(f"✓ {station['id']} running on port {station['port']}")

        # Start heartbeat daemons (workers only, master doesn't send heartbeats)
        for station in self.stations:
            if not station["is_master"]:
                self._start_heartbeat(station)

        # Wait for heartbeats to register
        time.sleep(3)

        print("✓ Test cluster ready")

    def _init_registry(self):
        """Initialize cluster registry on master station."""
        registry_path = self.stations[0]["dir"] / "data" / "cluster" / "stations.tsv"

        with open(registry_path, "w") as f:
            # Write header
            f.write("station_id\taddress\tport\tlast_heartbeat\tis_active\n")

            # Write all stations
            for station in self.stations:
                # Master starts as active, workers will activate via heartbeat
                is_active = "True" if station["is_master"] else "False"
                f.write(f"{station['id']}\tlocalhost\t{station['port']}\t0\t{is_active}\n")

    def _start_server(self, station):
        """Start server process for a station."""
        env = os.environ.copy()
        env["STATION_ID"] = station["id"]
        env["SERVER_PORT"] = str(station["port"])  # For SelfLogger to query correct port

        # Workers need to know where the master is (for log replication)
        if not station["is_master"]:
            master_station = self.stations[0]  # station1 is always master
            env["MASTER_HOST"] = "localhost"
            env["MASTER_PORT"] = str(master_station["port"])

        # Add packages directory to PYTHONPATH so server can import dbbasic packages
        source_dir = Path(__file__).parent.parent.parent
        packages_dir = source_dir / "packages"
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{packages_dir}:{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = str(packages_dir)

        cmd = [
            "python",
            "run_server.py",
            "--port", str(station["port"])
        ]

        log_file = open(station["dir"] / "server.log", "w")

        proc = subprocess.Popen(
            cmd,
            cwd=station["dir"],  # Run from station directory
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True  # Detach from parent
        )

        self.server_processes.append((proc, log_file))
        station["server_pid"] = proc.pid
        print(f"Started {station['id']} server (PID {proc.pid})")

    def _start_heartbeat(self, station):
        """Start heartbeat daemon for a worker station."""
        env = os.environ.copy()
        env["STATION_ID"] = station["id"]

        # Add packages directory to PYTHONPATH
        source_dir = Path(__file__).parent.parent.parent
        packages_dir = source_dir / "packages"
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{packages_dir}:{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = str(packages_dir)

        master_station = self.stations[0]  # station1 is master
        master_addr = "localhost"

        cmd = [
            "python",
            "cluster_heartbeat_daemon.py",
            master_addr,
            "--master-port", str(master_station["port"]),
            "--station-port", str(station["port"])
        ]

        log_file = open(station["dir"] / "heartbeat.log", "w")

        proc = subprocess.Popen(
            cmd,
            cwd=station["dir"],
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )

        self.heartbeat_processes.append((proc, log_file))
        station["heartbeat_pid"] = proc.pid
        print(f"Started {station['id']} heartbeat (PID {proc.pid})")

    def teardown(self):
        """Stop all processes and cleanup."""
        print("Tearing down test cluster...")

        # Kill all processes
        for proc, log_file in self.server_processes + self.heartbeat_processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            finally:
                log_file.close()

        # Clean up temp directory
        if self.base_dir and self.base_dir.exists():
            shutil.rmtree(self.base_dir)
            print(f"✓ Cleaned up {self.base_dir}")

    def get_url(self, station_id, path):
        """Get full URL for a path on a station."""
        station = next(s for s in self.stations if s["id"] == station_id)
        return f"http://localhost:{station['port']}{path}"

    def get_master_url(self, path):
        """Get full URL for a path on the master station."""
        return self.get_url("station1", path)


@pytest.fixture(scope="module")
def cluster():
    """Pytest fixture that provides a running 3-station cluster."""
    c = LocalCluster()
    c.setup()
    yield c
    c.teardown()


class TestClusterBasics:
    """Test basic cluster operations."""

    def test_all_stations_running(self, cluster):
        """Verify all 3 stations are running."""
        for station in cluster.stations:
            url = cluster.get_url(station["id"], "/cluster/info")
            resp = requests.get(url, timeout=5)
            assert resp.status_code == 200
            data = resp.json()
            assert data["station_id"] == station["id"]

    def test_registry_has_all_stations(self, cluster):
        """Verify cluster registry knows about all stations."""
        url = cluster.get_master_url("/cluster/stations")
        resp = requests.get(url, timeout=5)

        # Print error details if request failed
        if resp.status_code != 200:
            print(f"\nError: {resp.status_code}")
            print(f"Response: {resp.text}")

        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "ok"
        assert len(data["stations"]) == 3

        station_ids = [s["station_id"] for s in data["stations"]]
        assert "station1" in station_ids
        assert "station2" in station_ids
        assert "station3" in station_ids

    def test_workers_are_active(self, cluster):
        """Verify worker stations registered via heartbeat."""
        # Give heartbeats time to register
        time.sleep(5)

        url = cluster.get_master_url("/cluster/stations")
        resp = requests.get(url, timeout=5)
        data = resp.json()

        for station in data["stations"]:
            if station["station_id"] in ["station2", "station3"]:
                assert station["is_active"], f"{station['station_id']} should be active"


class TestStateReplication:
    """Test state replication across stations."""

    def test_state_replicates_to_all_stations(self, cluster):
        """Write state on station1, verify it appears on all stations."""
        # Create a test object on station1
        test_value = int(time.time())

        # Write to counter object on station1
        url = cluster.get_master_url("/objects/basics_counter")
        resp = requests.post(
            url,
            json={"value": test_value},
            headers={"Content-Type": "application/json"},
            timeout=5
        )

        # Debug: print response details
        print(f"\nPOST {url}")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text[:500]}")

        assert resp.status_code == 200

        # Wait for replication
        time.sleep(2)

        # Debug: Check what's in the data directory
        print(f"\nChecking data directories on station1...")
        station1_data = cluster.stations[0]["dir"] / "data"
        if station1_data.exists():
            import os
            for root, dirs, files in os.walk(station1_data):
                rel_path = os.path.relpath(root, station1_data)
                print(f"  {rel_path}/ - dirs: {dirs}, files: {files}")
        else:
            print(f"  data/ directory doesn't exist!")

        # Read state file on all 3 stations
        # NOTE: StateManager uses filename instead of full path ID, so "counter" not "basics_counter"
        for station in cluster.stations:
            state_file = station["dir"] / "data" / "state" / "counter" / "state.tsv"

            # State file should exist
            assert state_file.exists(), f"State file missing on {station['id']}"

            # Read state value
            with open(state_file) as f:
                lines = f.readlines()
                assert len(lines) >= 1  # Just the data line (no header)

                # Parse TSV (format: count\tVALUE\tTIMESTAMP)
                data_line = lines[0].strip().split("\t")
                actual_value = int(data_line[1])

                assert actual_value == test_value, \
                    f"State mismatch on {station['id']}: expected {test_value}, got {actual_value}"

        print(f"✓ State {test_value} replicated to all 3 stations")


class TestLogReplication:
    """Test log replication across stations."""

    def test_logs_replicate_to_all_stations(self, cluster):
        """Write logs on station2, verify they appear on all stations."""
        # Get current log count on all stations
        # NOTE: StateManager uses filename instead of full path ID, so "counter" not "basics_counter"
        initial_counts = {}
        for station in cluster.stations:
            log_file = station["dir"] / "data" / "logs" / "counter" / "log.tsv"
            if log_file.exists():
                with open(log_file) as f:
                    initial_counts[station["id"]] = len(f.readlines())
            else:
                initial_counts[station["id"]] = 0

        # Trigger some operations that generate logs (via station2)
        url = cluster.get_url("station2", "/objects/basics_counter")
        for i in range(5):
            resp = requests.post(
                url,
                json={"value": 1000 + i},
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            assert resp.status_code == 200

        # Wait for log replication
        time.sleep(3)

        # First check if logs were created on station2 (where requests were made)
        station2_log_file = cluster.stations[1]["dir"] / "data" / "logs" / "counter" / "log.tsv"
        print(f"\nChecking if logs were created on station2...")
        print(f"Log file path: {station2_log_file}")
        print(f"Exists: {station2_log_file.exists()}")

        if station2_log_file.exists():
            with open(station2_log_file) as f:
                lines = f.readlines()
                print(f"Station2 has {len(lines)} log lines")
                if len(lines) > 0:
                    print(f"First line: {lines[0][:100]}")
        else:
            # Log file doesn't exist on station2 - logging isn't working at all!
            # Let's check what directories do exist
            station2_data = cluster.stations[1]["dir"] / "data"
            print(f"\nContents of {station2_data}:")
            import os
            for root, dirs, files in os.walk(station2_data):
                rel_path = os.path.relpath(root, station2_data)
                print(f"  {rel_path}/ - dirs: {dirs}, files: {files}")

        # Require logs to exist on station2 first (origin station)
        assert station2_log_file.exists(), "Logs not created on origin station (station2)"

        with open(station2_log_file) as f:
            station2_count = len(f.readlines())
        assert station2_count > initial_counts["station2"], \
            f"No new logs on station2 (initial: {initial_counts['station2']}, final: {station2_count})"

        # Now check all stations have new logs
        for station in cluster.stations:
            log_file = station["dir"] / "data" / "logs" / "counter" / "log.tsv"
            assert log_file.exists(), f"Log file missing on {station['id']}"

            with open(log_file) as f:
                final_count = len(f.readlines())

            # Should have at least some of the 5 new logs
            # (may not be all due to fire-and-forget nature)
            new_logs = final_count - initial_counts[station["id"]]
            assert new_logs > 0, \
                f"{station['id']} has no new logs (initial: {initial_counts[station['id']]}, final: {final_count})"

        print("✓ Logs replicated to all stations")


class TestLoadBalancing:
    """Test load balancing across stations."""

    def test_stations_report_load_metrics(self, cluster):
        """Verify stations report CPU and memory metrics."""
        # Wait for heartbeats with metrics
        time.sleep(5)

        url = cluster.get_master_url("/cluster/stations")
        resp = requests.get(url, timeout=5)
        data = resp.json()

        for station in data["stations"]:
            if station["is_active"]:
                # Workers send metrics, master might not have them
                if station["station_id"] != "station1":
                    assert "metrics" in station, \
                        f"{station['station_id']} missing metrics dict"
                    metrics = station["metrics"]
                    assert "cpu_percent" in metrics or "memory_percent" in metrics, \
                        f"{station['station_id']} missing load metrics in metrics dict"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-s"])
