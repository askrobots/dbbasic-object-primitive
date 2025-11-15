#!/usr/bin/env python3
"""
Test the Object Primitive System REST API

Run this after starting the server with: python run_server.py

Usage:
    python test_api.py
"""
import requests
import json

BASE_URL = "http://localhost:8001"


def test_list_objects():
    """Test listing all objects"""
    print("\n" + "=" * 60)
    print("TEST: List all objects")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/objects")
    print(f"Status: {response.status_code}")
    print(f"Response:")
    data = response.json()
    print(json.dumps(data, indent=2))

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert 'objects' in data
    assert 'count' in data

    print(f"\n✅ Found {data['count']} objects")
    return data['objects']


def test_execute_counter():
    """Test executing counter object"""
    print("\n" + "=" * 60)
    print("TEST: Execute counter object (GET)")
    print("=" * 60)

    # Execute GET multiple times
    for i in range(3):
        response = requests.get(f"{BASE_URL}/objects/tutorial_03_counter")
        print(f"\nRequest {i+1}:")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")

        assert response.status_code == 200
        assert data['status'] == 'ok'
        assert 'count' in data

    print(f"\n✅ Counter working correctly")


def test_get_metadata():
    """Test getting object metadata"""
    print("\n" + "=" * 60)
    print("TEST: Get object metadata")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/objects/tutorial_03_counter?metadata=true")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:")
    print(json.dumps(data, indent=2))

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert 'metadata' in data

    metadata = data['metadata']
    assert 'name' in metadata
    assert 'version' in metadata
    assert 'log_count' in metadata

    print(f"\n✅ Metadata retrieved: {metadata['name']} v{metadata['version']}")


def test_get_logs():
    """Test getting object logs"""
    print("\n" + "=" * 60)
    print("TEST: Get object logs")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/objects/tutorial_03_counter?logs=true&limit=10")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:")
    print(json.dumps(data, indent=2))

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert 'logs' in data

    print(f"\n✅ Retrieved {data['count']} log entries")


def test_get_source():
    """Test getting object source code"""
    print("\n" + "=" * 60)
    print("TEST: Get object source code")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/objects/tutorial_03_counter?source=true")
    print(f"Status: {response.status_code}")
    data = response.json()

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert 'source' in data

    source_lines = data['source'].split('\n')
    print(f"Source code preview (first 10 lines):")
    for i, line in enumerate(source_lines[:10], 1):
        print(f"  {i:3d}: {line}")

    if len(source_lines) > 10:
        print(f"  ... ({len(source_lines) - 10} more lines)")

    print(f"\n✅ Retrieved {len(source_lines)} lines of source code")


def test_post_reset_counter():
    """Test POST request to reset counter"""
    print("\n" + "=" * 60)
    print("TEST: Reset counter (POST)")
    print("=" * 60)

    response = requests.post(
        f"{BASE_URL}/objects/tutorial_03_counter",
        json={"user_id": "test_user"},
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:")
    print(json.dumps(data, indent=2))

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert data['count'] == 0

    print(f"\n✅ Counter reset successfully")


def test_calculator():
    """Test calculator object with various operations"""
    print("\n" + "=" * 60)
    print("TEST: Calculator operations")
    print("=" * 60)

    operations = [
        {'a': 10, 'b': 5, 'operation': 'add'},
        {'a': 10, 'b': 5, 'operation': 'subtract'},
        {'a': 10, 'b': 5, 'operation': 'multiply'},
        {'a': 10, 'b': 5, 'operation': 'divide'},
    ]

    for op in operations:
        response = requests.get(
            f"{BASE_URL}/objects/tutorial_04_calculator",
            params=op,
        )
        print(f"\nOperation: {op['a']} {op['operation']} {op['b']}")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Result: {data.get('result')}")
        print(f"Operation string: {data.get('operation')}")

        assert response.status_code == 200
        assert data['status'] == 'ok'
        assert 'result' in data

    print(f"\n✅ Calculator working correctly")


def test_error_handling():
    """Test error handling"""
    print("\n" + "=" * 60)
    print("TEST: Error handling")
    print("=" * 60)

    # Test 404 - object not found
    response = requests.get(f"{BASE_URL}/objects/nonexistent_object")
    print(f"\n404 Test:")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")

    assert response.status_code == 404
    assert 'error' in data

    # Test validation error in calculator
    response = requests.get(f"{BASE_URL}/objects/tutorial_04_calculator")
    print(f"\nValidation Error Test:")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")

    assert response.status_code == 200
    assert data['status'] == 'error'  # Application-level error

    print(f"\n✅ Error handling working correctly")


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "Object Primitive System REST API Tests" + " " * 9 + "║")
    print("╚" + "=" * 58 + "╝")

    try:
        # Test listing objects
        objects = test_list_objects()

        # Test counter operations
        test_execute_counter()
        test_get_metadata()
        test_get_logs()
        test_get_source()
        test_post_reset_counter()

        # Test calculator
        test_calculator()

        # Test error handling
        test_error_handling()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✅")
        print("=" * 60)
        print()

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Make sure the server is running: python run_server.py")
        print()
        exit(1)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        print()
        exit(1)

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        print()
        exit(1)


if __name__ == "__main__":
    main()
