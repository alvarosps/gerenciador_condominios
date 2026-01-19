"""
Database restore utility for Condominios Manager

This script restores a PostgreSQL database from a backup created by backup_db.py.
Supports both plain SQL format (.sql) and custom format (.backup) backup files.

IMPORTANT: This script will DROP and RECREATE the database!
           Make sure you have a recent backup before proceeding.

The script handles UTF-8 encoding properly on Windows by:
1. Creating the database with explicit UTF-8 encoding
2. Using psql -f to restore (avoids PowerShell encoding issues)
3. Setting PGCLIENTENCODING=UTF8 environment variable

Usage:
    python scripts/restore_db.py path/to/backup.sql
    python scripts/restore_db.py path/to/backup.backup

Options:
    --yes       Skip confirmation prompt
    --list      List contents of backup file (custom format only)

Examples:
    # Restore SQL backup (recommended)
    python scripts/restore_db.py backups/backup_condominio_20260119_143116.sql

    # Restore with auto-confirmation
    python scripts/restore_db.py backups/backup_condominio_20260119_143116.sql --yes

Author: Development Team
Date: 2025-10-19
Updated: 2026-01-19 (Added UTF-8 encoding support for Windows)
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


def get_psql_env(db_password):
    """
    Create environment variables for psql with proper UTF-8 encoding.

    Args:
        db_password: Database password

    Returns:
        dict: Environment variables for subprocess
    """
    env = os.environ.copy()
    env["PGPASSWORD"] = db_password
    env["PGCLIENTENCODING"] = "UTF8"  # Force UTF-8 client encoding

    # Additional Windows-specific settings
    if sys.platform == "win32":
        env["PYTHONIOENCODING"] = "utf-8"

    return env


def list_backup_contents(backup_file, db_password):
    """
    List contents of a custom format backup file.

    Args:
        backup_file (str): Path to backup file
        db_password (str): Database password for authentication

    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 60)
    print("Backup File Contents")
    print("=" * 60)

    if backup_file.endswith(".sql"):
        print("\nNote: --list is not supported for plain SQL backups.")
        print("Use a text editor or 'head' command to view the file.")
        return False

    env = get_psql_env(db_password)
    cmd = ["pg_restore", "--list", backup_file]

    try:
        result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        print(result.stdout)
        print("=" * 60)
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Error listing backup contents: {e}")
        if e.stderr:
            print(f"Details: {e.stderr}")
        return False


