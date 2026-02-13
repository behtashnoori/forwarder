"""
Dynamic CORS Configuration
Automatically handles CORS origins for development environments
"""

import os
import re
from typing import List, Set, Union, Callable


def generate_cors_origins() -> List[str]:
    """
    Generate comprehensive CORS origins for development.
    Includes all common development ports and patterns.
    """
    origins: Set[str] = set()
    
    # Common development ports
    common_ports = [3000, 5173, 8080, 8081, 8082, 8083, 8084, 8085]
    
    # Vite development server port range (8080-8200)
    vite_ports = list(range(8080, 8201))
    
    # Combine all ports
    all_ports = list(set(common_ports + vite_ports))
    
    # Generate origins for localhost and 127.0.0.1
    for port in all_ports:
        origins.add(f"http://localhost:{port}")
        origins.add(f"http://127.0.0.1:{port}")
    
    # Add any custom origins from environment (e.g. http://130.185.77.25:8080 for network access)
    custom_origins = os.getenv('CORS_ORIGINS', '') or os.getenv('CORS_ORIGIN', '')
    if custom_origins:
        for origin in custom_origins.split(','):
            origin = origin.strip()
            if origin and origin.startswith('http'):
                origins.add(origin)
    
    return sorted(list(origins))


def validate_origin(origin: str) -> bool:
    """
    Validate if an origin is allowed for CORS.
    """
    if not origin:
        return False
    
    # Allow localhost and 127.0.0.1 with any port
    localhost_pattern = r'^http://(localhost|127\.0\.0\.1):\d+$'
    
    # Allow specific domains (add your production domains here)
    allowed_domains = [
        r'^https://yourdomain\.com$',
        r'^https://www\.yourdomain\.com$'
    ]
    
    # Check localhost pattern
    if re.match(localhost_pattern, origin):
        return True
    
    # Check allowed domains
    for pattern in allowed_domains:
        if re.match(pattern, origin):
            return True
    
    return False


def _allow_any_origin(origin: str) -> bool:
    """Allow any origin (for development / network access)."""
    return True


def get_cors_config() -> dict:
    """
    Get CORS configuration with dynamic origins.
    In development (or when CORS_ALLOW_ALL_ORIGINS=1), allow any origin for network/internet access.
    """
    origins_list = generate_cors_origins()
    is_dev = os.getenv('FLASK_ENV', '').lower() in ('development', 'dev') or os.getenv('FLASK_DEBUG', '').lower() in ('true', '1', 'yes')
    allow_all = os.getenv('CORS_ALLOW_ALL_ORIGINS', '').lower() in ('1', 'true', 'yes')

    # Flask-CORS expects origins to be an iterable (list), not a callable.
    # When is_dev or allow_all, we pass the full list; our after_request in __init__.py
    # adds CORS headers for any other origin via _is_cors_origin_allowed().
    origins: List[str] = origins_list

    return {
        'resources': {
            r'/*': {
                'origins': origins,
                'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
                'allow_headers': [
                    'Content-Type',
                    'Authorization',
                    'X-CSRF-Token',
                    'X-Requested-With',
                    'Accept',
                    'Origin'
                ],
                'supports_credentials': True,
                'max_age': 3600
            }
        },
        'supports_credentials': True,
        'origins': origins
    }


def log_cors_info():
    """
    Log CORS configuration information for debugging.
    """
    config = get_cors_config()
    origins = config['origins']
    
    print("CORS Configuration:")
    if callable(origins):
        print("   Mode: Allow any origin (development)")
    else:
        print(f"   Total Origins: {len(origins)}")
    print(f"   Supports Credentials: {config['supports_credentials']}")
    print(f"   Max Age: {config['resources'][r'/*']['max_age']} seconds")
    
    if not callable(origins) and origins:
        print("   Sample Origins:")
        for origin in origins[:5]:
            print(f"      - {origin}")
        if len(origins) > 5:
            print(f"      ... and {len(origins) - 5} more")
    
    print()


if __name__ == '__main__':
    log_cors_info()








