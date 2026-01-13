"""
Docker Service
===============
Docker Hub API integration and container management via Docker SDK.
"""

import requests
import docker
from docker.errors import DockerException, NotFound, APIError
from typing import Dict, List, Optional, Generator
import json


class DockerService:
    """
    Service for Docker operations including Hub search and container management.
    """
    
    DOCKER_HUB_API = "https://hub.docker.com/v2"
    DOCKER_REGISTRY_API = "https://registry.hub.docker.com/v2"
    
    def __init__(self):
        """Initialize Docker client."""
        self._client = None
    
    @property
    def client(self):
        """Lazily initialize Docker client."""
        if self._client is None:
            try:
                self._client = docker.from_env()
            except DockerException as e:
                raise DockerException(f"Не удалось подключиться к Docker: {e}")
        return self._client
    
    # ==================== Docker Hub Search ====================
    
    def search_hub(self, query: str, page: int = 1, page_size: int = 25) -> Dict:
        """
        Search Docker Hub for images.
        
        Args:
            query: Search query string
            page: Page number for pagination
            page_size: Number of results per page
        
        Returns:
            dict: Search results with summaries
        """
        try:
            url = f"{self.DOCKER_HUB_API}/search/repositories"
            params = {
                'query': query,
                'page': page,
                'page_size': page_size
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Format results
            results = []
            for item in data.get('results', []):
                results.append({
                    'name': item.get('repo_name', item.get('name', '')),
                    'description': item.get('short_description', '')[:200],
                    'stars': item.get('star_count', 0),
                    'pulls': item.get('pull_count', 0),
                    'is_official': item.get('is_official', False),
                    'is_automated': item.get('is_automated', False)
                })
            
            return {
                'results': results,
                'count': data.get('count', len(results)),
                'page': page,
                'page_size': page_size,
                'next': data.get('next'),
                'previous': data.get('previous')
            }
            
        except requests.RequestException as e:
            return {
                'error': f"Ошибка поиска в Docker Hub: {str(e)}",
                'results': [],
                'count': 0
            }
    
    def get_image_tags(self, image_name: str, page_size: int = 10) -> List[str]:
        """
        Get available tags for an image from Docker Hub.
        
        Args:
            image_name: Image name (e.g., 'nginx' or 'library/nginx')
        
        Returns:
            list: Available tag names
        """
        try:
            # Handle official images
            if '/' not in image_name:
                image_name = f"library/{image_name}"
            
            url = f"{self.DOCKER_HUB_API}/repositories/{image_name}/tags"
            params = {'page_size': page_size}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tags = [tag.get('name') for tag in data.get('results', [])]
            
            return tags
            
        except requests.RequestException:
            return ['latest']
    
    # ==================== Image Management ====================
    
    def pull_image(self, image_name: str, tag: str = 'latest') -> Generator[Dict, None, None]:
        """
        Pull a Docker image with progress streaming.
        
        Args:
            image_name: Image name to pull
            tag: Image tag (default: latest)
        
        Yields:
            dict: Progress updates
        """
        full_name = f"{image_name}:{tag}"
        
        try:
            for line in self.client.api.pull(image_name, tag=tag, stream=True, decode=True):
                status = line.get('status', '')
                progress = line.get('progress', '')
                layer_id = line.get('id', '')
                
                yield {
                    'status': status,
                    'progress': progress,
                    'id': layer_id,
                    'complete': status in ['Pull complete', 'Already exists', 'Downloaded newer image']
                }
            
            yield {
                'status': 'Completed',
                'progress': '100%',
                'complete': True,
                'image': full_name
            }
            
        except APIError as e:
            yield {
                'status': 'Error',
                'error': str(e),
                'complete': False
            }
    
    def list_images(self) -> List[Dict]:
        """
        List all local Docker images.
        
        Returns:
            list: Image information dicts
        """
        try:
            images = self.client.images.list()
            result = []
            
            for img in images:
                tags = img.tags if img.tags else ['<none>:<none>']
                result.append({
                    'id': img.short_id,
                    'tags': tags,
                    'size': img.attrs.get('Size', 0),
                    'created': img.attrs.get('Created', '')
                })
            
            return result
            
        except DockerException as e:
            return []
    
    def remove_image(self, image_id: str, force: bool = False) -> Dict:
        """Remove a Docker image."""
        try:
            self.client.images.remove(image_id, force=force)
            return {'success': True, 'message': 'Образ удален'}
        except NotFound:
            return {'success': False, 'error': 'Образ не найден'}
        except APIError as e:
            return {'success': False, 'error': str(e)}
    
    # ==================== Container Management ====================
    
    def create_container(
        self,
        image: str,
        name: str,
        ports: Optional[Dict] = None,
        volumes: Optional[List] = None,
        environment: Optional[Dict] = None,
        restart_policy: str = 'unless-stopped',
        network_mode: str = 'bridge',
        detach: bool = True
    ) -> Dict:
        """
        Create and start a new container.
        
        Args:
            image: Docker image name
            name: Container name
            ports: Port mappings {'80/tcp': 8080}
            volumes: Volume bindings ['/host/path:/container/path']
            environment: Environment variables {'KEY': 'value'}
            restart_policy: Restart policy name
            network_mode: Network mode
            detach: Run in background
        
        Returns:
            dict: Container info or error
        """
        try:
            # Convert ports format
            port_bindings = {}
            exposed_ports = {}
            if ports:
                for container_port, host_port in ports.items():
                    exposed_ports[container_port] = {}
                    port_bindings[container_port] = [{'HostPort': str(host_port)}]
            
            # Create container
            container = self.client.containers.run(
                image=image,
                name=name,
                ports=ports,
                volumes=volumes,
                environment=environment,
                restart_policy={'Name': restart_policy},
                network_mode=network_mode,
                detach=detach
            )
            
            return {
                'success': True,
                'container_id': container.id,
                'name': container.name,
                'status': container.status
            }
            
        except APIError as e:
            return {
                'success': False,
                'error': f'Ошибка создания контейнера: {str(e)}'
            }
    
    def list_containers(self, all_containers: bool = True) -> List[Dict]:
        """
        List all containers.
        
        Args:
            all_containers: Include stopped containers
        
        Returns:
            list: Container information dicts
        """
        try:
            containers = self.client.containers.list(all=all_containers)
            result = []
            
            for c in containers:
                # Get port mappings
                ports = c.attrs.get('NetworkSettings', {}).get('Ports', {})
                port_list = []
                for port, bindings in (ports or {}).items():
                    if bindings:
                        for b in bindings:
                            port_list.append(f"{b.get('HostPort', '?')}:{port}")
                    else:
                        port_list.append(port)
                
                result.append({
                    'id': c.id,
                    'short_id': c.short_id,
                    'name': c.name,
                    'image': c.image.tags[0] if c.image.tags else 'unknown',
                    'status': c.status,
                    'state': c.attrs.get('State', {}).get('Status', 'unknown'),
                    'ports': port_list,
                    'created': c.attrs.get('Created', '')
                })
            
            return result
            
        except DockerException:
            return []
    
    def get_container(self, container_id: str) -> Optional[Dict]:
        """Get container details."""
        try:
            c = self.client.containers.get(container_id)
            return {
                'id': c.id,
                'name': c.name,
                'image': c.image.tags[0] if c.image.tags else 'unknown',
                'status': c.status,
                'attrs': c.attrs
            }
        except NotFound:
            return None
    
    def start_container(self, container_id: str) -> Dict:
        """Start a container."""
        try:
            container = self.client.containers.get(container_id)
            container.start()
            return {'success': True, 'message': 'Контейнер запущен'}
        except NotFound:
            return {'success': False, 'error': 'Контейнер не найден'}
        except APIError as e:
            return {'success': False, 'error': str(e)}
    
    def stop_container(self, container_id: str, timeout: int = 10) -> Dict:
        """Stop a container."""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            return {'success': True, 'message': 'Контейнер остановлен'}
        except NotFound:
            return {'success': False, 'error': 'Контейнер не найден'}
        except APIError as e:
            return {'success': False, 'error': str(e)}
    
    def restart_container(self, container_id: str, timeout: int = 10) -> Dict:
        """Restart a container."""
        try:
            container = self.client.containers.get(container_id)
            container.restart(timeout=timeout)
            return {'success': True, 'message': 'Контейнер перезапущен'}
        except NotFound:
            return {'success': False, 'error': 'Контейнер не найден'}
        except APIError as e:
            return {'success': False, 'error': str(e)}
    
    def remove_container(self, container_id: str, force: bool = False, v: bool = False) -> Dict:
        """Remove a container."""
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force, v=v)
            return {'success': True, 'message': 'Контейнер удален'}
        except NotFound:
            return {'success': False, 'error': 'Контейнер не найден'}
        except APIError as e:
            return {'success': False, 'error': str(e)}
    
    def get_container_logs(
        self, 
        container_id: str, 
        tail: int = 100,
        stream: bool = False,
        timestamps: bool = True
    ) -> Generator[str, None, None]:
        """
        Get container logs.
        
        Args:
            container_id: Container ID
            tail: Number of lines to return
            stream: Stream logs in real-time
            timestamps: Include timestamps
        
        Yields:
            str: Log lines
        """
        try:
            container = self.client.containers.get(container_id)
            
            if stream:
                for line in container.logs(
                    stream=True, 
                    tail=tail, 
                    timestamps=timestamps,
                    follow=True
                ):
                    yield line.decode('utf-8', errors='replace')
            else:
                logs = container.logs(tail=tail, timestamps=timestamps)
                yield logs.decode('utf-8', errors='replace')
                
        except NotFound:
            yield "Контейнер не найден"
        except APIError as e:
            yield f"Ошибка: {str(e)}"
    
    def exec_command(self, container_id: str, command: str) -> Dict:
        """
        Execute a command in a container.
        
        Args:
            container_id: Container ID
            command: Command to execute
        
        Returns:
            dict: Command output and exit code
        """
        try:
            container = self.client.containers.get(container_id)
            exit_code, output = container.exec_run(command)
            
            return {
                'success': exit_code == 0,
                'exit_code': exit_code,
                'output': output.decode('utf-8', errors='replace')
            }
            
        except NotFound:
            return {'success': False, 'error': 'Контейнер не найден'}
        except APIError as e:
            return {'success': False, 'error': str(e)}
    
    def get_container_stats(self, container_id: str) -> Dict:
        """Get container resource usage stats."""
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Calculate CPU usage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            
            cpu_percent = 0.0
            if system_delta > 0:
                cpu_count = stats['cpu_stats'].get('online_cpus', 1)
                cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0
            
            # Calculate memory usage
            mem_usage = stats['memory_stats'].get('usage', 0)
            mem_limit = stats['memory_stats'].get('limit', 1)
            mem_percent = (mem_usage / mem_limit) * 100.0
            
            return {
                'cpu_percent': round(cpu_percent, 2),
                'memory_usage': mem_usage,
                'memory_limit': mem_limit,
                'memory_percent': round(mem_percent, 2),
                'network_rx': stats.get('networks', {}).get('eth0', {}).get('rx_bytes', 0),
                'network_tx': stats.get('networks', {}).get('eth0', {}).get('tx_bytes', 0)
            }
            
        except (NotFound, KeyError):
            return {}


# Singleton instance
docker_service = DockerService()