def drop_and_create_database(db_name, db_user, db_host, db_port, env):
    """
    Drop existing database and create a new one with UTF-8 encoding.

    Args:
        db_name: Database name
        db_user: Database user
        db_host: Database host
        db_port: Database port
        env: Environment variables

    Returns:
        bool: True if successful, False otherwise
    """
    psql_args = ["psql", "-h", db_host, "-p", str(db_port), "-U", db_user, "-d", "postgres"]

    # Step 1: Terminate existing connections
    print("\n[Step 1/3] Terminating existing connections...")
    terminate_sql = f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{db_name}'
        AND pid <> pg_backend_pid();
    """
    try:
        subprocess.run(
            psql_args + ["-c", terminate_sql],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        print("  Existing connections terminated")
    except Exception:
        pass  # Ignore errors - database might not exist

    # Step 2: Drop database
    print("\n[Step 2/3] Dropping existing database...")
    drop_sql = f'DROP DATABASE IF EXISTS "{db_name}";'
    try:
        result = subprocess.run(
            psql_args + ["-c", drop_sql],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode == 0:
            print("  Database dropped successfully")
        else:
            print(f"  Warning: {result.stderr.strip()}")
    except Exception as e:
        print(f"  Warning: Could not drop database: {e}")

    # Step 3: Create database with UTF-8 encoding
    print("\n[Step 3/3] Creating database with UTF-8 encoding...")

    # Use template0 to allow setting encoding
    # On Windows, LC_COLLATE/LC_CTYPE might not work, so we use simpler syntax
    create_sql = f"""CREATE DATABASE "{db_name}"
        WITH ENCODING 'UTF8'
        TEMPLATE template0;"""

    try:
        result = subprocess.run(
            psql_args + ["-c", create_sql],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            print(f"  Error creating database: {result.stderr.strip()}")
            return False
        print("  Database created with UTF-8 encoding")
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


def restore_sql_backup(backup_path, db_name, db_user, db_host, db_port, env):
    """
    Restore a plain SQL backup file using psql.

    This method uses psql -f to read the file directly, avoiding PowerShell
    encoding issues that occur when piping content.

    Args:
        backup_path: Path to backup file
        db_name: Database name
        db_user: Database user
        db_host: Database host
        db_port: Database port
        env: Environment variables

    Returns:
        bool: True if successful, False otherwise
    """
    print("\n[Restoring] Reading SQL backup file...")
    print("  This may take a while for large databases...")

    # Use psql -f to read file directly - this preserves encoding properly
    # The file contains \encoding UTF8 at the start which psql will honor
    psql_cmd = [
        "psql",
        "-h", db_host,
        "-p", str(db_port),
        "-U", db_user,
        "-d", db_name,
        "-v", "ON_ERROR_STOP=0",  # Continue on non-critical errors
        "-f", str(backup_path)
    ]

    try:
        result = subprocess.run(
            psql_cmd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"  # Replace encoding errors instead of failing
        )

        # Check for critical errors
        if result.stderr:
            # Filter out notices and non-critical messages
            critical_lines = []
            for line in result.stderr.split("\n"):
                line_lower = line.lower()
                if (line.strip() and
                    "notice:" not in line_lower and
                    "already exists" not in line_lower and
                    "skipping" not in line_lower):
                    critical_lines.append(line)

            if critical_lines:
                print("\n  Warnings during restore:")
                for line in critical_lines[:10]:
                    print(f"    {line}")
                if len(critical_lines) > 10:
                    print(f"    ... and {len(critical_lines) - 10} more")

        return True

    except subprocess.CalledProcessError as e:
        print(f"\n  Error during restore: {e}")
        if e.stderr:
            print(f"  Details: {e.stderr}")
        return False


def restore_custom_backup(backup_path, db_name, db_user, db_host, db_port, env):
    """
    Restore a custom format backup file using pg_restore.

    Args:
        backup_path: Path to backup file
        db_name: Database name
        db_user: Database user
        db_host: Database host
        db_port: Database port
        env: Environment variables

    Returns:
        bool: True if successful, False otherwise
    """
    print("\n[Restoring] Using pg_restore for custom format backup...")

    cmd = [
        "pg_restore",
        "-h", db_host,
        "-p", str(db_port),
        "-U", db_user,
        "-d", db_name,
        "-v",  # Verbose
        "--no-owner",  # Don't set ownership
        "--no-acl",  # Don't restore access privileges
        str(backup_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        # pg_restore returns non-zero for warnings too, so check stderr
        if result.stderr and "error" in result.stderr.lower():
            print(f"\n  Warnings: {result.stderr[:500]}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"\n  Error during restore: {e}")
        if e.stderr:
            print(f"  Details: {e.stderr}")
        return False


def restore_database(backup_file, skip_confirmation=False):
    """
    Restore PostgreSQL database from backup file with proper UTF-8 encoding.

    Args:
        backup_file (str): Path to backup file (.sql or .backup)
        skip_confirmation (bool): Skip user confirmation prompt

    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 60)
    print("Condominios Manager - Database Restore Utility")
    print("=" * 60)

    # Verify backup file exists
    backup_path = Path(backup_file)
    if not backup_path.exists():
        # Try relative to project root
        backup_path = project_root / backup_file
        if not backup_path.exists():
            print(f"\n[ERROR] Backup file not found: {backup_file}")
            list_available_backups()
            return False

    backup_path = backup_path.resolve()

    # Determine backup type
    is_sql_backup = str(backup_path).endswith(".sql")
    backup_type = "Plain SQL" if is_sql_backup else "Custom format"

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

    print(f"\nBackup File: {backup_path}")
    file_size = backup_path.stat().st_size / (1024 * 1024)
    print(f"File Size: {file_size:.2f} MB")
    print(f"Format: {backup_type}")

    # WARNING
    print("\n" + "!" * 60)
    print("WARNING: This will DROP and RECREATE the database!")
    print("         All existing data will be replaced!")
    print("!" * 60)

    # Prompt for confirmation
    if not skip_confirmation:
        response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            print("\n[CANCELLED] Restore cancelled by user")
            return False

    print("\nStarting restore process...")

    # Set up environment with UTF-8 encoding
    env = get_psql_env(db_password)

    # Drop and create database with UTF-8 encoding
    if not drop_and_create_database(db_name, db_user, db_host, db_port, env):
        print("\n[FAILED] Could not create database")
        return False

    # Restore based on backup type
    if is_sql_backup:
        success = restore_sql_backup(backup_path, db_name, db_user, db_host, db_port, env)
    else:
        success = restore_custom_backup(backup_path, db_name, db_user, db_host, db_port, env)

    if success:
        print("\n" + "=" * 60)
        print("[OK] RESTORE COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Database: {db_name}")
        print(f"Restored from: {backup_path}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nNext steps:")
        print("  1. Run migrations if needed:")
        print("     python manage.py migrate")
        print("  2. Verify UTF-8 encoding:")
        print("     python manage.py shell")
        print("     >>> from core.models import Tenant")
        print("     >>> print(Tenant.objects.first().name)")
        print("  3. Test application functionality")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("[FAILED] RESTORE FAILED")
        print("=" * 60)
        print("\nCommon issues:")
        print("  1. Database server not running")
        print("  2. Incorrect database credentials")
        print("  3. Insufficient permissions")
        print("  4. Corrupted backup file")
        print("=" * 60)
        return False


