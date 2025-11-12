"""Database Schema Validation Tests

These tests verify that the database schema matches expectations and that
all migrations have been applied correctly. They catch issues like missing
columns, incorrect types, and missing indexes.

This would have caught: "table task has no column named requires_adr"
"""

import pytest
import sqlite3
from pathlib import Path
from src.core.state import StateManager


class TestDatabaseSchema:
    """Verify database schema is correct"""

    @pytest.fixture
    def db_connection(self, state_manager):
        """Get direct database connection for schema checks"""
        # Get database URL from state manager
        db_url = state_manager._database_url
        if 'sqlite:///' in db_url:
            db_path = db_url.replace('sqlite:///', '')
            conn = sqlite3.connect(db_path)
            yield conn
            conn.close()
        else:
            pytest.skip("Only SQLite databases supported for schema tests")

    def test_task_table_has_all_required_columns(self, db_connection):
        """Verify task table has all columns from all migrations"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM pragma_table_info('task')")
        columns = {row[0] for row in cursor.fetchall()}

        # Base columns
        required_base = {
            'id', 'created_at', 'updated_at', 'project_id', 'parent_task_id',
            'title', 'description', 'status', 'assigned_to', 'priority',
            'dependencies', 'context', 'result', 'task_metadata',
            'retry_count', 'max_retries', 'started_at', 'completed_at', 'is_deleted'
        }

        # Migration 003 (Agile Hierarchy) columns
        required_agile = {'task_type', 'epic_id', 'story_id'}

        # Migration 004 (Documentation Infrastructure) columns
        required_docs = {
            'requires_adr', 'has_architectural_changes',
            'changes_summary', 'documentation_status'
        }

        all_required = required_base | required_agile | required_docs

        missing = all_required - columns
        assert not missing, f"Missing columns in task table: {missing}"

    def test_task_documentation_columns_types(self, db_connection):
        """Verify documentation columns have correct types (Migration 004)"""
        cursor = db_connection.cursor()
        cursor.execute(
            "SELECT name, type, dflt_value FROM pragma_table_info('task') "
            "WHERE name IN ('requires_adr', 'has_architectural_changes', 'changes_summary', 'documentation_status')"
        )
        columns_info = {row[0]: {'type': row[1], 'default': row[2]} for row in cursor.fetchall()}

        assert 'requires_adr' in columns_info, "requires_adr column missing"
        assert 'BOOLEAN' in columns_info['requires_adr']['type'].upper()
        assert columns_info['requires_adr']['default'] == '0'

        assert 'has_architectural_changes' in columns_info
        assert 'BOOLEAN' in columns_info['has_architectural_changes']['type'].upper()

        assert 'changes_summary' in columns_info
        assert 'TEXT' in columns_info['changes_summary']['type'].upper()

        assert 'documentation_status' in columns_info
        assert 'VARCHAR' in columns_info['documentation_status']['type'].upper()

    def test_task_agile_columns_exist(self, db_connection):
        """Verify agile hierarchy columns exist (Migration 003)"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM pragma_table_info('task') WHERE name IN ('task_type', 'epic_id', 'story_id')")
        columns = {row[0] for row in cursor.fetchall()}

        assert 'task_type' in columns, "task_type column missing (Migration 003)"
        assert 'epic_id' in columns, "epic_id column missing (Migration 003)"
        assert 'story_id' in columns, "story_id column missing (Migration 003)"

    def test_milestone_table_has_version_column(self, db_connection):
        """Verify milestone table has version column (Migration 004)"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM pragma_table_info('milestone') WHERE name = 'version'")
        result = cursor.fetchone()

        assert result is not None, "milestone.version column missing (Migration 004)"

    def test_task_indexes_exist(self, db_connection):
        """Verify required indexes exist"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='task'")
        indexes = {row[0] for row in cursor.fetchall()}

        # Migration 004 indexes
        required_indexes = {
            'idx_task_documentation_status',
            'idx_task_requires_adr'
        }

        missing = required_indexes - indexes
        assert not missing, f"Missing indexes on task table: {missing}"

    def test_all_tables_exist(self, db_connection):
        """Verify all expected tables exist"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = {row[0] for row in cursor.fetchall()}

        required_tables = {'project', 'task', 'milestone', 'session'}
        missing = required_tables - tables
        assert not missing, f"Missing database tables: {missing}"


class TestDatabaseOperations:
    """Test database operations work with current schema"""

    def test_create_task_with_documentation_fields(self, state_manager):
        """Verify task creation with Migration 004 fields works"""
        # Create project first
        project = state_manager.create_project(name="Test Project", working_dir="/tmp")

        # Create task with documentation fields
        task = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Test Task',
                'description': 'Test description',
                'requires_adr': True,
                'has_architectural_changes': True,
                'changes_summary': 'Added new feature',
                'documentation_status': 'pending'
            }
        )

        assert task.id is not None
        assert task.requires_adr is True
        assert task.has_architectural_changes is True
        assert task.changes_summary == 'Added new feature'
        assert task.documentation_status == 'pending'

    def test_create_epic_with_agile_fields(self, state_manager):
        """Verify epic creation with Migration 003 fields works"""
        project = state_manager.create_project(name="Test Project", working_dir="/tmp")

        epic_id = state_manager.create_epic(
            project_id=project.id,
            title='Test Epic',
            description='Test epic description'
        )

        epic = state_manager.get_task(epic_id)
        assert epic.task_type.value == 'epic'

    def test_create_story_with_epic_reference(self, state_manager):
        """Verify story creation with epic_id works"""
        project = state_manager.create_project(name="Test Project", working_dir="/tmp")
        epic_id = state_manager.create_epic(project.id, "Epic", "Desc")

        story_id = state_manager.create_story(
            project_id=project.id,
            epic_id=epic_id,
            title='Test Story',
            description='Story description'
        )

        story = state_manager.get_task(story_id)
        assert story.task_type.value == 'story'
        assert story.epic_id == epic_id

    def test_milestone_with_version(self, state_manager):
        """Verify milestone creation with version field works"""
        project = state_manager.create_project(name="Test Project", working_dir="/tmp")
        epic_id = state_manager.create_epic(project.id, "Epic", "Desc")

        milestone_id = state_manager.create_milestone(
            project_id=project.id,
            name='v1.5.0 Release',
            description='Release milestone',
            required_epic_ids=[epic_id],
            version='v1.5.0'
        )

        milestone = state_manager.get_milestone(milestone_id)
        assert milestone.version == 'v1.5.0'


class TestMigrationVerification:
    """Verify migrations are applied in production"""

    def test_migration_003_applied(self, state_manager):
        """Verify Migration 003 (Agile Hierarchy) is applied"""
        # Try to create an epic - should work if migration applied
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        try:
            epic_id = state_manager.create_epic(project.id, "Test", "Desc")
            assert epic_id > 0, "Epic creation should succeed"
        except Exception as e:
            pytest.fail(f"Migration 003 not applied: {e}")

    def test_migration_004_applied(self, state_manager):
        """Verify Migration 004 (Documentation Infrastructure) is applied"""
        # Try to create task with requires_adr - should work if migration applied
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        try:
            task = state_manager.create_task(
                project.id,
                {
                    'title': 'Test',
                    'description': 'Desc',
                    'requires_adr': True
                }
            )
            assert task.requires_adr is True
        except Exception as e:
            pytest.fail(f"Migration 004 not applied: {e}")


class TestDatabaseConstraints:
    """Test database constraints and integrity"""

    def test_foreign_key_constraint_project_to_task(self, state_manager):
        """Verify foreign key relationships work"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")
        task = state_manager.create_task(
            project.id,
            {'title': 'Test', 'description': 'Desc'}
        )

        # Verify task is linked to project
        retrieved_task = state_manager.get_task(task.id)
        assert retrieved_task.project_id == project.id

    def test_task_dependencies_json_field(self, state_manager):
        """Verify dependencies field handles JSON correctly"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        # Create tasks with dependencies
        task1 = state_manager.create_task(
            project.id,
            {'title': 'Task 1', 'description': 'Desc'}
        )
        task2 = state_manager.create_task(
            project.id,
            {'title': 'Task 2', 'description': 'Desc', 'dependencies': [task1.id]}
        )

        retrieved = state_manager.get_task(task2.id)
        assert task1.id in retrieved.dependencies

    def test_task_context_json_field(self, state_manager):
        """Verify context field handles JSON correctly"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        task = state_manager.create_task(
            project.id,
            {
                'title': 'Test',
                'description': 'Desc',
                'context': {'key': 'value', 'nested': {'data': 123}}
            }
        )

        retrieved = state_manager.get_task(task.id)
        assert retrieved.context == {'key': 'value', 'nested': {'data': 123}}
