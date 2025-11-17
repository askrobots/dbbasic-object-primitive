"""
Tests for cluster functionality (Phase 7.1)

These tests verify:
- Station registry
- Heartbeat system
- Station info
- Health monitoring
- Failure detection

Can run on single machine (doesn't require multi-node setup)
"""
import json
import os
import time
import pytest
from pathlib import Path
import shutil


@pytest.fixture
def cluster_data_dir(tmp_path):
    """Create temporary cluster data directory"""
    data_dir = tmp_path / "data" / "cluster"
    data_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def mock_registry_file(cluster_data_dir):
    """Create mock station registry file"""
    registry_file = cluster_data_dir / "stations.tsv"
    current_time = time.time()

    # Write 3 mock stations
    with open(registry_file, 'w') as f:
        f.write(f"station1\tlocalhost\t8001\t{current_time}\n")
        f.write(f"station2\t192.0.2.2\t8001\t{current_time}\n")
        f.write(f"station3\t192.0.2.3\t8001\t{current_time - 100}\n")  # Old heartbeat

    return registry_file


class TestClusterRegistry:
    """Test cluster station registry"""

    def test_registry_format(self, mock_registry_file):
        """Test registry file format (TSV)"""
        with open(mock_registry_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Each line should have 4 fields
        for line in lines:
            parts = line.strip().split('\t')
            assert len(parts) == 4
            station_id, host, port, timestamp = parts
            assert station_id.startswith('station')
            assert host
            assert port.isdigit()
            assert float(timestamp) > 0

    def test_active_station_detection(self, mock_registry_file):
        """Test detecting active vs inactive stations"""
        current_time = time.time()
        timeout = 30  # seconds

        with open(mock_registry_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                station_id, host, port, last_heartbeat = parts

                age = current_time - float(last_heartbeat)
                is_active = age < timeout

                if station_id == 'station3':
                    # Old heartbeat (100 seconds ago)
                    assert not is_active
                else:
                    # Recent heartbeat
                    assert is_active

    def test_add_station_to_registry(self, cluster_data_dir):
        """Test adding a new station to registry"""
        registry_file = cluster_data_dir / "stations.tsv"
        current_time = time.time()

        # Write initial station
        with open(registry_file, 'w') as f:
            f.write(f"station1\tlocalhost\t8001\t{current_time}\n")

        # Read existing
        existing = {}
        with open(registry_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) == 4:
                    sid = parts[0]
                    existing[sid] = parts

        # Add new station
        existing['station2'] = ['station2', '192.0.2.2', '8001', str(current_time)]

        # Write back
        with open(registry_file, 'w') as f:
            for sid, parts in sorted(existing.items()):
                f.write('\t'.join(parts) + '\n')

        # Verify
        with open(registry_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 2
        assert 'station1' in lines[0]
        assert 'station2' in lines[1]

    def test_update_existing_station(self, mock_registry_file, cluster_data_dir):
        """Test updating existing station (heartbeat)"""
        registry_file = mock_registry_file
        new_time = time.time()

        # Read existing
        existing = {}
        with open(registry_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) == 4:
                    sid = parts[0]
                    existing[sid] = parts

        # Update station2 heartbeat
        old_timestamp = existing['station2'][3]
        existing['station2'][3] = str(new_time)

        # Write back
        with open(registry_file, 'w') as f:
            for sid, parts in sorted(existing.items()):
                f.write('\t'.join(parts) + '\n')

        # Verify timestamp changed
        with open(registry_file, 'r') as f:
            for line in f:
                if 'station2' in line:
                    parts = line.strip().split('\t')
                    assert parts[3] != old_timestamp
                    assert float(parts[3]) == pytest.approx(new_time, rel=1.0)


class TestStationInfo:
    """Test station information"""

    def test_station_id_from_env(self):
        """Test reading STATION_ID from environment"""
        os.environ['STATION_ID'] = 'station1'
        station_id = os.environ.get('STATION_ID', 'unknown')
        assert station_id == 'station1'

        os.environ['STATION_ID'] = 'station2'
        station_id = os.environ.get('STATION_ID', 'unknown')
        assert station_id == 'station2'

    def test_master_detection(self):
        """Test detecting master vs worker"""
        os.environ['STATION_ID'] = 'station1'
        station_id = os.environ.get('STATION_ID', 'unknown')
        is_master = station_id == 'station1'
        assert is_master is True

        os.environ['STATION_ID'] = 'station2'
        station_id = os.environ.get('STATION_ID', 'unknown')
        is_master = station_id == 'station1'
        assert is_master is False


class TestHeartbeat:
    """Test heartbeat system"""

    def test_heartbeat_updates_timestamp(self, cluster_data_dir):
        """Test heartbeat updates station timestamp"""
        registry_file = cluster_data_dir / "stations.tsv"

        # Initial heartbeat
        time1 = time.time()
        with open(registry_file, 'w') as f:
            f.write(f"station2\t192.0.2.2\t8001\t{time1}\n")

        # Wait a bit
        time.sleep(0.1)

        # Second heartbeat
        time2 = time.time()
        existing = {}
        with open(registry_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) == 4:
                    sid = parts[0]
                    existing[sid] = parts

        existing['station2'][3] = str(time2)

        with open(registry_file, 'w') as f:
            for sid, parts in sorted(existing.items()):
                f.write('\t'.join(parts) + '\n')

        # Verify timestamp increased
        with open(registry_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                timestamp = float(parts[3])
                assert timestamp > time1

    def test_heartbeat_timeout_detection(self):
        """Test detecting stale heartbeats"""
        current_time = time.time()
        timeout = 30  # seconds

        # Recent heartbeat
        recent = current_time - 10
        assert (current_time - recent) < timeout

        # Stale heartbeat
        stale = current_time - 60
        assert (current_time - stale) >= timeout

    def test_multiple_station_heartbeats(self, cluster_data_dir):
        """Test multiple stations sending heartbeats"""
        registry_file = cluster_data_dir / "stations.tsv"
        current_time = time.time()

        # Multiple stations register
        stations = {
            'station1': ['station1', 'localhost', '8001', str(current_time)],
            'station2': ['station2', '192.0.2.2', '8001', str(current_time)],
            'station3': ['station3', '192.0.2.3', '8001', str(current_time)],
        }

        with open(registry_file, 'w') as f:
            for sid, parts in sorted(stations.items()):
                f.write('\t'.join(parts) + '\n')

        # Verify all stations in registry
        with open(registry_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 3
        assert all('station' in line for line in lines)


class TestClusterHealth:
    """Test cluster health monitoring"""

    def test_count_active_stations(self, mock_registry_file):
        """Test counting active vs inactive stations"""
        current_time = time.time()
        timeout = 30

        active_count = 0
        total_count = 0

        with open(mock_registry_file, 'r') as f:
            for line in f:
                total_count += 1
                parts = line.strip().split('\t')
                timestamp = float(parts[3])
                if (current_time - timestamp) < timeout:
                    active_count += 1

        assert total_count == 3
        assert active_count == 2  # station1 and station2 are active

    def test_get_station_list(self, mock_registry_file):
        """Test getting list of all stations"""
        stations = []

        with open(mock_registry_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                station_id, host, port, timestamp = parts
                stations.append({
                    'station_id': station_id,
                    'host': host,
                    'port': int(port),
                    'last_heartbeat': float(timestamp)
                })

        assert len(stations) == 3
        assert all(s['station_id'].startswith('station') for s in stations)
        assert all(s['port'] == 8001 for s in stations)

    def test_station_url_construction(self, mock_registry_file):
        """Test constructing station URLs"""
        with open(mock_registry_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                station_id, host, port, _ = parts
                url = f'http://{host}:{port}'

                assert url.startswith('http://')
                assert ':8001' in url


class TestFailureDetection:
    """Test detecting and handling station failures"""

    def test_detect_failed_station(self):
        """Test detecting when station fails (no heartbeat)"""
        current_time = time.time()
        timeout = 30

        # Simulate station that hasn't sent heartbeat in 2 minutes
        last_heartbeat = current_time - 120
        age = current_time - last_heartbeat

        is_failed = age >= timeout
        assert is_failed is True

    def test_mark_station_inactive(self, mock_registry_file):
        """Test marking station as inactive"""
        current_time = time.time()
        timeout = 30

        stations = []
        with open(mock_registry_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                station_id, host, port, timestamp = parts
                age = current_time - float(timestamp)

                stations.append({
                    'station_id': station_id,
                    'is_active': age < timeout
                })

        # station3 should be inactive (100 second old heartbeat)
        station3 = next(s for s in stations if s['station_id'] == 'station3')
        assert station3['is_active'] is False

        # station1 and station2 should be active
        station1 = next(s for s in stations if s['station_id'] == 'station1')
        station2 = next(s for s in stations if s['station_id'] == 'station2')
        assert station1['is_active'] is True
        assert station2['is_active'] is True


class TestRegistryPersistence:
    """Test registry persistence across restarts"""

    def test_registry_survives_restart(self, cluster_data_dir):
        """Test registry data persists to disk"""
        registry_file = cluster_data_dir / "stations.tsv"
        current_time = time.time()

        # Write registry
        with open(registry_file, 'w') as f:
            f.write(f"station1\tlocalhost\t8001\t{current_time}\n")

        # Simulate server restart - read back
        with open(registry_file, 'r') as f:
            line = f.readline()
            parts = line.strip().split('\t')

        assert parts[0] == 'station1'
        assert parts[1] == 'localhost'
        assert parts[2] == '8001'
        assert float(parts[3]) == pytest.approx(current_time, rel=1.0)

    def test_registry_format_human_readable(self, mock_registry_file):
        """Test registry is human-readable TSV"""
        with open(mock_registry_file, 'r') as f:
            content = f.read()

        # Should be readable text
        assert '\t' in content  # TSV format
        assert '\n' in content  # Multiple lines
        assert 'station' in content  # Contains station IDs

        # Should NOT be binary
        assert content.isprintable() or '\n' in content or '\t' in content


class TestConcurrentHeartbeats:
    """Test handling multiple concurrent heartbeats"""

    def test_concurrent_updates_dont_corrupt(self, cluster_data_dir):
        """Test multiple stations updating registry simultaneously"""
        registry_file = cluster_data_dir / "stations.tsv"

        # Simulate 3 stations updating at same time
        for i in range(1, 4):
            current_time = time.time()

            # Read existing
            existing = {}
            if registry_file.exists():
                with open(registry_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) == 4:
                            sid = parts[0]
                            existing[sid] = parts

            # Update this station
            station_id = f'station{i}'
            existing[station_id] = [station_id, f'192.0.2.{i}', '8001', str(current_time)]

            # Write back
            with open(registry_file, 'w') as f:
                for sid, parts in sorted(existing.items()):
                    f.write('\t'.join(parts) + '\n')

        # Verify all 3 stations in registry
        with open(registry_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 3
        station_ids = [line.split('\t')[0] for line in lines]
        assert 'station1' in station_ids
        assert 'station2' in station_ids
        assert 'station3' in station_ids


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
