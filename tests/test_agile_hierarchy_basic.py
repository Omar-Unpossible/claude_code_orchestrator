"""Basic smoke tests for Agile/Scrum hierarchy (ADR-013).

These are minimal tests to verify core functionality works.
Full comprehensive test suite (150+ tests) can be added incrementally.
"""

import pytest
from datetime import datetime, UTC

from src.core.models import TaskType, TaskStatus, Milestone
from src.core.state import StateManager


class TestTaskType:
    """Test TaskType enum."""

    def test_task_type_values(self):
        """Test TaskType enum has correct values."""
        assert TaskType.EPIC.value == 'epic'
        assert TaskType.STORY.value == 'story'
        assert TaskType.TASK.value == 'task'
        assert TaskType.SUBTASK.value == 'subtask'


class TestEpicCreation:
    """Test epic creation."""

    def test_create_epic(self, state_manager, sample_project):
        """Test basic epic creation."""
        epic_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="User Authentication System",
            description="Complete auth system with OAuth and MFA",
            priority=8
        )

        epic = state_manager.get_task(epic_id)
        assert epic is not None
        assert epic.task_type == TaskType.EPIC
        assert epic.title == "User Authentication System"
        assert epic.priority == 8


class TestStoryCreation:
    """Test story creation."""

    def test_create_story_under_epic(self, state_manager, sample_project):
        """Test story creation under an epic."""
        # Create epic
        epic_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="User Auth",
            description="Auth system"
        )

        # Create story
        story_id = state_manager.create_story(
            project_id=sample_project.id,
            epic_id=epic_id,
            title="Email/password login",
            description="As a user, I want to log in with email/password"
        )

        story = state_manager.get_task(story_id)
        assert story is not None
        assert story.task_type == TaskType.STORY
        assert story.epic_id == epic_id
        assert story.title == "Email/password login"

    def test_create_story_validates_epic(self, state_manager, sample_project):
        """Test story creation validates epic exists."""
        with pytest.raises(ValueError, match="Epic 9999 does not exist"):
            state_manager.create_story(
                project_id=sample_project.id,
                epic_id=9999,
                title="Invalid Story",
                description="Should fail"
            )


class TestEpicStoryQueries:
    """Test epic/story query methods."""

    def test_get_epic_stories(self, state_manager, sample_project):
        """Test retrieving stories for an epic."""
        # Create epic
        epic_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="User Auth",
            description="Auth system"
        )

        # Create 3 stories
        story_ids = []
        for i in range(3):
            story_id = state_manager.create_story(
                project_id=sample_project.id,
                epic_id=epic_id,
                title=f"Story {i}",
                description=f"Description {i}"
            )
            story_ids.append(story_id)

        # Get stories
        stories = state_manager.get_epic_stories(epic_id)
        assert len(stories) == 3
        assert all(s.task_type == TaskType.STORY for s in stories)
        assert all(s.epic_id == epic_id for s in stories)


class TestMilestone:
    """Test milestone functionality."""

    def test_create_milestone(self, state_manager, sample_project):
        """Test milestone creation."""
        # Create epic
        epic_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="User Auth",
            description="Auth system"
        )

        # Create milestone
        milestone_id = state_manager.create_milestone(
            project_id=sample_project.id,
            name="Auth Complete",
            description="Authentication system ready for production",
            required_epic_ids=[epic_id]
        )

        milestone = state_manager.get_milestone(milestone_id)
        assert milestone is not None
        assert milestone.name == "Auth Complete"
        assert epic_id in milestone.required_epic_ids
        assert not milestone.achieved

    def test_milestone_completion_check(self, state_manager, sample_project):
        """Test milestone completion checking."""
        # Create epic
        epic_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="User Auth",
            description="Auth system"
        )

        # Create milestone
        milestone_id = state_manager.create_milestone(
            project_id=sample_project.id,
            name="Test Milestone",
            required_epic_ids=[epic_id]
        )

        # Initially not complete (epic is pending)
        assert not state_manager.check_milestone_completion(milestone_id)

        # Complete the epic
        state_manager.update_task_status(epic_id, TaskStatus.COMPLETED)

        # Now should be complete
        assert state_manager.check_milestone_completion(milestone_id)

    def test_achieve_milestone(self, state_manager, sample_project):
        """Test marking milestone as achieved."""
        # Create and complete epic
        epic_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="User Auth",
            description="Auth system"
        )
        state_manager.update_task_status(epic_id, TaskStatus.COMPLETED)

        # Create milestone
        milestone_id = state_manager.create_milestone(
            project_id=sample_project.id,
            name="Test Milestone",
            required_epic_ids=[epic_id]
        )

        # Achieve milestone
        state_manager.achieve_milestone(milestone_id)

        # Verify achieved
        milestone = state_manager.get_milestone(milestone_id)
        assert milestone.achieved
        assert milestone.achieved_at is not None


class TestTaskModel:
    """Test Task model with new fields."""

    def test_task_to_dict_includes_hierarchy_fields(self, state_manager, sample_project):
        """Test Task.to_dict() includes new hierarchy fields."""
        epic_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="Test Epic",
            description="Test"
        )

        epic = state_manager.get_task(epic_id)
        task_dict = epic.to_dict()

        assert 'task_type' in task_dict
        assert task_dict['task_type'] == 'epic'
        assert 'epic_id' in task_dict
        assert 'story_id' in task_dict
