"""
Docker Store Blueprint
=======================
Docker Hub App Store and Container Management.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from flask_socketio import emit

from database import db
from models import Container
from services.docker_service import docker_service

docker_bp = Blueprint('docker', __name__, template_folder='../templates')


# ==================== Views ====================

@docker_bp.route('/store')
@login_required
def store():
    """Docker App Store page."""
    return render_template('docker/store.html')


@docker_bp.route('/containers')
@login_required
def containers():
    """Container management page."""
    return render_template('docker/containers.html')


# ==================== Docker Hub Search API ====================

@docker_bp.route('/api/search')
@login_required
def api_search():
    """
    Search Docker Hub for images.
    
    Query params:
        q: Search query
        page: Page number (default: 1)
        page_size: Results per page (default: 25)
    """
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'error': 'Введите поисковый запрос', 'results': []}), 400
    
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 25))
    
    results = docker_service.search_hub(query, page=page, page_size=page_size)
    return jsonify(results)


@docker_bp.route('/api/tags/<path:image_name>')
@login_required
def api_get_tags(image_name):
    """Get available tags for an image."""
    tags = docker_service.get_image_tags(image_name)
    return jsonify({'image': image_name, 'tags': tags})


# ==================== Image Management API ====================

@docker_bp.route('/api/images')
@login_required
def api_list_images():
    """List all local Docker images."""
    images = docker_service.list_images()
    return jsonify({'images': images})


@docker_bp.route('/api/images/pull', methods=['POST'])
@login_required
def api_pull_image():
    """
    Pull a Docker image.
    
    JSON body:
        image: Image name (e.g., 'nginx')
        tag: Image tag (default: 'latest')
    """
    data = request.get_json() or {}
    image = data.get('image', '').strip()
    tag = data.get('tag', 'latest').strip()
    
    if not image:
        return jsonify({'error': 'Укажите имя образа'}), 400
    
    try:
        # Pull image and collect progress
        progress_log = []
        for progress in docker_service.pull_image(image, tag):
            progress_log.append(progress)
            if progress.get('error'):
                return jsonify({
                    'success': False,
                    'error': progress['error']
                }), 400
        
        return jsonify({
            'success': True,
            'message': f'Образ {image}:{tag} загружен',
            'progress': progress_log
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@docker_bp.route('/api/images/<path:image_id>', methods=['DELETE'])
@login_required
def api_delete_image(image_id):
    """Delete a Docker image."""
    force = request.args.get('force', 'false').lower() == 'true'
    result = docker_service.remove_image(image_id, force=force)
    
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


# ==================== Container Management API ====================

@docker_bp.route('/api/containers')
@login_required
def api_list_containers():
    """List all containers."""
    all_containers = request.args.get('all', 'true').lower() == 'true'
    containers = docker_service.list_containers(all_containers=all_containers)
    return jsonify({'containers': containers})


@docker_bp.route('/api/containers/<container_id>')
@login_required
def api_get_container(container_id):
    """Get container details."""
    container = docker_service.get_container(container_id)
    if container:
        return jsonify(container)
    return jsonify({'error': 'Контейнер не найден'}), 404


@docker_bp.route('/api/containers', methods=['POST'])
@login_required
def api_create_container():
    """
    Create and start a new container.
    
    JSON body:
        image: Docker image name
        name: Container name
        ports: Port mappings {'80/tcp': 8080}
        volumes: Volume bindings ['/host:/container']
        environment: Environment variables {'KEY': 'value'}
    """
    data = request.get_json() or {}
    
    image = data.get('image', '').strip()
    name = data.get('name', '').strip()
    ports = data.get('ports', {})
    volumes = data.get('volumes', [])
    environment = data.get('environment', {})
    restart_policy = data.get('restart_policy', 'unless-stopped')
    
    # Validation
    if not image:
        return jsonify({'error': 'Укажите образ Docker'}), 400
    if not name:
        return jsonify({'error': 'Укажите имя контейнера'}), 400
    
    # Create container
    result = docker_service.create_container(
        image=image,
        name=name,
        ports=ports,
        volumes=volumes,
        environment=environment,
        restart_policy=restart_policy
    )
    
    if result.get('success'):
        # Save to database
        try:
            container_record = Container(
                container_id=result['container_id'],
                name=name,
                image=image,
                ports=ports,
                volumes=volumes,
                env=environment
            )
            db.session.add(container_record)
            db.session.commit()
        except Exception:
            pass  # Non-critical if DB save fails
        
        return jsonify(result), 201
    
    return jsonify(result), 400


@docker_bp.route('/api/containers/<container_id>/start', methods=['POST'])
@login_required
def api_start_container(container_id):
    """Start a container."""
    result = docker_service.start_container(container_id)
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@docker_bp.route('/api/containers/<container_id>/stop', methods=['POST'])
@login_required
def api_stop_container(container_id):
    """Stop a container."""
    timeout = int(request.args.get('timeout', 10))
    result = docker_service.stop_container(container_id, timeout=timeout)
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@docker_bp.route('/api/containers/<container_id>/restart', methods=['POST'])
@login_required
def api_restart_container(container_id):
    """Restart a container."""
    result = docker_service.restart_container(container_id)
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@docker_bp.route('/api/containers/<container_id>', methods=['DELETE'])
@login_required
def api_delete_container(container_id):
    """Delete a container."""
    force = request.args.get('force', 'false').lower() == 'true'
    remove_volumes = request.args.get('volumes', 'false').lower() == 'true'
    
    result = docker_service.remove_container(container_id, force=force, v=remove_volumes)
    
    if result.get('success'):
        # Remove from database
        try:
            Container.query.filter_by(container_id=container_id).delete()
            db.session.commit()
        except Exception:
            pass
        return jsonify(result)
    
    return jsonify(result), 400


@docker_bp.route('/api/containers/<container_id>/logs')
@login_required
def api_container_logs(container_id):
    """Get container logs."""
    tail = int(request.args.get('tail', 100))
    timestamps = request.args.get('timestamps', 'true').lower() == 'true'
    
    logs = []
    for line in docker_service.get_container_logs(
        container_id, 
        tail=tail, 
        stream=False,
        timestamps=timestamps
    ):
        logs.append(line)
    
    return jsonify({'logs': ''.join(logs)})


@docker_bp.route('/api/containers/<container_id>/exec', methods=['POST'])
@login_required
def api_container_exec(container_id):
    """Execute command in a container."""
    data = request.get_json() or {}
    command = data.get('command', 'echo "Hello"')
    
    result = docker_service.exec_command(container_id, command)
    return jsonify(result)


@docker_bp.route('/api/containers/<container_id>/stats')
@login_required
def api_container_stats(container_id):
    """Get container resource usage stats."""
    stats = docker_service.get_container_stats(container_id)
    if stats:
        return jsonify(stats)
    return jsonify({'error': 'Не удалось получить статистику'}), 400


# ==================== WebSocket Handlers for Live Logs ====================

def register_docker_socket_handlers(socketio):
    """Register WebSocket handlers for Docker operations."""
    
    @socketio.on('docker_logs_subscribe')
    def handle_logs_subscribe(data):
        """Subscribe to container log stream."""
        container_id = data.get('container_id')
        if not container_id:
            emit('error', {'message': 'Container ID required'})
            return
        
        try:
            for line in docker_service.get_container_logs(
                container_id,
                tail=50,
                stream=True,
                timestamps=True
            ):
                emit('docker_logs', {'container_id': container_id, 'line': line})
        except Exception as e:
            emit('error', {'message': str(e)})
    
    @socketio.on('docker_pull_subscribe')
    def handle_pull_subscribe(data):
        """Subscribe to image pull progress."""
        image = data.get('image')
        tag = data.get('tag', 'latest')
        
        if not image:
            emit('error', {'message': 'Image name required'})
            return
        
        try:
            for progress in docker_service.pull_image(image, tag):
                emit('docker_pull_progress', {
                    'image': f"{image}:{tag}",
                    'progress': progress
                })
        except Exception as e:
            emit('docker_pull_error', {'message': str(e)})
