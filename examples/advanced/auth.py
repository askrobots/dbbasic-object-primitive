"""
Auth System - Object Primitive Style

A complete authentication system demonstrating:
- User registration with password hashing
- Login with session tokens
- Token validation
- User management
- All in Object Primitive style (self-logging, persistent state)

Endpoints:
- POST /objects/advanced_auth - Register or login
- GET /objects/advanced_auth?token=xyz - Validate token
- PUT /objects/advanced_auth - Update user
- DELETE /objects/advanced_auth?token=xyz - Logout

This demonstrates how to build auth WITHOUT using dbbasic-accounts
(which uses traditional class-based architecture). Instead, we use
Object Primitive patterns: _state_manager for persistence, _logger
for audit trails, and REST methods for the interface.
"""

import hashlib
import secrets
import json
import time
from typing import Dict, Any, Optional

# Object Primitive dependencies (injected by runtime)
_logger = None
_state_manager = None


def GET(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate authentication token.

    Query params:
    - token: Session token to validate
    - user: Username to get info for (requires admin token)

    Returns:
    - User info if token is valid
    - Error if token is invalid or expired
    """
    token = request.get('token', '')
    username = request.get('user', '')

    if not token:
        return {'status': 'error', 'message': 'Token required'}

    # Validate token
    user_info = _validate_token(token)
    if not user_info:
        if _logger:
            _logger.warning('Invalid token attempt', token=token[:8])
        return {'status': 'error', 'message': 'Invalid or expired token'}

    if _logger:
        _logger.info('Token validated', username=user_info['username'])

    # If requesting another user's info, check admin permission
    if username and username != user_info['username']:
        if not user_info.get('is_admin', False):
            return {'status': 'error', 'message': 'Admin access required'}

        # Get requested user
        users = _get_users()
        if username not in users:
            return {'status': 'error', 'message': f'User not found: {username}'}

        user_data = users[username]
        return {
            'status': 'ok',
            'user': {
                'username': username,
                'email': user_data.get('email', ''),
                'is_admin': user_data.get('is_admin', False),
                'created_at': user_data.get('created_at', ''),
            }
        }

    # Return current user info
    return {
        'status': 'ok',
        'user': {
            'username': user_info['username'],
            'email': user_info.get('email', ''),
            'is_admin': user_info.get('is_admin', False),
            'token': token,
        }
    }


def POST(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Register new user or login existing user.

    Body (JSON):
    {
        "action": "register" | "login",
        "username": "alice",
        "password": "secret123",
        "email": "alice@example.com"  // only for register
    }

    Returns:
    - Session token on success
    - Error message on failure
    """
    action = request.get('action', 'login')
    username = request.get('username', '').strip()
    password = request.get('password', '')
    email = request.get('email', '').strip()

    # Validation
    if not username or not password:
        return {'status': 'error', 'message': 'Username and password required'}

    if action == 'register':
        return _register_user(username, password, email)
    elif action == 'login':
        return _login_user(username, password)
    else:
        return {'status': 'error', 'message': f'Unknown action: {action}'}


def PUT(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update user information.

    Body (JSON):
    {
        "token": "xyz",
        "email": "newemail@example.com",  // optional
        "password": "newpassword",         // optional
        "old_password": "oldpassword"      // required if changing password
    }

    Returns:
    - Success message
    - Error if unauthorized or validation fails
    """
    token = request.get('token', '')

    if not token:
        return {'status': 'error', 'message': 'Token required'}

    # Validate token
    user_info = _validate_token(token)
    if not user_info:
        return {'status': 'error', 'message': 'Invalid or expired token'}

    username = user_info['username']
    users = _get_users()

    if username not in users:
        return {'status': 'error', 'message': 'User not found'}

    user = users[username]
    updated = False

    # Update email
    new_email = request.get('email', '').strip()
    if new_email:
        user['email'] = new_email
        updated = True
        if _logger:
            _logger.info('Email updated', username=username, email=new_email)

    # Update password
    new_password = request.get('password', '')
    old_password = request.get('old_password', '')

    if new_password:
        # Verify old password
        if not old_password:
            return {'status': 'error', 'message': 'old_password required to change password'}

        if not _verify_password(old_password, user['password_hash']):
            if _logger:
                _logger.warning('Failed password change', username=username, reason='incorrect old password')
            return {'status': 'error', 'message': 'Incorrect old password'}

        # Hash and save new password
        user['password_hash'] = _hash_password(new_password)
        updated = True

        if _logger:
            _logger.warning('Password changed', username=username)

    if updated:
        _save_users(users)
        return {'status': 'ok', 'message': 'User updated'}
    else:
        return {'status': 'ok', 'message': 'No changes'}


def DELETE(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Logout (invalidate token) or delete user account.

    Query params:
    - token: Session token
    - delete_account: If 'true', delete account (requires password confirmation)
    - password: Required if delete_account=true

    Returns:
    - Success message
    - Error if unauthorized
    """
    token = request.get('token', '')

    if not token:
        return {'status': 'error', 'message': 'Token required'}

    # Validate token
    user_info = _validate_token(token)
    if not user_info:
        return {'status': 'error', 'message': 'Invalid or expired token'}

    # Check if deleting account
    delete_account = request.get('delete_account', '').lower() == 'true'

    if delete_account:
        # Confirm password
        password = request.get('password', '')
        if not password:
            return {'status': 'error', 'message': 'Password required to delete account'}

        users = _get_users()
        username = user_info['username']

        if username not in users:
            return {'status': 'error', 'message': 'User not found'}

        if not _verify_password(password, users[username]['password_hash']):
            if _logger:
                _logger.warning('Failed account deletion', username=username, reason='incorrect password')
            return {'status': 'error', 'message': 'Incorrect password'}

        # Delete user
        del users[username]
        _save_users(users)

        # Invalidate all tokens for this user
        _invalidate_user_tokens(username)

        if _logger:
            _logger.warning('Account deleted', username=username)

        return {'status': 'ok', 'message': f'Account {username} deleted'}
    else:
        # Just logout (invalidate token)
        _invalidate_token(token)

        if _logger:
            _logger.info('User logged out', username=user_info['username'])

        return {'status': 'ok', 'message': 'Logged out'}


# --- Internal Helper Functions ---

def _register_user(username: str, password: str, email: str) -> Dict[str, Any]:
    """Register a new user."""
    # Validation
    if len(username) < 3:
        return {'status': 'error', 'message': 'Username must be at least 3 characters'}

    if len(password) < 8:
        return {'status': 'error', 'message': 'Password must be at least 8 characters'}

    if not email or '@' not in email:
        return {'status': 'error', 'message': 'Valid email required'}

    # Check if user exists
    users = _get_users()
    if username in users:
        if _logger:
            _logger.warning('Registration failed', username=username, reason='already exists')
        return {'status': 'error', 'message': 'Username already exists'}

    # Create user
    users[username] = {
        'password_hash': _hash_password(password),
        'email': email,
        'is_admin': False,  # First user could be admin, or set manually
        'created_at': int(time.time()),
    }

    # Save users
    _save_users(users)

    # Create session token
    token = _create_token(username)

    if _logger:
        _logger.info('User registered', username=username, email=email)

    return {
        'status': 'ok',
        'message': 'User registered',
        'token': token,
        'username': username,
    }


def _login_user(username: str, password: str) -> Dict[str, Any]:
    """Login existing user."""
    users = _get_users()

    if username not in users:
        if _logger:
            _logger.warning('Login failed', username=username, reason='not found')
        # Don't reveal if user exists
        return {'status': 'error', 'message': 'Invalid username or password'}

    user = users[username]

    # Verify password
    if not _verify_password(password, user['password_hash']):
        if _logger:
            _logger.warning('Login failed', username=username, reason='incorrect password')
        return {'status': 'error', 'message': 'Invalid username or password'}

    # Create session token
    token = _create_token(username)

    if _logger:
        _logger.info('User logged in', username=username)

    return {
        'status': 'ok',
        'message': 'Login successful',
        'token': token,
        'username': username,
        'is_admin': user.get('is_admin', False),
    }


def _hash_password(password: str) -> str:
    """Hash password with SHA-256 (simple, not bcrypt for now)."""
    # In production, use bcrypt or argon2
    # For demo, using SHA-256 with salt
    salt = 'object_primitive_salt'  # In production, use per-user random salt
    return hashlib.sha256(f'{salt}{password}'.encode()).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify password matches hash."""
    return _hash_password(password) == password_hash


def _create_token(username: str) -> str:
    """Create session token for user."""
    token = secrets.token_urlsafe(32)

    # Store token
    tokens = _get_tokens()
    tokens[token] = {
        'username': username,
        'created_at': int(time.time()),
        'expires_at': int(time.time()) + 86400,  # 24 hours
    }
    _save_tokens(tokens)

    return token


def _validate_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate token and return user info."""
    tokens = _get_tokens()

    if token not in tokens:
        return None

    token_data = tokens[token]

    # Check expiration
    if token_data['expires_at'] < int(time.time()):
        # Token expired, clean up
        del tokens[token]
        _save_tokens(tokens)
        return None

    # Get user info
    username = token_data['username']
    users = _get_users()

    if username not in users:
        return None

    user = users[username]
    return {
        'username': username,
        'email': user.get('email', ''),
        'is_admin': user.get('is_admin', False),
    }


def _invalidate_token(token: str):
    """Invalidate a specific token."""
    tokens = _get_tokens()
    if token in tokens:
        del tokens[token]
        _save_tokens(tokens)


def _invalidate_user_tokens(username: str):
    """Invalidate all tokens for a user."""
    tokens = _get_tokens()
    to_delete = [t for t, data in tokens.items() if data['username'] == username]
    for token in to_delete:
        del tokens[token]
    _save_tokens(tokens)


def _get_users() -> Dict[str, Any]:
    """Get all users from state."""
    if _state_manager:
        users_json = _state_manager.get('users', '{}')
        return json.loads(users_json)
    return {}


def _save_users(users: Dict[str, Any]):
    """Save users to state."""
    if _state_manager:
        _state_manager.set('users', json.dumps(users))


def _get_tokens() -> Dict[str, Any]:
    """Get all tokens from state."""
    if _state_manager:
        tokens_json = _state_manager.get('tokens', '{}')
        return json.loads(tokens_json)
    return {}


def _save_tokens(tokens: Dict[str, Any]):
    """Save tokens to state."""
    if _state_manager:
        _state_manager.set('tokens', json.dumps(tokens))


# Metadata for object introspection
__endpoint__ = {
    'name': 'Auth System',
    'description': 'Complete authentication system in Object Primitive style',
    'version': '1.0.0',
    'author': 'Object Primitive System',
    'methods': ['GET', 'POST', 'PUT', 'DELETE'],
    'state_keys': ['users', 'tokens'],
}
