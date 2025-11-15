"""
Blog System - Object Primitive Style

A complete blog system demonstrating:
- Create, read, update, delete posts
- Integration with auth system for authorization
- Search and filtering
- Pagination
- Author attribution
- Timestamps and versioning
- All in Object Primitive style

Endpoints:
- GET /objects/advanced_blog - List posts (with pagination, filtering)
- GET /objects/advanced_blog?id=post123 - Get specific post
- POST /objects/advanced_blog - Create new post (requires auth token)
- PUT /objects/advanced_blog - Update post (requires auth token, must be author)
- DELETE /objects/advanced_blog - Delete post (requires auth token, must be author)

This demonstrates how to build a blog WITHOUT using dbbasic-content
(which uses traditional class-based architecture). Instead, we use
Object Primitive patterns and integrate with our auth system.
"""

import json
import time
import secrets
from typing import Dict, Any, List, Optional

# Object Primitive dependencies (injected by runtime)
_logger = None
_state_manager = None
_runtime = None  # Future: for calling other objects


def GET(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get post(s).

    Query params:
    - id: Post ID to retrieve (if not provided, list all)
    - author: Filter by author username
    - search: Search in title and content
    - limit: Number of posts to return (default 10, max 100)
    - offset: Pagination offset (default 0)
    - sort: Sort order (newest, oldest, title) (default newest)

    Returns:
    - Single post if id provided
    - List of posts otherwise
    """
    post_id = request.get('id', '').strip()
    author = request.get('author', '').strip()
    search = request.get('search', '').strip().lower()
    limit = min(int(request.get('limit', '10')), 100)
    offset = int(request.get('offset', '0'))
    sort = request.get('sort', 'newest')

    posts = _get_posts()

    # Get specific post
    if post_id:
        if post_id not in posts:
            return {'status': 'error', 'message': f'Post not found: {post_id}'}

        post = posts[post_id]
        if _logger:
            _logger.info('Post viewed', post_id=post_id, title=post['title'])

        return {
            'status': 'ok',
            'post': {
                'id': post_id,
                'title': post['title'],
                'content': post['content'],
                'author': post['author'],
                'created_at': post['created_at'],
                'updated_at': post.get('updated_at', post['created_at']),
                'tags': post.get('tags', []),
            }
        }

    # List posts with filtering
    post_list = []
    for pid, post in posts.items():
        # Filter by author
        if author and post['author'] != author:
            continue

        # Filter by search term
        if search:
            if search not in post['title'].lower() and search not in post['content'].lower():
                continue

        post_list.append({
            'id': pid,
            'title': post['title'],
            'excerpt': post['content'][:200] + ('...' if len(post['content']) > 200 else ''),
            'author': post['author'],
            'created_at': post['created_at'],
            'updated_at': post.get('updated_at', post['created_at']),
            'tags': post.get('tags', []),
        })

    # Sort posts
    if sort == 'newest':
        post_list.sort(key=lambda p: p['created_at'], reverse=True)
    elif sort == 'oldest':
        post_list.sort(key=lambda p: p['created_at'])
    elif sort == 'title':
        post_list.sort(key=lambda p: p['title'].lower())

    # Pagination
    total = len(post_list)
    post_list = post_list[offset:offset + limit]

    if _logger:
        _logger.info('Posts listed', count=len(post_list), total=total, author=author or 'all', search=search or 'none')

    return {
        'status': 'ok',
        'posts': post_list,
        'pagination': {
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total,
        }
    }


def POST(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new blog post.

    Body (JSON):
    {
        "token": "auth_token_here",
        "title": "My First Post",
        "content": "This is the content...",
        "tags": ["python", "tutorial"]  // optional
    }

    Returns:
    - Post ID on success
    - Error if unauthorized or validation fails
    """
    token = request.get('token', '').strip()
    title = request.get('title', '').strip()
    content = request.get('content', '').strip()
    tags = request.get('tags', [])

    # Validate token (simplified - in production, call auth object)
    if not token:
        return {'status': 'error', 'message': 'Authentication token required'}

    # In a real system, we'd call the auth object to validate the token
    # For now, we'll use a simple check
    # TODO: Integrate with auth object when _runtime injection is available
    user_info = _validate_token_simple(token)
    if not user_info:
        if _logger:
            _logger.warning('Unauthorized post creation attempt', token=token[:8])
        return {'status': 'error', 'message': 'Invalid or expired token'}

    # Validation
    if not title:
        return {'status': 'error', 'message': 'Title is required'}

    if len(title) > 200:
        return {'status': 'error', 'message': 'Title must be 200 characters or less'}

    if not content:
        return {'status': 'error', 'message': 'Content is required'}

    if len(content) > 100000:
        return {'status': 'error', 'message': 'Content must be 100,000 characters or less'}

    # Create post
    post_id = _generate_post_id()
    posts = _get_posts()

    posts[post_id] = {
        'title': title,
        'content': content,
        'author': user_info['username'],
        'created_at': int(time.time()),
        'tags': tags if isinstance(tags, list) else [],
    }

    _save_posts(posts)

    if _logger:
        _logger.info('Post created', post_id=post_id, title=title, author=user_info['username'])

    return {
        'status': 'ok',
        'message': 'Post created',
        'post_id': post_id,
        'title': title,
    }


def PUT(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing blog post.

    Body (JSON):
    {
        "token": "auth_token_here",
        "id": "post123",
        "title": "Updated Title",      // optional
        "content": "Updated content",  // optional
        "tags": ["python", "web"]      // optional
    }

    Returns:
    - Success message
    - Error if unauthorized, not found, or not the author
    """
    token = request.get('token', '').strip()
    post_id = request.get('id', '').strip()
    title = request.get('title', '').strip()
    content = request.get('content', '').strip()
    tags = request.get('tags')

    # Validate token
    if not token:
        return {'status': 'error', 'message': 'Authentication token required'}

    user_info = _validate_token_simple(token)
    if not user_info:
        if _logger:
            _logger.warning('Unauthorized post update attempt', token=token[:8])
        return {'status': 'error', 'message': 'Invalid or expired token'}

    # Validate post ID
    if not post_id:
        return {'status': 'error', 'message': 'Post ID is required'}

    posts = _get_posts()

    if post_id not in posts:
        return {'status': 'error', 'message': f'Post not found: {post_id}'}

    post = posts[post_id]

    # Check authorization (must be author)
    if post['author'] != user_info['username']:
        if _logger:
            _logger.warning('Unauthorized post update', post_id=post_id, author=post['author'], attempted_by=user_info['username'])
        return {'status': 'error', 'message': 'Only the author can update this post'}

    # Update fields
    updated = False

    if title:
        if len(title) > 200:
            return {'status': 'error', 'message': 'Title must be 200 characters or less'}
        post['title'] = title
        updated = True

    if content:
        if len(content) > 100000:
            return {'status': 'error', 'message': 'Content must be 100,000 characters or less'}
        post['content'] = content
        updated = True

    if tags is not None:
        if isinstance(tags, list):
            post['tags'] = tags
            updated = True

    if updated:
        post['updated_at'] = int(time.time())
        _save_posts(posts)

        if _logger:
            _logger.info('Post updated', post_id=post_id, title=post['title'], author=user_info['username'])

        return {'status': 'ok', 'message': 'Post updated', 'post_id': post_id}
    else:
        return {'status': 'ok', 'message': 'No changes'}


def DELETE(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete a blog post.

    Query params:
    - token: Authentication token
    - id: Post ID to delete

    Returns:
    - Success message
    - Error if unauthorized, not found, or not the author
    """
    token = request.get('token', '').strip()
    post_id = request.get('id', '').strip()

    # Validate token
    if not token:
        return {'status': 'error', 'message': 'Authentication token required'}

    user_info = _validate_token_simple(token)
    if not user_info:
        if _logger:
            _logger.warning('Unauthorized post deletion attempt', token=token[:8])
        return {'status': 'error', 'message': 'Invalid or expired token'}

    # Validate post ID
    if not post_id:
        return {'status': 'error', 'message': 'Post ID is required'}

    posts = _get_posts()

    if post_id not in posts:
        return {'status': 'error', 'message': f'Post not found: {post_id}'}

    post = posts[post_id]

    # Check authorization (must be author or admin)
    if post['author'] != user_info['username'] and not user_info.get('is_admin', False):
        if _logger:
            _logger.warning('Unauthorized post deletion', post_id=post_id, author=post['author'], attempted_by=user_info['username'])
        return {'status': 'error', 'message': 'Only the author or admin can delete this post'}

    # Delete post
    title = post['title']
    del posts[post_id]
    _save_posts(posts)

    if _logger:
        _logger.warning('Post deleted', post_id=post_id, title=title, author=post['author'], deleted_by=user_info['username'])

    return {'status': 'ok', 'message': f'Post deleted: {title}'}


# --- Internal Helper Functions ---

def _get_posts() -> Dict[str, Any]:
    """Get all posts from state."""
    if _state_manager:
        posts_json = _state_manager.get('posts', '{}')
        return json.loads(posts_json)
    return {}


def _save_posts(posts: Dict[str, Any]):
    """Save posts to state."""
    if _state_manager:
        _state_manager.set('posts', json.dumps(posts))


def _generate_post_id() -> str:
    """Generate unique post ID."""
    return f'post_{int(time.time())}_{secrets.token_hex(4)}'


def _validate_token_simple(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate token by calling the auth object.

    Now that _runtime is available, we can call other objects!
    """
    if not token:
        return None

    # Call auth object to validate token
    if _runtime:
        try:
            # Load auth object
            auth_obj = _runtime.load_object('examples/advanced/auth.py')

            # Call GET with token to validate
            result = auth_obj.execute('GET', {'token': token})

            if result.get('status') == 'ok' and 'user' in result:
                return result['user']
        except Exception as e:
            # If auth object not available or error, fall back to mock
            if _logger:
                _logger.warning('Auth validation failed, using fallback', error=str(e))

    # Fallback: Mock validation for demo purposes
    if token and len(token) > 10:
        return {
            'username': 'demo_user',
            'is_admin': False,
        }

    return None


# Metadata for object introspection
__endpoint__ = {
    'name': 'Blog System',
    'description': 'Complete blog system in Object Primitive style',
    'version': '1.0.0',
    'author': 'Object Primitive System',
    'methods': ['GET', 'POST', 'PUT', 'DELETE'],
    'state_keys': ['posts'],
    'requires': ['auth'],  # Depends on auth object
}
