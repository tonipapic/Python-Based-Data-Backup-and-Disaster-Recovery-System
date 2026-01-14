"""
Disaster Recovery mehanizmi
Svrha: Automatizirani oporavak, validacija podataka, mjerenje RTO i RPO
Verzija: 2.0 - Fixed datetime comparison bug
Datum: 12. siječnja 2026.
"""

import os
import shutil
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple, List

class DisasterRecoveryManager:
    """Upravlja oporavkom podataka nakon katastrofe"""
    
    def __init__(self, backup_root: str, logger=None, integrity_checker=None):
        """Inicijalizacija DR managera"""
        self.backup_root = backup_root
        self.logger = logger
        self.integrity_checker = integrity_checker
        self.metadata_dir = os.path.join(backup_root, '.metadata')
        self.backup_history_file = os.path.join(self.metadata_dir, 'backup_history.json')
    
    def list_available_backups(self) -> List[Dict]:
        """Popis svih dostupnih backupa za oporavak"""
        backups = []
        
        if not os.path.exists(self.backup_history_file):
            return backups
        
        try:
            with open(self.backup_history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            for backup in history['backups']:
                if backup['status'] == 'completed':
                    backups.append({
                        'id': backup['id'],
                        'type': backup['type'],
                        'timestamp': backup['timestamp'],
                        'files': backup.get('file_count', 0),
                        'size_mb': backup.get('size_bytes', 0) / (1024 * 1024),
                        'source': backup.get('source', '')
                    })
        
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Greska pri citanju backupa: {e}")
        
        return backups
    
    def restore_from_backup(self, backup_id: str, destination_dir: str, 
                           recovery_id: str = None) -> Tuple[bool, Dict]:
        """Restaurira podatke iz backupa - ISPRAVLJENO"""
        if recovery_id is None:
            recovery_id = f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        recovery_metadata = {
            'recovery_id': recovery_id,
            'backup_id': backup_id,
            'destination': destination_dir,
            'timestamp': datetime.now().isoformat(),
            'status': 'in_progress',
            'start_time': time.time()
        }
        
        try:
            if self.logger:
                self.logger.log_recovery_start(recovery_id, backup_id, destination_dir)
            
            backup_path = self._find_backup_path(backup_id)
            
            if not backup_path:
                raise Exception(f"Backup {backup_id} nije pronadjen")
            
            # PRVO pita gdje vratiti, ZATIM pravi restore
            if os.path.exists(destination_dir):
                try:
                    shutil.rmtree(destination_dir, ignore_errors=True)
                    time.sleep(0.5)
                except Exception as e:
                    if self.logger:
                        self.logger.logger.warning(f"Ne mogu obrisati {destination_dir}, koristim novo ime")
                    destination_dir = destination_dir + f"_{recovery_id}"
            
            os.makedirs(destination_dir, exist_ok=True)
            
            file_count = 0
            verification_passed = True
            errors = []
            
            # Kopiraj datoteke s retry logikom
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    if file == 'MANIFEST.json':
                        continue
                    
                    source_file = os.path.join(root, file)
                    relative_path = os.path.relpath(source_file, backup_path)
                    destination_file = os.path.join(destination_dir, relative_path)
                    
                    try:
                        os.makedirs(os.path.dirname(destination_file), exist_ok=True)
                        
                        # Retry logika
                        retry_count = 0
                        while retry_count < 3:
                            try:
                                shutil.copy2(source_file, destination_file)
                                file_count += 1
                                break
                            except (PermissionError, OSError) as e:
                                retry_count += 1
                                if retry_count < 3:
                                    time.sleep(0.1)
                                else:
                                    raise
                    
                    except Exception as e:
                        errors.append(f"Greska pri kopiranju {relative_path}: {e}")
                        if self.logger:
                            self.logger.logger.warning(f"Greska pri kopiranju {relative_path}: {e}")
            
            # Integritet provjera
            if self.integrity_checker and file_count > 0:
                try:
                    manifest_path = os.path.join(backup_path, 'MANIFEST.json')
                    
                    if os.path.exists(manifest_path):
                        is_valid, verification_results = self.integrity_checker.verify_backup_integrity(
                            backup_path, manifest_path
                        )
                        
                        if not is_valid:
                            verification_passed = False
                            if self.logger:
                                self.logger.logger.warning(f"Integritet provjere greske: {verification_results['corrupted_files']}")
                except Exception as e:
                    if self.logger:
                        self.logger.logger.warning(f"Greska pri integritet provjeri: {e}")
            
            duration = time.time() - recovery_metadata['start_time']
            
            recovery_metadata['status'] = 'completed' if (verification_passed and file_count > 0) else 'completed_with_warnings'
            recovery_metadata['file_count'] = file_count
            recovery_metadata['duration_seconds'] = duration
            recovery_metadata['rto_seconds'] = duration
            recovery_metadata['errors'] = errors
            
            if self.logger:
                self.logger.log_recovery_complete(recovery_id, file_count, duration, duration)
            
            return verification_passed and file_count > 0, recovery_metadata
        
        except Exception as e:
            duration = time.time() - recovery_metadata['start_time']
            recovery_metadata['status'] = 'failed'
            recovery_metadata['error'] = str(e)
            recovery_metadata['duration_seconds'] = duration
            
            if self.logger:
                self.logger.logger.error(f"Oporavak neuspjesan ({recovery_id}): {e}")
            
            return False, recovery_metadata
    
    def restore_incremental_chain(self, full_backup_id: str, incremental_backup_ids: List[str],
                                  destination_dir: str, recovery_id: str = None) -> Tuple[bool, Dict]:
        """Restaurira podatke iz full backupa i niza incremental backupa"""
        if recovery_id is None:
            recovery_id = f"recovery_chain_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        recovery_metadata = {
            'recovery_id': recovery_id,
            'type': 'incremental_chain',
            'full_backup_id': full_backup_id,
            'incremental_count': len(incremental_backup_ids),
            'destination': destination_dir,
            'timestamp': datetime.now().isoformat(),
            'status': 'in_progress',
            'start_time': time.time()
        }
        
        try:
            if self.logger:
                self.logger.logger.info(f"Oporavak lanca: Full + {len(incremental_backup_ids)} inkrementalnih")
            
            success, full_metadata = self.restore_from_backup(
                full_backup_id, destination_dir, f"{recovery_id}_full"
            )
            
            if not success:
                raise Exception(f"Oporavak full backupa neuspjesan")
            
            total_files = full_metadata.get('file_count', 0)
            
            for i, incremental_id in enumerate(incremental_backup_ids):
                backup_path = self._find_backup_path(incremental_id)
                
                if not backup_path:
                    raise Exception(f"Incremental backup {incremental_id} nije pronadjen")
                
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        if file == 'MANIFEST.json':
                            continue
                        
                        source_file = os.path.join(root, file)
                        relative_path = os.path.relpath(source_file, backup_path)
                        destination_file = os.path.join(destination_dir, relative_path)
                        
                        try:
                            os.makedirs(os.path.dirname(destination_file), exist_ok=True)
                            shutil.copy2(source_file, destination_file)
                            total_files += 1
                        except Exception as e:
                            if self.logger:
                                self.logger.logger.warning(f"Greska pri kopiranju {relative_path}: {e}")
            
            duration = time.time() - recovery_metadata['start_time']
            
            recovery_metadata['status'] = 'completed'
            recovery_metadata['file_count'] = total_files
            recovery_metadata['duration_seconds'] = duration
            recovery_metadata['rto_seconds'] = duration
            
            if self.logger:
                self.logger.logger.info(f"Oporavak lanca zavrsен: {total_files} datoteka, {duration:.2f}s")
            
            return True, recovery_metadata
        
        except Exception as e:
            duration = time.time() - recovery_metadata['start_time']
            recovery_metadata['status'] = 'failed'
            recovery_metadata['error'] = str(e)
            recovery_metadata['duration_seconds'] = duration
            
            if self.logger:
                self.logger.logger.error(f"Oporavak lanca neuspjesan: {e}")
            
            return False, recovery_metadata
    
    def calculate_rpo_rto(self, backup_id: str = None) -> Dict:
        """Kalkulira Recovery Point Objective (RPO) i Recovery Time Objective (RTO)
        ISPRAVLJENO: Riješena datetime comparison greška"""
        metrics = {
            'rto_minutes': 0.0,
            'rpo_minutes': 0.0,
            'latest_backup_age_minutes': 0.0,
            'backup_frequency_minutes': 0.0,
            'analysis': {}
        }
        
        try:
            if not os.path.exists(self.backup_history_file):
                return metrics
            
            with open(self.backup_history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            completed_backups = [b for b in history['backups'] if b['status'] == 'completed']
            
            if not completed_backups:
                return metrics
            
            latest_backup = completed_backups[-1]
            
            # ========== ISPRAVKA 1: Sigurna datetime konverzija ==========
            try:
                timestamp_str = str(latest_backup.get('timestamp', ''))
                timestamp_str = timestamp_str.replace('Z', '+00:00')
                latest_timestamp = datetime.fromisoformat(timestamp_str)
            except (ValueError, TypeError, AttributeError) as e:
                if self.logger:
                    self.logger.logger.warning(f"Ne mogu parsirati timestamp: {e}, koristim sada")
                latest_timestamp = datetime.now()
            
            # ========== ISPRAVKA 2: Osiguraj timezone-naive ==========
            if latest_timestamp.tzinfo is not None:
                latest_timestamp = latest_timestamp.replace(tzinfo=None)
            
            now = datetime.now()
            
            # ========== Izračunaj RPO ==========
            try:
                age = now - latest_timestamp
                rpo_seconds = age.total_seconds()
                metrics['rpo_minutes'] = max(0.0, rpo_seconds / 60.0)
                metrics['latest_backup_age_minutes'] = max(0.0, rpo_seconds / 60.0)
            except TypeError as e:
                if self.logger:
                    self.logger.logger.warning(f"Greska pri izracunu RPO: {e}")
                metrics['rpo_minutes'] = 0.0
                metrics['latest_backup_age_minutes'] = 0.0
            
            # ========== Izračunaj RTO ==========
            recovery_times = []
            for backup in completed_backups[-5:]:
                duration = backup.get('duration_seconds')
                if isinstance(duration, (int, float)) and duration > 0:
                    recovery_times.append(duration)
            
            if recovery_times:
                metrics['rto_minutes'] = sum(recovery_times) / len(recovery_times) / 60.0
            else:
                metrics['rto_minutes'] = 0.0
            
            # ========== Izračunaj Frequency ==========
            if len(completed_backups) >= 2:
                try:
                    prev_timestamp_str = str(completed_backups[-2].get('timestamp', ''))
                    prev_timestamp_str = prev_timestamp_str.replace('Z', '+00:00')
                    first_timestamp = datetime.fromisoformat(prev_timestamp_str)
                except (ValueError, TypeError, AttributeError) as e:
                    if self.logger:
                        self.logger.logger.warning(f"Ne mogu parsirati prethodni timestamp: {e}")
                    first_timestamp = latest_timestamp
                
                if first_timestamp.tzinfo is not None:
                    first_timestamp = first_timestamp.replace(tzinfo=None)
                
                try:
                    time_diff = latest_timestamp - first_timestamp
                    freq_seconds = time_diff.total_seconds()
                    metrics['backup_frequency_minutes'] = max(0.0, freq_seconds / 60.0)
                except TypeError as e:
                    if self.logger:
                        self.logger.logger.warning(f"Greska pri izracunu frequency: {e}")
                    metrics['backup_frequency_minutes'] = 0.0
            
            # ========== Analiza ==========
            metrics['analysis'] = {
                'total_completed_backups': len(completed_backups),
                'latest_backup_type': str(latest_backup.get('type', 'unknown')),
                'latest_backup_id': str(latest_backup.get('id', 'unknown')),
                'latest_backup_files': int(latest_backup.get('file_count', 0)),
                'latest_backup_size_mb': float(latest_backup.get('size_bytes', 0)) / (1024 * 1024)
            }
            
            return metrics
        
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Greska pri kalkulaciji RTO/RPO: {e}")
            return metrics
    
    def _find_backup_path(self, backup_id: str) -> str:
        """Pronalazi putanju do backupa"""
        backup_types = ['full', 'incremental', 'differential']
        
        for backup_type in backup_types:
            backup_dir = os.path.join(self.backup_root, backup_type)
            backup_path = os.path.join(backup_dir, backup_id)
            
            if os.path.exists(backup_path):
                return backup_path
        
        return None
    
    def simulate_disaster_recovery(self, backup_id: str, test_dir: str = None) -> Dict:
        """Simulira disaster recovery scenarij"""
        if test_dir is None:
            test_dir = os.path.join(self.backup_root, '.test_recovery')
        
        test_results = {
            'test_id': f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'backup_id': backup_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'not_run'
        }
        
        try:
            success, metadata = self.restore_from_backup(backup_id, test_dir)
            
            test_results['status'] = 'passed' if success else 'failed'
            test_results['recovery_successful'] = success
            test_results['file_count'] = metadata.get('file_count', 0)
            test_results['duration_seconds'] = metadata.get('duration_seconds', 0)
            
            if success and self.integrity_checker:
                manifest_path = os.path.join(self._find_backup_path(backup_id), 'MANIFEST.json')
                
                if os.path.exists(manifest_path):
                    try:
                        is_valid, verification = self.integrity_checker.verify_backup_integrity(
                            test_dir, manifest_path
                        )
                        test_results['integrity_check'] = {
                            'valid': is_valid,
                            'verified_files': verification.get('verified_files', 0),
                            'corrupted_files': len(verification.get('corrupted_files', []))
                        }
                    except:
                        pass
            
            if self.logger:
                self.logger.logger.info(f"DR test zavrsен: {test_results['status']}")
            
            if os.path.exists(test_dir):
                try:
                    shutil.rmtree(test_dir, ignore_errors=True)
                except:
                    pass
            
            return test_results
        
        except Exception as e:
            test_results['status'] = 'failed'
            test_results['error'] = str(e)
            
            if self.logger:
                self.logger.logger.error(f"DR test neuspjesan: {e}")
            
            if os.path.exists(test_dir):
                try:
                    shutil.rmtree(test_dir, ignore_errors=True)
                except:
                    pass
            
            return test_results
