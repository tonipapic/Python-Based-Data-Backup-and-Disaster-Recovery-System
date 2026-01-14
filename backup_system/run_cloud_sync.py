"""
Jednostavni skripti za cloud sinhronizaciju
"""

import os
from cloud_sync import CloudSync
from logger import BackupLogger


def main():
    logger = BackupLogger('./logs/cloud_sync.log')
    cloud_sync = CloudSync('advanced_config.json', logger)

    print("""
1. Sinhronizacija SVI backup-a
2. Pregled backup-a na S3-u
3. Čišćenje starih backup-a sa S3-a
""")

    choice = input("Odaberi opciju: ").strip()

    if choice == '1':
        results = cloud_sync.sync_all_backups()
        print(f"\n Sinhronizacija završena!")
        print(f"  Uspješno: {results['successful_uploads']}")
        print(f"  Neuspješno: {results['failed_uploads']}")

    elif choice == '2':
        backups = cloud_sync.get_s3_backup_list()
        print(f"\n{'='*80}")
        print(f"BACKUP-I NA S3-u ({len(backups)} datoteka)")
        print(f"{'='*80}")

        total_size = 0
        for backup in backups:
            size_mb = backup['size_bytes'] / (1024 * 1024)
            total_size += backup['size_bytes']
            print(f" {backup['key']}")
            print(f"   Veličina: {size_mb:.2f} MB")
            print(f"   Storage: {backup['storage_class']}")
            print(f"   Vrijeme: {backup['last_modified']}\n")

        print(f"{'='*80}")
        print(f"Ukupna veličina: {total_size / (1024*1024*1024):.2f} GB")

    elif choice == '3':
        days = input("Koliko dana? (default 90): ").strip()
        days = int(days) if days.isdigit() else 90

        results = cloud_sync.cleanup_old_s3_backups(days)
        print(f"\n Čišćenje završeno!")
        print(f"  Obrisani backup-i: {results['deleted_count']}")
        print(f"  Oslobodjeno: {results['total_size_freed_bytes'] / (1024*1024*1024):.2f} GB")

    

    else:
        print("Izlaz!")


if __name__ == '__main__':
    main()
