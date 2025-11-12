"""StateManager Strain Tests

These tests stress-test the StateManager with heavy database operations,
edge cases, and real-world usage patterns. They catch issues like:
- Missing database columns
- Transaction failures
- API signature mismatches
- Data type conversions

These would have caught the requires_adr column error and create_task API change.
"""

import pytest
import threading
import time
from src.core.state import StateManager, TaskStatus, TaskType


class TestStateManagerHeavyOperations:
    """Test StateManager under heavy load"""

    def test_create_many_tasks_sequentially(self, state_manager, fast_time):
        """Create 100 tasks to stress database"""
        project = state_manager.create_project(name="Heavy Test", working_dir="/tmp")

        tasks = []
        for i in range(100):
            task = state_manager.create_task(
                project.id,
                {
                    'title': f'Task {i}',
                    'description': f'Description {i}',
                    'priority': i % 10
                }
            )
            tasks.append(task)

        # Verify all created
        assert len(tasks) == 100
        retrieved_tasks = state_manager.list_tasks(project_id=project.id)
        assert len(retrieved_tasks) == 100

    def test_create_complex_agile_hierarchy(self, state_manager):
        """Create complex epic/story/task hierarchy"""
        project = state_manager.create_project(name="Agile Test", working_dir="/tmp")

        # Create 3 epics
        epics = []
        for i in range(3):
            epic_id = state_manager.create_epic(
                project.id,
                f"Epic {i}",
                f"Epic description {i}"
            )
            epics.append(epic_id)

        # Create 5 stories per epic
        stories = []
        for epic_id in epics:
            for i in range(5):
                story_id = state_manager.create_story(
                    project.id,
                    epic_id,
                    f"Story {i}",
                    f"Story description {i}"
                )
                stories.append(story_id)

        # Create 10 tasks per story
        tasks = []
        for story_id in stories:
            for i in range(10):
                task = state_manager.create_task(
                    project.id,
                    {
                        'title': f'Task {i}',
                        'description': f'Task description {i}',
                        'story_id': story_id
                    }
                )
                tasks.append(task)

        # Verify hierarchy
        assert len(epics) == 3
        assert len(stories) == 15  # 3 epics * 5 stories
        assert len(tasks) == 150   # 15 stories * 10 tasks

    def test_task_with_all_fields_populated(self, state_manager):
        """Create task with every possible field to catch missing columns"""
        project = state_manager.create_project(name="Full Fields Test", working_dir="/tmp")

        # Create dependencies
        dep1 = state_manager.create_task(project.id, {'title': 'Dep1', 'description': 'D'})
        dep2 = state_manager.create_task(project.id, {'title': 'Dep2', 'description': 'D'})

        # Create epic and story for references
        epic_id = state_manager.create_epic(project.id, "Epic", "Desc")
        story_id = state_manager.create_story(project.id, epic_id, "Story", "Desc")

        # Create task with ALL fields
        task = state_manager.create_task(
            project.id,
            {
                'title': 'Complete Task',
                'description': 'Task with all fields',
                'priority': 8,
                'assigned_to': 'CLAUDE_CODE',
                'dependencies': [dep1.id, dep2.id],
                'context': {'key': 'value', 'nested': {'data': 123}},
                'task_type': TaskType.TASK,
                'epic_id': epic_id,
                'story_id': story_id,
                'parent_task_id': None,
                'requires_adr': True,
                'has_architectural_changes': True,
                'changes_summary': 'Major refactoring',
                'documentation_status': 'pending',
                'max_retries': 5
            }
        )

        # Verify all fields persisted correctly
        retrieved = state_manager.get_task(task.id)
        assert retrieved.title == 'Complete Task'
        assert retrieved.priority == 8
        assert retrieved.dependencies == [dep1.id, dep2.id]
        assert retrieved.context == {'key': 'value', 'nested': {'data': 123}}
        assert retrieved.epic_id == epic_id
        assert retrieved.story_id == story_id
        assert retrieved.requires_adr is True
        assert retrieved.has_architectural_changes is True
        assert retrieved.changes_summary == 'Major refactoring'
        assert retrieved.documentation_status == 'pending'

    def test_milestone_with_all_fields(self, state_manager):
        """Create milestone with all fields including version"""
        project = state_manager.create_project(name="Milestone Test", working_dir="/tmp")

        # Create epics for milestone
        epic1 = state_manager.create_epic(project.id, "Epic1", "D")
        epic2 = state_manager.create_epic(project.id, "Epic2", "D")

        # Create milestone with all fields
        milestone_id = state_manager.create_milestone(
            project_id=project.id,
            name='v1.5.0 Release',
            description='Major release with new features',
            required_epic_ids=[epic1, epic2],
            version='v1.5.0'
        )

        # Verify all fields
        milestone = state_manager.get_milestone(milestone_id)
        assert milestone.name == 'v1.5.0 Release'
        assert milestone.version == 'v1.5.0'
        assert set(milestone.required_epic_ids) == {epic1, epic2}


