"""
Test the blog system endpoint.

Tests:
- Create post
- List posts
- Get specific post
- Update post
- Delete post
- Pagination
- Filtering by author
- Search
"""

import requests
import json

BASE_URL = 'http://localhost:8001'

# Mock token for testing (in production, get from auth system)
MOCK_TOKEN = 'demo_token_12345678901234567890'


def test_create_post():
    """Test creating a blog post."""
    print('\n=== Test 1: Create Post ===')

    response = requests.post(
        f'{BASE_URL}/objects/advanced_blog',
        json={
            'token': MOCK_TOKEN,
            'title': 'My First Post',
            'content': 'This is my first blog post using the Object Primitive System!',
            'tags': ['introduction', 'first-post'],
        }
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert 'post_id' in data
    assert data['title'] == 'My First Post'

    print('✅ Post creation works')
    return data['post_id']


def test_create_multiple_posts():
    """Test creating multiple posts."""
    print('\n=== Test 2: Create Multiple Posts ===')

    posts = [
        {
            'title': 'Getting Started with Object Primitives',
            'content': 'Learn how to build applications using the Object Primitive paradigm...',
            'tags': ['tutorial', 'beginner'],
        },
        {
            'title': 'Advanced Auth Patterns',
            'content': 'Deep dive into authentication and authorization patterns...',
            'tags': ['tutorial', 'security'],
        },
        {
            'title': 'Building a Blog',
            'content': 'Step by step guide to building a blog system...',
            'tags': ['tutorial', 'project'],
        },
    ]

    post_ids = []
    for post in posts:
        response = requests.post(
            f'{BASE_URL}/objects/advanced_blog',
            json={'token': MOCK_TOKEN, **post}
        )
        data = response.json()
        assert data['status'] == 'ok'
        post_ids.append(data['post_id'])

    print(f'Created {len(post_ids)} posts')
    print('✅ Multiple post creation works')
    return post_ids


def test_list_posts():
    """Test listing all posts."""
    print('\n=== Test 3: List Posts ===')

    response = requests.get(f'{BASE_URL}/objects/advanced_blog')

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert 'posts' in data
    assert len(data['posts']) >= 4  # We created 4 posts
    assert 'pagination' in data

    print(f'Found {len(data["posts"])} posts (total: {data["pagination"]["total"]})')
    print('✅ Post listing works')


def test_get_specific_post(post_id):
    """Test getting a specific post."""
    print('\n=== Test 4: Get Specific Post ===')

    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'id': post_id}
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert 'post' in data
    assert data['post']['id'] == post_id
    assert 'title' in data['post']
    assert 'content' in data['post']
    assert 'author' in data['post']

    print('✅ Specific post retrieval works')


def test_update_post(post_id):
    """Test updating a post."""
    print('\n=== Test 5: Update Post ===')

    response = requests.put(
        f'{BASE_URL}/objects/advanced_blog',
        json={
            'token': MOCK_TOKEN,
            'id': post_id,
            'title': 'My First Post (Updated)',
            'content': 'This is my updated blog post!',
        }
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'

    # Verify update
    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'id': post_id}
    )
    data = response.json()
    assert data['post']['title'] == 'My First Post (Updated)'
    assert data['post']['content'] == 'This is my updated blog post!'

    print('✅ Post update works')


def test_pagination():
    """Test pagination."""
    print('\n=== Test 6: Pagination ===')

    # Get first 2 posts
    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'limit': '2', 'offset': '0'}
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'
    assert len(data['posts']) <= 2
    assert data['pagination']['limit'] == 2
    assert data['pagination']['offset'] == 0
    assert 'has_more' in data['pagination']

    # Get next 2 posts
    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'limit': '2', 'offset': '2'}
    )
    data = response.json()
    assert len(data['posts']) <= 2

    print('✅ Pagination works')


