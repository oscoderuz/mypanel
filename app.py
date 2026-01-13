"""
MyPanel - Server Management Panel
===================================
Main application entry point with Flask and SocketIO.

A lightweight, beautiful alternative to aaPanel/Umbrel
for Ubuntu Server management.
"""

import os
import eventlet
eventlet.monkey_patch()

from flask import Flask, redirect, url_for
from flask_socketio import SocketIO
from flask_login import LoginManager

from config import get_config, Config
from database import db, init_db

# Initialize SocketIO
socketio = SocketIO(
    async_mode='eventlet',
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25
)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к панели.'
login_manager.login_message_category = 'warning'


def create_app(config_class=None):
    """
    Application factory for creating Flask app.
    
    Args:
        config_class: Configuration class to use (optional)
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    
    # Ensure data directory exists
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Initialize extensions
    init_db(app)
    socketio.init_app(app)
    login_manager.init_app(app)
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.docker_store import docker_bp
    from blueprints.websites import websites_bp
    from blueprints.files import files_bp
    from blueprints.terminal import terminal_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(docker_bp, url_prefix='/docker')
    app.register_blueprint(websites_bp, url_prefix='/websites')
    app.register_blueprint(files_bp, url_prefix='/files')
    app.register_blueprint(terminal_bp, url_prefix='/terminal')
    
    # Root redirect
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.index'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Страница не найдена'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error': 'Внутренняя ошибка сервера'}, 500
    
    # Context processors
    @app.context_processor
    def inject_globals():
        """Inject global variables into templates."""
        from models import User
        return {
            'panel_name': 'MyPanel',
            'panel_version': '1.0.0',
            'is_first_run': User.query.count() == 0
        }
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███╗   ███╗██╗   ██╗██████╗  █████╗ ███╗   ██╗███████╗██╗  ║
║   ████╗ ████║╚██╗ ██╔╝██╔══██╗██╔══██╗████╗  ██║██╔════╝██║  ║
║   ██╔████╔██║ ╚████╔╝ ██████╔╝███████║██╔██╗ ██║█████╗  ██║  ║
║   ██║╚██╔╝██║  ╚██╔╝  ██╔═══╝ ██╔══██║██║╚██╗██║██╔══╝  ██║  ║
║   ██║ ╚═╝ ██║   ██║   ██║     ██║  ██║██║ ╚████║███████╗███████╗
║   ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝
║                                                              ║
║   Server Management Panel v1.0.0                             ║
║   Running on http://{app.config['HOST']}:{app.config['PORT']}                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    return app


# Terminal WebSocket handlers
def register_terminal_handlers(socketio_instance):
    """Register terminal WebSocket event handlers."""
    from blueprints.terminal import register_socket_handlers
    register_socket_handlers(socketio_instance)


if __name__ == '__main__':
    app = create_app()
    register_terminal_handlers(socketio)
    
    socketio.run(
        app,
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )
