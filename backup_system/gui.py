"""
Grafičko sučelje za Backup and Disaster Recovery System
Koristi tkinter za jednostavni UI
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from logger import BackupLogger
from integrity_checker import IntegrityChecker
from backup_engine import BackupEngine
from version_manager import VersionManager
from disaster_recovery import DisasterRecoveryManager
from scheduler import BackupScheduler
from cloud_sync import CloudSync
import shutil


class BackupGUI:
    """Grafičko sučelje za sustav"""

    def __init__(self, root):
        """Inicijalizacija GUI-ja"""
        self.root = root
        self.root.title("Backup & Recovery System")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')

        self.config = self._load_config()
        self.logger = BackupLogger(self.config['logging']['log_file'])
        self.integrity_checker = IntegrityChecker('sha256', self.logger)
        self.backup_engine = BackupEngine(
            self.config['system_config']['backup_root'],
            self.logger,
            self.integrity_checker
        )
        self.version_manager = VersionManager(
            self.config['system_config']['backup_root'],
            self.config['system_config']['retention_policy'],
            self.logger
        )
        self.disaster_recovery = DisasterRecoveryManager(
            self.config['system_config']['backup_root'],
            self.logger,
            self.integrity_checker
        )

        self.scheduler = BackupScheduler(
            backup_engine=self.backup_engine,
            logger=self.logger
        )
        self.scheduler.start_scheduler()  # start scheduler u pozadini

        self.cloud_sync = CloudSync(logger=self.logger)

        self._create_ui()
        self._refresh_backup_list()

    def _load_config(self):
        """Učitava konfiguraciju"""
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def _create_ui(self):
        """Kreira korisničko sučelje"""

        # Header
        header = tk.Frame(self.root, bg='#2c3e50', height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title = tk.Label(header, text="Backup & Disaster Recovery System",
                         font=("Arial", 18, "bold"), bg='#2c3e50', fg='white')
        title.pack(pady=10)

        # Main content
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Akcije i Scheduler
        left_panel = ttk.LabelFrame(main_frame, text="Akcije", padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))

        # Backup tipke
        tk.Button(left_panel, text="Full Backup", command=self.full_backup,
                  bg='#2e3330', fg='white', width=15, height=2).pack(pady=5)
        tk.Button(left_panel, text="Incremental Backup", command=self.incremental_backup,
                  bg='#2e3330', fg='white', width=15, height=2).pack(pady=5)
        tk.Button(left_panel, text="Differential Backup", command=self.differential_backup,
                  bg='#2e3330', fg='white', width=15, height=2).pack(pady=5)

        

        # Scheduler gumb
        
        ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, pady=10)
# ---------------- Scheduler dodatno ----------------
        # Scheduler gumb
        tk.Button(left_panel, text="Schedule Backup", command=self.schedule_backup_gui,
                  bg='#2e3330', fg='white', width=20).pack(pady=5)

        # Gumb za prikaz statusa schedula
        tk.Button(left_panel, text="Show Scheduler Status", command=self.show_scheduler_status,
                  bg='#2e3330', fg='white', width=20).pack(pady=5)

        # Gumb za otkazivanje svih zakazanih backup-a
        tk.Button(left_panel, text="Cancel All Scheduled Backups", command=self.cancel_all_scheduled_backups,
                  bg='#2e3330', fg='white', width=25).pack(pady=5)
        ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, pady=10)
        # Restore
        tk.Button(left_panel, text="Restore Backup", command=self.restore_backup,
                  bg='#2e3330', fg='white', width=15, height=2).pack(pady=5)

        ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, pady=10)

        # Novi gumb za brisanje svih backup-a
        tk.Button(left_panel, text="Delete All Backups", command=self.delete_all_backups_gui,
                  bg='#2e3330', fg='white', width=20).pack(pady=5)

        ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, pady=10)

        tk.Button(left_panel, text="Upload All to Cloud", command=self.upload_all_to_cloud,
                  bg='#2e3330', fg='white', width=25).pack(pady=5)

        tk.Button(left_panel, text="Refresh", command=self._refresh_backup_list,
                  bg='#2e3330', fg='white', width=15).pack(pady=5)

        # Right panel - Backup lista
        right_panel = ttk.LabelFrame(main_frame, text="Dostupni Backupi", padding=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(right_panel)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(right_panel, columns=('ID', 'Tip', 'Datoteke', 'Velicina', 'Status', 'Timestamp'),
                                 yscrollcommand=scrollbar.set, height=15)
        scrollbar.config(command=self.tree.yview)

        self.tree.column('#0', width=0, stretch=tk.NO)
        self.tree.column('ID', anchor=tk.W, width=150)
        self.tree.column('Tip', anchor=tk.W, width=80)
        self.tree.column('Datoteke', anchor=tk.CENTER, width=80)
        self.tree.column('Velicina', anchor=tk.CENTER, width=80)
        self.tree.column('Status', anchor=tk.CENTER, width=80)
        self.tree.column('Timestamp', anchor=tk.CENTER, width=150)

        self.tree.heading('#0', text='', anchor=tk.W)
        self.tree.heading('ID', text='Backup ID', anchor=tk.W)
        self.tree.heading('Tip', text='Tip', anchor=tk.W)
        self.tree.heading('Datoteke', text='Datoteke', anchor=tk.CENTER)
        self.tree.heading('Velicina', text='Velicina (MB)', anchor=tk.CENTER)
        self.tree.heading('Status', text='Status', anchor=tk.CENTER)
        self.tree.heading('Timestamp', text='Timestamp', anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True)

    # ---------------- Backup funkcije ----------------
    def full_backup(self):
        source = filedialog.askdirectory(title="Odaberi direktorij za backup")
        if not source: return
        try:
            self.logger.logger.info(f"Pokretanje full backupa za: {source}")
            success, metadata = self.backup_engine.full_backup(source)
            if success:
                messagebox.showinfo("Uspjeh",
                                    f"Full backup završen!\n\n"
                                    f"ID: {metadata['id']}\n"
                                    f"Datoteke: {metadata['file_count']}\n"
                                    f"Veličina: {metadata['size_bytes'] / 1024:.2f} KB\n"
                                    f"Trajanje: {metadata['duration_seconds']:.2f}s")
                self._refresh_backup_list()
            else:
                messagebox.showerror("Greška", f"Backup neuspjesan:\n{metadata.get('error')}")
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri backupu:\n{e}")

    def incremental_backup(self):
        source = filedialog.askdirectory(title="Odaberi direktorij za backup")
        if not source: return
        try:
            self.logger.logger.info(f"Pokretanje incremental backupa za: {source}")
            success, metadata = self.backup_engine.incremental_backup(source)
            if success:
                messagebox.showinfo("Uspjeh",
                                    f"Incremental backup završen!\n\n"
                                    f"ID: {metadata['id']}\n"
                                    f"Datoteke: {metadata['file_count']}\n"
                                    f"Veličina: {metadata['size_bytes'] / 1024:.2f} KB\n"
                                    f"Trajanje: {metadata['duration_seconds']:.2f}s")
                self._refresh_backup_list()
            else:
                messagebox.showerror("Greška", f"Backup neuspjesan:\n{metadata.get('error')}")
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri backupu:\n{e}")

    def differential_backup(self):
        source = filedialog.askdirectory(title="Odaberi direktorij za backup")
        if not source: return
        try:
            self.logger.logger.info(f"Pokretanje differential backupa za: {source}")
            success, metadata = self.backup_engine.differential_backup(source)
            if success:
                messagebox.showinfo("Uspjeh",
                                    f"Differential backup završen!\n\n"
                                    f"ID: {metadata['id']}\n"
                                    f"Datoteke: {metadata['file_count']}\n"
                                    f"Veličina: {metadata['size_bytes'] / 1024:.2f} KB\n"
                                    f"Trajanje: {metadata['duration_seconds']:.2f}s")
                self._refresh_backup_list()
            else:
                messagebox.showerror("Greška", f"Backup neuspjesan:\n{metadata.get('error')}")
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri backupu:\n{e}")

    def restore_backup(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Odaberi backup za restauraciju!")
            return
        item = selection[0]
        backup_id = self.tree.item(item)['values'][0]

        dest = filedialog.askdirectory(title="Odaberi direktorij gdje vratiti podatke")
        if not dest:
            messagebox.showinfo("Otkazano", "Restauracija otkazana")
            return

        if os.path.exists(dest) and os.listdir(dest):
            response = messagebox.askyesno(
                "Potvrda",
                f"Direktorij {dest} nije prazan!\nŽelim vratiti podatke ovdje?"
            )
            if not response:
                return

        try:
            self.logger.logger.info(f"Pokretanje restauracije: {backup_id}")
            success, metadata = self.disaster_recovery.restore_from_backup(backup_id, dest)
            if success:
                messagebox.showinfo("Uspjeh",
                                    f"Restauracija završena!\n\n"
                                    f"Recovery ID: {metadata['recovery_id']}\n"
                                    f"Datoteke: {metadata['file_count']}\n"
                                    f"Trajanje: {metadata['duration_seconds']:.2f}s\n"
                                    f"Lokacija: {dest}")
            else:
                messagebox.showerror("Greška",
                                     f"Restauracija neuspješna:\n{metadata.get('error')}")
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri restauraciji:\n{e}")

    def cleanup_backups(self):
        """Čišćenje prema retention policy"""
        try:
            if messagebox.askyesno("Potvrda", "Obrisati stare backupe prema retention politici?"):
                self.logger.logger.info("Pokretanje čišćenja starih backupa")
                results = self.version_manager.apply_retention_policy()
                messagebox.showinfo("Uspjeh",
                                    f"Čišćenje završeno!\n\n"
                                    f"Obrisani backupi:\n"
                                    f"  - Full: {results['full_backups_deleted']}\n"
                                    f"  - Incremental: {results['incremental_backups_deleted']}\n"
                                    f"  - Differential: {results['differential_backups_deleted']}\n"
                                    f"Oslobođeno prostora: {results['total_space_freed_bytes'] / (1024*1024):.2f} MB")
                self._refresh_backup_list()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čišćenju:\n{e}")

    def delete_all_backups_gui(self):
        """Obriši cijelu backups mapu"""
        confirm = messagebox.askyesno(
            "Potvrda", "Želite li obrisati cijelu backups mapu?"
        )
        if not confirm:
            return

        success, msg = self.backup_engine.delete_all_backups()
        if success:
            messagebox.showinfo("Uspjeh", msg)
            self._refresh_backup_list()  # odmah osvježi TreeView
        else:
            messagebox.showerror("Greška", msg)

    # ---------------- Cloud funkcije ----------------
    def upload_all_to_cloud(self):
        """Upload svih backup-a na cloud (S3)"""
        try:
            confirm = messagebox.askyesno(
                "Potvrda",
                "Želite li uploadati SVE backup-e na cloud?"
            )
            if not confirm:
                return

            results = self.cloud_sync.sync_all_backups()
            messagebox.showinfo("Cloud Sync",
                                f"Uspješno: {results['successful_uploads']}\n"
                                f"Neuspješno: {results['failed_uploads']}\n"
                                f"Ukupno datoteka: {results['total_files']}")
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri uploadu na cloud:\n{e}")

    # ---------------- Lista backupa ----------------
    def _refresh_backup_list(self):
        """Osvježi listu backupa"""
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)

            summary = self.backup_engine.get_backup_summary()

            for backup in summary['backups']:
                ts_str = backup['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if backup.get('timestamp') else ''
                status_color = 'green' if backup['status'] == 'completed' else 'red'

                self.tree.insert('', 'end',
                                 values=(backup['id'], backup['type'], backup['files'],
                                         f"{backup['size_mb']:.2f}", backup['status'], ts_str),
                                 tags=(status_color,))

            self.tree.tag_configure('green', foreground='green')
            self.tree.tag_configure('red', foreground='red')

            # Osvježi info
            metrics = self.disaster_recovery.calculate_rpo_rto()
            info_text = (
                f"Ukupno backupa: {summary['total_backups']} | "
                f"Ukupna veličina: {summary['total_size_bytes'] / (1024*1024):.2f} MB | "
                f"RTO: {metrics['rto_minutes']:.1f} min | "
                f"RPO: {metrics['rpo_minutes']:.1f} min"
            )
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri osvježavanju:\n{e}")

    # ---------------- Scheduler popup ----------------
    def schedule_backup_gui(self):
        """Popup za zakazani backup"""
        # Korisnik prvo bira direktorij za backup
        source = filedialog.askdirectory(title="Odaberi direktorij za backup")
        if not source:
            return

        # Novi popup prozor za vrijeme
        popup = tk.Toplevel(self.root)
        popup.title("Schedule Backup")
        popup.geometry("300x150")
        popup.grab_set()  # modal

        tk.Label(popup, text=f"Zakazivanje backup-a za:\n{source}", wraplength=280).pack(pady=10)

        tk.Label(popup, text="Vrijeme (HH:MM, 24h format):").pack(pady=5)
        time_entry = tk.Entry(popup)
        time_entry.pack(pady=5)
        time_entry.insert(0, "14:00")  # default vrijeme

        def schedule():
            time_str = time_entry.get()
            try:
                hour, minute = map(int, time_str.split(":"))
                self.scheduler.schedule_backup(source_dir=source, hour=hour, minute=minute)
                self.logger.logger.info(f"Backup za {source} zakazan u {hour:02d}:{minute:02d}")
                messagebox.showinfo("Scheduler", f"Backup za {source} zakazan u {hour:02d}:{minute:02d}")
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Greška", f"Neispravno vrijeme ili problem sa zakazivanjem:\n{e}")

        tk.Button(popup, text="Schedule", command=schedule, bg='#2980b9', fg='white').pack(pady=10)

        # ---------------- Scheduler status ----------------
    def show_scheduler_status(self):
        """Prikaz statusa zakazanih backup-a"""
        try:
            status = self.scheduler.get_scheduler_status()
            running = status['running']
            scheduled_count = status['scheduled_jobs']
            jobs = status['jobs']
            next_run = status['next_run']

            text = f"Scheduler running: {running}\n"
            text += f"Scheduled jobs: {scheduled_count}\n"
            text += f"Next run: {next_run}\n\n"
            text += "Detalji jobova:\n"
            for job in jobs:
                text += f"- {job['type'].capitalize()} backup | {job['source']} | {job['time']}\n"

            messagebox.showinfo("Scheduler Status", text)
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri dohvaćanju statusa schedula:\n{e}")

    def cancel_all_scheduled_backups(self):
        """Otkazuje sve zakazane backup-e"""
        confirm = messagebox.askyesno(
            "Potvrda", "Jeste li sigurni da želite otkazati sve zakazane backup-e?"
        )
        if not confirm:
            return

        try:
            count = self.scheduler.cancel_all_backups()
            messagebox.showinfo("Scheduler", f"Svi zakazani backup-i otkazani ({count} jobova).")
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri otkazivanju schedula:\n{e}")


def main():
    root = tk.Tk()
    app = BackupGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
