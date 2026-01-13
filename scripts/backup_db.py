"""
Database backup utility for Condominios Manager

This script creates a PostgreSQL database backup using pg_dump.
The backup is saved in custom format (-F c) which provides:
- Compression
- Selective restore capabilities
- Cross-platform compatibility

Usage:
    python scripts/backup_db.py

Output:
    backups/backup_{db_name}_{timestamp}.sql

Author: Development Team
Date: 2025-10-19
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path to import settings
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "condominios_manager.settings")
import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402


def backup_database():
    """
    Create PostgreSQL database backup using pg_dump.

    Returns:
        Path: Path to the created backup file, or None if backup failed
    """
    print("=" * 60)
    print("Condominios Manager - Database Backup Utility")
    print("=" * 60)

    # Get database configuration
    db_config = settings.DATABASES["default"]
    db_name = db_config["NAME"]
    db_user = db_config["USER"]
    db_host = db_config["HOST"]
    db_port = db_config["PORT"]
    db_password = db_config["PASSWORD"]

    print("\nDatabase Configuration:")
    print(f"  Host: {db_host}:{db_port}")
    print(f"  Database: {db_name}")
    print(f"  User: {db_user}")

    # Create backup directory
    backup_dir = project_root / "backups"
    backup_dir.mkdir(exist_ok=True)
    print(f"\nBackup Directory: {backup_dir}")

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"backup_{db_name}_{timestamp}.backup"

    print(f"Backup File: {backup_file}")
    print("\nStarting backup process...")

    # Set password environment variable for pg_dump
    env = os.environ.copy()
    env["PGPASSWORD"] = db_password

    # Construct pg_dump command
    cmd = [
        "pg_dump",
        "-h",
        db_host,
        "-p",
        str(db_port),
        "-U",
        db_user,
        "-F",
        "c",  # Custom format (compressed)
        "-b",  # Include large objects (blobs)
        "-v",  # Verbose output
        "-f",
        str(backup_file),
        db_name,
    ]

    try:
        # Execute pg_dump
        subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)

        # Check if backup file was created
        if backup_file.exists():
            file_size = backup_file.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            print("\n" + "=" * 60)
            print("✓ BACKUP SUCCESSFUL")
            print("=" * 60)
            print(f"Backup File: {backup_file}")
            print(f"File Size: {file_size_mb:.2f} MB")
            print(f"Timestamp: {timestamp}")
            print("\nTo restore this backup, run:")
            print(f"  python scripts/restore_db.py {backup_file}")
            print("=" * 60)

            return backup_file
        else:
            raise FileNotFoundError("Backup file was not created")

    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("✗ BACKUP FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        if e.stderr:
            print(f"Details: {e.stderr}")
        print("\nCommon issues:")
        print("  1. PostgreSQL client tools (pg_dump) not installed")
        print("  2. Database server not running")
        print("  3. Incorrect database credentials")
        print("  4. Network connectivity issues")
        print("=" * 60)
        return None

    except FileNotFoundError:
        print("\n" + "=" * 60)
        print("✗ BACKUP FAILED")
        print("=" * 60)
        print("Error: pg_dump command not found")
        print("\nInstallation instructions:")
        print("  Windows: Install PostgreSQL from https://www.postgresql.org/download/")
        print("  Linux: sudo apt-get install postgresql-client")
        print("  macOS: brew install postgresql")
        print("=" * 60)
        return None

    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ BACKUP FAILED")
        print("=" * 60)
        print(f"Unexpected error: {e}")
        print("=" * 60)
        return None


def list_existing_backups():
    """List all existing backup files"""
    backup_dir = project_root / "backups"
    if not backup_dir.exists():
        return []

    backups = sorted(backup_dir.glob("backup_*.backup"), reverse=True)
    return backups


def main():
    """Main function"""
    # List existing backups
    existing_backups = list_existing_backups()
    if existing_backups:
        print(f"\nExisting backups ({len(existing_backups)}):")
        for i, backup in enumerate(existing_backups[:5], 1):  # Show last 5
            file_size = backup.stat().st_size / (1024 * 1024)
            print(f"  {i}. {backup.name} ({file_size:.2f} MB)")
        if len(existing_backups) > 5:
            print(f"  ... and {len(existing_backups) - 5} more")
        print()

    # Perform backup
    backup_file = backup_database()

    # Exit with appropriate status code
    if backup_file:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