def test_filter_by_author():
    """Test filtering by author."""
    print('\n=== Test 7: Filter by Author ===')

    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'author': 'demo_user'}
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'

    # All posts should be by demo_user
    for post in data['posts']:
        assert post['author'] == 'demo_user'

    print(f'Found {len(data["posts"])} posts by demo_user')
    print('✅ Author filtering works')


def test_search():
    """Test search functionality."""
    print('\n=== Test 8: Search ===')

    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'search': 'tutorial'}
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'

    # Should find posts with "tutorial" in title or content
    print(f'Found {len(data["posts"])} posts matching "tutorial"')

    # Verify results contain search term
    for post in data['posts']:
        assert 'tutorial' in post['title'].lower() or 'tutorial' in post['excerpt'].lower()

    print('✅ Search works')


def test_sort_order():
    """Test different sort orders."""
    print('\n=== Test 9: Sort Order ===')

    # Test newest first (default)
    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'sort': 'newest'}
    )
    data = response.json()
    posts_newest = data['posts']

    # Test oldest first
    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'sort': 'oldest'}
    )
    data = response.json()
    posts_oldest = data['posts']

    # First post in newest should be last post in oldest (if all posts are shown)
    if len(posts_newest) > 0 and len(posts_oldest) > 0:
        print(f'Newest first: {posts_newest[0]["title"]}')
        print(f'Oldest first: {posts_oldest[0]["title"]}')

    # Test alphabetical by title
    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'sort': 'title'}
    )
    data = response.json()
    posts_alpha = data['posts']

    if len(posts_alpha) > 1:
        # Verify alphabetical order
        titles = [p['title'] for p in posts_alpha]
        assert titles == sorted(titles, key=lambda t: t.lower())

    print('✅ Sorting works')


def test_delete_post(post_id):
    """Test deleting a post."""
    print('\n=== Test 10: Delete Post ===')

    response = requests.delete(
        f'{BASE_URL}/objects/advanced_blog',
        params={'token': MOCK_TOKEN, 'id': post_id}
    )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Response: {json.dumps(data, indent=2)}')

    assert response.status_code == 200
    assert data['status'] == 'ok'

    # Verify post is deleted
    response = requests.get(
        f'{BASE_URL}/objects/advanced_blog',
        params={'id': post_id}
    )
    data = response.json()
    assert data['status'] == 'error'
    assert 'not found' in data['message'].lower()

    print('✅ Post deletion works')


def test_validation():
    """Test input validation."""
    print('\n=== Test 11: Input Validation ===')

    # Test missing title
    response = requests.post(
        f'{BASE_URL}/objects/advanced_blog',
        json={
            'token': MOCK_TOKEN,
            'content': 'Content without title',
        }
    )
    data = response.json()
    assert data['status'] == 'error'
    assert 'title' in data['message'].lower()

    # Test missing content
    response = requests.post(
        f'{BASE_URL}/objects/advanced_blog',
        json={
            'token': MOCK_TOKEN,
            'title': 'Title without content',
        }
    )
    data = response.json()
    assert data['status'] == 'error'
    assert 'content' in data['message'].lower()

    # Test missing token
    response = requests.post(
        f'{BASE_URL}/objects/advanced_blog',
        json={
            'title': 'Test',
            'content': 'Test content',
        }
    )
    data = response.json()
    assert data['status'] == 'error'
    assert 'token' in data['message'].lower()

    print('✅ Input validation works')


if __name__ == '__main__':
    print('Testing Blog System (Object Primitive Style)')
    print('=' * 50)

    try:
        # Create first post
        post_id = test_create_post()

        # Create multiple posts
        more_post_ids = test_create_multiple_posts()

        # Test listing
        test_list_posts()

        # Test getting specific post
        test_get_specific_post(post_id)

        # Test updating post
        test_update_post(post_id)

        # Test pagination
        test_pagination()

        # Test filtering
        test_filter_by_author()

        # Test search
        test_search()

        # Test sorting
        test_sort_order()

        # Test deletion
        test_delete_post(post_id)

        # Test validation
        test_validation()

        print('\n' + '=' * 50)
        print('✅ All 11 blog tests passed!')
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
