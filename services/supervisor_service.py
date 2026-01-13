"""
Supervisor Service
==================
Supervisor process management service.
"""

import subprocess
import re
from typing import Dict, List, Optional


class SupervisorService:
    """
    Service for managing Supervisor processes.
    """
    
    def __init__(self):
        self._supervisorctl = 'supervisorctl'
    
    def _run_command(self, args: List[str], timeout: int = 10) -> Dict:
        """Run supervisorctl command."""
        try:
            result = subprocess.run(
                [self._supervisorctl] + args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Taym-aut'}
        except FileNotFoundError:
            return {'success': False, 'error': 'Supervisor o\'rnatilmagan'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def is_installed(self) -> bool:
        """Check if supervisor is installed."""
        try:
            result = subprocess.run(
                ['which', 'supervisorctl'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_status(self) -> Dict:
        """Get supervisor daemon status."""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'supervisor'],
                capture_output=True,
                text=True,
                timeout=5
            )
            status = result.stdout.strip()
            return {
                'installed': self.is_installed(),
                'running': status == 'active',
                'status': status
            }
        except Exception as e:
            return {
                'installed': False,
                'running': False,
                'status': 'unknown',
                'error': str(e)
            }
    
    def list_processes(self) -> List[Dict]:
        """List all supervised processes."""
        result = self._run_command(['status'])
        
        if not result.get('success') and result.get('error'):
            return []
        
        processes = []
        lines = result.get('stdout', '').strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            # Parse: name RUNNING pid 12345, uptime 0:05:32
            # or: name STOPPED Jul 13 12:00 PM
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                state = parts[1]
                
                process = {
                    'name': name,
                    'state': state,
                    'running': state == 'RUNNING',
                    'info': ' '.join(parts[2:]) if len(parts) > 2 else ''
                }
                
                # Extract PID if running
                if state == 'RUNNING' and 'pid' in line.lower():
                    pid_match = re.search(r'pid\s+(\d+)', line)
                    if pid_match:
                        process['pid'] = int(pid_match.group(1))
                
                # Extract uptime
                uptime_match = re.search(r'uptime\s+([\d:]+)', line)
                if uptime_match:
                    process['uptime'] = uptime_match.group(1)
                
                processes.append(process)
        
        return processes
    
    def start_process(self, name: str) -> Dict:
        """Start a process."""
        result = self._run_command(['start', name])
        if result.get('success'):
            return {'success': True, 'message': f'{name} ishga tushirildi'}
        return {'success': False, 'error': result.get('stderr') or result.get('error', 'Xatolik')}
    
    def stop_process(self, name: str) -> Dict:
        """Stop a process."""
        result = self._run_command(['stop', name])
        if result.get('success'):
            return {'success': True, 'message': f'{name} to\'xtatildi'}
        return {'success': False, 'error': result.get('stderr') or result.get('error', 'Xatolik')}
    
    def restart_process(self, name: str) -> Dict:
        """Restart a process."""
        result = self._run_command(['restart', name])
        if result.get('success'):
            return {'success': True, 'message': f'{name} qayta ishga tushirildi'}
        return {'success': False, 'error': result.get('stderr') or result.get('error', 'Xatolik')}
    
    def start_all(self) -> Dict:
        """Start all processes."""
        result = self._run_command(['start', 'all'])
        if result.get('success'):
            return {'success': True, 'message': 'Barcha jarayonlar ishga tushirildi'}
        return {'success': False, 'error': result.get('stderr') or result.get('error', 'Xatolik')}
    
    def stop_all(self) -> Dict:
        """Stop all processes."""
        result = self._run_command(['stop', 'all'])
        if result.get('success'):
            return {'success': True, 'message': 'Barcha jarayonlar to\'xtatildi'}
        return {'success': False, 'error': result.get('stderr') or result.get('error', 'Xatolik')}
    
    def reload_config(self) -> Dict:
        """Reload supervisor configuration."""
        result = self._run_command(['reread'])
        if result.get('success'):
            update_result = self._run_command(['update'])
            return {'success': True, 'message': 'Konfiguratsiya yangilandi'}
        return {'success': False, 'error': result.get('stderr') or result.get('error', 'Xatolik')}
    
    def get_process_logs(self, name: str, tail: int = 100) -> Dict:
        """Get process logs."""
        result = self._run_command(['tail', '-{}'.format(tail), name])
        if result.get('success'):
            return {'success': True, 'logs': result.get('stdout', '')}
        return {'success': False, 'error': result.get('stderr') or result.get('error', 'Xatolik')}
    
    def get_process_info(self, name: str) -> Optional[Dict]:
        """Get detailed info about a process."""
        processes = self.list_processes()
        for p in processes:
            if p['name'] == name:
                return p
        return None


# Singleton instance
supervisor_service = SupervisorService()