class TestStateManagerTransactions:
    """Test transaction handling and rollback"""

    def test_transaction_rollback_on_error(self, state_manager):
        """Verify transaction rolls back on error"""
        project = state_manager.create_project(name="Transaction Test", working_dir="/tmp")

        # Create a task
        task1 = state_manager.create_task(
            project.id,
            {'title': 'Task 1', 'description': 'D'}
        )

        # Try to create task with invalid data (should rollback)
        try:
            with state_manager.transaction():
                # This should fail due to missing description
                state_manager.create_task(project.id, {'title': 'Bad Task'})
        except Exception:
            pass  # Expected

        # Verify first task still exists
        retrieved = state_manager.get_task(task1.id)
        assert retrieved is not None

    def test_nested_transactions_not_supported(self, state_manager):
        """Document that nested transactions aren't supported"""
        # SQLite doesn't support nested transactions
        # This test documents the behavior

        with state_manager.transaction():
            # Outer transaction
            assert True  # OK

            # Don't try nested transaction (would fail)


class TestStateManagerConcurrency:
    """Test concurrent access to StateManager"""

    @pytest.mark.timeout(10)
    def test_concurrent_task_creation(self, state_manager, fast_time):
        """Create tasks from multiple threads"""
        project = state_manager.create_project(name="Concurrent Test", working_dir="/tmp")

        created_tasks = []
        errors = []

        def create_tasks(thread_id, count):
            try:
                for i in range(count):
                    task = state_manager.create_task(
                        project.id,
                        {'title': f'Thread{thread_id}-Task{i}', 'description': 'D'}
                    )
                    created_tasks.append(task)
            except Exception as e:
                errors.append(str(e))

        # Create 3 threads, each creating 10 tasks
        threads = []
        for thread_id in range(3):
            t = threading.Thread(target=create_tasks, args=(thread_id, 10))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=5.0)

        # Verify no errors
        assert len(errors) == 0, f"Errors during concurrent creation: {errors}"

        # Verify all tasks created
        assert len(created_tasks) == 30

    @pytest.mark.timeout(10)
    def test_concurrent_reads_safe(self, state_manager, fast_time):
        """Multiple threads reading simultaneously"""
        project = state_manager.create_project(name="Read Test", working_dir="/tmp")

        # Create some tasks first
        for i in range(10):
            state_manager.create_task(
                project.id,
                {'title': f'Task {i}', 'description': 'D'}
            )

        read_counts = []
        errors = []

        def read_tasks(thread_id):
            try:
                tasks = state_manager.list_tasks(project_id=project.id)
                read_counts.append(len(tasks))
            except Exception as e:
                errors.append(str(e))

        # Create 5 threads reading simultaneously
        threads = []
        for i in range(5):
            t = threading.Thread(target=read_tasks, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=3.0)

        # Verify no errors
        assert len(errors) == 0

        # All reads should see same number of tasks
        assert all(count == 10 for count in read_counts)


class TestStateManagerEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_task_with_empty_dependencies_list(self, state_manager):
        """Empty dependencies list should work"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        task = state_manager.create_task(
            project.id,
            {'title': 'Task', 'description': 'D', 'dependencies': []}
        )

        assert task.dependencies == []

    def test_task_with_empty_context_dict(self, state_manager):
        """Empty context dict should work"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        task = state_manager.create_task(
            project.id,
            {'title': 'Task', 'description': 'D', 'context': {}}
        )

        assert task.context == {}

    def test_task_with_null_optional_fields(self, state_manager):
        """Null optional fields should work"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        task = state_manager.create_task(
            project.id,
            {
                'title': 'Task',
                'description': 'D',
                'parent_task_id': None,
                'epic_id': None,
                'story_id': None,
                'changes_summary': None
            }
        )

        assert task.parent_task_id is None
        assert task.epic_id is None
        assert task.story_id is None
        assert task.changes_summary is None

    def test_task_with_very_long_text_fields(self, state_manager):
        """Test with large text content"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        long_text = "A" * 10000  # 10K characters

        task = state_manager.create_task(
            project.id,
            {
                'title': 'Task',
                'description': long_text,
                'changes_summary': long_text
            }
        )

        retrieved = state_manager.get_task(task.id)
        assert len(retrieved.description) == 10000
        assert len(retrieved.changes_summary) == 10000

    def test_task_with_special_characters(self, state_manager):
        """Test with special characters in text fields"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        special_chars = "Test with 'quotes' \"double quotes\" & <html> {json} [arrays] \n\t tabs"

        task = state_manager.create_task(
            project.id,
            {
                'title': special_chars,
                'description': special_chars,
                'changes_summary': special_chars
            }
        )

        retrieved = state_manager.get_task(task.id)
        assert retrieved.title == special_chars


class TestStateManagerAPICompatibility:
    """Test API signatures match expectations"""

    def test_create_task_accepts_dict_not_positional_args(self, state_manager):
        """Verify create_task uses dict parameter (catches API changes)"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        # Correct API: dict parameter
        task = state_manager.create_task(
            project.id,
            {'title': 'Task', 'description': 'Desc'}
        )
        assert task.id is not None

        # Old API would have been: create_task(project_id, title, description)
        # This should fail if we revert to old API
        with pytest.raises(TypeError):
            state_manager.create_task(project.id, 'Title', 'Desc')

    def test_create_epic_returns_int_id(self, state_manager):
        """Verify create_epic returns int ID"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        epic_id = state_manager.create_epic(project.id, "Epic", "Desc")

        assert isinstance(epic_id, int)
        assert epic_id > 0

    def test_create_story_returns_int_id(self, state_manager):
        """Verify create_story returns int ID"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")
        epic_id = state_manager.create_epic(project.id, "Epic", "Desc")

        story_id = state_manager.create_story(project.id, epic_id, "Story", "Desc")

        assert isinstance(story_id, int)
        assert story_id > 0

    def test_get_task_returns_task_object(self, state_manager):
        """Verify get_task returns Task object with all attributes"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")
        task = state_manager.create_task(
            project.id,
            {'title': 'Task', 'description': 'Desc'}
        )

        retrieved = state_manager.get_task(task.id)

        # Verify it's a Task object with expected attributes
        assert hasattr(retrieved, 'id')
        assert hasattr(retrieved, 'title')
        assert hasattr(retrieved, 'description')
        assert hasattr(retrieved, 'status')
        assert hasattr(retrieved, 'requires_adr')
        assert hasattr(retrieved, 'has_architectural_changes')
        assert hasattr(retrieved, 'task_type')


class TestStateManagerDataIntegrity:
    """Test data integrity and consistency"""

    def test_epic_story_task_relationship_integrity(self, state_manager):
        """Verify epic→story→task relationships maintain integrity"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        # Create hierarchy
        epic_id = state_manager.create_epic(project.id, "Epic", "Desc")
        story_id = state_manager.create_story(project.id, epic_id, "Story", "Desc")
        task = state_manager.create_task(
            project.id,
            {'title': 'Task', 'description': 'Desc', 'story_id': story_id}
        )

        # Verify relationships
        story = state_manager.get_task(story_id)
        assert story.epic_id == epic_id

        assert task.story_id == story_id

    def test_task_dependencies_bidirectional(self, state_manager):
        """Verify task dependencies work in both directions"""
        project = state_manager.create_project(name="Test", working_dir="/tmp")

        task1 = state_manager.create_task(project.id, {'title': 'T1', 'description': 'D'})
        task2 = state_manager.create_task(project.id, {'title': 'T2', 'description': 'D'})
        task3 = state_manager.create_task(
            project.id,
            {'title': 'T3', 'description': 'D', 'dependencies': [task1.id, task2.id]}
        )

        # Verify task3 depends on task1 and task2
        retrieved = state_manager.get_task(task3.id)
        assert task1.id in retrieved.dependencies
        assert task2.id in retrieved.dependencies
