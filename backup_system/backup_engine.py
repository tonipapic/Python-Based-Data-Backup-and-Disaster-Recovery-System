"""
Jezgra sustava za backup
Implementira sve tri strategije: Full, Incremental, Differential
"""

import os
import shutil
import json
from datetime import datetime, timedelta
from typing import Dict, Tuple
import time

from shutil import rmtree


class BackupEngine:
    def __init__(self, backup_root: str, logger=None, integrity_checker=None):
        self.backup_root = backup_root
        self.logger = logger
        self.integrity_checker = integrity_checker
        self.metadata_dir = os.path.join(backup_root, '.metadata')
        self.backup_history_file = os.path.join(self.metadata_dir, 'backup_history.json')
        
        os.makedirs(self.metadata_dir, exist_ok=True)
        os.makedirs(os.path.join(backup_root, 'full'), exist_ok=True)
        os.makedirs(os.path.join(backup_root, 'incremental'), exist_ok=True)
        os.makedirs(os.path.join(backup_root, 'differential'), exist_ok=True)
        
        self.backup_history = self._load_history()
    
    def _load_history(self) -> Dict:
        if os.path.exists(self.backup_history_file):
            with open(self.backup_history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # osiguraj da svi timestampi budu datetime
                for b in data.get('backups', []):
                    if isinstance(b.get('timestamp'), str):
                        try:
                            b['timestamp'] = datetime.fromisoformat(b['timestamp'])
                        except Exception:
                            b['timestamp'] = datetime.now()
                return data
        return {'backups': []}
    
    def _save_history(self):
        # osiguraj da folder postoji
        os.makedirs(self.metadata_dir, exist_ok=True)

        # prije spremanja, pretvori datetime u string
        save_data = {'backups': []}
        for b in self.backup_history.get('backups', []):
            b_copy = b.copy()
            if isinstance(b_copy.get('timestamp'), datetime):
                b_copy['timestamp'] = b_copy['timestamp'].isoformat()
            save_data['backups'].append(b_copy)

        with open(self.backup_history_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2)
    
    def _get_file_list(self, directory: str) -> Dict[str, Dict]:
        file_list = {}
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, directory)
                    file_list[relative_path] = {
                        'modified': os.path.getmtime(file_path),
                        'size': os.path.getsize(file_path)
                    }
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Greska pri citanju datoteka: {e}")
        return file_list
    
    # --- FULL BACKUP ---
    def full_backup(self, source_dir: str, backup_id: str = None) -> Tuple[bool, Dict]:
        if backup_id is None:
            backup_id = f"full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_dir = os.path.join(self.backup_root, 'full', backup_id)
        metadata = {
            'id': backup_id,
            'type': 'full',
            'timestamp': datetime.now(),
            'source': source_dir,
            'status': 'in_progress'
        }
        
        try:
            start_time = time.time()
            if self.logger:
                self.logger.log_backup_start('FULL', source_dir, backup_dir)
            
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            
            shutil.copytree(source_dir, backup_dir)
            
            file_list = self._get_file_list(backup_dir)
            duration = time.time() - start_time
            
            metadata.update({
                'file_count': len(file_list),
                'size_bytes': sum(info['size'] for info in file_list.values()),
                'duration_seconds': duration,
                'status': 'completed',
                'files': file_list
            })
            
            if self.integrity_checker:
                manifest_path = os.path.join(backup_dir, 'MANIFEST.json')
                self.integrity_checker.create_backup_manifest(backup_dir, manifest_path)
            
            self.backup_history['backups'].append(metadata)
            self._save_history()
            
            if self.logger:
                self.logger.log_backup_complete(backup_id, metadata['file_count'], 
                                               metadata['size_bytes'], duration)
            
            return True, metadata
        except Exception as e:
            metadata['status'] = 'failed'
            metadata['error'] = str(e)
            self.backup_history['backups'].append(metadata)
            self._save_history()
            if self.logger:
                self.logger.log_backup_error(backup_id, str(e))
            return False, metadata
    
    # --- INCREMENTAL BACKUP ---
    def incremental_backup(self, source_dir: str, backup_id: str = None) -> Tuple[bool, Dict]:
        if backup_id is None:
            backup_id = f"incremental_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = os.path.join(self.backup_root, 'incremental', backup_id)
        metadata = {'id': backup_id, 'type': 'incremental', 'timestamp': datetime.now(),
                    'source': source_dir, 'status': 'in_progress'}
        
        try:
            start_time = time.time()
            if self.logger:
                self.logger.log_backup_start('INCREMENTAL', source_dir, backup_dir)
            
            last_backup_time = self._get_last_backup_time()
            
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            os.makedirs(backup_dir)
            
            file_list = {}
            copied_count = 0
            
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, source_dir)
                    if os.path.getmtime(file_path) > last_backup_time:
                        target_path = os.path.join(backup_dir, relative_path)
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        shutil.copy2(file_path, target_path)
                        copied_count += 1
                        file_list[relative_path] = {
                            'modified': os.path.getmtime(file_path),
                            'size': os.path.getsize(file_path)
                        }
            
            duration = time.time() - start_time
            metadata.update({
                'file_count': copied_count,
                'size_bytes': sum(info['size'] for info in file_list.values()),
                'duration_seconds': duration,
                'status': 'completed',
                'files': file_list
            })
            
            if self.integrity_checker:
                manifest_path = os.path.join(backup_dir, 'MANIFEST.json')
                self.integrity_checker.create_backup_manifest(backup_dir, manifest_path)
            
            self.backup_history['backups'].append(metadata)
            self._save_history()
            if self.logger:
                self.logger.log_backup_complete(backup_id, metadata['file_count'], 
                                               metadata['size_bytes'], duration)
            return True, metadata
        except Exception as e:
            metadata['status'] = 'failed'
            metadata['error'] = str(e)
            self.backup_history['backups'].append(metadata)
            self._save_history()
            if self.logger:
                self.logger.log_backup_error(backup_id, str(e))
            return False, metadata
    
    # --- DIFFERENTIAL BACKUP ---
    def differential_backup(self, source_dir: str, backup_id: str = None) -> Tuple[bool, Dict]:
        if backup_id is None:
            backup_id = f"differential_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = os.path.join(self.backup_root, 'differential', backup_id)
        metadata = {'id': backup_id, 'type': 'differential', 'timestamp': datetime.now(),
                    'source': source_dir, 'status': 'in_progress'}
        
        try:
            start_time = time.time()
            if self.logger:
                self.logger.log_backup_start('DIFFERENTIAL', source_dir, backup_dir)
            
            last_full_time = self._get_last_full_backup_time()
            
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            os.makedirs(backup_dir)
            
            file_list = {}
            copied_count = 0
            
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, source_dir)
                    if os.path.getmtime(file_path) > last_full_time:
                        target_path = os.path.join(backup_dir, relative_path)
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        shutil.copy2(file_path, target_path)
                        copied_count += 1
                        file_list[relative_path] = {
                            'modified': os.path.getmtime(file_path),
                            'size': os.path.getsize(file_path)
                        }
            
            duration = time.time() - start_time
            metadata.update({
                'file_count': copied_count,
                'size_bytes': sum(info['size'] for info in file_list.values()),
                'duration_seconds': duration,
                'status': 'completed',
                'files': file_list
            })
            
            if self.integrity_checker:
                manifest_path = os.path.join(backup_dir, 'MANIFEST.json')
                self.integrity_checker.create_backup_manifest(backup_dir, manifest_path)
            
            self.backup_history['backups'].append(metadata)
            self._save_history()
            if self.logger:
                self.logger.log_backup_complete(backup_id, metadata['file_count'], 
                                               metadata['size_bytes'], duration)
            return True, metadata
        except Exception as e:
            metadata['status'] = 'failed'
            metadata['error'] = str(e)
            self.backup_history['backups'].append(metadata)
            self._save_history()
            if self.logger:
                self.logger.log_backup_error(backup_id, str(e))
            return False, metadata
    
    # --- POMOĆNE FUNKCIJE ---
    def _get_last_backup_time(self) -> float:
        for backup in reversed(self.backup_history.get('backups', [])):
            if backup.get('status') == 'completed':
                ts = backup['timestamp']
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                return ts.timestamp()
        return (datetime.now() - timedelta(days=365)).timestamp()
    
    def _get_last_full_backup_time(self) -> float:
        for backup in reversed(self.backup_history.get('backups', [])):
            if backup.get('type') == 'full' and backup.get('status') == 'completed':
                ts = backup['timestamp']
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                return ts.timestamp()
        return (datetime.now() - timedelta(days=365)).timestamp()
    
    def get_backup_summary(self) -> Dict:
        """Vrati sažetak svih backup-a"""
        summary = {
            'total_backups': 0,
            'total_size_bytes': 0,
            'backups': []
        }
        
        for backup in self.backup_history.get('backups', []):
            ts = backup['timestamp']
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
                backup['timestamp'] = ts
            
            summary['backups'].append({
                'id': backup['id'],
                'type': backup['type'],
                'files': backup.get('file_count', 0),
                'size_mb': backup.get('size_bytes', 0) / (1024*1024),
                'status': backup.get('status', 'unknown'),
                'timestamp': ts
            })
            summary['total_backups'] += 1
            summary['total_size_bytes'] += backup.get('size_bytes', 0)
        
        # sortiranje po timestamp, newest first
        summary['backups'].sort(key=lambda b: b['timestamp'], reverse=True)
        return summary

    # --- DELETE ALL BACKUPS ---
    def delete_all_backups(self) -> Tuple[bool, str]:
        """Obriši sve backup-e i metadata odmah"""
        try:
            # Briše foldere backupa
            for backup_type in ['full', 'incremental', 'differential']:
                type_dir = os.path.join(self.backup_root, backup_type)
                if os.path.exists(type_dir):
                    rmtree(type_dir)
                    if self.logger:
                        self.logger.logger.info(f"Deleted backup folder: {type_dir}")

            # Provjeri .metadata folder i backup_history.json
            if os.path.exists(self.metadata_dir):
                rmtree(self.metadata_dir)
                if self.logger:
                    self.logger.logger.info(f"Deleted metadata directory: {self.metadata_dir}")

            # Ponovo kreiraj prazne foldere da sustav ne puca
            os.makedirs(self.metadata_dir, exist_ok=True)
            os.makedirs(os.path.join(self.backup_root, 'full'), exist_ok=True)
            os.makedirs(os.path.join(self.backup_root, 'incremental'), exist_ok=True)
            os.makedirs(os.path.join(self.backup_root, 'differential'), exist_ok=True)

            self.backup_history = {'backups': []}

            return True, "Svi backup-i i metadata su obrisani"
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Greška pri brisanju backup-a: {e}")
            return False, str(e)
