"""
Websites Blueprint
===================
Domain management, Nginx configuration, and SSL certificates.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required

from database import db
from models import Domain
from services.nginx_service import nginx_service

websites_bp = Blueprint('websites', __name__, template_folder='../templates')


# ==================== Views ====================

@websites_bp.route('/')
@login_required
def index():
    """Website management page."""
    return render_template('websites/index.html')


# ==================== Domain API ====================

@websites_bp.route('/api/domains')
@login_required
def api_list_domains():
    """List all configured domains."""
    domains = Domain.query.all()
    
    # Merge with Nginx config status
    nginx_sites = {s['domain']: s for s in nginx_service.list_sites()}
    
    result = []
    for domain in domains:
        data = domain.to_dict()
        nginx_data = nginx_sites.get(domain.domain_name, {})
        data['nginx_enabled'] = nginx_data.get('enabled', False)
        result.append(data)
    
    return jsonify({'domains': result})


@websites_bp.route('/api/domains', methods=['POST'])
@login_required
def api_create_domain():
    """
    Create a new domain configuration.
    
    JSON body:
        domain_name: Domain name (e.g., 'example.com')
        proxy_type: 'reverse_proxy' or 'static'
        target_port: Port to proxy to (for reverse_proxy)
        root_path: Document root (for static sites)
        container_id: Associated container ID (optional)
    """
    data = request.get_json() or {}
    
    domain_name = data.get('domain_name', '').strip().lower()
    proxy_type = data.get('proxy_type', 'reverse_proxy')
    target_port = data.get('target_port')
    root_path = data.get('root_path', '').strip()
    container_id = data.get('container_id')
    
    # Validation
    if not domain_name:
        return jsonify({'error': 'Укажите доменное имя'}), 400
    
    if Domain.query.filter_by(domain_name=domain_name).first():
        return jsonify({'error': 'Домен уже существует'}), 400
    
    if proxy_type == 'reverse_proxy' and not target_port:
        return jsonify({'error': 'Укажите порт для проксирования'}), 400
    
    if proxy_type == 'static' and not root_path:
        return jsonify({'error': 'Укажите путь к файлам сайта'}), 400
    
    try:
        # Create domain in database
        domain = Domain(
            domain_name=domain_name,
            proxy_type=proxy_type,
            target_port=int(target_port) if target_port else None,
            root_path=root_path if proxy_type == 'static' else None
        )
        domain.container_id = container_id
        
        # Create Nginx config
        if proxy_type == 'reverse_proxy':
            result = nginx_service.create_config(
                domain=domain_name,
                config_type='reverse_proxy',
                target_port=int(target_port)
            )
        else:
            result = nginx_service.create_config(
                domain=domain_name,
                config_type='static',
                root_path=root_path
            )
        
        if not result.get('success'):
            return jsonify(result), 400
        
        domain.config_path = result.get('config_path')
        
        # Enable site
        nginx_service.enable_site(domain_name)
        
        # Reload Nginx
        nginx_service.reload_nginx()
        
        # Save to database
        db.session.add(domain)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Домен {domain_name} создан',
            'domain': domain.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@websites_bp.route('/api/domains/<int:domain_id>')
@login_required
def api_get_domain(domain_id):
    """Get domain details."""
    domain = Domain.query.get(domain_id)
    if not domain:
        return jsonify({'error': 'Домен не найден'}), 404
    return jsonify(domain.to_dict())


@websites_bp.route('/api/domains/<int:domain_id>', methods=['PUT'])
@login_required
def api_update_domain(domain_id):
    """Update domain settings."""
    domain = Domain.query.get(domain_id)
    if not domain:
        return jsonify({'error': 'Домен не найден'}), 404
    
    data = request.get_json() or {}
    
    if 'target_port' in data:
        domain.target_port = int(data['target_port'])
    if 'root_path' in data:
        domain.root_path = data['root_path']
    if 'is_enabled' in data:
        domain.is_enabled = data['is_enabled']
    
    db.session.commit()
    
    # Regenerate and reload Nginx config if needed
    if domain.proxy_type == 'reverse_proxy' and domain.target_port:
        content = nginx_service.generate_reverse_proxy_config(
            domain.domain_name,
            domain.target_port
        )
        nginx_service.update_config(domain.domain_name, content)
        nginx_service.reload_nginx()
    
    return jsonify({
        'success': True,
        'message': 'Домен обновлен',
        'domain': domain.to_dict()
    })


@websites_bp.route('/api/domains/<int:domain_id>', methods=['DELETE'])
@login_required
def api_delete_domain(domain_id):
    """Delete a domain configuration."""
    domain = Domain.query.get(domain_id)
    if not domain:
        return jsonify({'error': 'Домен не найден'}), 404
    
    try:
        # Remove Nginx config
        nginx_service.delete_config(domain.domain_name)
        nginx_service.reload_nginx()
        
        # Remove from database
        db.session.delete(domain)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Домен {domain.domain_name} удален'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== Nginx Config API ====================

@websites_bp.route('/api/domains/<int:domain_id>/config')
@login_required
def api_get_config(domain_id):
    """Get Nginx configuration content for a domain."""
    domain = Domain.query.get(domain_id)
    if not domain:
        return jsonify({'error': 'Домен не найден'}), 404
    
    result = nginx_service.read_config(domain.domain_name)
    return jsonify(result)


@websites_bp.route('/api/domains/<int:domain_id>/config', methods=['PUT'])
@login_required
def api_update_config(domain_id):
    """Update Nginx configuration for a domain."""
    domain = Domain.query.get(domain_id)
    if not domain:
        return jsonify({'error': 'Домен не найден'}), 404
    
    data = request.get_json() or {}
    content = data.get('content', '')
    
    if not content:
        return jsonify({'error': 'Пустой конфиг'}), 400
    
    result = nginx_service.update_config(domain.domain_name, content)
    
    if result.get('success'):
        nginx_service.reload_nginx()
        return jsonify(result)
    
    return jsonify(result), 400


@websites_bp.route('/api/domains/<int:domain_id>/enable', methods=['POST'])
@login_required
def api_enable_domain(domain_id):
    """Enable a domain in Nginx."""
    domain = Domain.query.get(domain_id)
    if not domain:
        return jsonify({'error': 'Домен не найден'}), 404
    
    result = nginx_service.enable_site(domain.domain_name)
    if result.get('success'):
        nginx_service.reload_nginx()
        domain.is_enabled = True
        db.session.commit()
    
    return jsonify(result)


@websites_bp.route('/api/domains/<int:domain_id>/disable', methods=['POST'])
@login_required
def api_disable_domain(domain_id):
    """Disable a domain in Nginx."""
    domain = Domain.query.get(domain_id)
    if not domain:
        return jsonify({'error': 'Домен не найден'}), 404
    
    result = nginx_service.disable_site(domain.domain_name)
    if result.get('success'):
        nginx_service.reload_nginx()
        domain.is_enabled = False
        db.session.commit()
    
    return jsonify(result)


# ==================== SSL API ====================

@websites_bp.route('/api/domains/<int:domain_id>/ssl', methods=['POST'])
@login_required
def api_issue_ssl(domain_id):
    """Issue SSL certificate for a domain."""
    domain = Domain.query.get(domain_id)
    if not domain:
        return jsonify({'error': 'Домен не найден'}), 404
    
    data = request.get_json() or {}
    email = data.get('email')
    
    result = nginx_service.issue_ssl_certificate(domain.domain_name, email=email)
    
    if result.get('success'):
        domain.ssl_enabled = True
        db.session.commit()
        return jsonify(result)
    
    return jsonify(result), 400


@websites_bp.route('/api/ssl/renew', methods=['POST'])
@login_required
def api_renew_ssl():
    """Renew all SSL certificates."""
    result = nginx_service.renew_certificates()
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


# ==================== Nginx Status API ====================

@websites_bp.route('/api/nginx/status')
@login_required
def api_nginx_status():
    """Get Nginx service status."""
    return jsonify(nginx_service.get_nginx_status())


@websites_bp.route('/api/nginx/reload', methods=['POST'])
@login_required
def api_nginx_reload():
    """Reload Nginx configuration."""
    result = nginx_service.reload_nginx()
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@websites_bp.route('/api/nginx/restart', methods=['POST'])
@login_required
def api_nginx_restart():
    """Restart Nginx service."""
    result = nginx_service.restart_nginx()
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@websites_bp.route('/api/nginx/test')
@login_required
def api_nginx_test():
    """Test Nginx configuration."""
    return jsonify(nginx_service.test_config())
