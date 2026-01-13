"""
MyPanel Blueprints Package
===========================
Flask Blueprints for routing and API endpoints.
"""

from blueprints.auth import auth_bp
from blueprints.dashboard import dashboard_bp
from blueprints.docker_store import docker_bp
from blueprints.websites import websites_bp
from blueprints.files import files_bp
from blueprints.terminal import terminal_bp
from blueprints.supervisor import supervisor_bp

__all__ = [
    'auth_bp',
    'dashboard_bp', 
    'docker_bp',
    'websites_bp',
    'files_bp',
    'terminal_bp',
    'supervisor_bp'
]
