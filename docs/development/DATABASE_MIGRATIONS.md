# Database Migrations with Alembic

This guide explains how to use Alembic for database schema migrations in the Claude Code Orchestrator project.

## Overview

Alembic is a database migration tool for SQLAlchemy. It allows us to:
- Version control database schema changes
- Create migrations automatically by detecting model changes
- Apply migrations to upgrade the database
- Rollback migrations to downgrade the database
- Maintain production databases without manual SQL

## Setup

Alembic is already configured for this project:

- **Configuration**: `alembic.ini` - Contains database URL and Alembic settings
- **Environment**: `alembic/env.py` - Imports models and configures migration context
- **Migrations**: `alembic/versions/` - Contains all migration scripts
- **Database URL**: `sqlite:///data/orchestrator.db` (from `config/default_config.yaml`)

## Common Commands

### Check Current Migration Status

```bash
# Activate virtual environment
source venv/bin/activate

# Check current database version
alembic current

# View migration history
alembic history
```

### Create a New Migration

When you modify models in `src/core/models.py`, create a migration:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Example:
alembic revision --autogenerate -m "Add user_preferences table"
```

Alembic will:
1. Compare current database schema with your models
2. Detect changes (new tables, columns, indexes, etc.)
3. Generate a migration script in `alembic/versions/`
4. Include both `upgrade()` and `downgrade()` functions

### Apply Migrations

```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Upgrade to specific version
alembic upgrade <revision_id>

# Example:
alembic upgrade 1a6a70f64ea3
```

### Rollback Migrations

```bash
# Downgrade one version
alembic downgrade -1

# Downgrade to base (empty database)
alembic downgrade base

# Downgrade to specific version
alembic downgrade <revision_id>
```

## Workflow

### Adding a New Model

1. **Define the model** in `src/core/models.py`:

```python
class NewFeature(Base):
    __tablename__ = 'new_feature'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
```

2. **Create migration**:

```bash
alembic revision --autogenerate -m "Add new_feature table"
```

3. **Review the generated migration** in `alembic/versions/`:

```python
def upgrade() -> None:
    # Verify auto-generated upgrade logic
    op.create_table('new_feature', ...)

def downgrade() -> None:
    # Verify auto-generated downgrade logic
    op.drop_table('new_feature')
```

4. **Apply migration**:

```bash
alembic upgrade head
```

### Modifying an Existing Model

1. **Update the model** in `src/core/models.py`:

```python
class Task(Base):
    __tablename__ = 'task'

    # ... existing columns ...

    # New column
    estimated_duration = Column(Integer, nullable=True)
```

2. **Create migration**:

```bash
alembic revision --autogenerate -m "Add estimated_duration to task"
```

3. **Review and test** the migration

4. **Apply migration**:

```bash
alembic upgrade head
```

## Migration Best Practices

### 1. Always Review Auto-Generated Migrations

Alembic's autogenerate is smart but not perfect. Always:
- Review the generated migration file
- Verify both upgrade() and downgrade() logic
- Test the migration on a copy of production data
- Check for data migration needs (not just schema changes)

### 2. Data Migrations

For complex changes involving data transformation:

```python
def upgrade() -> None:
    # Add new column (nullable initially)
    op.add_column('task', sa.Column('new_field', sa.String, nullable=True))

    # Migrate data
    connection = op.get_bind()
    connection.execute(
        text("UPDATE task SET new_field = 'default_value' WHERE new_field IS NULL")
    )

    # Make column non-nullable
    op.alter_column('task', 'new_field', nullable=False)
```

### 3. Irreversible Migrations

If a migration cannot be reversed (e.g., dropping a column), document it:

```python
def downgrade() -> None:
    # WARNING: This will lose data!
    op.drop_column('task', 'sensitive_data')
```

Or raise an error:

```python
def downgrade() -> None:
    raise NotImplementedError("Cannot reverse this migration without data loss")
```

### 4. Testing Migrations

Before deploying to production:

```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Test re-upgrade
alembic upgrade head
```

## Production Deployment

### Initial Setup (New Environment)

```bash
# 1. Install dependencies
pip install -r requirements.txt  # or use setup.py

# 2. Create data directory
mkdir -p data

# 3. Apply all migrations
alembic upgrade head
```

### Upgrading Production Database

```bash
# 1. Backup database
cp data/orchestrator.db data/orchestrator.db.backup

# 2. Check current version
alembic current

# 3. View pending migrations
alembic history

# 4. Apply migrations
alembic upgrade head

# 5. Verify application works
# (run tests, check logs, etc.)

# 6. If issues occur, rollback:
# alembic downgrade -1
# Restore from backup if needed
```

## Troubleshooting

### "Database is not under version control"

If you see this error, initialize Alembic:

```bash
# This stamps the database with the current version
alembic stamp head
```

### "Can't locate revision identified by X"

The database version doesn't match migration files:

```bash
# Check migration history
alembic history

# Stamp to a known version
alembic stamp <revision_id>
```

### "Target database is not up to date"

You have unapplied migrations:

```bash
# View pending migrations
alembic current
alembic history

# Apply them
alembic upgrade head
```

### Migration Conflicts

If multiple developers create migrations simultaneously:

1. Merge migration files (Git conflict)
2. Create a merge migration:

```bash
alembic merge <rev1> <rev2> -m "Merge migrations"
```

## StateManager Integration

The `StateManager` class (in `src/core/state.py`) currently uses:

```python
Base.metadata.create_all(self._engine)  # Line 105
```

This approach:
- ✅ Works for development and testing
- ❌ Not suitable for production (no version control)
- ❌ Cannot handle schema changes safely

With Alembic:
- ✅ Version-controlled schema changes
- ✅ Safe upgrades and rollbacks
- ✅ Production-ready migration workflow
- ✅ Audit trail of database changes

**Note**: `Base.metadata.create_all()` is still used in StateManager for backwards compatibility and testing. In production, always use Alembic migrations instead.

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- Project Configuration: `alembic.ini`
- Migration Environment: `alembic/env.py`
- Database Models: `src/core/models.py`
- Database Config: `config/default_config.yaml`

## Quick Reference

```bash
# Status
alembic current                                    # Show current version
alembic history                                    # Show migration history

# Create
alembic revision --autogenerate -m "message"       # Auto-generate migration
alembic revision -m "message"                      # Create empty migration

# Apply
alembic upgrade head                               # Upgrade to latest
alembic upgrade +1                                 # Upgrade one version
alembic upgrade <revision>                         # Upgrade to specific version

# Rollback
alembic downgrade -1                               # Downgrade one version
alembic downgrade base                             # Downgrade to empty database
alembic downgrade <revision>                       # Downgrade to specific version

# Other
alembic stamp head                                 # Mark database as current
alembic merge <rev1> <rev2> -m "message"          # Merge migrations
```
