-- Documentation Infrastructure Maintenance Migration (ADR-015)
-- Adds documentation metadata fields to task and milestone tables
-- Migration: v1.3 → v1.4.0

-- ============================================================================
-- Step 1: Add documentation columns to task table
-- ============================================================================

-- Add requires_adr column (indicates if epic requires ADR creation)
ALTER TABLE task ADD COLUMN requires_adr BOOLEAN DEFAULT 0 NOT NULL;

-- Add has_architectural_changes column (indicates architectural impact)
ALTER TABLE task ADD COLUMN has_architectural_changes BOOLEAN DEFAULT 0 NOT NULL;

-- Add changes_summary column (summary of changes for documentation)
ALTER TABLE task ADD COLUMN changes_summary TEXT NULL;

-- Add documentation_status column (pending/updated/skipped)
ALTER TABLE task ADD COLUMN documentation_status VARCHAR(20) DEFAULT 'pending' NOT NULL;

-- ============================================================================
-- Step 2: Create indexes for new task columns
-- ============================================================================

CREATE INDEX idx_task_documentation_status ON task(documentation_status);
CREATE INDEX idx_task_requires_adr ON task(requires_adr) WHERE requires_adr = 1;

-- ============================================================================
-- Step 3: Add version column to milestone table
-- ============================================================================

-- Add version column (e.g., "v1.4.0" for version tracking)
ALTER TABLE milestone ADD COLUMN version VARCHAR(20) NULL;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Verify task table columns
-- SELECT name, type, dflt_value FROM pragma_table_info('task')
--   WHERE name IN ('requires_adr', 'has_architectural_changes', 'changes_summary', 'documentation_status');

-- Verify milestone table column
-- SELECT name, type FROM pragma_table_info('milestone') WHERE name = 'version';

-- Verify indexes created
-- SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='task'
--   AND name IN ('idx_task_documentation_status', 'idx_task_requires_adr');

-- ============================================================================
-- Rollback (if needed)
-- ============================================================================

-- To rollback this migration (use with caution):
-- DROP INDEX IF EXISTS idx_task_documentation_status;
-- DROP INDEX IF EXISTS idx_task_requires_adr;
-- ALTER TABLE milestone DROP COLUMN version;              -- Not supported in SQLite, requires table rebuild
-- ALTER TABLE task DROP COLUMN requires_adr;              -- Not supported in SQLite, requires table rebuild
-- ALTER TABLE task DROP COLUMN has_architectural_changes; -- Not supported in SQLite, requires table rebuild
-- ALTER TABLE task DROP COLUMN changes_summary;           -- Not supported in SQLite, requires table rebuild
-- ALTER TABLE task DROP COLUMN documentation_status;      -- Not supported in SQLite, requires table rebuild

-- ============================================================================
-- Notes
-- ============================================================================

-- SQLite Limitations:
-- - ALTER TABLE DROP COLUMN is not supported in SQLite < 3.35.0
-- - To rollback, would need to recreate tables (see SQLite docs)
-- - For production use, consider using Alembic for more robust migrations

-- Documentation Status Values:
-- - 'pending': Documentation update not started
-- - 'updated': Documentation has been updated
-- - 'skipped': Documentation update not required for this task

-- ADR Creation Workflow:
-- 1. Epic marked with requires_adr=True or has_architectural_changes=True
-- 2. On epic completion, DocumentationManager creates maintenance task
-- 3. Maintenance task includes ADR creation in prompt if suggested
-- 4. After completion, documentation_status updated to 'updated'
