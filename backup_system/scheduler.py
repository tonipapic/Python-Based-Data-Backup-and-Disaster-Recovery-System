"""
Planiranje i automatizacija backup operacija
"""

import schedule
import time
import threading
from datetime import datetime
from typing import Dict, List


class BackupScheduler:
    """Upravlja planiranjem i izvršavanjem backup operacija"""
    
    def __init__(self, backup_engine=None, logger=None):
        self.backup_engine = backup_engine
        self.logger = logger
        self.schedule_jobs = []
        self.is_running = False
        self.scheduler_thread = None
    
    # ---------------- Schedule backup ----------------
    def schedule_full_backup(self, source_dir: str, time_str: str = "02:00"):
        def job():
            if self.logger:
                self.logger.logger.info(f"Pokretanje scheduled full backup: {source_dir}")
            if self.backup_engine:
                success, metadata = self.backup_engine.full_backup(source_dir)
                if success:
                    if self.logger:
                        self.logger.logger.info(f"Scheduled full backup uspjesna: {metadata['id']}")
                else:
                    if self.logger:
                        self.logger.logger.error(f"Scheduled full backup neuspjesna: {metadata.get('error')}")
        scheduled_job = schedule.every().day.at(time_str).do(job)
        self.schedule_jobs.append({'type': 'full', 'source': source_dir, 'time': time_str, 'job': scheduled_job})
        if self.logger:
            self.logger.logger.info(f"Planirano daily full backup: {source_dir} u {time_str}")
    
    def schedule_incremental_backup(self, source_dir: str, time_str: str = "12:00"):
        def job():
            if self.logger:
                self.logger.logger.info(f"Pokretanje scheduled incremental backup: {source_dir}")
            if self.backup_engine:
                success, metadata = self.backup_engine.incremental_backup(source_dir)
                if success:
                    if self.logger:
                        self.logger.logger.info(f"Scheduled incremental backup uspjesna: {metadata['id']}")
                else:
                    if self.logger:
                        self.logger.logger.error(f"Scheduled incremental backup neuspjesna: {metadata.get('error')}")
        scheduled_job = schedule.every().day.at(time_str).do(job)
        self.schedule_jobs.append({'type': 'incremental', 'source': source_dir, 'time': time_str, 'job': scheduled_job})
        if self.logger:
            self.logger.logger.info(f"Planirano daily incremental backup: {source_dir} u {time_str}")
    
    def schedule_differential_backup(self, source_dir: str, time_str: str = "18:00"):
        def job():
            if self.logger:
                self.logger.logger.info(f"Pokretanje scheduled differential backup: {source_dir}")
            if self.backup_engine:
                success, metadata = self.backup_engine.differential_backup(source_dir)
                if success:
                    if self.logger:
                        self.logger.logger.info(f"Scheduled differential backup uspjesna: {metadata['id']}")
                else:
                    if self.logger:
                        self.logger.logger.error(f"Scheduled differential backup neuspjesna: {metadata.get('error')}")
        scheduled_job = schedule.every().day.at(time_str).do(job)
        self.schedule_jobs.append({'type': 'differential', 'source': source_dir, 'time': time_str, 'job': scheduled_job})
        if self.logger:
            self.logger.logger.info(f"Planirano daily differential backup: {source_dir} u {time_str}")

    # ---------------- Scheduler kontrola ----------------
    def start_scheduler(self):
        if self.is_running:
            if self.logger:
                self.logger.logger.warning("Scheduler je već pokrenut")
            return
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        if self.logger:
            self.logger.logger.info("Scheduler pokrenut")
    
    def _run_scheduler(self):
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                if self.logger:
                    self.logger.logger.error(f"Greska u scheduler petlji: {e}")
    
    def stop_scheduler(self):
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        if self.logger:
            self.logger.logger.info("Scheduler zaustavljen")

    def cancel_all_backups(self):
        """Otkazivanje svih zakazanih backup-a"""
        for job in self.schedule_jobs:
            schedule.cancel_job(job['job'])
        self.schedule_jobs.clear()
        if self.logger:
            self.logger.logger.info("Otkazani svi zakazani backup-i")

    # ---------------- Informacije ----------------
    def get_scheduled_jobs(self) -> List[Dict]:
        return self.schedule_jobs
    
    def get_scheduler_status(self) -> Dict:
        return {
            'running': self.is_running,
            'scheduled_jobs': len(self.schedule_jobs),
            'jobs': [{'type': j['type'], 'source': j.get('source'), 'time': j['time']} for j in self.schedule_jobs],
            'next_run': schedule.next_run().isoformat() if schedule.get_jobs() else None
        }

    # ---------------- Universal scheduler ----------------
    def schedule_backup(self, source_dir: str, hour: int = 2, minute: int = 0, backup_type: str = "full"):
        """Planiranje backup-a prema tipu"""
        time_str = f"{hour:02d}:{minute:02d}"
        if backup_type == "full":
            self.schedule_full_backup(source_dir, time_str)
        elif backup_type == "incremental":
            self.schedule_incremental_backup(source_dir, time_str)
        elif backup_type == "differential":
            self.schedule_differential_backup(source_dir, time_str)
        else:
            if self.logger:
                self.logger.logger.error(f"Neispravan tip backup-a: {backup_type}")
