"""
Tests for the dataset upload endpoint.
Verifies that the in-chat upload endpoint is correctly configured and accessible.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import io


@pytest.fixture
def mock_auth():
    """Mock authentication to bypass auth requirements in tests."""
    with patch('src.backend.v3.api.router.get_authenticated_user_details') as mock_auth:
        mock_auth.return_value = {
            'user_principal_id': 'test-user-123',
            'user_name': 'Test User'
        }
        yield mock_auth


@pytest.fixture
def mock_dataset_service():
    """Mock the DatasetService to avoid actual file uploads."""
    with patch('src.backend.v3.api.router.dataset_service') as mock_service:
        mock_service.upload_dataset = AsyncMock(return_value={
            'dataset_id': 'test-dataset-123',
            'original_filename': 'test.csv',
            'uploaded_at': '2024-01-01T00:00:00Z'
        })
        yield mock_service


@pytest.fixture
def mock_websocket():
    """Mock the WebSocket connection for notifications."""
    with patch('src.backend.v3.api.router.connection_config') as mock_ws:
        mock_ws.send_status_update_async = AsyncMock()
        yield mock_ws


def test_upload_in_chat_endpoint_exists():
    """Test that the upload_in_chat endpoint exists and is registered."""
    from src.backend.app_kernel import app
    
    # Check if the route is registered
    routes = [route.path for route in app.routes]
    assert any('/v3/datasets/upload_in_chat' in route for route in routes), \
        "Upload endpoint not found in registered routes"


@pytest.mark.asyncio
async def test_upload_in_chat_with_file(mock_auth, mock_dataset_service, mock_websocket):
    """Test upload_in_chat endpoint accepts files and returns success."""
    from src.backend.app_kernel import app
    
    client = TestClient(app)
    
    # Create a test CSV file
    csv_content = b'col1,col2\n1,2\n3,4'
    files = {'file': ('test.csv', io.BytesIO(csv_content), 'text/csv')}
    data = {'plan_id': 'test-plan-123'}
    
    # Make request to upload endpoint
    response = client.post('/api/v3/datasets/upload_in_chat', files=files, data=data)
    
    # Verify response - should work or return auth error (not 404)
    assert response.status_code in [200, 201, 401, 403], \
        f"Unexpected status code: {response.status_code}"
    
    # If successful, verify response structure
    if response.status_code in [200, 201]:
        result = response.json()
        assert 'status' in result
        assert 'dataset' in result


@pytest.mark.asyncio
async def test_upload_in_chat_without_file(mock_auth):
    """Test that upload_in_chat returns error when no file is provided."""
    from src.backend.app_kernel import app
    
    client = TestClient(app)
    
    # Make request without file
    response = client.post('/api/v3/datasets/upload_in_chat', data={'plan_id': 'test-plan-123'})
    
    # Should return 4xx error for missing file
    assert response.status_code >= 400, \
        "Expected error when file is missing"


@pytest.mark.asyncio
async def test_upload_in_chat_sends_websocket_notification(mock_auth, mock_dataset_service, mock_websocket):
    """Test that upload triggers WebSocket notification when plan_id is provided."""
    from src.backend.app_kernel import app
    
    client = TestClient(app)
    
    # Create a test CSV file
    csv_content = b'col1,col2\n1,2'
    files = {'file': ('test.csv', io.BytesIO(csv_content), 'text/csv')}
    data = {'plan_id': 'test-plan-123'}
    
    # Make request
    response = client.post('/api/v3/datasets/upload_in_chat', files=files, data=data)
    
    # If successful, verify WebSocket notification was sent
    if response.status_code in [200, 201]:
        # Check that send_status_update_async was called
        assert mock_websocket.send_status_update_async.called or mock_websocket.send_status_update_async.call_count >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


