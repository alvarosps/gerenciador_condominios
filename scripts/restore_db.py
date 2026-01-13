"""
Database restore utility for Condominios Manager

This script restores a PostgreSQL database from a backup created by backup_db.py.
It uses pg_restore to restore custom format (-F c) backup files.

IMPORTANT: This will DROP and RECREATE all database objects!
           Make sure you have a recent backup before proceeding.

Usage:
    python scripts/restore_db.py path/to/backup.backup

Options:
    --clean     Drop database objects before recreating (default: True)
    --no-clean  Do not drop existing objects
    --list      List contents of backup file without restoring

Examples:
    # Restore with cleanup (recommended)
    python scripts/restore_db.py backups/backup_condominio_20251019_143022.backup

    # List backup contents
    python scripts/restore_db.py backups/backup_condominio_20251019_143022.backup --list

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


def list_backup_contents(backup_file, db_password):
    """
    List contents of a backup file.

    Args:
        backup_file (str): Path to backup file
        db_password (str): Database password for authentication

    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 60)
    print("Backup File Contents")
    print("=" * 60)

    env = os.environ.copy()
    env["PGPASSWORD"] = db_password

    cmd = ["pg_restore", "--list", backup_file]

    try:
        result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)

        print(result.stdout)
        print("=" * 60)
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error listing backup contents: {e}")
        if e.stderr:
            print(f"Details: {e.stderr}")
        return False


def restore_database(backup_file, clean=True):  # noqa: C901
    """
    Restore PostgreSQL database from backup file.

    Args:
        backup_file (str): Path to backup file
        clean (bool): Whether to drop existing objects before restore

    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 60)
    print("Condominios Manager - Database Restore Utility")
    print("=" * 60)

    # Verify backup file exists
    backup_path = Path(backup_file)
    if not backup_path.exists():
        print(f"\n✗ Error: Backup file not found: {backup_file}")
        print("\nAvailable backups:")
        backup_dir = project_root / "backups"
        if backup_dir.exists():
            backups = sorted(backup_dir.glob("backup_*.backup"), reverse=True)
            for i, b in enumerate(backups[:10], 1):
                file_size = b.stat().st_size / (1024 * 1024)
                print(f"  {i}. {b.name} ({file_size:.2f} MB)")
        return False

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

    print(f"\nBackup File: {backup_file}")
    file_size = backup_path.stat().st_size / (1024 * 1024)
    print(f"File Size: {file_size:.2f} MB")

    # WARNING
    print("\n" + "!" * 60)
    print("WARNING: This will replace ALL data in the database!")
    print("!" * 60)

    # Prompt for confirmation
    response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    if response not in ["yes", "y"]:
        print("\n✗ Restore cancelled by user")
        return False

    print("\nStarting restore process...")

    # Set password environment variable
    env = os.environ.copy()
    env["PGPASSWORD"] = db_password

    # Construct pg_restore command
    cmd = [
        "pg_restore",
        "-h",
        db_host,
        "-p",
        str(db_port),
        "-U",
        db_user,
        "-d",
        db_name,
        "-v",  # Verbose output
    ]

    if clean:
        cmd.append("-c")  # Clean (drop) database objects before recreating
        print("Mode: Clean restore (existing objects will be dropped)")
    else:
        print("Mode: Additive restore (existing objects will be kept)")

    cmd.append(str(backup_file))

    try:
        # Execute pg_restore
        subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)

        print("\n" + "=" * 60)
        print("✓ RESTORE SUCCESSFUL")
        print("=" * 60)
        print(f"Database: {db_name}")
        print(f"Restored from: {backup_file}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nNext steps:")
        print("  1. Verify data integrity")
        print("  2. Run migrations if needed: python manage.py migrate")
        print("  3. Test application functionality")
        print("=" * 60)

        return True

    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("✗ RESTORE FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        if e.stderr:
            print(f"Details: {e.stderr}")
        print("\nCommon issues:")
        print("  1. Database server not running")
        print("  2. Incorrect database credentials")
        print("  3. Database doesn't exist (create it first)")
        print("  4. Incompatible PostgreSQL versions")
        print("=" * 60)
        return False

    except FileNotFoundError:
        print("\n" + "=" * 60)
        print("✗ RESTORE FAILED")
        print("=" * 60)
        print("Error: pg_restore command not found")
        print("\nInstallation instructions:")
        print("  Windows: Install PostgreSQL from https://www.postgresql.org/download/")
        print("  Linux: sudo apt-get install postgresql-client")
        print("  macOS: brew install postgresql")
        print("=" * 60)
        return False

    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ RESTORE FAILED")
        print("=" * 60)
        print(f"Unexpected error: {e}")
        print("=" * 60)
        return False


def main():
    """Main function"""
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("=" * 60)
        print("Database Restore Utility")
        print("=" * 60)
        print("\nUsage:")
        print("  python scripts/restore_db.py <backup_file> [options]")
        print("\nOptions:")
        print("  --clean     Drop database objects before recreating (default)")
        print("  --no-clean  Do not drop existing objects")
        print("  --list      List contents of backup file")
        print("\nExamples:")
        print("  python scripts/restore_db.py backups/backup_condominio_20251019_143022.backup")
        print("  python scripts/restore_db.py backups/backup_condominio_20251019_143022.backup --list")
        print("=" * 60)

        # List available backups
        backup_dir = project_root / "backups"
        if backup_dir.exists():
            backups = sorted(backup_dir.glob("backup_*.backup"), reverse=True)
            if backups:
                print(f"\nAvailable backups ({len(backups)}):")
                for i, backup in enumerate(backups[:10], 1):
                    file_size = backup.stat().st_size / (1024 * 1024)
                    print(f"  {i}. {backup.name} ({file_size:.2f} MB)")
                if len(backups) > 10:
                    print(f"  ... and {len(backups) - 10} more")

        sys.exit(1)

    backup_file = sys.argv[1]
    clean = "--no-clean" not in sys.argv
    list_only = "--list" in sys.argv

    # Get database password
    db_config = settings.DATABASES["default"]
    db_password = db_config["PASSWORD"]

    # List contents if requested
    if list_only:
        success = list_backup_contents(backup_file, db_password)
        sys.exit(0 if success else 1)

    # Perform restore
    success = restore_database(backup_file, clean=clean)

    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
