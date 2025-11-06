-- Agile Hierarchy Migration (ADR-013)
-- Adds TaskType enum support and Milestone model
-- Migration: v1.2 → v1.3.0

-- ============================================================================
-- Step 1: Add columns to task table
-- ============================================================================

-- Add task_type column (defaults to 'task' for existing tasks)
ALTER TABLE task ADD COLUMN task_type TEXT DEFAULT 'task' NOT NULL;

-- Add epic_id foreign key column
ALTER TABLE task ADD COLUMN epic_id INTEGER;

-- Add story_id foreign key column
ALTER TABLE task ADD COLUMN story_id INTEGER;

-- ============================================================================
-- Step 2: Create indexes for new task columns
-- ============================================================================

CREATE INDEX idx_task_type ON task(task_type);
CREATE INDEX idx_task_epic ON task(epic_id);
CREATE INDEX idx_task_story ON task(story_id);
CREATE INDEX idx_task_type_status ON task(task_type, status);

-- ============================================================================
-- Step 3: Create milestone table
-- ============================================================================

CREATE TABLE milestone (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    target_date DATETIME,
    achieved BOOLEAN DEFAULT 0 NOT NULL,
    achieved_at DATETIME,
    required_epic_ids JSON DEFAULT '[]' NOT NULL,
    milestone_metadata JSON DEFAULT '{}',
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (project_id) REFERENCES project_state(id)
);

-- ============================================================================
-- Step 4: Create indexes for milestone table
-- ============================================================================

CREATE INDEX idx_milestone_project_achieved ON milestone(project_id, achieved);
CREATE INDEX idx_milestone_project_id ON milestone(project_id);

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Verify task table columns
-- SELECT name, type FROM pragma_table_info('task') WHERE name IN ('task_type', 'epic_id', 'story_id');

-- Verify milestone table created
-- SELECT name FROM sqlite_master WHERE type='table' AND name='milestone';

-- Verify indexes created
-- SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='task' AND name LIKE 'idx_task_%';
-- SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='milestone';

-- ============================================================================
-- Rollback (if needed)
-- ============================================================================

-- To rollback this migration (use with caution):
-- DROP INDEX IF EXISTS idx_task_type;
-- DROP INDEX IF EXISTS idx_task_epic;
-- DROP INDEX IF EXISTS idx_task_story;
-- DROP INDEX IF EXISTS idx_task_type_status;
-- DROP INDEX IF EXISTS idx_milestone_project_achieved;
-- DROP INDEX IF EXISTS idx_milestone_project_id;
-- DROP TABLE IF EXISTS milestone;
-- ALTER TABLE task DROP COLUMN task_type;  -- Not supported in SQLite, requires table rebuild
-- ALTER TABLE task DROP COLUMN epic_id;    -- Not supported in SQLite, requires table rebuild
-- ALTER TABLE task DROP COLUMN story_id;   -- Not supported in SQLite, requires table rebuild
