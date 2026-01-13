"""
Supervisor Blueprint
=====================
Supervisor process management panel.
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required

from services.supervisor_service import supervisor_service

supervisor_bp = Blueprint('supervisor', __name__, template_folder='../templates')


@supervisor_bp.route('/')
@login_required
def index():
    """Supervisor management page."""
    return render_template('supervisor.html')


@supervisor_bp.route('/api/status')
@login_required
def api_status():
    """Get supervisor daemon status."""
    status = supervisor_service.get_status()
    return jsonify(status)


@supervisor_bp.route('/api/processes')
@login_required
def api_list_processes():
    """List all supervised processes."""
    processes = supervisor_service.list_processes()
    return jsonify({'processes': processes})


@supervisor_bp.route('/api/process/<name>')
@login_required
def api_get_process(name):
    """Get process details."""
    process = supervisor_service.get_process_info(name)
    if process:
        return jsonify(process)
    return jsonify({'error': 'Jarayon topilmadi'}), 404


@supervisor_bp.route('/api/process/<name>/start', methods=['POST'])
@login_required
def api_start_process(name):
    """Start a process."""
    result = supervisor_service.start_process(name)
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@supervisor_bp.route('/api/process/<name>/stop', methods=['POST'])
@login_required
def api_stop_process(name):
    """Stop a process."""
    result = supervisor_service.stop_process(name)
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@supervisor_bp.route('/api/process/<name>/restart', methods=['POST'])
@login_required
def api_restart_process(name):
    """Restart a process."""
    result = supervisor_service.restart_process(name)
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@supervisor_bp.route('/api/process/<name>/logs')
@login_required
def api_process_logs(name):
    """Get process logs."""
    tail = int(request.args.get('tail', 100))
    result = supervisor_service.get_process_logs(name, tail=tail)
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@supervisor_bp.route('/api/start-all', methods=['POST'])
@login_required
def api_start_all():
    """Start all processes."""
    result = supervisor_service.start_all()
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@supervisor_bp.route('/api/stop-all', methods=['POST'])
@login_required
def api_stop_all():
    """Stop all processes."""
    result = supervisor_service.stop_all()
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@supervisor_bp.route('/api/reload', methods=['POST'])
@login_required
def api_reload():
    """Reload supervisor configuration."""
    result = supervisor_service.reload_config()
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400
