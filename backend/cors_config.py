"""
Dynamic CORS Configuration
Automatically handles CORS origins for development environments
"""

import re
from typing import List, Set


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
    
    # Add any custom origins from environment
    import os
    custom_origins = os.getenv('CORS_ORIGINS', '')
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


def get_cors_config():
    """
    Get CORS configuration with dynamic origins.
    """
    origins = generate_cors_origins()
    
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
    
    print("🌐 CORS Configuration:")
    print(f"   📊 Total Origins: {len(origins)}")
    print(f"   🔧 Supports Credentials: {config['supports_credentials']}")
    print(f"   ⏰ Max Age: {config['resources'][r'/*']['max_age']} seconds")
    
    # Show first few origins as examples
    if origins:
        print("   📋 Sample Origins:")
        for origin in origins[:5]:
            print(f"      ✅ {origin}")
        if len(origins) > 5:
            print(f"      ... and {len(origins) - 5} more")
    
    print()


if __name__ == '__main__':
    log_cors_info()


