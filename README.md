# Python-Based-Data-Backup-and-Disaster-Recovery-System
Python tool that automates data backup and disaster recovery processes, aligned with ISO 22301 requirements for business continuity and information recovery.
Component:
Automated Data Backup: contains Python script that automatically backs up critical data from various systems to secure locations (cloud storage - AWS S3 bucket). Uses boto3 for AWS S3 integration.
Data Integrity Checks: Contains integrity checks to ensure that the backups are complete and accurate. Uses hashing algorithms (SHA-256) to verify the integrity of the backup files.
Disaster Recovery Automation: Contains a disaster recovery plan that can be triggered automatically. The Python tool restores data from the most recent backup and bring systems back online with minimal downtime.
