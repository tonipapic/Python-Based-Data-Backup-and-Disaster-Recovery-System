"""
Upravljanje verzijama i retention politikom
"""

import os
import shutil
import json
from datetime import datetime, timedelta
from typing import Dict, List

class VersionManager:
    """Upravlja verzijama backup-a i primjenom retention politike"""
    
    def __init__(self, backup_root: str, retention_policy: Dict = None, logger=None):
        self.backup_root = backup_root
        self.logger = logger
        self.retention_policy = retention_policy or {
            'full_backup_days': 7,
            'incremental_backup_days': 1,
            'differential_backup_days': 3,
            'monthly_retention_months': 12
        }
    
    def apply_retention_policy(self) -> Dict:
        """Primijeni retention politiku i obriši stare backupe"""
        results = {
            'full_backups_deleted': 0,
            'incremental_backups_deleted': 0,
            'differential_backups_deleted': 0,
            'total_space_freed_bytes': 0
        }
        
        cutoff_dates = {
            'full': datetime.now() - timedelta(days=self.retention_policy['full_backup_days']),
            'incremental': datetime.now() - timedelta(days=self.retention_policy['incremental_backup_days']),
            'differential': datetime.now() - timedelta(days=self.retention_policy['differential_backup_days'])
        }
        
        for backup_type in ['full', 'incremental', 'differential']:
            type_dir = os.path.join(self.backup_root, backup_type)
            
            if not os.path.exists(type_dir):
                continue
            
            for backup_id in os.listdir(type_dir):
                backup_path = os.path.join(type_dir, backup_id)
                
                if os.path.isdir(backup_path):
                    backup_time = datetime.fromtimestamp(os.path.getctime(backup_path))
                    
                    if backup_time < cutoff_dates[backup_type]:
                        try:
                            space_freed = self._get_directory_size(backup_path)
                            shutil.rmtree(backup_path)
                            
                            results[f'{backup_type}_backups_deleted'] += 1
                            results['total_space_freed_bytes'] += space_freed
                            
                            if self.logger:
                                self.logger.logger.info(f"Obrisan stari {backup_type} backup: {backup_id}")
                        except Exception as e:
                            if self.logger:
                                self.logger.logger.error(f"Greska pri brisanju {backup_id}: {e}")
        
        if self.logger:
            self.logger.log_version_cleanup(
                results['full_backups_deleted'] + results['incremental_backups_deleted'] + results['differential_backups_deleted'],
                results['total_space_freed_bytes']
            )
        
        return results
    
    def get_version_statistics(self) -> Dict:
        """Statistika verzija"""
        stats = {
            'total_backups': 0,
            'by_type': {'full': 0, 'incremental': 0, 'differential': 0},
            'total_size_bytes': 0,
            'oldest_backup': None,
            'newest_backup': None
        }
        
        for backup_type in ['full', 'incremental', 'differential']:
            type_dir = os.path.join(self.backup_root, backup_type)
            
            if not os.path.exists(type_dir):
                continue
            
            for backup_id in os.listdir(type_dir):
                backup_path = os.path.join(type_dir, backup_id)
                
                if os.path.isdir(backup_path):
                    size = self._get_directory_size(backup_path)
                    
                    stats['total_backups'] += 1
                    stats['by_type'][backup_type] += 1
                    stats['total_size_bytes'] += size
                    
                    backup_time = datetime.fromtimestamp(os.path.getctime(backup_path))
                    
                    if stats['oldest_backup'] is None or backup_time < stats['oldest_backup']:
                        stats['oldest_backup'] = backup_time.isoformat()
                    
                    if stats['newest_backup'] is None or backup_time > stats['newest_backup']:
                        stats['newest_backup'] = backup_time.isoformat()
        
        return stats
    
    def _get_directory_size(self, directory: str) -> int:
        """Izračunaj veličinu direktorija"""
        total_size = 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Greska pri izracunu veličine: {e}")
        
        return total_size
    
    def get_backup_chain(self, full_backup_id: str) -> List[Dict]:
        """Pronađi sve backupe koji su dio lanca"""
        chain = []
        
        try:
            full_backup_dir = os.path.join(self.backup_root, 'full', full_backup_id)
            full_time = os.path.getctime(full_backup_dir)
            
            chain.append({
                'id': full_backup_id,
                'type': 'full',
                'timestamp': datetime.fromtimestamp(full_time).isoformat()
            })
            
            for backup_type in ['incremental', 'differential']:
                type_dir = os.path.join(self.backup_root, backup_type)
                
                if not os.path.exists(type_dir):
                    continue
                
                for backup_id in sorted(os.listdir(type_dir)):
                    backup_path = os.path.join(type_dir, backup_id)
                    backup_time = os.path.getctime(backup_path)
                    
                    if backup_time > full_time:
                        chain.append({
                            'id': backup_id,
                            'type': backup_type,
                            'timestamp': datetime.fromtimestamp(backup_time).isoformat()
                        })
        
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Greska pri pronalaženju backup lanca: {e}")
        
        return chain
