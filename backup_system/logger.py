"""
Logger - KOMPLETNO ISPRAVLJENO
Problem: PermissionError pri kreiranju log datoteka
Rješenje: Osiguraj da direktorij postoji prije nego što kreiramo FileHandler
"""

import logging
import os
from datetime import datetime

class BackupLogger:
    """Logger za backup operacije"""
    
    def __init__(self, log_dir: str = './logs'):
        """Inicijalizacija loggera - ISPRAVLJENO"""
        self.log_dir = log_dir
        
        # ISPRAVKA 1: Kreiraj direktorij ako ne postoji
        try:
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir, exist_ok=True)
                print(f"✓ Created log directory: {self.log_dir}")
        except Exception as e:
            print(f"⚠ Warning: Could not create log directory: {e}")
            # Ako ne možemo kreirati, koristimo trenutni direktorij
            self.log_dir = '.'
        
        # Generiraj imena logova
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_log = os.path.join(self.log_dir, f'backup_{timestamp}.log')
        self.recovery_log = os.path.join(self.log_dir, f'recovery_{timestamp}.log')
        self.error_log = os.path.join(self.log_dir, f'error_{timestamp}.log')
        
        # Setup logger
        self.logger = logging.getLogger('BackupSystem')
        self.logger.setLevel(logging.DEBUG)
        
        # ISPRAVKA 2: Kreiraj handlers nakon što znamo da direktorij postoji
        try:
            # File handler
            fh = logging.FileHandler(self.backup_log, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            
            # Console handler
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            
            # Dodaj handlere
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)
            
            self.logger.info(f"Logger initialized: {self.backup_log}")
        
        except Exception as e:
            print(f"⚠ Warning: Could not initialize file logging: {e}")
            print(f"  Using console logging only")
            
            # Kreiraj samo console handler ako file logging ne radi
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)
    
    def log_backup_start(self, backup_id: str, backup_type: str, source_path: str):
        """Logiraj početak backupa"""
        msg = f"Backup started | ID: {backup_id} | Type: {backup_type} | Source: {source_path}"
        self.logger.info(msg)
    
    def log_backup_complete(self, backup_id: str, file_count: int, size_bytes: int, duration_seconds: float):
        """Logiraj završetak backupa"""
        size_mb = size_bytes / (1024 * 1024)
        msg = f"Backup completed | ID: {backup_id} | Files: {file_count} | Size: {size_mb:.2f} MB | Duration: {duration_seconds:.2f}s"
        self.logger.info(msg)
    
    def log_backup_error(self, backup_id: str, error_message: str):
        """Logiraj grešku pri backupu"""
        msg = f"Backup error | ID: {backup_id} | Error: {error_message}"
        self.logger.error(msg)
    
    def log_recovery_start(self, recovery_id: str, backup_id: str, destination: str):
        """Logiraj početak oporavka"""
        msg = f"Recovery started | Recovery ID: {recovery_id} | Backup ID: {backup_id} | Destination: {destination}"
        self.logger.info(msg)
    
    def log_recovery_complete(self, recovery_id: str, file_count: int, duration_seconds: float, rto_seconds: float):
        """Logiraj završetak oporavka"""
        msg = f"Recovery completed | ID: {recovery_id} | Files: {file_count} | Duration: {duration_seconds:.2f}s | RTO: {rto_seconds:.2f}s"
        self.logger.info(msg)
    
    def log_recovery_error(self, recovery_id: str, error_message: str):
        """Logiraj grešku pri oporavku"""
        msg = f"Recovery error | ID: {recovery_id} | Error: {error_message}"
        self.logger.error(msg)
    
    def log_integrity_check(self, backup_id: str, status: str, details: str):
        """Logiraj provjeru integriteta"""
        msg = f"Integrity check | Backup ID: {backup_id} | Status: {status} | Details: {details}"
        self.logger.info(msg)
    
    def log_verification_error(self, backup_id: str, file_path: str, error: str):
        """Logiraj grešku pri verifikaciji"""
        msg = f"Verification error | Backup ID: {backup_id} | File: {file_path} | Error: {error}"
        self.logger.warning(msg)
    
    def log_scheduler_start(self, schedule_id: str, schedule_type: str):
        """Logiraj početak schedulera"""
        msg = f"Scheduler started | ID: {schedule_id} | Type: {schedule_type}"
        self.logger.info(msg)
    
    def log_scheduler_task(self, schedule_id: str, task_type: str, status: str):
        """Logiraj scheduler task"""
        msg = f"Scheduler task | ID: {schedule_id} | Task: {task_type} | Status: {status}"
        self.logger.info(msg)
    
    def log_version_update(self, version_id: str, changes: str):
        """Logiraj verziju backupa"""
        msg = f"Version update | ID: {version_id} | Changes: {changes}"
        self.logger.info(msg)
    
    def close(self):
        """Zatvori logger"""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
    def log_version_cleanup(self, deleted_backups: int, freed_bytes: int):
        """Logiraj čišćenje svih starih backup-a"""
        size_mb = freed_bytes / (1024*1024)
        msg = f"Version cleanup | Deleted backups: {deleted_backups} | Freed space: {size_mb:.2f} MB"
        self.logger.info(msg)

# Test script
if __name__ == '__main__':
    print("Testing logger...")
    
    logger = BackupLogger('./logs')
    
    logger.log_backup_start('backup_001', 'full', './data')
    logger.log_backup_complete('backup_001', 150, 104857600, 45.5)
    logger.log_backup_error('backup_002', 'Permission denied')
    
    logger.log_recovery_start('recovery_001', 'backup_001', './restore')
    logger.log_recovery_complete('recovery_001', 150, 30.2, 30.2)
    
    logger.log_integrity_check('backup_001', 'passed', 'All files verified')
    logger.log_verification_error('backup_001', 'file.txt', 'CRC mismatch')
    
    print("\n✓ Logger test completed!")
    print(f"  Backup log: {logger.backup_log}")
    print(f"  Recovery log: {logger.recovery_log}")
    print(f"  Error log: {logger.error_log}")
