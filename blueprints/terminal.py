"""
Terminal Blueprint
===================
Web-based SSH terminal using WebSocket and PTY.
"""

import os
import pty
import select
import subprocess
import struct
import fcntl
import termios
from flask import Blueprint, render_template
from flask_login import login_required, current_user

terminal_bp = Blueprint('terminal', __name__, template_folder='../templates')

# Store active terminal sessions
terminal_sessions = {}


@terminal_bp.route('/')
@login_required
def index():
    """Web terminal page."""
    return render_template('terminal.html')


def set_winsize(fd, row, col, xpix=0, ypix=0):
    """Set the window size of the PTY."""
    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def register_socket_handlers(socketio):
    """
    Register WebSocket handlers for terminal operations.
    
    Args:
        socketio: Flask-SocketIO instance
    """
    
    @socketio.on('terminal_connect')
    def handle_terminal_connect(data=None):
        """Handle new terminal connection."""
        from flask_socketio import emit
        from flask import request
        
        if not current_user.is_authenticated:
            emit('terminal_error', {'message': 'Требуется авторизация'})
            return
        
        session_id = request.sid
        
        try:
            # Create pseudo-terminal
            master_fd, slave_fd = pty.openpty()
            
            # Spawn shell process
            shell = os.environ.get('SHELL', '/bin/bash')
            env = os.environ.copy()
            env['TERM'] = 'xterm-256color'
            
            pid = subprocess.Popen(
                [shell],
                preexec_fn=os.setsid,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env
            )
            
            # Store session
            terminal_sessions[session_id] = {
                'master_fd': master_fd,
                'slave_fd': slave_fd,
                'pid': pid,
                'user': current_user.username
            }
            
            # Set initial size
            set_winsize(master_fd, 24, 80)
            
            emit('terminal_ready', {'session_id': session_id})
            
            # Start reading output
            def read_output():
                while session_id in terminal_sessions:
                    try:
                        if select.select([master_fd], [], [], 0.1)[0]:
                            output = os.read(master_fd, 1024)
                            if output:
                                socketio.emit('terminal_output', {
                                    'data': output.decode('utf-8', errors='replace')
                                }, room=session_id)
                    except (OSError, IOError):
                        break
            
            socketio.start_background_task(read_output)
            
        except Exception as e:
            emit('terminal_error', {'message': str(e)})
    
    @socketio.on('terminal_input')
    def handle_terminal_input(data):
        """Handle terminal input from client."""
        from flask import request
        
        session_id = request.sid
        session = terminal_sessions.get(session_id)
        
        if not session:
            return
        
        try:
            input_data = data.get('data', '')
            if input_data:
                os.write(session['master_fd'], input_data.encode('utf-8'))
        except (OSError, IOError):
            pass
    
    @socketio.on('terminal_resize')
    def handle_terminal_resize(data):
        """Handle terminal resize event."""
        from flask import request
        
        session_id = request.sid
        session = terminal_sessions.get(session_id)
        
        if not session:
            return
        
        try:
            rows = int(data.get('rows', 24))
            cols = int(data.get('cols', 80))
            set_winsize(session['master_fd'], rows, cols)
        except (OSError, IOError, ValueError):
            pass
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Clean up terminal session on disconnect."""
        from flask import request
        
        session_id = request.sid
        session = terminal_sessions.pop(session_id, None)
        
        if session:
            try:
                # Close file descriptors
                os.close(session['master_fd'])
                os.close(session['slave_fd'])
                
                # Terminate process
                session['pid'].terminate()
                session['pid'].wait(timeout=5)
            except Exception:
                try:
                    session['pid'].kill()
                except Exception:
                    pass
