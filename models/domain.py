"""
Domain Model
=============
Website/Domain management with Nginx configuration.
"""

from datetime import datetime
from database import db


class Domain(db.Model):
    """Domain model for managing websites and reverse proxy configs."""
    
    __tablename__ = 'domains'
    
    id = db.Column(db.Integer, primary_key=True)
    domain_name = db.Column(db.String(255), unique=True, nullable=False, index=True)
    
    # Proxy settings
    proxy_type = db.Column(db.String(20), default='reverse_proxy')  # reverse_proxy, static
    target_host = db.Column(db.String(255), default='127.0.0.1')
    target_port = db.Column(db.Integer, nullable=True)
    root_path = db.Column(db.String(500), nullable=True)  # For static sites
    
    # SSL
    ssl_enabled = db.Column(db.Boolean, default=False)
    ssl_certificate = db.Column(db.String(500), nullable=True)
    ssl_key = db.Column(db.String(500), nullable=True)
    ssl_issued_at = db.Column(db.DateTime, nullable=True)
    ssl_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Nginx config
    config_path = db.Column(db.String(500), nullable=True)
    is_enabled = db.Column(db.Boolean, default=True)
    
    # Associated container
    container_id = db.Column(db.String(100), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, domain_name, proxy_type='reverse_proxy', target_port=None, root_path=None):
        """
        Initialize a new domain.
        
        Args:
            domain_name: The domain name (e.g., example.com)
            proxy_type: 'reverse_proxy' or 'static'
            target_port: Port to proxy to (for reverse_proxy)
            root_path: Document root path (for static sites)
        """
        self.domain_name = domain_name.lower().strip()
        self.proxy_type = proxy_type
        self.target_port = target_port
        self.root_path = root_path
    
    @property
    def config_filename(self):
        """Get the Nginx config filename."""
        return f"{self.domain_name}.conf"
    
    @property
    def ssl_status(self):
        """Get SSL certificate status."""
        if not self.ssl_enabled:
            return 'disabled'
        if self.ssl_expires_at and self.ssl_expires_at < datetime.utcnow():
            return 'expired'
        return 'active'
    
    def to_dict(self):
        """
        Convert domain to dictionary representation.
        
        Returns:
            dict: Domain data
        """
        return {
            'id': self.id,
            'domain_name': self.domain_name,
            'proxy_type': self.proxy_type,
            'target_host': self.target_host,
            'target_port': self.target_port,
            'root_path': self.root_path,
            'ssl_enabled': self.ssl_enabled,
            'ssl_status': self.ssl_status,
            'ssl_expires_at': self.ssl_expires_at.isoformat() if self.ssl_expires_at else None,
            'is_enabled': self.is_enabled,
            'container_id': self.container_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Domain {self.domain_name}>'
