"""
05_user_registry.py - User registry with CRUD operations
"""

import json
from datetime import datetime

_logger = None
_state_manager = None


def GET(request):
    """
    Get user(s).

    Request:
        {'user_id': 'alice'}  # Get specific user
        {}                     # Get all users
    """

    user_id = request.get('user_id')

    # Get all users
    users = _get_users()

    if user_id:
        # Get specific user
        user = users.get(user_id)

        if not user:
            if _logger:
                _logger.warning('User not found', user_id=user_id)

            return {
                'status': 'error',
                'message': f'User not found: {user_id}',
            }

        if _logger:
            _logger.info('User retrieved', user_id=user_id)

        return {
            'status': 'ok',
            'user': user,
        }
    else:
        # Get all users
        if _logger:
            _logger.info('All users retrieved', count=len(users))

        return {
            'status': 'ok',
            'users': users,
            'count': len(users),
        }


def POST(request):
    """
    Create a new user.

    Request:
        {
            'user_id': 'alice',
            'email': 'alice@example.com',
            'name': 'Alice Smith'
        }
    """

    # Validate
    if 'user_id' not in request:
        return {'status': 'error', 'message': 'Missing field: user_id'}

    if 'email' not in request:
        return {'status': 'error', 'message': 'Missing field: email'}

    user_id = request['user_id']
    email = request['email']
    name = request.get('name', '')

    # Check if user exists
    users = _get_users()

    if user_id in users:
        if _logger:
            _logger.warning('User already exists', user_id=user_id)

        return {
            'status': 'error',
            'message': f'User already exists: {user_id}',
        }

    # Create user
    user = {
        'user_id': user_id,
        'email': email,
        'name': name,
        'created_at': datetime.now().isoformat(),
    }

    users[user_id] = user
    _save_users(users)

    if _logger:
        _logger.info('User created', user_id=user_id, email=email)

    return {
        'status': 'ok',
        'message': f'User created: {user_id}',
        'user': user,
    }


def PUT(request):
    """
    Update a user.

    Request:
        {
            'user_id': 'alice',
            'email': 'alice.new@example.com',  # Optional
            'name': 'Alice Johnson'             # Optional
        }
    """

    if 'user_id' not in request:
        return {'status': 'error', 'message': 'Missing field: user_id'}

    user_id = request['user_id']

    # Get user
    users = _get_users()

    if user_id not in users:
        if _logger:
            _logger.warning('User not found for update', user_id=user_id)

        return {
            'status': 'error',
            'message': f'User not found: {user_id}',
        }

    # Update fields
    user = users[user_id]

    if 'email' in request:
        user['email'] = request['email']

    if 'name' in request:
        user['name'] = request['name']

    user['updated_at'] = datetime.now().isoformat()

    _save_users(users)

    if _logger:
        _logger.info('User updated', user_id=user_id)

    return {
        'status': 'ok',
        'message': f'User updated: {user_id}',
        'user': user,
    }


def DELETE(request):
    """
    Delete a user.

    Request:
        {'user_id': 'alice'}
    """

    if 'user_id' not in request:
        return {'status': 'error', 'message': 'Missing field: user_id'}

    user_id = request['user_id']

    # Get users
    users = _get_users()

    if user_id not in users:
        if _logger:
            _logger.warning('User not found for deletion', user_id=user_id)

        return {
            'status': 'error',
            'message': f'User not found: {user_id}',
        }

    # Delete
    user = users[user_id]
    del users[user_id]
    _save_users(users)

    if _logger:
        _logger.warning('User deleted', user_id=user_id)

    return {
        'status': 'ok',
        'message': f'User deleted: {user_id}',
        'user': user,
    }


def _get_users():
    """Get all users from state"""
    if _state_manager:
        users_json = _state_manager.get('users', '{}')
        return json.loads(users_json)
    else:
        return {}


def _save_users(users):
    """Save users to state"""
    if _state_manager:
        users_json = json.dumps(users)
        _state_manager.set('users', users_json)


__endpoint__ = {
    'name': 'user_registry',
    'description': 'CRUD API for user management',
    'version': '1.0.0',
    'author': 'tutorial',
    'methods': ['GET', 'POST', 'PUT', 'DELETE'],
}
