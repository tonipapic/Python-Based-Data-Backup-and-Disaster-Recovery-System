"""
Provjera integriteta podataka
"""

import hashlib
import os
import json
from typing import Dict, Tuple
from datetime import datetime

class IntegrityChecker:
    ALGORITHMS = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha256': hashlib.sha256,
        'sha512': hashlib.sha512
    }
    
    def __init__(self, algorithm: str = 'sha256', logger=None):
        if algorithm not in self.ALGORITHMS:
            raise ValueError(f"Nepoznat algoritam: {algorithm}")
        
        self.algorithm = algorithm
        self.hash_func = self.ALGORITHMS[algorithm]
        self.logger = logger
    
    def calculate_file_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        hash_obj = self.hash_func()
        
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Greska pri izracunu hasha za {file_path}: {e}")
            raise
    
    def create_backup_manifest(self, backup_dir: str, manifest_path: str) -> Dict:
        manifest = {
            'algorithm': self.algorithm,
            'created': datetime.now().isoformat(),
            'files': {}
        }
        
        try:
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, backup_dir)
                    
                    file_hash = self.calculate_file_hash(file_path)
                    manifest['files'][relative_path] = {
                        'hash': file_hash,
                        'size': os.path.getsize(file_path),
                        'modified': os.path.getmtime(file_path)
                    }
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            
            if self.logger:
                self.logger.logger.info(f"Manifest kreiran: {len(manifest['files'])} datoteka")
            
            return manifest
        
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Greska pri kreiranju manifesta: {e}")
            raise
    
    def verify_backup_integrity(self, backup_dir: str, manifest_path: str) -> Tuple[bool, Dict]:
        results = {
            'valid': True,
            'total_files': 0,
            'verified_files': 0,
            'corrupted_files': [],
            'missing_files': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            results['total_files'] = len(manifest['files'])
            
            for file_path, file_info in manifest['files'].items():
                full_path = os.path.join(backup_dir, file_path)
                
                if not os.path.exists(full_path):
                    results['missing_files'].append(file_path)
                    results['valid'] = False
                    continue
                
                current_hash = self.calculate_file_hash(full_path)
                expected_hash = file_info['hash']
                
                if current_hash != expected_hash:
                    results['corrupted_files'].append({
                        'file': file_path,
                        'expected_hash': expected_hash[:16] + '...',
                        'actual_hash': current_hash[:16] + '...'
                    })
                    results['valid'] = False
                else:
                    results['verified_files'] += 1
            
            if self.logger:
                if results['valid']:
                    self.logger.logger.info(f"Integritet provjeren: {results['verified_files']}/{results['total_files']} datoteka je validno")
                else:
                    self.logger.logger.warning(f"Integritet provjeren: problemi pronajdeni!")
            
            return results['valid'], results
        
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Greska pri provjeri integriteta: {e}")
            results['valid'] = False
            return False, results
    
    def verify_file_during_restore(self, file_path: str, expected_hash: str) -> bool:
        try:
            actual_hash = self.calculate_file_hash(file_path)
            
            if actual_hash == expected_hash:
                if self.logger:
                    self.logger.log_integrity_check(file_path, actual_hash, 'OK')
                return True
            else:
                if self.logger:
                    self.logger.logger.warning(f"Hash mismatch za {file_path}")
                return False
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Greska pri provjeri datoteke: {e}")
            return False
    
    def calculate_directory_hash(self, directory: str) -> str:
        combined_hash = self.hash_func()
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in sorted(files):
                    file_path = os.path.join(root, file)
                    file_hash = self.calculate_file_hash(file_path)
                    combined_hash.update(file_hash.encode())
            
            return combined_hash.hexdigest()
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Greska pri izracunu direktorij hasha: {e}")
            raise
