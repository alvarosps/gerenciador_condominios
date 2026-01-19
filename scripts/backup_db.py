"""
Database backup utility for Condominios Manager

This script creates a PostgreSQL database backup using pg_dump.
The backup is saved in plain SQL format which provides:
- Human-readable SQL statements
- Easy restoration with psql
- Maximum portability across PostgreSQL versions

Usage:
    python scripts/backup_db.py

Output:
    backups/backup_{db_name}_{timestamp}.sql

Restore:
    psql -h localhost -U postgres -d database_name < backup_file.sql

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


def verify_utf8_encoding(file_path):
    """
    Verify that a file contains valid UTF-8 content.

    Args:
        file_path: Path to the file to verify

    Returns:
        bool: True if file is valid UTF-8, False otherwise
    """
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        # Try to decode as UTF-8
        content.decode("utf-8")

        # Check for common encoding issues (replacement characters)
        decoded = content.decode("utf-8")
        if "\ufffd" in decoded:
            # Contains replacement characters - indicates encoding issues
            return False

        return True
    except UnicodeDecodeError:
        return False


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
    backup_file = backup_dir / f"backup_{db_name}_{timestamp}.sql"

    print(f"Backup File: {backup_file}")
    print("\nStarting backup process...")

    # Set environment variables for pg_dump
    env = os.environ.copy()
    env["PGPASSWORD"] = db_password
    env["PGCLIENTENCODING"] = "UTF8"  # Force UTF-8 client encoding

    # Platform-specific locale settings
    if sys.platform == "win32":
        # On Windows, LC_ALL might not work as expected
        # Use PYTHONIOENCODING as additional safeguard
        env["PYTHONIOENCODING"] = "utf-8"
    else:
        env["LC_ALL"] = "en_US.UTF-8"  # Set locale for proper encoding on Linux/macOS

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
        "p",  # Plain SQL format (human-readable, portable)
        "--encoding=UTF8",  # Explicit UTF-8 encoding
        "--no-owner",  # Don't output ownership commands
        "--no-acl",  # Don't output access privilege commands
        "-f",
        str(backup_file),
        db_name,
    ]

    try:
        # Execute pg_dump
        subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)

        # Check if backup file was created
        if backup_file.exists():
            # Prepend \encoding UTF8 command for psql to ensure proper encoding on restore
            # This must be at the very beginning so psql reads the file in UTF-8
            with open(backup_file, "rb") as f:
                original_content = f.read()

            with open(backup_file, "wb") as f:
                # Write psql encoding directive first (this is a psql meta-command)
                f.write(b"\\encoding UTF8\n\n")
                f.write(original_content)

            # Verify the backup file is valid UTF-8
            if not verify_utf8_encoding(backup_file):
                print("\n[WARNING] Backup file may have encoding issues")
                print("         This could indicate corrupted data in the database")

            file_size = backup_file.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            print("\n" + "=" * 60)
            print("[OK] BACKUP SUCCESSFUL")
            print("=" * 60)
            print(f"Backup File: {backup_file}")
            print(f"File Size: {file_size_mb:.2f} MB")
            print(f"Timestamp: {timestamp}")
            print("\nTo restore this backup, run:")
            print(f"  psql -h {db_host} -p {db_port} -U {db_user} -d {db_name} < {backup_file}")
            print("=" * 60)

            return backup_file
        else:
            raise FileNotFoundError("Backup file was not created")

    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("[FAILED] BACKUP FAILED")
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
        print("[FAILED] BACKUP FAILED")
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
        print("[FAILED] BACKUP FAILED")
        print("=" * 60)
        print(f"Unexpected error: {e}")
        print("=" * 60)
        return None


def list_existing_backups():
    """List all existing backup files"""
    backup_dir = project_root / "backups"
    if not backup_dir.exists():
        return []

    # Include both .sql and legacy .backup files
    sql_backups = list(backup_dir.glob("backup_*.sql"))
    legacy_backups = list(backup_dir.glob("backup_*.backup"))
    backups = sorted(sql_backups + legacy_backups, key=lambda f: f.stat().st_mtime, reverse=True)
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
