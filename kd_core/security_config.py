"""
Security Configuration for KD-Code System
Best practices and security measures implemented
"""

import os
from flask import Flask
from flask_talisman import Talisman
from flask_seasurf import SeaSurf


def configure_security(app):
    """
    Apply security configurations to the Flask app
    """
    # Enable HTTPS in production
    if not app.debug:
        app.config['PREFERRED_URL_SCHEME'] = 'https'
    
    # CSRF protection
    csrf = SeaSurf(app)
    csrf.init_app(app)
    
    # HTTP security headers using Talisman
    Talisman(
        app,
        force_https_permanent=True,
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        frame_options='DENY',
        content_security_policy={
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline' https://cdn.tailwindcss.com",
            'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
            'font-src': "'self' https://fonts.gstatic.com",
            'img-src': "'self' data: https:",
        }
    )
    
    # Additional security configurations
    app.config['SESSION_COOKIE_SECURE'] = not app.debug  # Only send cookies over HTTPS in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS attacks
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
    
    return app


def security_checklist():
    """
    Checklist of security measures implemented
    """
    checklist = {
        "Authentication": {
            "JWT tokens implemented": True,
            "Token expiration configured": True,
            "Secure token storage": True
        },
        "Authorization": {
            "Role-based access control": False,  # Could be added
            "Rate limiting implemented": True,
            "API endpoint protection": True
        },
        "Data Protection": {
            "Data encryption at rest": False,  # Could be added
            "Data encryption in transit": True,  # HTTPS/TLS
            "Sensitive data masking": True,  # In logs
            "Input validation": True,
            "SQL injection prevention": True,  # Using ORM/parameterized queries
            "XSS prevention": True  # Using templating engine
        },
        "Network Security": {
            "HTTPS enforcement": True,
            "CORS policies": False,  # Could be added
            "DDoS protection": False,  # Would need infrastructure level
            "Firewall rules": False  # Infrastructure level
        },
        "Application Security": {
            "Dependency scanning": False,  # Would need external tools
            "Secure configuration management": True,  # Environment variables
            "Error handling": True,  # Custom error pages
            "Logging and monitoring": False  # Could be added
        },
        "Audit and Compliance": {
            "Access logging": False,  # Could be added
            "Security event logging": False,  # Could be added
            "Regular security updates": False  # Process, not code
        }
    }
    return checklist


def get_security_recommendations():
    """
    Recommendations for further security improvements
    """
    recommendations = [
        "Implement role-based access control (RBAC)",
        "Add CORS policy configuration",
        "Implement comprehensive logging for security events",
        "Add dependency vulnerability scanning to CI/CD",
        "Implement secure session management",
        "Add security headers validation",
        "Perform regular penetration testing",
        "Implement API rate limiting per user/IP",
        "Add brute force protection for authentication",
        "Encrypt sensitive data at rest using libraries like cryptography"
    ]
    return recommendations


# Example usage in app initialization
if __name__ == "__main__":
    # Example of how to use security configuration
    app = Flask(__name__)
    
    # Apply security configurations
    app = configure_security(app)
    
    print("Security configuration applied successfully!")
    print("\nSecurity Checklist:")
    checklist = security_checklist()
    for category, items in checklist.items():
        print(f"\n{category}:")
        for item, implemented in items.items():
            status = "✅" if implemented else "❌"
            print(f"  {status} {item}")
    
    print("\nSecurity Recommendations:")
    for rec in get_security_recommendations():
        print(f"  • {rec}")