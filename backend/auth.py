"""Authentication and authorization system."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
import bcrypt

from flask import request, jsonify, g, current_app
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import ExpertUser
from backend.security import security, require_auth, validate_input


class AuthManager:
    """Authentication and authorization manager."""
    
    def __init__(self):
        self.login_attempts = {}  # In production, use Redis
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password."""
        # Check for brute force attempts
        client_ip = request.remote_addr
        if self._is_locked_out(client_ip):
            return None
        
        try:
            user = ExpertUser.query.filter_by(username=username, is_active=True).first()
            if not user:
                self._record_failed_attempt(client_ip)
                return None
            
            # Verify password using bcrypt
            if user.password_hash and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                self._clear_failed_attempts(client_ip)
                
                # Update last login
                user.last_login_at = datetime.utcnow()
                db.session.commit()
                
                return {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'email': user.email,
                    'role': user.role
                }
            else:
                self._record_failed_attempt(client_ip)
                return None
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error during authentication: {e}")
            return None
    
    def _is_locked_out(self, client_ip: str) -> bool:
        """Check if IP is locked out due to too many failed attempts."""
        if client_ip not in self.login_attempts:
            return False
        
        attempts = self.login_attempts[client_ip]
        max_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
        lockout_duration = current_app.config.get('LOCKOUT_DURATION', timedelta(minutes=15))
        
        if attempts['count'] >= max_attempts:
            if datetime.utcnow() - attempts['last_attempt'] < lockout_duration:
                return True
            else:
                # Lockout period expired, reset attempts
                del self.login_attempts[client_ip]
        
        return False
    
    def _record_failed_attempt(self, client_ip: str):
        """Record a failed login attempt."""
        if client_ip not in self.login_attempts:
            self.login_attempts[client_ip] = {'count': 0, 'last_attempt': None}
        
        self.login_attempts[client_ip]['count'] += 1
        self.login_attempts[client_ip]['last_attempt'] = datetime.utcnow()
    
    def _clear_failed_attempts(self, client_ip: str):
        """Clear failed attempts for successful login."""
        if client_ip in self.login_attempts:
            del self.login_attempts[client_ip]
    
    def generate_tokens(self, user_id: int) -> Dict[str, str]:
        """Generate access and refresh tokens for user."""
        access_token = security.generate_token(user_id, 'access')
        refresh_token = security.generate_token(user_id, 'refresh')
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
        }
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Generate new access token using refresh token."""
        payload = security.verify_token(refresh_token)
        if not payload or payload.get('token_type') != 'refresh':
            return None
        
        user_id = payload['user_id']
        return self.generate_tokens(user_id)


# Global auth manager instance
auth_manager = AuthManager()


def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'current_user_id'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'current_user_id'):
            return jsonify({'error': 'Authentication required'}), 401
        
        # TODO: Implement proper role checking
        # For now, allow all authenticated users
        return f(*args, **kwargs)
    return decorated_function


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current authenticated user information."""
    if not hasattr(g, 'current_user_id'):
        return None
    
    try:
        user = ExpertUser.query.get(g.current_user_id)
        if not user or not user.is_active:
            return None
        
        return {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'email': user.email,
            'role': user.role
        }
    except SQLAlchemyError:
        return None
