# Database Migration Guide

This guide explains how to apply database migrations to your Obra installation.

## Current Migrations

### Migration 003: Agile Work Hierarchy (v1.3.0)
**File**: `migrations/versions/003_agile_hierarchy.sql`
**Status**: Required for v1.3.0+
**Adds**: Epic, Story, Task hierarchy support

### Migration 004: Documentation Infrastructure (v1.4.0)
**File**: `migrations/versions/004_documentation_fields.sql`
**Status**: Required for v1.4.0+
**Adds**: ADR tracking and documentation maintenance fields

## How to Apply Migrations

### Option 1: Using SQLite CLI (Recommended)

If you're using the default SQLite database:

```bash
# Navigate to project root
cd /home/omarwsl/projects/claude_code_orchestrator

# Find your database file (check config/config.yaml)
# Default location: runtime/obra.db

# Apply migration 004
sqlite3 runtime/obra.db < migrations/versions/004_documentation_fields.sql

# Verify the migration
sqlite3 runtime/obra.db "SELECT name, type FROM pragma_table_info('task') WHERE name IN ('requires_adr', 'has_architectural_changes', 'changes_summary', 'documentation_status');"
```

### Option 2: Using Python Script

Create and run this helper script:

```python
#!/usr/bin/env python3
"""Apply pending database migrations"""

import sqlite3
import sys
from pathlib import Path

# Database path (update if needed)
DB_PATH = "runtime/obra.db"

def apply_migration(db_path: str, migration_file: str):
    """Apply SQL migration file to database"""

    # Read migration SQL
    migration_sql = Path(migration_file).read_text()

    # Connect and execute
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(migration_sql)
        conn.commit()
        print(f"✅ Applied migration: {migration_file}")
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    # Apply migration 004
    apply_migration(DB_PATH, "migrations/versions/004_documentation_fields.sql")
    print("✅ All migrations applied successfully!")
```

Save as `scripts/apply_migrations.py` and run:
```bash
python scripts/apply_migrations.py
```

### Option 3: Manual SQL Execution

1. Open your database with your preferred SQLite tool
2. Copy the contents of `migrations/versions/004_documentation_fields.sql`
3. Execute the SQL statements
4. Verify with the verification queries at the end of the file

## Verification

After applying migration 004, verify the columns exist:

```bash
sqlite3 runtime/obra.db "SELECT name, type, dflt_value FROM pragma_table_info('task') WHERE name IN ('requires_adr', 'has_architectural_changes', 'changes_summary', 'documentation_status');"
```

Expected output:
```
requires_adr|BOOLEAN|0
has_architectural_changes|BOOLEAN|0
changes_summary|TEXT|
documentation_status|VARCHAR(20)|'pending'
```

## Troubleshooting

### Error: "table task has no column named requires_adr"

**Cause**: Migration 004 has not been applied
**Solution**: Apply migration 004 using one of the methods above

### Error: "duplicate column name"

**Cause**: Migration 004 has already been applied
**Solution**: No action needed, your database is up to date

### Database Location Unknown

Check your configuration file:
```bash
grep -A5 "database:" config/config.yaml
```

Or check the default location:
```bash
ls -lh runtime/obra.db
```

## Migration History

| Version | Migration | Required | Status |
|---------|-----------|----------|--------|
| v1.3.0  | 003_agile_hierarchy.sql | ✅ Yes | Required for epic/story support |
| v1.4.0  | 004_documentation_fields.sql | ✅ Yes | Required for ADR tracking |

## PostgreSQL Users

If you're using PostgreSQL instead of SQLite:

1. The SQL syntax is similar but may need minor adjustments
2. Use `psql` instead of `sqlite3`:
   ```bash
   psql -h localhost -U obra_user -d obra_db -f migrations/versions/004_documentation_fields.sql
   ```
3. Verify with PostgreSQL's `\d task` command

## Future Migrations

For new migrations, always:
1. Check the `migrations/versions/` directory
2. Apply migrations in numerical order (003, then 004, etc.)
3. Verify each migration before moving to the next
4. Back up your database before applying migrations

## Automated Migration (Coming Soon)

A CLI command for automated migrations is planned:
```bash
obra migrate apply    # Apply all pending migrations
obra migrate status   # Check migration status
obra migrate verify   # Verify database schema
```

---

**Last Updated**: 2025-11-11
**Current Version**: v1.5.0
