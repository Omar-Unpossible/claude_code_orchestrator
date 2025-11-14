#!/usr/bin/env python3
"""Apply pending database migrations to Obra database

This script applies SQL migrations to the Obra database. It checks which
migrations have been applied and applies any pending ones in order.

Usage:
    python scripts/apply_migrations.py [--db-path PATH]

Examples:
    python scripts/apply_migrations.py                    # Use default DB path
    python scripts/apply_migrations.py --db-path obra.db  # Custom DB path
"""

import argparse
import sqlite3
import sys
from pathlib import Path


def get_db_path() -> str:
    """Get database path from config or use default"""
    try:
        import yaml
        config_path = Path("config/config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                db_url = config.get('database', {}).get('url', '')
                if 'sqlite:///' in db_url:
                    # Extract path from sqlite:///path/to/db
                    return db_url.replace('sqlite:///', '')
    except Exception:
        pass

    # Default path
    return "runtime/obra.db"


def check_migration_applied(conn: sqlite3.Connection, migration_name: str) -> bool:
    """Check if a migration has been applied by checking if columns exist"""
    cursor = conn.cursor()

    # Check specific columns added by each migration
    checks = {
        '003_agile_hierarchy': "SELECT COUNT(*) FROM pragma_table_info('task') WHERE name = 'task_type'",
        '004_documentation_fields': "SELECT COUNT(*) FROM pragma_table_info('task') WHERE name = 'requires_adr'"
    }

    check_sql = checks.get(migration_name)
    if not check_sql:
        return False

    try:
        cursor.execute(check_sql)
        return cursor.fetchone()[0] > 0
    except sqlite3.Error:
        return False


def apply_migration(conn: sqlite3.Connection, migration_file: Path) -> bool:
    """Apply SQL migration file to database

    Args:
        conn: Database connection
        migration_file: Path to migration SQL file

    Returns:
        True if successful, False otherwise
    """
    migration_name = migration_file.stem

    # Check if already applied
    if check_migration_applied(conn, migration_name):
        print(f"⏭️  Skipping {migration_name} (already applied)")
        return True

    # Read migration SQL
    try:
        migration_sql = migration_file.read_text()
    except Exception as e:
        print(f"❌ Cannot read {migration_file}: {e}")
        return False

    # Apply migration
    try:
        conn.executescript(migration_sql)
        conn.commit()
        print(f"✅ Applied migration: {migration_name}")
        return True
    except sqlite3.Error as e:
        print(f"❌ Migration failed ({migration_name}): {e}")
        conn.rollback()
        return False


def verify_migrations(conn: sqlite3.Connection):
    """Verify all expected columns exist"""
    cursor = conn.cursor()

    # Check migration 003 columns
    cursor.execute("SELECT COUNT(*) FROM pragma_table_info('task') WHERE name = 'task_type'")
    if cursor.fetchone()[0] == 0:
        print("⚠️  Migration 003 not applied: task_type column missing")
        return False

    # Check migration 004 columns
    cursor.execute("SELECT COUNT(*) FROM pragma_table_info('task') WHERE name = 'requires_adr'")
    if cursor.fetchone()[0] == 0:
        print("⚠️  Migration 004 not applied: requires_adr column missing")
        return False

    print("✅ All migrations verified!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Apply database migrations to Obra",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--db-path',
        help="Path to SQLite database file (default: auto-detect from config)"
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help="Only verify migrations, don't apply"
    )

    args = parser.parse_args()

    # Get database path
    db_path = args.db_path or get_db_path()
    db_file = Path(db_path)

    if not db_file.exists():
        print(f"❌ Database not found: {db_path}")
        print(f"\nSearched at: {db_file.absolute()}")
        print("\nOptions:")
        print("  1. Create the database by running: python -m src.cli init")
        print("  2. Specify path with: --db-path /path/to/obra.db")
        sys.exit(1)

    print(f"📂 Database: {db_path}")
    print(f"📍 Location: {db_file.absolute()}\n")

    # Connect to database
    try:
        conn = sqlite3.connect(str(db_file))
    except sqlite3.Error as e:
        print(f"❌ Cannot connect to database: {e}")
        sys.exit(1)

    # Verify only mode
    if args.verify_only:
        success = verify_migrations(conn)
        conn.close()
        sys.exit(0 if success else 1)

    # Find migration files
    migrations_dir = Path("migrations/versions")
    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        sys.exit(1)

    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        print(f"❌ No migration files found in {migrations_dir}")
        sys.exit(1)

    print(f"Found {len(migration_files)} migration(s)\n")

    # Apply migrations in order
    success = True
    for migration_file in migration_files:
        if not apply_migration(conn, migration_file):
            success = False
            break

    # Verify
    print()
    verify_migrations(conn)

    # Cleanup
    conn.close()

    if success:
        print("\n✅ All migrations completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
