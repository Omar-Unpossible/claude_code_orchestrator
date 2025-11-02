"""Tests for core infrastructure (exceptions, config, models, state)."""

import pytest
import os
import tempfile
from pathlib import Path
from datetime import datetime

from src.core.exceptions import *
from src.core.config import Config
from src.core.models import *
from src.core.state import StateManager


class TestCoreExceptions:
    """Test core exception hierarchy."""

    def test_orchestrator_exception_basic(self):
        """Test basic exception creation."""
        exc = OrchestratorException(
            "Test error",
            context={'key': 'value'},
            recovery="Do something"
        )
        assert str(exc) == "Test error"
        assert exc.context_data == {'key': 'value'}
        assert exc.recovery_suggestion == "Do something"

    def test_exception_to_dict(self):
        """Test exception serialization."""
        exc = DatabaseException(
            operation='test_op',
            details='Test details'
        )
        data = exc.to_dict()
        assert data['type'] == 'DatabaseException'
        assert 'test_op' in data['message']
        assert exc.recovery_suggestion is not None

    def test_database_exception(self):
        """Test DatabaseException."""
        exc = DatabaseException(
            operation='insert',
            details='Connection lost'
        )
        assert 'insert' in str(exc)
        assert exc.context_data['operation'] == 'insert'

    def test_transaction_exception(self):
        """Test TransactionException."""
        exc = TransactionException(
            reason='Deadlock',
            operations=['op1', 'op2']
        )
        assert 'Deadlock' in str(exc)
        assert exc.context_data['operations'] == ['op1', 'op2']

    def test_checkpoint_exception(self):
        """Test CheckpointException."""
        exc = CheckpointException(
            operation='restore',
            checkpoint_id='chk_123',
            details='Not found'
        )
        assert 'chk_123' in str(exc)
        assert exc.context_data['checkpoint_id'] == 'chk_123'

    def test_config_validation_exception(self):
        """Test ConfigValidationException."""
        exc = ConfigValidationException(
            config_key='agent.type',
            expected='string',
            got='int'
        )
        assert 'agent.type' in str(exc)
        assert exc.context_data['expected'] == 'string'

    def test_config_not_found_exception(self):
        """Test ConfigNotFoundException."""
        exc = ConfigNotFoundException(
            config_path='/path/to/config.yaml'
        )
        assert '/path/to/config.yaml' in str(exc)

    def test_response_incomplete_exception(self):
        """Test ResponseIncompleteException."""
        exc = ResponseIncompleteException(
            reason='Code block not closed',
            response_preview='def main():'
        )
        assert 'Code block not closed' in str(exc)

    def test_quality_too_low_exception(self):
        """Test QualityTooLowException."""
        exc = QualityTooLowException(
            quality_score=45,
            threshold=70,
            issues=['Tests failed']
        )
        assert '45' in str(exc)
        assert exc.context_data['threshold'] == 70

    def test_task_dependency_error(self):
        """Test TaskDependencyError."""
        exc = TaskDependencyError(
            task_id='task-123',
            dependency_chain=['task-123', 'task-456', 'task-123']
        )
        assert 'task-123' in str(exc)
        assert 'circular' in exc.recovery_suggestion.lower()

    def test_breakpoint_triggered(self):
        """Test BreakpointTriggered."""
        exc = BreakpointTriggered(
            reason='Low confidence',
            task_id='task-123',
            context_info={'confidence': 25}
        )
        assert 'Low confidence' in str(exc)
        assert exc.context_data['confidence'] == 25


class TestConfiguration:
    """Test configuration management."""

    @pytest.fixture(autouse=True)
    def reset_config(self):
        """Reset config singleton before each test."""
        Config.reset()
        yield
        Config.reset()

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
llm:
  model: test-model
  temperature: 0.5

