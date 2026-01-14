"""
Cloud Sync - Automatski upload svih backup-a na S3
Šalje datoteke iz ./backups na AWS S3
"""

import os
import json
import boto3
from datetime import datetime
from pathlib import Path
from typing import Dict, List

class CloudSync:
    
    
    def __init__(self, config_file: str = 'advanced_config.json', logger=None):
        self.config_file = config_file
        self.config = self._load_config()
        self.logger = logger
        self.s3_client = None
        self.backup_root = './backups'
        
        self._init_s3_client()
    
    def _load_config(self) -> Dict:
        """Učitaj config"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Greška pri učitavanju config-a: {e}")
            return {}
    
    def _init_s3_client(self):
        """Inicijaliziraj S3 klijent"""
        aws_config = self.config.get('aws_s3', {})
        
        if not aws_config.get('enabled'):
            print("S3 nije omogućen u config-u!")
            return
        
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_config.get('access_key'),
                aws_secret_access_key=aws_config.get('secret_key'),
                region_name=aws_config.get('region', 'eu-central-1')
            )
            print("S3 klijent inicijaliziran")
        except Exception as e:
            print(f"Greška pri inicijalizaciji S3: {e}")
    
    def sync_all_backups(self) -> Dict:
        """Sinhronizira sve backup-e iz ./backups na S3"""
        if not self.s3_client:
            return {'success': False, 'error': 'S3 nije dostupan'}
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_files': 0,
            'total_size_bytes': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'uploaded_files': [],
            'failed_files': []
        }
        
        bucket = self.config['aws_s3']['bucket_name']
        
        print(f"\n{'='*80}")
        print(f"CLOUD SYNC - Sinhronizacija ./backups → {bucket}")
        print(f"{'='*80}\n")
        
        # Prođi kroz sve backup-e
        for backup_type in ['full', 'incremental', 'differential']:
            type_dir = os.path.join(self.backup_root, backup_type)
            
            if not os.path.exists(type_dir):
                continue
            
            print(f"Obrađujem {backup_type} backup-e...")
            
            for backup_id in os.listdir(type_dir):
                backup_path = os.path.join(type_dir, backup_id)
                
                if not os.path.isdir(backup_path):
                    continue
                
                # Upload datoteke iz backup-a
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        local_file = os.path.join(root, file)
                        
                        # Generiraj S3 key
                        relative_path = os.path.relpath(local_file, self.backup_root)
                        s3_key = f"backups/{relative_path}"
                        
                        file_size = os.path.getsize(local_file)
                        results['total_files'] += 1
                        results['total_size_bytes'] += file_size
                        
                        try:
                            # Upload na S3
                            self.s3_client.upload_file(
                                local_file,
                                bucket,
                                s3_key,
                                ExtraArgs={'StorageClass': 'GLACIER'}
                            )
                            
                            results['successful_uploads'] += 1
                            results['uploaded_files'].append({
                                'local_path': local_file,
                                's3_path': s3_key,
                                'size_bytes': file_size,
                                'timestamp': datetime.now().isoformat()
                            })
                            
                            size_mb = file_size / (1024*1024)
                            print(f"   {s3_key} ({size_mb:.2f} MB)")
                            
                            if self.logger:
                                self.logger.logger.info(f"S3 upload: {s3_key}")
                        
                        except Exception as e:
                            results['failed_uploads'] += 1
                            results['failed_files'].append({
                                'local_path': local_file,
                                'error': str(e)
                            })
                            
                            print(f"   {s3_key} - Greška: {e}")
                            
                            if self.logger:
                                self.logger.logger.error(f"S3 upload greška {s3_key}: {e}")
        
        # Summary
        print(f"\n{'='*80}")
        print(f"SAŽETAK:")
        print(f"{'='*80}")
        print(f" Uspješno uploadano: {results['successful_uploads']}")
        print(f" Neuspješno: {results['failed_uploads']}")
        print(f" Ukupno datoteka: {results['total_files']}")
        print(f" Ukupna veličina: {results['total_size_bytes'] / (1024*1024*1024):.2f} GB")
        print(f"{'='*80}\n")
        
        return results
    
    def sync_backup_type(self, backup_type: str) -> Dict:
        """Sinhronizira samo određeni tip backup-a"""
        if not self.s3_client:
            return {'success': False, 'error': 'S3 nije dostupan'}
        
        if backup_type not in ['full', 'incremental', 'differential']:
            return {'success': False, 'error': f'Nepoznat tip backup-a: {backup_type}'}
        
        results = {
            'backup_type': backup_type,
            'uploaded_count': 0,
            'failed_count': 0,
            'total_size_bytes': 0
        }
        
        bucket = self.config['aws_s3']['bucket_name']
        type_dir = os.path.join(self.backup_root, backup_type)
        
        if not os.path.exists(type_dir):
            return {'success': False, 'error': f'Direktorij ne postoji: {type_dir}'}
        
        print(f"\nSinhronizacija {backup_type} backup-a...\n")
        
        for backup_id in os.listdir(type_dir):
            backup_path = os.path.join(type_dir, backup_id)
            
            if not os.path.isdir(backup_path):
                continue
            
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    local_file = os.path.join(root, file)
                    relative_path = os.path.relpath(local_file, self.backup_root)
                    s3_key = f"backups/{relative_path}"
                    
                    try:
                        self.s3_client.upload_file(
                            local_file,
                            bucket,
                            s3_key,
                            ExtraArgs={'StorageClass': 'GLACIER'}
                        )
                        
                        results['uploaded_count'] += 1
                        results['total_size_bytes'] += os.path.getsize(local_file)
                        print(f" {s3_key}")
                    
                    except Exception as e:
                        results['failed_count'] += 1
                        print(f" {s3_key} - {e}")
        
        return results
    
    def sync_latest_backup(self) -> Dict:
        """Sinhronizira samo najnoviji backup"""
        if not self.s3_client:
            return {'success': False, 'error': 'S3 nije dostupan'}
        
        # Pronađi najnoviji backup
        latest_backup = None
        latest_time = 0
        
        for backup_type in ['full', 'incremental', 'differential']:
            type_dir = os.path.join(self.backup_root, backup_type)
            
            if not os.path.exists(type_dir):
                continue
            
            for backup_id in os.listdir(type_dir):
                backup_path = os.path.join(type_dir, backup_id)
                
                if os.path.isdir(backup_path):
                    backup_time = os.path.getctime(backup_path)
                    
                    if backup_time > latest_time:
                        latest_time = backup_time
                        latest_backup = (backup_type, backup_id, backup_path)
        
        if not latest_backup:
            return {'success': False, 'error': 'Nema backup-a za sinhronizaciju'}
        
        backup_type, backup_id, backup_path = latest_backup
        results = {
            'backup_id': backup_id,
            'backup_type': backup_type,
            'uploaded_count': 0,
            'failed_count': 0
        }
        
        bucket = self.config['aws_s3']['bucket_name']
        
        print(f"\nSinhronizacija najnovijeg backup-a: {backup_id}\n")
        
        for root, dirs, files in os.walk(backup_path):
            for file in files:
                local_file = os.path.join(root, file)
                relative_path = os.path.relpath(local_file, self.backup_root)
                s3_key = f"backups/{relative_path}"
                
                try:
                    self.s3_client.upload_file(
                        local_file,
                        bucket,
                        s3_key,
                        ExtraArgs={'StorageClass': 'GLACIER'}
                    )
                    
                    results['uploaded_count'] += 1
                    print(f" {s3_key}")
                
                except Exception as e:
                    results['failed_count'] += 1
                    print(f" {s3_key} - {e}")
        
        return results
    
    def get_s3_backup_list(self) -> List[Dict]:
        """Lista svih backup-a koji su na S3-u"""
        if not self.s3_client:
            return []
        
        backups = []
        bucket = self.config['aws_s3']['bucket_name']
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix='backups/')
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        backups.append({
                            'key': obj['Key'],
                            'size_bytes': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat(),
                            'storage_class': obj.get('StorageClass', 'STANDARD')
                        })
        
        except Exception as e:
            print(f"Greška pri čitanju S3 lista: {e}")
        
        return backups
    
    def download_from_s3(self, s3_key: str, local_path: str) -> bool:
        """Download datoteke sa S3-a"""
        if not self.s3_client:
            return False
        
        try:
            bucket = self.config['aws_s3']['bucket_name']
            
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.s3_client.download_file(bucket, s3_key, local_path)
            
            print(f" Download: {s3_key} → {local_path}")
            return True
        
        except Exception as e:
            print(f" Download greška: {e}")
            return False
    
    def cleanup_old_s3_backups(self, days: int = 90) -> Dict:
        """Briše stare backup-e sa S3-a"""
        if not self.s3_client:
            return {'success': False, 'error': 'S3 nije dostupan'}
        
        from datetime import datetime, timedelta
        
        results = {
            'deleted_count': 0,
            'total_size_freed_bytes': 0,
            'deleted_files': []
        }
        
        bucket = self.config['aws_s3']['bucket_name']
        cutoff_date = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=days)
        
        print(f"\nBrisanje backup-a starijih od {days} dana...\n")
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix='backups/')
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['LastModified'] < cutoff_date:
                            try:
                                self.s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
                                
                                results['deleted_count'] += 1
                                results['total_size_freed_bytes'] += obj['Size']
                                results['deleted_files'].append(obj['Key'])
                                
                                print(f" Obrisan: {obj['Key']}")
                            
                            except Exception as e:
                                print(f" Greška pri brisanju {obj['Key']}: {e}")
        
        except Exception as e:
            print(f"Greška pri čitanju S3: {e}")
        
        print(f"\nOslobodjeno prostora: {results['total_size_freed_bytes'] / (1024*1024*1024):.2f} GB")
        
        return results
        
   
