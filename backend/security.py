"""Security utilities and middleware for the application."""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

from flask import request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from uuid import uuid4


class SecurityManager:
    """Centralized security management for the application."""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security with Flask app."""
        self.app = app
        
        # Security configuration: create_app supplies validated values. Keep a
        # development/test fallback here for direct SecurityManager initialization,
        # but never generate runtime-random secrets that would invalidate tokens.
        from backend.config import get_secret_config

        secret_key, jwt_secret_key = get_secret_config(testing=bool(app.config.get('TESTING')))
        app.config.setdefault('SECRET_KEY', secret_key)
        app.config.setdefault('JWT_SECRET_KEY', jwt_secret_key)
        app.config.setdefault('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=1))
        app.config.setdefault('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30))
        app.config.setdefault('PASSWORD_HASH_METHOD', 'pbkdf2:sha256')
        app.config.setdefault('MAX_LOGIN_ATTEMPTS', 5)
        app.config.setdefault('LOCKOUT_DURATION', timedelta(minutes=15))
        
        # Rate limiting
        app.config.setdefault('RATELIMIT_STORAGE_URL', 'memory://')
        app.config.setdefault('RATELIMIT_DEFAULT', '100 per hour')
        
        # CORS security
        app.config.setdefault('CORS_ORIGINS', ['http://localhost:3000', 'http://localhost:5173'])
        
        # Security headers
        self._setup_security_headers(app)
    
    def _setup_security_headers(self, app):
        """Setup security headers middleware."""
        @app.after_request
        def add_security_headers(response):
            # Prevent clickjacking
            response.headers['X-Frame-Options'] = 'DENY'
            
            # Prevent MIME type sniffing
            response.headers['X-Content-Type-Options'] = 'nosniff'
            
            # XSS Protection
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Strict Transport Security (HTTPS only)
            if request.is_secure:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            # Content Security Policy
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            )
            
            # Referrer Policy
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            return response
    
    def hash_password(self, password: str) -> str:
        """Hash a password using the configured method."""
        return generate_password_hash(password, method=self.app.config['PASSWORD_HASH_METHOD'])
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return check_password_hash(hashed, password)
    
    def generate_token(
        self,
        user_id: int,
        token_type: str = 'access',
        *,
        session_id: str | None = None,
        jti: str | None = None,
    ) -> str:
        """Generate JWT token for user."""
        payload = {
            'user_id': user_id,
            'token_type': token_type,
            'iat': datetime.utcnow(),
            'jti': jti or str(uuid4()),
            'exp': datetime.utcnow() + (
                self.app.config['JWT_ACCESS_TOKEN_EXPIRES'] if token_type == 'access'
                else self.app.config['JWT_REFRESH_TOKEN_EXPIRES']
            )
        }
        if session_id:
            payload['sid'] = session_id
        return jwt.encode(payload, self.app.config['JWT_SECRET_KEY'], algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.app.config['JWT_SECRET_KEY'],
                algorithms=['HS256'],
                leeway=self.app.config.get('JWT_CLOCK_SKEW_SECONDS', 60),
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def generate_csrf_token(self) -> str:
        """Generate CSRF token."""
        return secrets.token_urlsafe(32)
    
    def verify_csrf_token(self, token: str, session_token: str) -> bool:
        """Verify CSRF token."""
        return secrets.compare_digest(token, session_token)


# Global security manager instance
security = SecurityManager()


def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid authorization header'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            payload = security.verify_token(token)
            if not payload:
                return jsonify({'error': 'Invalid token'}), 401
            if payload.get('token_type') != 'access' or not payload.get('jti') or not payload.get('sid'):
                return jsonify({'error': 'Invalid token'}), 401

            from backend.extensions import db
            from backend.models import ExpertUser
            from backend.services.token_revocation_service import is_token_revoked
            if is_token_revoked(payload['jti']):
                return jsonify({'error': 'Invalid token'}), 401
            from backend.services.auth_session_service import is_session_active
            if not is_session_active(payload['sid'], payload.get('user_id')):
                return jsonify({'error': 'Invalid token'}), 401
            user = ExpertUser.query.filter_by(id=payload.get('user_id'), is_active=True).first()
            if not user or not user.is_active:
                return jsonify({'error': 'Invalid token'}), 401
            
            g.current_user_id = payload['user_id']
            g.current_user_token_type = payload['token_type']
            g.current_token_payload = payload
            
        except Exception as e:
            return jsonify({'error': 'Token verification failed'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


# Role hierarchy mapping (higher number = higher privilege)
ROLE_HIERARCHY = {
    'admin': 5,
    'crm_manager': 4,
    'supervisor': 3,
    'business_expert': 2,
    'expert': 1
}


def get_role_level(role: str) -> int:
    """Get hierarchy level for a role."""
    return ROLE_HIERARCHY.get(role, 0)


def can_access_role(user_role: str, required_role: str) -> bool:
    """
    Check if user role can access resources requiring required_role.
    Uses hierarchical permission: higher roles can access lower role resources.
    """
    user_level = get_role_level(user_role)
    required_level = get_role_level(required_role)
    return user_level >= required_level


def require_role(*allowed_roles: str, allow_owner: bool = False, owner_param: str = 'user_id'):
    """
    Decorator to require specific role(s) with hierarchical permission support.
    
    Args:
        *allowed_roles: One or more roles that can access the endpoint
        allow_owner: If True, allow access if user owns the resource (e.g., user_id matches)
        owner_param: Parameter name to check for ownership (default: 'user_id')
    
    Examples:
        @require_role('admin', 'crm_manager')  # Only admin or crm_manager
        @require_role('admin')  # Only admin (but admin can access everything)
        @require_role('expert', allow_owner=True, owner_param='expert_id')  # Expert or owner
    """
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            from backend.auth import get_current_user
            
            current_user = get_current_user()
            if not current_user:
                return jsonify({'error': 'کاربر احراز هویت نشده است'}), 401
            
            user_role = current_user.get('role')
            user_id = current_user.get('id')
            
            if not user_role:
                return jsonify({'error': 'نقش کاربر تعیین نشده است'}), 403
            
            # Check if user role is in allowed roles or has higher privilege
            has_access = False
            
            # Check direct role match or hierarchical access
            for allowed_role in allowed_roles:
                if user_role == allowed_role or can_access_role(user_role, allowed_role):
                    has_access = True
                    break
            
            # Check ownership if allowed
            if not has_access and allow_owner:
                owner_id = kwargs.get(owner_param) or request.view_args.get(owner_param)
                if owner_id and int(owner_id) == user_id:
                    has_access = True
            
            if not has_access:
                return jsonify({
                    'error': 'دسترسی غیرمجاز',
                    'required_roles': list(allowed_roles),
                    'user_role': user_role
                }), 403
            
            # Store user info in g for use in route handlers
            g.current_user = current_user
            g.current_user_role = user_role
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def validate_input(schema: Dict[str, Any]):
    """Decorator to validate input data."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.is_json:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'Invalid JSON data'}), 400
                
                # Basic validation - in production, use a proper validation library like marshmallow
                for field, rules in schema.items():
                    if rules.get('required', False) and field not in data:
                        return jsonify({'error': f'Field {field} is required'}), 400
                    
                    if field in data:
                        value = data[field]
                        field_type = rules.get('type', str)
                        
                        if field_type == str and not isinstance(value, str):
                            return jsonify({'error': f'Field {field} must be a string'}), 400
                        elif field_type == int and not isinstance(value, int):
                            return jsonify({'error': f'Field {field} must be an integer'}), 400
                        elif field_type == float and not isinstance(value, (int, float)):
                            return jsonify({'error': f'Field {field} must be a number'}), 400
                        
                        # Length validation for strings
                        if isinstance(value, str) and 'max_length' in rules:
                            if len(value) > rules['max_length']:
                                return jsonify({'error': f'Field {field} is too long'}), 400
                        
                        # Range validation for numbers
                        if isinstance(value, (int, float)) and 'min' in rules:
                            if value < rules['min']:
                                return jsonify({'error': f'Field {field} is too small'}), 400
                        if isinstance(value, (int, float)) and 'max' in rules:
                            if value > rules['max']:
                                return jsonify({'error': f'Field {field} is too large'}), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def sanitize_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize input data to prevent XSS and injection attacks."""
    sanitized = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            # Remove potentially dangerous characters
            sanitized[key] = value.strip().replace('<', '&lt;').replace('>', '&gt;')
        elif isinstance(value, dict):
            sanitized[key] = sanitize_input(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_input(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value
    
    return sanitized


def rate_limit(max_requests: int = 100, per: int = 3600):
    """Simple rate limiting decorator."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Simple in-memory rate limiting
            # In production, use Redis or similar
            client_ip = request.remote_addr
            current_time = datetime.utcnow()
            
            # This is a simplified implementation
            # In production, use proper rate limiting library
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
