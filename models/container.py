"""
Container Model
================
Docker container settings and configuration storage.
"""

from datetime import datetime
import json
from database import db


class Container(db.Model):
    """Container model for storing Docker container configurations."""
    
    __tablename__ = 'containers'
    
    id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    
    # Configuration (stored as JSON)
    ports_config = db.Column(db.Text, nullable=True)  # JSON: {"80/tcp": 8080}
    volumes_config = db.Column(db.Text, nullable=True)  # JSON: ["/host:/container"]
    env_config = db.Column(db.Text, nullable=True)  # JSON: {"KEY": "value"}
    
    # Custom settings
    auto_restart = db.Column(db.Boolean, default=True)
    auto_update = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, container_id, name, image, ports=None, volumes=None, env=None):
        """
        Initialize a container record.
        
        Args:
            container_id: Docker container ID
            name: Container name
            image: Docker image name
            ports: Port mappings dict
            volumes: Volume mappings list
            env: Environment variables dict
        """
        self.container_id = container_id
        self.name = name
        self.image = image
        self.set_ports(ports or {})
        self.set_volumes(volumes or [])
        self.set_env(env or {})
    
    def set_ports(self, ports):
        """Set port mappings from dict."""
        self.ports_config = json.dumps(ports)
    
    def get_ports(self):
        """Get port mappings as dict."""
        if self.ports_config:
            return json.loads(self.ports_config)
        return {}
    
    def set_volumes(self, volumes):
        """Set volume mappings from list."""
        self.volumes_config = json.dumps(volumes)
    
    def get_volumes(self):
        """Get volume mappings as list."""
        if self.volumes_config:
            return json.loads(self.volumes_config)
        return []
    
    def set_env(self, env):
        """Set environment variables from dict."""
        self.env_config = json.dumps(env)
    
    def get_env(self):
        """Get environment variables as dict."""
        if self.env_config:
            return json.loads(self.env_config)
        return {}
    
    def to_dict(self):
        """
        Convert container to dictionary representation.
        
        Returns:
            dict: Container data
        """
        return {
            'id': self.id,
            'container_id': self.container_id,
            'name': self.name,
            'image': self.image,
            'ports': self.get_ports(),
            'volumes': self.get_volumes(),
            'env': self.get_env(),
            'auto_restart': self.auto_restart,
            'auto_update': self.auto_update,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Container {self.name}>'