agent:
  type: test-agent
  timeout: 60
            """)
            path = f.name

        yield path
        os.unlink(path)

    def test_load_config_defaults(self):
        """Test loading with defaults only."""
        config = Config.load(defaults_only=True)
        assert config is not None

    def test_load_config_from_file(self, temp_config_file):
        """Test loading config from file."""
        config = Config.load(temp_config_file)
        assert config.get('llm.model') == 'test-model'
        assert config.get('llm.temperature') == 0.5

    def test_dot_notation_access(self, temp_config_file):
        """Test dot notation access."""
        config = Config.load(temp_config_file)
        assert config.get('agent.type') == 'test-agent'
        assert config.get('agent.timeout') == 60
        assert config.get('missing.key', 'default') == 'default'

    def test_set_config_value(self):
        """Test setting config values."""
        config = Config.load(defaults_only=True)
        config.set('test.key', 'test_value')
        assert config.get('test.key') == 'test_value'

    def test_env_var_override(self, temp_config_file):
        """Test environment variable override."""
        os.environ['ORCHESTRATOR_AGENT_TYPE'] = 'override-agent'
        try:
            config = Config.load(temp_config_file)
            assert config.get('agent.type') == 'override-agent'
        finally:
            del os.environ['ORCHESTRATOR_AGENT_TYPE']

    def test_secret_sanitization(self):
        """Test that secrets are sanitized."""
        config = Config.load(defaults_only=True)
        config.set('agent.ssh.key_path', '/secret/key')
        config.set('database.password', 'secret123')

        exported = config.export(sanitize_secrets=True)
        # Secrets should be sanitized
        assert 'secret123' not in str(exported)

    def test_get_llm_config(self, temp_config_file):
        """Test getting LLM config section."""
        config = Config.load(temp_config_file)
        llm_config = config.get_llm_config()
        assert llm_config['model'] == 'test-model'
        assert llm_config['temperature'] == 0.5

    def test_get_agent_config(self, temp_config_file):
        """Test getting agent config section."""
        config = Config.load(temp_config_file)
        agent_config = config.get_agent_config()
        assert agent_config['type'] == 'test-agent'

    def test_malformed_yaml_raises(self):
        """Test that malformed YAML raises exception."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            path = f.name

        try:
            with pytest.raises(ConfigException):
                Config.load(path)
        finally:
            os.unlink(path)


