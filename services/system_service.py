"""
System Service
===============
System monitoring and information using psutil.
"""

import psutil
import platform
import os
from datetime import datetime, timedelta
from typing import Dict, List


class SystemService:
    """
    Service for system monitoring and resource usage tracking.
    """
    
    @staticmethod
    def get_cpu_info() -> Dict:
        """
        Get CPU information and usage.
        
        Returns:
            dict: CPU stats including usage percentage and core count
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_percent_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
            cpu_freq = psutil.cpu_freq()
            
            return {
                'percent': cpu_percent,
                'percent_per_core': cpu_percent_per_core,
                'cores_physical': psutil.cpu_count(logical=False),
                'cores_logical': psutil.cpu_count(logical=True),
                'frequency_current': cpu_freq.current if cpu_freq else 0,
                'frequency_max': cpu_freq.max if cpu_freq else 0,
                'load_average': list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            }
        except Exception as e:
            return {'error': str(e), 'percent': 0}
    
    @staticmethod
    def get_memory_info() -> Dict:
        """
        Get memory (RAM) information.
        
        Returns:
            dict: Memory stats including usage and available memory
        """
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'total': mem.total,
                'available': mem.available,
                'used': mem.used,
                'percent': mem.percent,
                'total_gb': round(mem.total / (1024**3), 2),
                'used_gb': round(mem.used / (1024**3), 2),
                'available_gb': round(mem.available / (1024**3), 2),
                'swap': {
                    'total': swap.total,
                    'used': swap.used,
                    'percent': swap.percent,
                    'total_gb': round(swap.total / (1024**3), 2),
                    'used_gb': round(swap.used / (1024**3), 2)
                }
            }
        except Exception as e:
            return {'error': str(e), 'percent': 0}
    
    @staticmethod
    def get_disk_info() -> List[Dict]:
        """
        Get disk usage information for all partitions.
        
        Returns:
            list: Disk usage stats for each partition
        """
        disks = []
        
        try:
            partitions = psutil.disk_partitions(all=False)
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent,
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round(usage.used / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2)
                    })
                except (PermissionError, OSError):
                    continue
            
            return disks
            
        except Exception as e:
            return [{'error': str(e)}]
    
    @staticmethod
    def get_network_info() -> Dict:
        """
        Get network I/O statistics.
        
        Returns:
            dict: Network stats including bytes sent/received
        """
        try:
            net_io = psutil.net_io_counters()
            
            # Get per-interface stats
            interfaces = {}
            for iface, stats in psutil.net_io_counters(pernic=True).items():
                interfaces[iface] = {
                    'bytes_sent': stats.bytes_sent,
                    'bytes_recv': stats.bytes_recv,
                    'packets_sent': stats.packets_sent,
                    'packets_recv': stats.packets_recv,
                    'sent_mb': round(stats.bytes_sent / (1024**2), 2),
                    'recv_mb': round(stats.bytes_recv / (1024**2), 2)
                }
            
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'sent_gb': round(net_io.bytes_sent / (1024**3), 2),
                'recv_gb': round(net_io.bytes_recv / (1024**3), 2),
                'interfaces': interfaces
            }
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def get_system_info() -> Dict:
        """
        Get general system information.
        
        Returns:
            dict: System info including OS, hostname, uptime
        """
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            return {
                'hostname': platform.node(),
                'os': platform.system(),
                'os_release': platform.release(),
                'os_version': platform.version(),
                'architecture': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'boot_time': boot_time.isoformat(),
                'uptime_seconds': int(uptime.total_seconds()),
                'uptime_human': str(timedelta(seconds=int(uptime.total_seconds())))
            }
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def get_processes(sort_by: str = 'cpu', limit: int = 10) -> List[Dict]:
        """
        Get top processes by resource usage.
        
        Args:
            sort_by: Sort key ('cpu', 'memory', 'name')
            limit: Number of processes to return
        
        Returns:
            list: Process information dicts
        """
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'username']):
                try:
                    pinfo = proc.info
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'cpu_percent': pinfo['cpu_percent'] or 0,
                        'memory_percent': round(pinfo['memory_percent'] or 0, 2),
                        'status': pinfo['status'],
                        'username': pinfo['username']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort processes
            if sort_by == 'cpu':
                processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            elif sort_by == 'memory':
                processes.sort(key=lambda x: x['memory_percent'], reverse=True)
            elif sort_by == 'name':
                processes.sort(key=lambda x: x['name'].lower())
            
            return processes[:limit]
            
        except Exception as e:
            return [{'error': str(e)}]
    
    @staticmethod
    def get_all_stats() -> Dict:
        """
        Get comprehensive system statistics.
        
        Returns:
            dict: All system stats combined
        """
        return {
            'cpu': SystemService.get_cpu_info(),
            'memory': SystemService.get_memory_info(),
            'disk': SystemService.get_disk_info(),
            'network': SystemService.get_network_info(),
            'system': SystemService.get_system_info(),
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def kill_process(pid: int) -> Dict:
        """
        Kill a process by PID.
        
        Args:
            pid: Process ID to kill
        
        Returns:
            dict: Result with success status
        """
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=5)
            return {'success': True, 'message': f'Процесс {pid} завершен'}
        except psutil.NoSuchProcess:
            return {'success': False, 'error': 'Процесс не найден'}
        except psutil.AccessDenied:
            return {'success': False, 'error': 'Доступ запрещен'}
        except psutil.TimeoutExpired:
            try:
                proc.kill()
                return {'success': True, 'message': f'Процесс {pid} принудительно завершен'}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Singleton instance
system_service = SystemService()