def list_available_backups():
    """List all available backup files"""
    backup_dir = project_root / "backups"
    if not backup_dir.exists():
        print("\nNo backup directory found")
        return

    # Include both .sql and .backup files
    sql_backups = list(backup_dir.glob("backup_*.sql"))
    custom_backups = list(backup_dir.glob("backup_*.backup"))
    all_backups = sorted(sql_backups + custom_backups, key=lambda f: f.stat().st_mtime, reverse=True)

    if all_backups:
        print(f"\nAvailable backups ({len(all_backups)}):")
        for i, backup in enumerate(all_backups[:10], 1):
            file_size = backup.stat().st_size / (1024 * 1024)
            backup_type = "SQL" if str(backup).endswith(".sql") else "Custom"
            print(f"  {i}. {backup.name} ({file_size:.2f} MB) [{backup_type}]")
        if len(all_backups) > 10:
            print(f"  ... and {len(all_backups) - 10} more")
    else:
        print("\nNo backup files found in 'backups/' directory")


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
        print("  --yes     Skip confirmation prompt")
        print("  --list    List contents of backup file (custom format only)")
        print("\nSupported formats:")
        print("  .sql      Plain SQL format (recommended)")
        print("  .backup   PostgreSQL custom format")
        print("\nExamples:")
        print("  python scripts/restore_db.py backups/backup_condominio_20260119.sql")
        print("  python scripts/restore_db.py backups/backup_condominio_20260119.sql --yes")
        print("=" * 60)

        list_available_backups()
        sys.exit(1)

    backup_file = sys.argv[1]
    skip_confirmation = "--yes" in sys.argv or "-y" in sys.argv
    list_only = "--list" in sys.argv

    # Get database password for --list
    db_config = settings.DATABASES["default"]
    db_password = db_config["PASSWORD"]

    # List contents if requested
    if list_only:
        success = list_backup_contents(backup_file, db_password)
        sys.exit(0 if success else 1)

    # Perform restore
    try:
        success = restore_database(backup_file, skip_confirmation=skip_confirmation)
        sys.exit(0 if success else 1)
    except FileNotFoundError as e:
        if "psql" in str(e) or "pg_restore" in str(e):
            print("\n" + "=" * 60)
            print("[FAILED] PostgreSQL client tools not found")
            print("=" * 60)
            print("\nInstallation instructions:")
            print("  Windows: Install PostgreSQL from https://www.postgresql.org/download/")
            print("           Make sure to add bin folder to PATH")
            print("  Linux: sudo apt-get install postgresql-client")
            print("  macOS: brew install postgresql")
            print("=" * 60)
        else:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
