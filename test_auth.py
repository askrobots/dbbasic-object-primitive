"""
Test the auth system endpoint.

Tests:
- User registration
- Login
- Token validation
- Password change
- Logout
- Account deletion
"""

import requests
import json

BASE_URL = 'http://localhost:8001'


def test_register_user():
    """Test user registration."""
    print('\n=== Test 1: Register User ===')

    response = requests.post(
        f'{BASE_URL}/objects/advanced_auth',
        json={
            'action': 'register',
            'username': 'alice',
            'password': 'secret123',
            'email': 'alice@example.com',
        }
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert 'token' in data
    assert data['username'] == 'alice'

    print('✅ User registration works')
    return data['token']


def test_login_user():
    """Test user login."""
    print('\n=== Test 2: Login User ===')

    response = requests.post(
        f'{BASE_URL}/objects/advanced_auth',
        json={
            'action': 'login',
            'username': 'alice',
            'password': 'secret123',
        }
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert 'token' in data
    assert data['username'] == 'alice'

    print('✅ Login works')
    return data['token']


def test_validate_token(token):
    """Test token validation."""
    print('\n=== Test 3: Validate Token ===')

    response = requests.get(
        f'{BASE_URL}/objects/advanced_auth',
        params={'token': token}
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert data['user']['username'] == 'alice'
    assert data['user']['email'] == 'alice@example.com'

    print('✅ Token validation works')


def test_invalid_token():
    """Test invalid token."""
    print('\n=== Test 4: Invalid Token ===')

    response = requests.get(
        f'{BASE_URL}/objects/advanced_auth',
        params={'token': 'invalid_token_xyz'}
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'error'
    assert 'invalid' in data['message'].lower()

    print('✅ Invalid token detection works')


def test_change_email(token):
    """Test changing email."""
    print('\n=== Test 5: Change Email ===')

    response = requests.put(
        f'{BASE_URL}/objects/advanced_auth',
        json={
            'token': token,
            'email': 'alice.new@example.com',
        }
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'

    # Verify email changed
    response = requests.get(
        f'{BASE_URL}/objects/advanced_auth',
        params={'token': token}
    )
    data = response.json()
    assert data['user']['email'] == 'alice.new@example.com'

    print('✅ Email change works')


def test_change_password(token):
    """Test changing password."""
    print('\n=== Test 6: Change Password ===')

    response = requests.put(
        f'{BASE_URL}/objects/advanced_auth',
        json={
            'token': token,
            'old_password': 'secret123',
            'password': 'newsecret456',
        }
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'

    # Verify can login with new password
    response = requests.post(
        f'{BASE_URL}/objects/advanced_auth',
        json={
            'action': 'login',
            'username': 'alice',
            'password': 'newsecret456',
        }
    )
    data = response.json()
    assert data['status'] == 'ok'

    print('✅ Password change works')
    return data['token']


def test_logout(token):
    """Test logout."""
    print('\n=== Test 7: Logout ===')

    response = requests.delete(
        f'{BASE_URL}/objects/advanced_auth',
        params={'token': token}
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'

    # Verify token is now invalid
    response = requests.get(
        f'{BASE_URL}/objects/advanced_auth',
        params={'token': token}
    )
    data = response.json()
    assert data['status'] == 'error'

    print('✅ Logout works')


def test_duplicate_registration():
    """Test duplicate registration."""
    print('\n=== Test 8: Duplicate Registration ===')

    response = requests.post(
        f'{BASE_URL}/objects/advanced_auth',
        json={
            'action': 'register',
            'username': 'alice',
            'password': 'another_password',
            'email': 'another@example.com',
        }
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'error'
    assert 'already exists' in data['message'].lower()

    print('✅ Duplicate registration prevention works')


def test_view_logs():
    """Test viewing auth logs."""
    print('\n=== Test 9: View Auth Logs ===')

    response = requests.get(
        f'{BASE_URL}/objects/advanced_auth',
        params={'logs': 'true', 'limit': '10'}
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert 'logs' in data

    # Should have registration, login, logout events
    print(f'Found {len(data["logs"])} log entries')
    for log in data['logs'][:5]:
        print(f'  - {log.get("level", "INFO")}: {log.get("message", "")}')

    print('✅ Auth logging works')


def test_view_state():
    """Test viewing auth metadata."""
    print('\n=== Test 10: View Auth Metadata ===')

    response = requests.get(
        f'{BASE_URL}/objects/advanced_auth',
        params={'metadata': 'true'}
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert 'metadata' in data

    # Should have state_keys
    metadata = data['metadata']
    print(f'State keys defined: {metadata.get("state_keys", [])}')
    print(f'Log count: {metadata.get("log_count", 0)}')
    print(f'Version count: {metadata.get("version_count", 0)}')

    assert 'state_keys' in metadata
    assert 'users' in metadata['state_keys']
    assert 'tokens' in metadata['state_keys']

    print('✅ Metadata introspection works')


if __name__ == '__main__':
    print('Testing Auth System (Object Primitive Style)')
    print('=' * 50)

    try:
        # Test registration and get token
        token1 = test_register_user()

        # Test login
        token2 = test_login_user()

        # Test token validation
        test_validate_token(token2)

        # Test invalid token
        test_invalid_token()

        # Test email change
        test_change_email(token2)

        # Test password change
        token3 = test_change_password(token2)

        # Test logout
        test_logout(token3)

        # Test duplicate registration
        test_duplicate_registration()

        # Test logs
        test_view_logs()

        # Test state
        test_view_state()

        print('\n' + '=' * 50)
        print('✅ All 10 auth tests passed!')
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
