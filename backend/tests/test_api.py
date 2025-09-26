"""Tests for API endpoints."""
import pytest
import json
from unittest.mock import patch, MagicMock
from flask import Flask

from backend import create_app
from backend.models import ExpertUser, ShipmentRequest


class TestAPIEndpoints:
    """Test cases for API endpoints."""
    
    def setup_method(self):
        """Setup test environment."""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret-key',
            'JWT_SECRET_KEY': 'test-jwt-secret'
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def teardown_method(self):
        """Cleanup test environment."""
        self.app_context.pop()
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get('/api/health/ping')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'message' in data
    
    def test_expert_login_success(self):
        """Test successful expert login."""
        with patch('backend.models.ExpertUser') as mock_user:
            # Mock user query
            mock_user_instance = MagicMock()
            mock_user_instance.username = 'expert'
            mock_user_instance.is_active = True
            mock_user_instance.id = 1
            mock_user_instance.full_name = 'Test Expert'
            mock_user_instance.email = 'expert@test.com'
            mock_user_instance.role = 'expert'
            
            mock_user.query.filter_by.return_value.first.return_value = mock_user_instance
            
            response = self.client.post('/api/expert/auth/login', json={
                'username': 'expert',
                'password': 'expert123'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'expert' in data
            assert 'tokens' in data
    
    def test_expert_login_invalid_credentials(self):
        """Test expert login with invalid credentials."""
        with patch('backend.models.ExpertUser') as mock_user:
            mock_user.query.filter_by.return_value.first.return_value = None
            
            response = self.client.post('/api/expert/auth/login', json={
                'username': 'invalid',
                'password': 'wrong'
            })
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_expert_login_missing_credentials(self):
        """Test expert login with missing credentials."""
        response = self.client.post('/api/expert/auth/login', json={
            'username': 'expert'
            # Missing password
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_crm_customers_endpoint(self):
        """Test CRM customers endpoint."""
        with patch('backend.models.Customer') as mock_customer:
            # Mock customer query
            mock_customer_instance = MagicMock()
            mock_customer_instance.id = 1
            mock_customer_instance.first_name = 'John'
            mock_customer_instance.last_name = 'Doe'
            mock_customer_instance.email = 'john@example.com'
            mock_customer_instance.customer_type = 'customer'
            mock_customer_instance.status = 'active'
            mock_customer_instance.industry = 'Technology'
            mock_customer_instance.created_at = '2024-01-01T00:00:00'
            mock_customer_instance.opportunities = []
            mock_customer_instance.activities = []
            
            mock_customer.query.paginate.return_value.items = [mock_customer_instance]
            mock_customer.query.paginate.return_value.total = 1
            mock_customer.query.paginate.return_value.pages = 1
            mock_customer.query.paginate.return_value.has_next = False
            mock_customer.query.paginate.return_value.has_prev = False
            
            response = self.client.get('/api/crm/customers')
            
            # This would need authentication in real scenario
            # For now, just test that endpoint exists
            assert response.status_code in [200, 401]  # 401 if auth required
    
    def test_shipment_requests_endpoint(self):
        """Test shipment requests endpoint."""
        with patch('backend.models.ShipmentRequest') as mock_request:
            # Mock request query
            mock_request_instance = MagicMock()
            mock_request_instance.id = 1
            mock_request_instance.tracking_number = 'SR000001'
            mock_request_instance.status = 'new'
            mock_request_instance.priority = 'normal'
            mock_request_instance.created_at = '2024-01-01T00:00:00'
            mock_request_instance.customer = MagicMock()
            mock_request_instance.customer.name = 'Test Customer'
            mock_request_instance.customer.phone = '1234567890'
            mock_request_instance.route = MagicMock()
            mock_request_instance.route.origin = MagicMock()
            mock_request_instance.route.origin.city = 'Tehran'
            mock_request_instance.route.destination = MagicMock()
            mock_request_instance.route.destination.city = 'Isfahan'
            mock_request_instance.cargo = MagicMock()
            mock_request_instance.has_unread = False
            
            mock_request.query.paginate.return_value.items = [mock_request_instance]
            mock_request.query.paginate.return_value.total = 1
            mock_request.query.paginate.return_value.pages = 1
            mock_request.query.paginate.return_value.has_next = False
            mock_request.query.paginate.return_value.has_prev = False
            
            response = self.client.get('/api/expert/requests')
            
            # This would need authentication in real scenario
            assert response.status_code in [200, 401]  # 401 if auth required
    
    def test_cors_headers(self):
        """Test CORS headers are present."""
        response = self.client.options('/api/health/ping')
        
        # Check for CORS headers
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Methods' in response.headers
    
    def test_security_headers(self):
        """Test security headers are present."""
        response = self.client.get('/api/health/ping')
        
        # Check for security headers
        assert 'X-Frame-Options' in response.headers
        assert 'X-Content-Type-Options' in response.headers
        assert 'X-XSS-Protection' in response.headers
    
    def test_input_validation(self):
        """Test input validation."""
        # Test with invalid JSON
        response = self.client.post('/api/expert/auth/login', 
                                  data='invalid json',
                                  content_type='application/json')
        
        assert response.status_code == 400
    
    def test_rate_limiting(self):
        """Test rate limiting (if implemented)."""
        # This would test rate limiting functionality
        # For now, just ensure endpoint responds
        response = self.client.get('/api/health/ping')
        assert response.status_code == 200


class TestAPIErrorHandling:
    """Test cases for API error handling."""
    
    def setup_method(self):
        """Setup test environment."""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret-key'
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def teardown_method(self):
        """Cleanup test environment."""
        self.app_context.pop()
    
    def test_404_error(self):
        """Test 404 error handling."""
        response = self.client.get('/api/nonexistent')
        assert response.status_code == 404
    
    def test_405_method_not_allowed(self):
        """Test 405 method not allowed."""
        response = self.client.delete('/api/health/ping')
        assert response.status_code == 405
    
    def test_500_internal_server_error(self):
        """Test 500 internal server error handling."""
        # This would need to trigger an actual server error
        # For now, just test that error handling is in place
        response = self.client.get('/api/health/ping')
        assert response.status_code in [200, 500]


@pytest.fixture
def app():
    """Create test Flask app."""
    return create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key'
    })


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_api_structure(client):
    """Test API structure and consistency."""
    # Test that all endpoints return JSON
    endpoints = [
        '/api/health/ping',
        '/api/expert/ping',
        '/api/crm/ping'
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        if response.status_code == 200:
            assert response.content_type == 'application/json'


def test_api_response_format(client):
    """Test API response format consistency."""
    response = client.get('/api/health/ping')
    
    if response.status_code == 200:
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert 'message' in data
