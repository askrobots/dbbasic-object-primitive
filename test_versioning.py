"""
Test Phase 3: Versioning System

Tests for version retrieval and rollback functionality.
"""

import requests
import json

BASE_URL = 'http://localhost:8001'


def test_get_version():
    """Test getting specific version"""
    print('\n=== Test 1: Get Specific Version ===')

    # First, update the counter object to create versions
    # Get current source
    response = requests.get(f'{BASE_URL}/objects/basics_counter?source=true')
    data = response.json()
    original_source = data['source']
    print(f"Original source length: {len(original_source)} chars")

    # Modify it to create version 2
    new_source = original_source.replace('count = 1', 'count = 100')
    response = requests.put(
        f'{BASE_URL}/objects/basics_counter?source=true',
        json={
            'code': new_source,
            'author': 'test_user',
            'message': 'Change count to 100'
        }
    )
    print(f"Update status: {response.json()['status']}")
    assert response.json()['status'] == 'ok'

    # Modify again to create version 3
    new_source2 = new_source.replace('count = 100', 'count = 999')
    response = requests.put(
        f'{BASE_URL}/objects/basics_counter?source=true',
        json={
            'code': new_source2,
            'author': 'test_user',
            'message': 'Change count to 999'
        }
    )
    print(f"Update status: {response.json()['status']}")
    assert response.json()['status'] == 'ok'

    # Now get version 1 (original)
    response = requests.get(f'{BASE_URL}/objects/basics_counter?version=1')
    data = response.json()

    print(f"\nVersion 1 retrieval:")
    print(f"  Status: {response.status_code}")
    print(f"  Timestamp: {data['version'].get('timestamp', 'N/A')}")
    print(f"  Author: {data['version'].get('author', 'N/A')}")
    print(f"  Message: {data['version'].get('message', 'N/A')}")
    print(f"  Content contains 'count = 1': {'count = 1' in data['version']['content']}")

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert 'version' in data
    assert 'content' in data['version']
    assert 'count = 1' in data['version']['content']  # Original value

    # Get version 2
    response = requests.get(f'{BASE_URL}/objects/basics_counter?version=2')
    data = response.json()

    print(f"\nVersion 2 retrieval:")
    print(f"  Content contains 'count = 100': {'count = 100' in data['version']['content']}")

    assert 'count = 100' in data['version']['content']  # Modified value

    print('\n✅ Version retrieval works')


def test_rollback():
    """Test rollback to previous version"""
    print('\n=== Test 2: Rollback to Previous Version ===')

    # Rollback to version 1
    response = requests.post(
        f'{BASE_URL}/objects/basics_counter',
        json={
            'action': 'rollback',
            'version_id': 1,
            'author': 'test_user',
            'message': 'Rollback to original version'
        }
    )
    data = response.json()

    print(f"Rollback response:")
    print(f"  Status: {response.status_code}")
    print(f"  Message: {data.get('message', 'N/A')}")

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert 'Rolled back' in data['message']
    assert data['version_id'] == 1

    # Verify source code is back to version 1
    response = requests.get(f'{BASE_URL}/objects/basics_counter?source=true')
    data = response.json()

    print(f"\nCurrent source after rollback:")
    print(f"  Contains 'count = 1': {'count = 1' in data['source']}")

    assert 'count = 1' in data['source']  # Should be back to original

    # Verify version history shows the rollback as a new version
    response = requests.get(f'{BASE_URL}/objects/basics_counter?versions=true')
    data = response.json()

    print(f"\nVersion history after rollback:")
    print(f"  Total versions: {data['count']}")
    if data['count'] >= 4:
        latest = data['versions'][0]  # Newest first
        print(f"  Latest version message: {latest.get('message', 'N/A')}")
        assert 'Rollback' in latest.get('message', '')

    print('\n✅ Rollback works')


def test_invalid_version():
    """Test error handling for invalid version"""
    print('\n=== Test 3: Invalid Version Handling ===')

    # Try to get non-existent version
    response = requests.get(f'{BASE_URL}/objects/basics_counter?version=999')
    data = response.json()

    print(f"Invalid version response:")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {data}")

    assert response.status_code == 404
    # Error response might be in different format
    if 'status' in data:
        assert data['status'] == 'error'
    if 'message' in data:
        assert 'not found' in data['message'].lower()

    # Try rollback to non-existent version
    response = requests.post(
        f'{BASE_URL}/objects/basics_counter',
        json={
            'action': 'rollback',
            'version_id': 999,
            'author': 'test_user',
            'message': 'Should fail'
        }
    )
    data = response.json()

    print(f"\nInvalid rollback response:")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {data}")

    # Should be an error (either 4xx or 5xx or status='error')
    if 'status' in data:
        assert data['status'] == 'error'
    else:
        # If no status field, check HTTP status code
        assert response.status_code >= 400

    print('\n✅ Error handling works')


if __name__ == '__main__':
    print('Testing Phase 3: Versioning System')
    print('=' * 50)

    try:
        # Test version retrieval
        test_get_version()

        # Test rollback
        test_rollback()

        # Test error handling
        test_invalid_version()

        print('\n' + '=' * 50)
        print('✅ All versioning tests passed!')
        print('=' * 50)

    except AssertionError as e:
        print(f'\n❌ Test failed: {e}')
        raise
    except requests.exceptions.ConnectionError:
        print('\n❌ Error: Server not running')
        print('Start server with: python run_server.py')
    except Exception as e:
        print(f'\n❌ Unexpected error: {e}')
        raise
