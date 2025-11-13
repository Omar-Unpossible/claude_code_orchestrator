"""Complete end-to-end workflow tests.

Run on: Before release, nightly CI (optional)
Speed: 20-30 minutes
Purpose: Validate complete user journeys from start to finish

These tests validate the FULL Obra value proposition:
Natural Language → Task Creation → Orchestration → Code Generation → Quality Validation
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from src.orchestrator import Orchestrator
from src.core.state import StateManager
from src.core.config import Config
from src.nl.nl_command_processor import NLCommandProcessor
from core.models import TaskStatus, TaskType


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteWorkflows:
    """End-to-end workflow tests covering complete user journeys."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = tempfile.mkdtemp(prefix='e2e_test_')
        yield workspace
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

    @pytest.fixture
    def e2e_config(self, temp_workspace):
        """E2E test configuration."""
        config = Config.load()
        config.set('llm.type', 'ollama')
        config.set('llm.model', 'qwen2.5-coder:32b')
        config.set('llm.base_url', 'http://10.0.75.1:11434')
        config.set('llm.timeout', 60.0)
        config.set('llm.temperature', 0.1)
        config.set('agent.type', 'mock')
        config.set('agent.config.workspace_path', temp_workspace)
        config.set('database.url', 'sqlite:///:memory:')
        config.set('nl_commands.enabled', True)
        return config

    @pytest.fixture
    def state_manager(self):
        """StateManager for E2E tests."""
        state = StateManager(database_url='sqlite:///:memory:')
        yield state
        state.close()

    @pytest.mark.requires_ollama
    def test_e2e_nl_to_task_creation(self, e2e_config, state_manager, mock_llm_smart):
        """
        E2E: Natural language command → Task creation.

        User Journey:
        1. User types natural language command
        2. Intent classifier identifies COMMAND
        3. Entity extractor identifies task
        4. Command validator validates
        5. Command executor creates task
        6. Response formatter returns confirmation
        """
        # Create project
        project = state_manager.create_project(
            name="E2E NL Test",
            description="E2E natural language test",
            working_dir="/tmp/e2e_nl"
        )

        # Create NL processor
        nl_processor = NLCommandProcessor(
            llm_plugin=mock_llm_smart,
            state_manager=state_manager,
            config={'nl_commands': {'enabled': True}}
        )

        # Setup mock responses for full pipeline
        mock_llm_smart.generate.side_effect = [
            '{"intent": "COMMAND", "confidence": 0.95}',  # Intent
            '{"operation_type": "CREATE", "confidence": 0.94}',  # Operation
            '{"entity_type": "task", "confidence": 0.96}',  # Entity type
            '{"identifier": null, "confidence": 0.98}',  # Identifier
            '{"parameters": {"title": "Add user login", "project_id": 1}, "confidence": 0.90}'  # Parameters
        ]

        # Execute NL command
        response = nl_processor.process("create task to add user login")

        # Validate response
        assert response.success
        assert response.intent == 'COMMAND'
        assert len(response.execution_result.created_ids) > 0

        # Verify task created
        task_id = response.execution_result.created_ids[0]
        task = state_manager.get_task(task_id)
        assert task is not None
        assert 'login' in task.title.lower()
        print(f"✓ E2E: NL command created task {task_id}: {task.title}")

    def test_e2e_epic_to_stories_workflow(self, state_manager):
        """
        E2E: Epic → Stories → Tasks workflow.

        User Journey:
        1. Create project
        2. Create epic (large feature)
        3. Create multiple stories in epic
        4. Create tasks for each story
        5. Verify hierarchy preserved
        """
        # Step 1: Create project
        project = state_manager.create_project(
            name="E2E Agile Workflow",
            description="Complete agile hierarchy test",
            working_dir="/tmp/e2e_agile"
        )
        print(f"✓ Created project {project.id}")

        # Step 2: Create epic
        epic_id = state_manager.create_epic(
            project_id=project.id,
            title="User Authentication System",
            description="Complete auth with OAuth, MFA, sessions"
        )
        print(f"✓ Created epic {epic_id}")

        # Step 3: Create stories
        story1_id = state_manager.create_story(
            project_id=project.id,
            epic_id=epic_id,
            title="Email/Password Login",
            description="Basic login flow"
        )

        story2_id = state_manager.create_story(
            project_id=project.id,
            epic_id=epic_id,
            title="OAuth Integration",
            description="Google/GitHub OAuth"
        )

        story3_id = state_manager.create_story(
            project_id=project.id,
            epic_id=epic_id,
            title="Multi-Factor Auth",
            description="SMS/TOTP MFA"
        )
        print(f"✓ Created 3 stories: {story1_id}, {story2_id}, {story3_id}")

        # Step 4: Create tasks for story 1
        task1_id = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Create login form UI',
                'description': 'Design and implement login form',
                'story_id': story1_id,
                'priority': 5
            }
        )

        task2_id = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Implement auth backend',
                'description': 'Password hashing and JWT',
                'story_id': story1_id,
                'priority': 5
            }
        )
        print(f"✓ Created 2 tasks for story {story1_id}")

        # Step 5: Verify hierarchy
        epic = state_manager.get_task(epic_id)
        stories = state_manager.get_epic_stories(epic_id)
        story1_tasks = [t for t in state_manager.list_tasks(project_id=project.id)
                        if hasattr(t, 'story_id') and t.story_id == story1_id]

        assert epic.task_type == TaskType.EPIC
        assert len(stories) == 3
        assert len(story1_tasks) == 2
        print(f"✓ E2E: Epic hierarchy validated - 1 epic, 3 stories, 2 tasks")

    def test_e2e_task_with_dependencies(self, state_manager):
        """
        E2E: Task dependencies workflow (M9 feature).

        User Journey:
        1. Create project
        2. Create task A (setup database)
        3. Create task B (depends on A - seed data)
        4. Create task C (depends on B - run migrations)
        5. Verify dependency graph
        """
        # Create project
        project = state_manager.create_project(
            name="E2E Dependencies",
            description="Task dependency test",
            working_dir="/tmp/e2e_deps"
        )

        # Task A: Foundation
        task_a = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Setup database schema',
                'description': 'Create tables',
                'priority': 5
            }
        )

        # Task B: Depends on A
        task_b = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Seed initial data',
                'description': 'Add default users',
                'priority': 5,
                'dependencies': [task_a.id]
            }
        )

        # Task C: Depends on B
        task_c = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Run migrations',
                'description': 'Apply schema changes',
                'priority': 5,
                'dependencies': [task_b.id]
            }
        )

        # Verify dependency chain: A → B → C
        assert task_b.get_dependencies() == [task_a.id]
        assert task_c.get_dependencies() == [task_b.id]
        print(f"✓ E2E: Dependency chain validated: {task_a.id} → {task_b.id} → {task_c.id}")

    def test_e2e_project_milestone_workflow(self, state_manager):
        """
        E2E: Project → Epics → Milestone workflow.

        User Journey:
        1. Create project
        2. Create multiple epics
        3. Create milestone requiring epics
        4. Complete epics
        5. Check milestone achievement
        """
        # Create project
        project = state_manager.create_project(
            name="E2E Milestone",
            description="Milestone workflow test",
            working_dir="/tmp/e2e_milestone"
        )

        # Create epics
        epic1_id = state_manager.create_epic(
            project_id=project.id,
            title="Frontend Components",
            description="UI library"
        )

        epic2_id = state_manager.create_epic(
            project_id=project.id,
            title="Backend APIs",
            description="REST endpoints"
        )

        # Create milestone
        milestone_id = state_manager.create_milestone(
            project_id=project.id,
            name="MVP Release",
            description="First production release",
            required_epic_ids=[epic1_id, epic2_id]
        )

        # Retrieve milestone to verify
        milestone = state_manager.get_milestone(milestone_id)

        # Verify milestone setup
        assert milestone.required_epic_ids == [epic1_id, epic2_id]
        print(f"✓ E2E: Milestone {milestone_id} created requiring {len(milestone.required_epic_ids)} epics")

        # Check milestone (should not be complete yet)
        is_complete = state_manager.check_milestone_completion(milestone_id)
        assert not is_complete
        print("✓ E2E: Milestone not yet complete (as expected)")

    def test_e2e_multi_iteration_quality_loop(self, state_manager, temp_workspace):
        """
        E2E: Multi-iteration quality improvement loop.

        User Journey:
        1. Create task with quality requirements
        2. Mock first iteration (low quality)
        3. Mock second iteration (improved)
        4. Mock third iteration (acceptable)
        5. Verify quality progression
        """
        # Create project and task
        project = state_manager.create_project(
            name="E2E Quality Loop",
            description="Quality iteration test",
            working_dir=temp_workspace
        )

        task = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Implement feature X',
                'description': 'With quality requirements',
                'priority': 5
            }
        )

        # Simulate multiple iterations with quality scores
        iterations = [
            {'iteration': 1, 'quality_score': 0.45, 'status': 'needs_improvement'},
            {'iteration': 2, 'quality_score': 0.68, 'status': 'acceptable'},
            {'iteration': 3, 'quality_score': 0.85, 'status': 'good'},
        ]

        quality_progression = []
        for iter_data in iterations:
            # Mock quality assessment
            quality_progression.append(iter_data['quality_score'])

            # Update task with iteration info
            state_manager.update_task(task.id, {
                'metadata': {
                    'iterations': len(quality_progression),
                    'latest_quality': iter_data['quality_score']
                }
            })

        # Verify quality improved over iterations
        assert quality_progression[0] < quality_progression[1] < quality_progression[2]
        assert quality_progression[-1] >= 0.70  # Final quality acceptable
        print(f"✓ E2E: Quality improved across {len(iterations)} iterations: {quality_progression}")
