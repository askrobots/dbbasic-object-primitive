"""
User Profile Object with File Storage

Demonstrates file storage capabilities:
- Upload avatar (profile picture)
- Download avatar
- List all profile files
- Store profile data in state

Example usage:
    # Set profile data
    POST /objects/basics_user_profile
    {"name": "Alice", "email": "alice@example.com"}

    # Upload avatar (multipart/form-data)
    POST /objects/basics_user_profile
    file: avatar.jpg

    # Get profile data
    GET /objects/basics_user_profile

    # Download avatar
    GET /objects/basics_user_profile?file=avatar.jpg

    # List all files
    GET /objects/basics_user_profile?files=true
"""

__endpoint__ = {
    'id': 'basics_user_profile',
    'methods': ['GET', 'POST', 'PUT', 'DELETE'],
    'description': 'User profile with file storage (avatar)',
    'version': '1.0.0',
    'author': 'system'
}

# Injected by runtime
_state_manager = None
_logger = None
_files = None


def GET(request=None):
    """Get user profile data"""
    if not _state_manager:
        return {'status': 'error', 'error': 'No state manager'}

    # Get profile data from state
    name = _state_manager.get('name', 'Unknown')
    email = _state_manager.get('email', '')
    created_at = _state_manager.get('created_at', 0)

    # Get file list
    files = []
    if _files:
        try:
            files = _files.list()
        except:
            pass

    # Find avatar
    avatar = None
    for file in files:
        if file['name'].startswith('avatar'):
            avatar = file['name']
            break

    if _logger:
        _logger.info('Profile accessed', name=name, email=email)

    return {
        'status': 'ok',
        'profile': {
            'name': name,
            'email': email,
            'created_at': created_at,
            'avatar': avatar
        },
        'files': files
    }


def POST(request=None):
    """Update user profile data"""
    if not _state_manager or not request:
        return {'status': 'error', 'error': 'No state manager or request'}

    # Get current time
    import time
    now = time.time()

    # Update profile fields
    updated = []

    if 'name' in request:
        _state_manager.set('name', request['name'])
        updated.append('name')

    if 'email' in request:
        _state_manager.set('email', request['email'])
        updated.append('email')

    # Set created_at if not exists
    if not _state_manager.get('created_at'):
        _state_manager.set('created_at', now)

    _state_manager.set('updated_at', now)
    updated.append('updated_at')

    if _logger:
        _logger.info('Profile updated', updated=updated, timestamp=now)

    return {
        'status': 'ok',
        'message': f'Updated {len(updated)} field(s)',
        'updated': updated,
        'timestamp': now
    }


def PUT(request=None):
    """Replace entire profile"""
    if not _state_manager or not request:
        return {'status': 'error', 'error': 'No state manager or request'}

    import time
    now = time.time()

    # Set all fields
    _state_manager.set('name', request.get('name', 'Unknown'))
    _state_manager.set('email', request.get('email', ''))
    _state_manager.set('created_at', request.get('created_at', now))
    _state_manager.set('updated_at', now)

    if _logger:
        _logger.info('Profile replaced', timestamp=now)

    return {
        'status': 'ok',
        'message': 'Profile replaced',
        'timestamp': now
    }


def DELETE(request=None):
    """Delete avatar file"""
    if not _files or not request:
        return {'status': 'error', 'error': 'No file manager or request'}

    filename = request.get('filename', 'avatar.jpg')

    try:
        _files.delete(filename)

        if _logger:
            _logger.info('File deleted', filename=filename)

        return {
            'status': 'ok',
            'message': f'Deleted {filename}',
            'filename': filename
        }
    except FileNotFoundError:
        return {
            'status': 'error',
            'error': f'File not found: {filename}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': f'Delete failed: {e}'
        }


# Self-testing
def test_profile_creation():
    """Test creating a user profile"""
    if not _state_manager:
        return {'status': 'skip', 'reason': 'No state manager'}

    # Set profile data
    _state_manager.set('name', 'Test User')
    _state_manager.set('email', 'test@example.com')
    _state_manager.set('created_at', 1234567890.0)

    # Get profile
    result = GET({})

    assert result['status'] == 'ok', f"Expected status=ok, got {result['status']}"
    assert result['profile']['name'] == 'Test User', f"Expected name=Test User, got {result['profile']['name']}"
    assert result['profile']['email'] == 'test@example.com', f"Expected correct email"

    if _logger:
        _logger.info('test_profile_creation passed', test='test_profile_creation', result='pass')

    return {'status': 'pass', 'test': 'test_profile_creation'}


def test_profile_update():
    """Test updating profile fields"""
    if not _state_manager:
        return {'status': 'skip', 'reason': 'No state manager'}

    # Update name only
    result = POST({'name': 'Updated Name'})

    assert result['status'] == 'ok', f"Expected status=ok"
    assert 'name' in result['updated'], f"Expected 'name' in updated fields"

    # Verify update
    assert _state_manager.get('name') == 'Updated Name', f"Name not updated in state"

    if _logger:
        _logger.info('test_profile_update passed', test='test_profile_update', result='pass')

    return {'status': 'pass', 'test': 'test_profile_update'}
