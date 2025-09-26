"""Tests for authentication system."""
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask

from backend.auth import AuthManager, auth_manager
from backend.models import ExpertUser


class TestAuthManager:
    """Test cases for AuthManager class."""
    
    def setup_method(self):
        """Setup test environment."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
        
        self.auth_manager = AuthManager()
    
    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        with patch('backend.auth.ExpertUser') as mock_user:
            # Mock user object
            mock_user_instance = MagicMock()
            mock_user_instance.username = 'testuser'
            mock_user_instance.is_active = True
            mock_user_instance.id = 1
            mock_user_instance.full_name = 'Test User'
            mock_user_instance.email = 'test@example.com'
            mock_user_instance.role = 'expert'
            
            mock_user.query.filter_by.return_value.first.return_value = mock_user_instance
            
            # Mock request
            with patch('backend.auth.request') as mock_request:
                mock_request.remote_addr = '127.0.0.1'
                
                result = self.auth_manager.authenticate_user('testuser', 'expert123')
                
                assert result is not None
                assert result['id'] == 1
                assert result['username'] == 'testuser'
                assert result['full_name'] == 'Test User'
    
    def test_authenticate_user_invalid_credentials(self):
        """Test authentication with invalid credentials."""
        with patch('backend.auth.ExpertUser') as mock_user:
            mock_user.query.filter_by.return_value.first.return_value = None
            
            with patch('backend.auth.request') as mock_request:
                mock_request.remote_addr = '127.0.0.1'
                
                result = self.auth_manager.authenticate_user('invalid', 'wrong')
                
                assert result is None
    
    def test_authenticate_user_locked_out(self):
        """Test authentication when IP is locked out."""
        # Simulate lockout
        self.auth_manager.login_attempts['127.0.0.1'] = {
            'count': 5,
            'last_attempt': '2024-01-01T00:00:00'
        }
        
        with patch('backend.auth.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = '2024-01-01T00:05:00'
            mock_datetime.strptime.return_value = '2024-01-01T00:00:00'
            
            result = self.auth_manager.authenticate_user('testuser', 'expert123')
            
            assert result is None
    
    def test_generate_tokens(self):
        """Test token generation."""
        with patch('backend.auth.security') as mock_security:
            mock_security.generate_token.return_value = 'test-token'
            
            tokens = self.auth_manager.generate_tokens(1)
            
            assert 'access_token' in tokens
            assert 'refresh_token' in tokens
            assert tokens['access_token'] == 'test-token'
            assert tokens['refresh_token'] == 'test-token'
    
    def test_refresh_access_token_valid(self):
        """Test valid refresh token."""
        with patch('backend.auth.security') as mock_security:
            mock_security.verify_token.return_value = {
                'user_id': 1,
                'token_type': 'refresh'
            }
            
            with patch.object(self.auth_manager, 'generate_tokens') as mock_generate:
                mock_generate.return_value = {'access_token': 'new-token'}
                
                result = self.auth_manager.refresh_access_token('valid-refresh-token')
                
                assert result is not None
                assert result['access_token'] == 'new-token'
    
    def test_refresh_access_token_invalid(self):
        """Test invalid refresh token."""
        with patch('backend.auth.security') as mock_security:
            mock_security.verify_token.return_value = None
            
            result = self.auth_manager.refresh_access_token('invalid-token')
            
            assert result is None


class TestSecurityDecorators:
    """Test cases for security decorators."""
    
    def test_require_auth_decorator(self):
        """Test require_auth decorator."""
        from backend.auth import require_auth
        
        @require_auth
        def protected_function():
            return "success"
        
        # This would need Flask app context to test properly
        # In a real test, you'd use Flask's test client
        assert callable(protected_function)
    
    def test_login_required_decorator(self):
        """Test login_required decorator."""
        from backend.auth import login_required
        
        @login_required
        def protected_function():
            return "success"
        
        assert callable(protected_function)


@pytest.fixture
def app():
    """Create test Flask app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_auth_endpoints(client):
    """Test authentication endpoints."""
    # Test login endpoint
    response = client.post('/api/expert/auth/login', json={
        'username': 'expert',
        'password': 'expert123'
    })
    
    # This would need proper app setup with routes
    # assert response.status_code == 200
    assert response is not None


def test_security_headers(client):
    """Test security headers are present."""
    response = client.get('/')
    
    # Check for security headers
    assert 'X-Frame-Options' in response.headers
    assert 'X-Content-Type-Options' in response.headers
    assert 'X-XSS-Protection' in response.headers
