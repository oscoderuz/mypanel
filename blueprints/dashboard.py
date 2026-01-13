"""
Dashboard Blueprint
====================
Main dashboard with system statistics.
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required

from services.system_service import system_service
from services.docker_service import docker_service

dashboard_bp = Blueprint('dashboard', __name__, template_folder='../templates')


@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')


@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    """
    Get real-time system statistics.
    
    Returns JSON with CPU, memory, disk, and network stats.
    """
    try:
        stats = system_service.get_all_stats()
        
        # Add Docker container count
        try:
            containers = docker_service.list_containers(all_containers=True)
            running = sum(1 for c in containers if c.get('status') == 'running')
            stats['docker'] = {
                'total': len(containers),
                'running': running,
                'stopped': len(containers) - running
            }
        except Exception:
            stats['docker'] = {'total': 0, 'running': 0, 'stopped': 0, 'error': True}
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/stats/cpu')
@login_required
def api_cpu_stats():
    """Get CPU statistics."""
    return jsonify(system_service.get_cpu_info())


@dashboard_bp.route('/api/stats/memory')
@login_required
def api_memory_stats():
    """Get memory statistics."""
    return jsonify(system_service.get_memory_info())


@dashboard_bp.route('/api/stats/disk')
@login_required
def api_disk_stats():
    """Get disk statistics."""
    return jsonify({'disks': system_service.get_disk_info()})


@dashboard_bp.route('/api/stats/network')
@login_required
def api_network_stats():
    """Get network statistics."""
    return jsonify(system_service.get_network_info())


@dashboard_bp.route('/api/stats/system')
@login_required
def api_system_info():
    """Get general system information."""
    return jsonify(system_service.get_system_info())


@dashboard_bp.route('/api/processes')
@login_required
def api_processes():
    """Get top processes by resource usage."""
    sort_by = request.args.get('sort', 'cpu')
    limit = int(request.args.get('limit', 10))
    
    from flask import request
    processes = system_service.get_processes(sort_by=sort_by, limit=limit)
    return jsonify({'processes': processes})


@dashboard_bp.route('/api/processes/<int:pid>/kill', methods=['POST'])
@login_required
def api_kill_process(pid):
    """Kill a process by PID."""
    result = system_service.kill_process(pid)
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400
