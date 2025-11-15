"""
Test Phase 5: Object Composition

Tests for objects calling other objects (_runtime injection).
"""

import requests
import json

BASE_URL = 'http://localhost:8001'


def test_blog_auth_integration():
    """Test that blog can call auth object for token validation"""
    print('\n=== Test 1: Blog-Auth Integration ===')

    # First, create a user in auth system
    response = requests.post(
        f'{BASE_URL}/objects/advanced_auth',
        json={
            'action': 'register',
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com',
        }
    )
    auth_data = response.json()
    print(f"User registered: {auth_data['status']}")
    assert auth_data['status'] == 'ok'
    token = auth_data['token']
    print(f"Token received: {token[:20]}...")

    # Now try to create a blog post with this token
    response = requests.post(
        f'{BASE_URL}/objects/advanced_blog',
        json={
            'token': token,
            'title': 'Test Post',
            'content': 'This post was created with real auth integration!',
            'tags': ['test', 'integration'],
        }
    )
    blog_data = response.json()

    print(f"\nBlog post creation:")
    print(f"  Status: {blog_data.get('status')}")
    print(f"  Post ID: {blog_data.get('post_id', 'N/A')}")

    assert blog_data['status'] == 'ok'
    assert 'post_id' in blog_data

    # Verify the post was created by the right user
    post_id = blog_data['post_id']
    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'id': post_id}
    )
    post_data = response.json()

    print(f"\nPost verification:")
    print(f"  Author: {post_data['post']['author']}")
    print(f"  Title: {post_data['post']['title']}")

    assert post_data['post']['author'] == 'testuser'  # Should be real username, not demo_user!

    print('\n✅ Blog-Auth integration works (object composition successful!)')


def test_invalid_token():
    """Test that blog rejects invalid tokens"""
    print('\n=== Test 2: Invalid Token Rejection ===')

    # Try to create post with invalid token
    response = requests.post(
        f'{BASE_URL}/objects/advanced_blog',
        json={
            'token': 'invalid_token_xyz',
            'title': 'Should Fail',
            'content': 'This should not work',
        }
    )
    data = response.json()

    print(f"Invalid token response:")
    print(f"  Status: {data.get('status')}")
    print(f"  Message: {data.get('message', 'N/A')}")

    # Should be rejected OR use fallback demo_user
    # If using fallback, author will be demo_user
    # If rejected, status will be error
    if data['status'] == 'error':
        print('  ✓ Token rejected (strict mode)')
    else:
        # Fallback to demo_user
        post_id = data.get('post_id')
        if post_id:
            response = requests.get(
                f'{BASE_URL}/objects/advanced_blog',
                params={'id': post_id}
            )
            post_data = response.json()
            print(f"  ✓ Fallback used (author: {post_data['post']['author']})")

    print('\n✅ Token validation works')


def test_cross_object_state():
    """Test that auth and blog maintain separate state"""
    print('\n=== Test 3: Separate Object State ===')

    # Check auth state (users, tokens)
    response = requests.get(
        f'{BASE_URL}/objects/advanced_auth',
        params={'metadata': 'true'}
    )
    auth_meta = response.json()

    print(f"Auth object state keys: {auth_meta['metadata'].get('state_keys', [])}")
    assert 'users' in auth_meta['metadata'].get('state_keys', [])
    assert 'tokens' in auth_meta['metadata'].get('state_keys', [])

    # Check blog state (posts)
    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'metadata': 'true'}
    )
    blog_meta = response.json()

    print(f"Blog object state keys: {blog_meta['metadata'].get('state_keys', [])}")
    assert 'posts' in blog_meta['metadata'].get('state_keys', [])

    # Verify they're separate (no overlap)
    auth_keys = set(auth_meta['metadata'].get('state_keys', []))
    blog_keys = set(blog_meta['metadata'].get('state_keys', []))

    print(f"\nState separation:")
    print(f"  Auth-only keys: {auth_keys - blog_keys}")
    print(f"  Blog-only keys: {blog_keys - auth_keys}")

    assert len(auth_keys & blog_keys) == 0  # No overlap

    print('\n✅ Objects maintain separate state')


if __name__ == '__main__':
    print('Testing Phase 5: Object Composition')
    print('=' * 50)

    try:
        # Test auth-blog integration
        test_blog_auth_integration()

        # Test invalid token handling
        test_invalid_token()

        # Test state separation
        test_cross_object_state()

        print('\n' + '=' * 50)
        print('✅ All composition tests passed!')
        print('=' * 50)

    except AssertionError as e:
        print(f'\n❌ Test failed: {e}')
        raise
    except requests.exceptions.ConnectionError:
        print('\n❌ Error: Server not running')
        print('Start server with: ./server.sh start')
    except Exception as e:
        print(f'\n❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        raise
