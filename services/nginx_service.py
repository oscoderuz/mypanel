"""
Nginx Service
==============
Nginx configuration generation and management.
"""

import os
import subprocess
import re
from typing import Dict, Optional, List
from datetime import datetime


class NginxService:
    """
    Service for Nginx configuration management and SSL certificate handling.
    """
    
    # Default paths
    SITES_AVAILABLE = '/etc/nginx/sites-available'
    SITES_ENABLED = '/etc/nginx/sites-enabled'
    NGINX_CONF = '/etc/nginx/nginx.conf'
    CERTBOT_PATH = '/usr/bin/certbot'
    
    # Config templates
    REVERSE_PROXY_TEMPLATE = """# Managed by MyPanel - {domain}
# Created: {created_at}

server {{
    listen 80;
    listen [::]:80;
    server_name {domain} www.{domain};

    location / {{
        proxy_pass http://{target_host}:{target_port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }}

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}}
"""

    STATIC_SITE_TEMPLATE = """# Managed by MyPanel - {domain}
# Created: {created_at}

server {{
    listen 80;
    listen [::]:80;
    server_name {domain} www.{domain};

    root {root_path};
    index index.html index.htm index.php;

    location / {{
        try_files $uri $uri/ =404;
    }}

    # Deny access to hidden files
    location ~ /\\. {{
        deny all;
    }}

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
}}
"""

    SSL_SERVER_BLOCK = """
server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {domain} www.{domain};

    ssl_certificate {ssl_certificate};
    ssl_certificate_key {ssl_key};
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    {location_block}
}}

# Redirect HTTP to HTTPS
server {{
    listen 80;
    listen [::]:80;
    server_name {domain} www.{domain};
    return 301 https://$server_name$request_uri;
}}
"""

    def __init__(self, sites_available: str = None, sites_enabled: str = None):
        """Initialize Nginx service with custom paths if provided."""
        self.sites_available = sites_available or self.SITES_AVAILABLE
        self.sites_enabled = sites_enabled or self.SITES_ENABLED
    
    def _get_config_path(self, domain: str) -> str:
        """Get the full path to a domain's config file."""
        return os.path.join(self.sites_available, f"{domain}.conf")
    
    def _get_enabled_path(self, domain: str) -> str:
        """Get the full path to a domain's enabled symlink."""
        return os.path.join(self.sites_enabled, f"{domain}.conf")
    
    # ==================== Config Generation ====================
    
    def generate_reverse_proxy_config(
        self,
        domain: str,
        target_port: int,
        target_host: str = '127.0.0.1'
    ) -> str:
        """
        Generate Nginx reverse proxy configuration.
        
        Args:
            domain: Domain name
            target_port: Port to proxy to
            target_host: Target host (default: localhost)
        
        Returns:
            str: Nginx configuration content
        """
        return self.REVERSE_PROXY_TEMPLATE.format(
            domain=domain,
            target_host=target_host,
            target_port=target_port,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    
    def generate_static_site_config(self, domain: str, root_path: str) -> str:
        """
        Generate Nginx static site configuration.
        
        Args:
            domain: Domain name
            root_path: Document root path
        
        Returns:
            str: Nginx configuration content
        """
        return self.STATIC_SITE_TEMPLATE.format(
            domain=domain,
            root_path=root_path,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    
    # ==================== Config Management ====================
    
    def create_config(
        self,
        domain: str,
        config_type: str = 'reverse_proxy',
        target_port: int = None,
        root_path: str = None,
        target_host: str = '127.0.0.1'
    ) -> Dict:
        """
        Create a new Nginx configuration file.
        
        Args:
            domain: Domain name
            config_type: 'reverse_proxy' or 'static'
            target_port: Target port for reverse proxy
            root_path: Document root for static sites
            target_host: Target host for proxy
        
        Returns:
            dict: Result with success status
        """
        try:
            config_path = self._get_config_path(domain)
            
            # Check if config already exists
            if os.path.exists(config_path):
                return {
                    'success': False,
                    'error': f'Конфиг для {domain} уже существует'
                }
            
            # Generate config content
            if config_type == 'reverse_proxy':
                if not target_port:
                    return {'success': False, 'error': 'Порт не указан'}
                content = self.generate_reverse_proxy_config(domain, target_port, target_host)
            elif config_type == 'static':
                if not root_path:
                    return {'success': False, 'error': 'Путь к файлам не указан'}
                content = self.generate_static_site_config(domain, root_path)
            else:
                return {'success': False, 'error': 'Неизвестный тип конфигурации'}
            
            # Write config file
            with open(config_path, 'w') as f:
                f.write(content)
            
            return {
                'success': True,
                'message': f'Конфиг создан: {config_path}',
                'config_path': config_path
            }
            
        except PermissionError:
            return {
                'success': False,
                'error': 'Недостаточно прав для создания конфига'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка: {str(e)}'
            }
    
    def read_config(self, domain: str) -> Dict:
        """
        Read a domain's Nginx configuration.
        
        Args:
            domain: Domain name
        
        Returns:
            dict: Config content or error
        """
        try:
            config_path = self._get_config_path(domain)
            
            if not os.path.exists(config_path):
                return {'success': False, 'error': 'Конфиг не найден'}
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            return {
                'success': True,
                'content': content,
                'path': config_path
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_config(self, domain: str, content: str) -> Dict:
        """
        Update a domain's Nginx configuration.
        
        Args:
            domain: Domain name
            content: New config content
        
        Returns:
            dict: Result with success status
        """
        try:
            config_path = self._get_config_path(domain)
            
            # Backup existing config
            if os.path.exists(config_path):
                backup_path = f"{config_path}.bak"
                with open(config_path, 'r') as f:
                    with open(backup_path, 'w') as bf:
                        bf.write(f.read())
            
            # Write new content
            with open(config_path, 'w') as f:
                f.write(content)
            
            # Test configuration
            test_result = self.test_config()
            if not test_result['success']:
                # Restore backup
                if os.path.exists(f"{config_path}.bak"):
                    os.rename(f"{config_path}.bak", config_path)
                return {
                    'success': False,
                    'error': f'Ошибка синтаксиса: {test_result.get("error", "")}'
                }
            
            return {
                'success': True,
                'message': 'Конфиг обновлен'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_config(self, domain: str) -> Dict:
        """Delete a domain's configuration."""
        try:
            config_path = self._get_config_path(domain)
            enabled_path = self._get_enabled_path(domain)
            
            # Remove symlink first
            if os.path.exists(enabled_path):
                os.unlink(enabled_path)
            
            # Remove config file
            if os.path.exists(config_path):
                os.remove(config_path)
            
            return {'success': True, 'message': 'Конфиг удален'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ==================== Enable/Disable ====================
    
    def enable_site(self, domain: str) -> Dict:
        """Enable a site by creating symlink in sites-enabled."""
        try:
            config_path = self._get_config_path(domain)
            enabled_path = self._get_enabled_path(domain)
            
            if not os.path.exists(config_path):
                return {'success': False, 'error': 'Конфиг не найден'}
            
            if os.path.exists(enabled_path):
                return {'success': True, 'message': 'Сайт уже включен'}
            
            os.symlink(config_path, enabled_path)
            
            return {'success': True, 'message': 'Сайт включен'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def disable_site(self, domain: str) -> Dict:
        """Disable a site by removing symlink."""
        try:
            enabled_path = self._get_enabled_path(domain)
            
            if os.path.exists(enabled_path):
                os.unlink(enabled_path)
            
            return {'success': True, 'message': 'Сайт отключен'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ==================== Nginx Control ====================
    
    def test_config(self) -> Dict:
        """Test Nginx configuration syntax."""
        try:
            result = subprocess.run(
                ['nginx', '-t'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {'success': True, 'message': 'Синтаксис корректен'}
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Таймаут проверки'}
        except FileNotFoundError:
            return {'success': False, 'error': 'Nginx не установлен'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def reload_nginx(self) -> Dict:
        """Reload Nginx configuration."""
        try:
            # Test config first
            test_result = self.test_config()
            if not test_result['success']:
                return test_result
            
            result = subprocess.run(
                ['systemctl', 'reload', 'nginx'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {'success': True, 'message': 'Nginx перезагружен'}
            else:
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def restart_nginx(self) -> Dict:
        """Restart Nginx service."""
        try:
            result = subprocess.run(
                ['systemctl', 'restart', 'nginx'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {'success': True, 'message': 'Nginx перезапущен'}
            else:
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_nginx_status(self) -> Dict:
        """Get Nginx service status."""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'nginx'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            status = result.stdout.strip()
            return {
                'running': status == 'active',
                'status': status
            }
            
        except Exception as e:
            return {'running': False, 'status': 'unknown', 'error': str(e)}
    
    # ==================== SSL/Certbot ====================
    
    def issue_ssl_certificate(self, domain: str, email: str = None) -> Dict:
        """
        Issue SSL certificate using Certbot.
        
        Args:
            domain: Domain name
            email: Email for certificate notifications
        
        Returns:
            dict: Result with success status
        """
        try:
            cmd = [
                self.CERTBOT_PATH,
                '--nginx',
                '-d', domain,
                '-d', f'www.{domain}',
                '--non-interactive',
                '--agree-tos',
                '--redirect'
            ]
            
            if email:
                cmd.extend(['--email', email])
            else:
                cmd.append('--register-unsafely-without-email')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'SSL сертификат выпущен для {domain}'
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr or result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Таймаут выпуска сертификата'}
        except FileNotFoundError:
            return {'success': False, 'error': 'Certbot не установлен'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def renew_certificates(self) -> Dict:
        """Renew all SSL certificates."""
        try:
            result = subprocess.run(
                [self.CERTBOT_PATH, 'renew', '--quiet'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return {'success': True, 'message': 'Сертификаты обновлены'}
            else:
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ==================== Site Listing ====================
    
    def list_sites(self) -> List[Dict]:
        """List all configured sites."""
        sites = []
        
        try:
            if not os.path.exists(self.sites_available):
                return sites
            
            for filename in os.listdir(self.sites_available):
                if filename.endswith('.conf'):
                    domain = filename[:-5]  # Remove .conf
                    config_path = os.path.join(self.sites_available, filename)
                    enabled_path = os.path.join(self.sites_enabled, filename)
                    
                    sites.append({
                        'domain': domain,
                        'config_path': config_path,
                        'enabled': os.path.exists(enabled_path),
                        'modified': datetime.fromtimestamp(
                            os.path.getmtime(config_path)
                        ).isoformat()
                    })
            
            return sites
            
        except Exception:
            return sites


# Singleton instance
nginx_service = NginxService()
