"""
MyPanel Configuration Module
=============================
Centralized configuration for the application.
"""

import os
import secrets

# Base directory of the application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Base configuration class."""
    
    # Flask
    SECRET_KEY = os.environ.get('MYPANEL_SECRET_KEY') or secrets.token_hex(32)
    DEBUG = os.environ.get('MYPANEL_DEBUG', 'False').lower() == 'true'
    
    # Server
    HOST = os.environ.get('MYPANEL_HOST', '0.0.0.0')
    PORT = int(os.environ.get('MYPANEL_PORT', 8888))
    
    # Database
    DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'mypanel.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    
    # File Manager
    FILE_MANAGER_ROOT = os.environ.get('MYPANEL_FILE_ROOT', '/')
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'svg',
        'html', 'css', 'js', 'json', 'xml', 'yml', 'yaml',
        'py', 'php', 'sh', 'conf', 'env', 'md', 'log'
    }
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max upload
    
    # Nginx Paths
    NGINX_SITES_AVAILABLE = '/etc/nginx/sites-available'
    NGINX_SITES_ENABLED = '/etc/nginx/sites-enabled'
    NGINX_CONF_PATH = '/etc/nginx/nginx.conf'
    
    # Certbot
    CERTBOT_PATH = '/usr/bin/certbot'
    
    # Docker
    DOCKER_SOCKET = 'unix://var/run/docker.sock'
    
    # Supervisor
    SUPERVISOR_CONF_DIR = '/etc/supervisor/conf.d'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FILE_MANAGER_ROOT = os.path.expanduser('~')


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}


def get_config():
    """Get configuration based on environment."""
    env = os.environ.get('MYPANEL_ENV', 'production')
    return config_map.get(env, config_map['default'])
