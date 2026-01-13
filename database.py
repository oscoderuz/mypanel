"""
MyPanel Database Module
========================
SQLAlchemy database initialization and session management.
"""

import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Initialize SQLAlchemy
db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key support for SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db(app):
    """
    Initialize the database with the Flask application.
    
    Args:
        app: Flask application instance
    """
    # Ensure data directory exists
    db_path = app.config.get('DATABASE_PATH')
    if db_path:
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    # Initialize SQLAlchemy with app
    db.init_app(app)
    
    # Create all tables
    with app.app_context():
        # Import models to register them
        from models import User, Domain, Container
        db.create_all()
        
        print(f"[Database] Initialized at {db_path}")


def get_session():
    """Get current database session."""
    return db.session