class TestDatabaseModels:
    """Test SQLAlchemy models."""

    @pytest.fixture
    def session(self):
        """Create in-memory database session."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        yield session

        session.close()

    def test_create_project(self, session):
        """Test creating a project."""
        project = ProjectState(
            project_name='test-project',
            description='Test project',
            working_directory='/tmp/test',
            status=ProjectStatus.ACTIVE
        )
        session.add(project)
        session.commit()

        assert project.id is not None
        assert project.project_name == 'test-project'
        assert project.created_at is not None

    def test_create_task(self, session):
        """Test creating a task."""
        project = ProjectState(
            project_name='test',
            description='Test',
            working_directory='/tmp',
            status=ProjectStatus.ACTIVE
        )
        session.add(project)
        session.commit()

        task = Task(
            project_id=project.id,
            title='Test task',
            description='Do something',
            status=TaskStatus.PENDING,
            priority=5
        )
        session.add(task)
        session.commit()

        assert task.id is not None
        assert task.status == TaskStatus.PENDING
        assert task.project_id == project.id

    def test_task_project_relationship(self, session):
        """Test task-project relationship."""
        project = ProjectState(
            project_name='test',
            description='Test',
            working_directory='/tmp',
            status=ProjectStatus.ACTIVE
        )
        task = Task(
            project=project,
            title='Test',
            description='Test',
            status=TaskStatus.PENDING
        )
        session.add(project)
        session.commit()

        assert task.project == project
        assert task in project.tasks

    def test_task_to_dict(self, session):
        """Test task serialization."""
        project = ProjectState(
            project_name='test',
            description='Test',
            working_directory='/tmp',
            status=ProjectStatus.ACTIVE
        )
        task = Task(
            project=project,
            title='Test task',
            description='Do something',
            status=TaskStatus.PENDING
        )
        session.add(project)
        session.commit()

        data = task.to_dict()
        assert data['title'] == 'Test task'
        assert data['status'] == 'pending'
        assert 'created_at' in data


class TestStateManager:
    """Test StateManager functionality."""

    @pytest.fixture
    def state_manager(self):
        """Create StateManager with in-memory database."""
        StateManager.reset_instance()
        sm = StateManager.get_instance('sqlite:///:memory:', echo=False)
        yield sm
        StateManager.reset_instance()

    def test_singleton_pattern(self):
        """Test StateManager is singleton."""
        StateManager.reset_instance()
        sm1 = StateManager.get_instance('sqlite:///:memory:')
        sm2 = StateManager.get_instance()
        assert sm1 is sm2
        StateManager.reset_instance()

    def test_create_project(self, state_manager):
        """Test creating a project."""
        project = state_manager.create_project(
            name='test-project',
            description='Test project',
            working_dir='/tmp/test'
        )

        assert project.id is not None
        assert project.project_name == 'test-project'

    def test_get_project(self, state_manager):
        """Test getting a project."""
        project = state_manager.create_project(
            name='test',
            description='Test',
            working_dir='/tmp'
        )

        retrieved = state_manager.get_project(project.id)
        assert retrieved.id == project.id
        assert retrieved.project_name == 'test'

    def test_list_projects(self, state_manager):
        """Test listing projects."""
        state_manager.create_project('p1', 'Test 1', '/tmp/1')
        state_manager.create_project('p2', 'Test 2', '/tmp/2')

        projects = state_manager.list_projects()
        assert len(projects) == 2

    def test_create_task(self, state_manager):
        """Test creating a task."""
        project = state_manager.create_project('test', 'Test', '/tmp')

        task = state_manager.create_task(
            project.id,
            {
                'title': 'Test task',
                'description': 'Do something'
            }
        )

        assert task.id is not None
        assert task.title == 'Test task'
        assert task.status == TaskStatus.PENDING

    def test_update_task_status(self, state_manager):
        """Test updating task status."""
        project = state_manager.create_project('test', 'Test', '/tmp')
        task = state_manager.create_task(
            project.id,
            {'title': 'Test', 'description': 'Test'}
        )

        updated = state_manager.update_task_status(task.id, TaskStatus.RUNNING)
        assert updated.status == TaskStatus.RUNNING
        assert updated.started_at is not None

    def test_record_interaction(self, state_manager):
        """Test recording an interaction."""
        project = state_manager.create_project('test', 'Test', '/tmp')
        task = state_manager.create_task(
            project.id,
            {'title': 'Test', 'description': 'Test'}
        )

        interaction = state_manager.record_interaction(
            project.id,
            task.id,
            {
                'source': InteractionSource.CLAUDE_CODE,
                'prompt': 'Test prompt',
                'response': 'Test response',
                'confidence_score': 0.95
            }
        )

        assert interaction.id is not None
        assert interaction.prompt == 'Test prompt'
        assert interaction.confidence_score == 0.95

    def test_get_interactions(self, state_manager):
        """Test getting interactions."""
        project = state_manager.create_project('test', 'Test', '/tmp')
        state_manager.record_interaction(
            project.id,
            None,
            {
                'source': InteractionSource.LOCAL_LLM,
                'prompt': 'Test 1'
            }
        )
        state_manager.record_interaction(
            project.id,
            None,
            {
                'source': InteractionSource.CLAUDE_CODE,
                'prompt': 'Test 2'
            }
        )

        interactions = state_manager.get_interactions(project.id)
        assert len(interactions) == 2

    def test_create_checkpoint(self, state_manager):
        """Test creating a checkpoint."""
        project = state_manager.create_project('test', 'Test', '/tmp')

        checkpoint = state_manager.create_checkpoint(
            project.id,
            'manual',
            'Test checkpoint'
        )

        assert checkpoint.id is not None
        assert checkpoint.checkpoint_type == 'manual'
        assert checkpoint.state_snapshot is not None

    def test_log_breakpoint_event(self, state_manager):
        """Test logging breakpoint event."""
        project = state_manager.create_project('test', 'Test', '/tmp')

        event = state_manager.log_breakpoint_event(
            project.id,
            None,
            {
                'breakpoint_type': 'low_confidence',
                'reason': 'Confidence below threshold',
                'severity': BreakpointSeverity.MEDIUM
            }
        )

        assert event.id is not None
        assert event.breakpoint_type == 'low_confidence'
        assert not event.resolved

    def test_resolve_breakpoint(self, state_manager):
        """Test resolving a breakpoint."""
        project = state_manager.create_project('test', 'Test', '/tmp')
        event = state_manager.log_breakpoint_event(
            project.id,
            None,
            {
                'breakpoint_type': 'test',
                'reason': 'Test reason'
            }
        )

        resolved = state_manager.resolve_breakpoint(
            event.id,
            'User approved',
            'human'
        )

        assert resolved.resolved is True
        assert resolved.resolution == 'User approved'
        assert resolved.resolved_at is not None

    def test_record_file_change(self, state_manager):
        """Test recording file changes."""
        project = state_manager.create_project('test', 'Test', '/tmp')

        file_state = state_manager.record_file_change(
            project.id,
            None,
            '/tmp/test.py',
            'abc123',
            1024,
            'created'
        )

        assert file_state.id is not None
        assert file_state.file_path == '/tmp/test.py'
        assert file_state.change_type == 'created'

    def test_transaction_rollback(self, state_manager):
        """Test that transaction rolls back on error."""
        project = state_manager.create_project('test', 'Test', '/tmp')

        try:
            with state_manager.transaction():
                # This should work
                state_manager.create_task(
                    project.id,
                    {'title': 'Task 1', 'description': 'Test'}
                )
                # Force an error
                raise Exception("Test error")
        except:
            pass

        # Verify transaction was rolled back (task not created)
        tasks = state_manager.get_tasks_by_status(project.id, TaskStatus.PENDING)
        assert len(tasks) == 0
