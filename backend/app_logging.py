"""Advanced logging system for the application."""
import logging
import logging.handlers
import os
import json
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps

from flask import request, g, current_app
from werkzeug.exceptions import HTTPException


class StructuredLogger:
    """Structured logging with JSON format for better analysis."""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize logging with Flask app."""
        self.app = app
        
        # Create logs directory
        logs_dir = os.path.join(app.instance_path, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Configure logging
        self._setup_logging(app, logs_dir)
    
    def _setup_logging(self, app, logs_dir):
        """Setup comprehensive logging configuration."""
        
        # Application logger
        app_logger = logging.getLogger('forwarder')
        app_logger.setLevel(logging.INFO)
        
        # Security logger
        security_logger = logging.getLogger('forwarder.security')
        security_logger.setLevel(logging.WARNING)
        
        # API logger
        api_logger = logging.getLogger('forwarder.api')
        api_logger.setLevel(logging.INFO)
        
        # Database logger
        db_logger = logging.getLogger('forwarder.database')
        db_logger.setLevel(logging.WARNING)
        
        # Performance logger
        perf_logger = logging.getLogger('forwarder.performance')
        perf_logger.setLevel(logging.INFO)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        json_formatter = JSONFormatter()
        
        # File handlers with rotation
        app_handler = logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, 'app.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        app_handler.setFormatter(detailed_formatter)
        app_logger.addHandler(app_handler)
        
        # Security log file
        security_handler = logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, 'security.log'),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        security_handler.setFormatter(json_formatter)
        security_logger.addHandler(security_handler)
        
        # API log file
        api_handler = logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, 'api.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        api_handler.setFormatter(json_formatter)
        api_logger.addHandler(api_handler)
        
        # Error log file
        error_handler = logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, 'error.log'),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setFormatter(detailed_formatter)
        error_handler.setLevel(logging.ERROR)
        app_logger.addHandler(error_handler)
        
        # Console handler for development
        if app.debug:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(detailed_formatter)
            app_logger.addHandler(console_handler)
    
    def log_api_request(self, method: str, endpoint: str, status_code: int, 
                       response_time: float, user_id: Optional[int] = None):
        """Log API request with structured data."""
        logger = logging.getLogger('forwarder.api')
        
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'api_request',
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'response_time_ms': round(response_time * 1000, 2),
            'user_id': user_id,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'request_id': getattr(g, 'request_id', None)
        }
        
        logger.info(json.dumps(log_data))
    
    def log_security_event(self, event_type: str, severity: str, 
                          description: str, user_id: Optional[int] = None,
                          additional_data: Optional[Dict] = None):
        """Log security events."""
        logger = logging.getLogger('forwarder.security')
        
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'security_event',
            'event_type': event_type,
            'severity': severity,
            'description': description,
            'user_id': user_id,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'additional_data': additional_data or {}
        }
        
        if severity == 'CRITICAL':
            logger.critical(json.dumps(log_data))
        elif severity == 'HIGH':
            logger.error(json.dumps(log_data))
        elif severity == 'MEDIUM':
            logger.warning(json.dumps(log_data))
        else:
            logger.info(json.dumps(log_data))
    
    def log_performance(self, operation: str, duration: float, 
                       additional_metrics: Optional[Dict] = None):
        """Log performance metrics."""
        logger = logging.getLogger('forwarder.performance')
        
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'performance',
            'operation': operation,
            'duration_ms': round(duration * 1000, 2),
            'additional_metrics': additional_metrics or {}
        }
        
        logger.info(json.dumps(log_data))
    
    def log_database_operation(self, operation: str, table: str, 
                              duration: float, rows_affected: Optional[int] = None):
        """Log database operations."""
        logger = logging.getLogger('forwarder.database')
        
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'database_operation',
            'operation': operation,
            'table': table,
            'duration_ms': round(duration * 1000, 2),
            'rows_affected': rows_affected
        }
        
        logger.info(json.dumps(log_data))
    
    def log_error(self, error: Exception, context: Optional[Dict] = None):
        """Log errors with full context."""
        logger = logging.getLogger('forwarder')
        
        error_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'error',
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'request_data': {
                'method': request.method,
                'url': request.url,
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', '')
            }
        }
        
        logger.error(json.dumps(error_data, indent=2))


class JSONFormatter(logging.Formatter):
    """Custom formatter for JSON logs."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        return json.dumps(log_entry)


# Global logger instance
logger = StructuredLogger()


def log_api_call(f):
    """Decorator to log API calls."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = datetime.utcnow()
        
        try:
            result = f(*args, **kwargs)
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            # Log successful API call
            logger.log_api_request(
                method=request.method,
                endpoint=request.endpoint or request.path,
                status_code=200,
                response_time=response_time,
                user_id=getattr(g, 'current_user_id', None)
            )
            
            return result
            
        except HTTPException as e:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            # Log HTTP exception
            logger.log_api_request(
                method=request.method,
                endpoint=request.endpoint or request.path,
                status_code=e.code,
                response_time=response_time,
                user_id=getattr(g, 'current_user_id', None)
            )
            
            raise
            
        except Exception as e:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            # Log error
            logger.log_error(e, {
                'endpoint': request.endpoint or request.path,
                'method': request.method,
                'response_time': response_time
            })
            
            raise
    
    return decorated_function


def log_performance(operation_name: str):
    """Decorator to log performance metrics."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            
            try:
                result = f(*args, **kwargs)
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                logger.log_performance(operation_name, duration)
                
                return result
                
            except Exception as e:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                logger.log_performance(operation_name, duration, {
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                
                raise
        
        return wrapper
    return decorator


def log_database_operation(operation: str, table: str):
    """Decorator to log database operations."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            
            try:
                result = f(*args, **kwargs)
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                # Try to get rows affected from result
                rows_affected = None
                if hasattr(result, 'rowcount'):
                    rows_affected = result.rowcount
                
                logger.log_database_operation(operation, table, duration, rows_affected)
                
                return result
                
            except Exception as e:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                logger.log_database_operation(operation, table, duration)
                logger.log_error(e, {
                    'operation': operation,
                    'table': table
                })
                
                raise
        
        return wrapper
    return decorator


def log_security_event(event_type: str, severity: str = 'MEDIUM', 
                      description: str = '', additional_data: Optional[Dict] = None):
    """Log security events."""
    logger.log_security_event(
        event_type=event_type,
        severity=severity,
        description=description,
        user_id=getattr(g, 'current_user_id', None),
        additional_data=additional_data
    )
