#!/usr/bin/env python3
"""Fix task_type enum values in database.

This script ensures existing tasks have proper task_type values
that match the TaskType enum expectations.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine, text
from core.config import Config

def fix_task_type_enum():
    """Fix task_type column values to match enum."""

    # Load config
    config = Config.load()

    # Get database URL
    db_url = config.get('database.url', 'sqlite:///orchestrator.db')

    print(f"Connecting to database: {db_url}")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Check if task_type column exists
        result = conn.execute(text(
            "SELECT COUNT(*) FROM pragma_table_info('task') WHERE name='task_type'"
        ))
        col_exists = result.scalar() > 0

        if not col_exists:
            print("task_type column doesn't exist yet, creating it...")
            # Apply the migration SQL
            with open('migrations/versions/003_agile_hierarchy.sql', 'r') as f:
                migration_sql = f.read()

            # Execute each statement
            for statement in migration_sql.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        conn.execute(text(statement))
                    except Exception as e:
                        # Skip errors for already existing columns
                        if 'duplicate column' not in str(e).lower():
                            print(f"Warning: {e}")

            conn.commit()
            print("Migration applied successfully!")
        else:
            print("task_type column already exists")

        # Check current task_type values
        result = conn.execute(text("SELECT DISTINCT task_type FROM task"))
        existing_types = [row[0] for row in result]
        print(f"Existing task_type values: {existing_types}")

        # Update any NULL values to 'task'
        result = conn.execute(text(
            "UPDATE task SET task_type = 'task' WHERE task_type IS NULL"
        ))
        if result.rowcount > 0:
            print(f"Updated {result.rowcount} NULL task_type values to 'task'")

        # Ensure all values are lowercase (enum values are lowercase)
        for old_val in ['TASK', 'EPIC', 'STORY', 'SUBTASK']:
            result = conn.execute(text(
                f"UPDATE task SET task_type = '{old_val.lower()}' WHERE task_type = '{old_val}'"
            ))
            if result.rowcount > 0:
                print(f"Updated {result.rowcount} {old_val} values to {old_val.lower()}")

        conn.commit()

        # Verify final state
        result = conn.execute(text("SELECT task_type, COUNT(*) FROM task GROUP BY task_type"))
        print("\nFinal task_type distribution:")
        for row in result:
            print(f"  {row[0]}: {row[1]} tasks")

    print("\n✓ Database fixed successfully!")

if __name__ == '__main__':
    fix_task_type_enum()
