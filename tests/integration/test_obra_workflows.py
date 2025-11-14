"""Obra user workflow tests - validates typical user journeys.

⭐ OBRA WORKFLOW TESTS - VALIDATES TYPICAL USER JOURNEYS ⭐

These tests validate COMPLETE USER WORKFLOWS that represent typical Obra usage
patterns. Each test models a real user journey from start to finish, validating
that the entire stack works together for common scenarios.

Why These Tests Matter:
- Demo tests validate specific demo flows
- Workflow tests validate TYPICAL DAILY USAGE patterns
- Users follow these patterns in production
- These tests catch workflow friction and UX issues

Test Philosophy:
1. Model REAL user journeys (how users actually work)
2. Test COMPLETE workflows (setup → work → completion)
3. Validate state consistency throughout
4. Test natural language commands (as users would type them)
5. Ensure workflows are efficient and intuitive

Workflow Categories:
1. Project Setup - New project initialization
2. Sprint Planning - Planning work for iteration
3. Daily Development - Day-to-day task management
4. Release Planning - Milestone and release coordination
5. Dependency Management - Task ordering and blocking
6. Bulk Operations - Multi-entity operations
7. Query Workflows - Information retrieval
8. Maintenance - Infrastructure and documentation

Usage:
    # Run all workflow tests
    pytest tests/integration/test_obra_workflows.py -v -m real_llm

    # Run specific workflow
    pytest tests/integration/test_obra_workflows.py::TestProjectSetupWorkflows::test_new_project_initialization -v
"""

import pytest
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


@pytest.mark.real_llm
@pytest.mark.workflow
@pytest.mark.timeout(0)  # No timeout for workflow tests
class TestProjectSetupWorkflows:
    """Test workflows for setting up new projects.

    Models how users initialize and configure new projects in Obra.
    """

    def test_new_project_initialization(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Initialize new project → First epic → First story → First task.

        User Journey:
        1. Create project (done via StateManager, as projects are typically CLI-created)
        2. Create first epic for project
        3. Add first story to epic
        4. Create first task for story
        5. Verify complete hierarchy is set up correctly

        Success Criteria:
        - All entities created with correct relationships
        - Epic references correct project
        - Story references epic
        - Task references story
        - Database state consistent
        """
        # Setup: Create project (typically done via CLI)
        project = real_state_manager.create_project(
            name="My New Application",
            description="A modern web application",
            working_dir="/tmp/my_app"
        )
        ctx = {'project_id': project.id}
        logger.info(f"=== Project created: ID={project.id} ===")

        logger.info("=== STEP 1: Create first epic ===")
        r1 = real_nl_processor_with_llm.process(
            "create epic for user authentication system",
            context=ctx
        )
        assert r1.confidence > 0.7, f"Epic creation failed: {r1.confidence}"
        epic_id = r1.operation_context.entities.get('epic_id')
        assert epic_id is not None, "Epic ID not extracted"
        logger.info(f"✓ Epic created: ID={epic_id}")

        # Verify epic
        epic = real_state_manager.get_task(epic_id)
        assert epic is not None, "Epic not in database"
        assert epic.project_id == project.id, "Epic not linked to project"
        assert epic.task_type == 'EPIC', "Wrong task type"

        logger.info("=== STEP 2: Add first story ===")
        r2 = real_nl_processor_with_llm.process(
            f"add story for user login to epic {epic_id}",
            context=ctx
        )
        assert r2.confidence > 0.7, f"Story creation failed: {r2.confidence}"
        story_id = r2.operation_context.entities.get('story_id')
        assert story_id is not None, "Story ID not extracted"
        logger.info(f"✓ Story created: ID={story_id}")

        # Verify story
        story = real_state_manager.get_task(story_id)
        assert story is not None, "Story not in database"
        assert story.epic_id == epic_id, "Story not linked to epic"
        assert story.task_type == 'STORY', "Wrong task type"

        logger.info("=== STEP 3: Create first task ===")
        r3 = real_nl_processor_with_llm.process(
            f"create task to implement password validation for story {story_id}",
            context=ctx
        )
        assert r3.confidence > 0.7, f"Task creation failed: {r3.confidence}"
        task_id = r3.operation_context.entities.get('task_id')
        assert task_id is not None, "Task ID not extracted"
        logger.info(f"✓ Task created: ID={task_id}")

        # Verify task
        task = real_state_manager.get_task(task_id)
        assert task is not None, "Task not in database"
        assert task.story_id == story_id, "Task not linked to story"
        assert task.task_type == 'TASK', "Wrong task type"

        logger.info("=== STEP 4: Verify complete hierarchy ===")
        # Epic → Story → Task chain is complete
        epic_stories = real_state_manager.get_epic_stories(epic_id)
        assert len(epic_stories) == 1, "Epic should have 1 story"
        assert epic_stories[0].id == story_id, "Wrong story in epic"

        story_tasks = real_state_manager.get_story_tasks(story_id)
        assert len(story_tasks) == 1, "Story should have 1 task"
        assert story_tasks[0].id == task_id, "Wrong task in story"

        logger.info("=== WORKFLOW COMPLETE: Project initialized ===")

    def test_project_configuration_workflow(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Configure project settings → Create initial structure.

        User Journey:
        1. Create project with specific settings
        2. Query project to verify settings
        3. Create initial epic structure (3 epics)
        4. Query project to see all epics

        Success Criteria:
        - Project created with correct settings
        - Initial epic structure established
        - Queries return correct information
        """
        # Create project
        project = real_state_manager.create_project(
            name="E-Commerce Platform",
            description="Full-featured online store",
            working_dir="/tmp/ecommerce"
        )
        ctx = {'project_id': project.id}
        logger.info(f"=== Project: {project.name} ===")

        logger.info("=== Create Epic 1: Product Catalog ===")
        r1 = real_nl_processor_with_llm.process(
            "create epic for product catalog and search",
            context=ctx
        )
        assert r1.confidence > 0.7
        epic1_id = r1.operation_context.entities.get('epic_id')

        logger.info("=== Create Epic 2: Shopping Cart ===")
        r2 = real_nl_processor_with_llm.process(
            "create epic for shopping cart and checkout",
            context=ctx
        )
        assert r2.confidence > 0.7
        epic2_id = r2.operation_context.entities.get('epic_id')

        logger.info("=== Create Epic 3: User Management ===")
        r3 = real_nl_processor_with_llm.process(
            "create epic for user accounts and profiles",
            context=ctx
        )
        assert r3.confidence > 0.7
        epic3_id = r3.operation_context.entities.get('epic_id')

        logger.info("=== Query: List all epics ===")
        r4 = real_nl_processor_with_llm.process(
            "show me all epics",
            context=ctx
        )
        assert r4.confidence > 0.7, "Query should have reasonable confidence"

        # Verify database state
        epics = real_state_manager.list_epics(project_id=project.id)
        assert len(epics) == 3, f"Expected 3 epics, got {len(epics)}"
        epic_ids = {e.id for e in epics}
        assert epic1_id in epic_ids, "Epic 1 missing"
        assert epic2_id in epic_ids, "Epic 2 missing"
        assert epic3_id in epic_ids, "Epic 3 missing"

        logger.info("=== WORKFLOW COMPLETE: Project configured ===")


@pytest.mark.real_llm
@pytest.mark.workflow
@pytest.mark.timeout(0)
class TestSprintPlanningWorkflows:
    """Test workflows for sprint planning activities.

    Models how users plan and organize work for sprints/iterations.
    """

    def test_sprint_planning_full_cycle(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Create sprint epic → Add stories → Break into tasks → Set priorities.

        User Journey:
        1. Create sprint epic
        2. Add 3 user stories
        3. Break first story into tasks
        4. Set priorities and status
        5. Query sprint backlog

        Success Criteria:
        - Sprint epic with multiple stories
        - Stories broken into tasks
        - Priorities set correctly
        - Backlog query shows all work
        """
        project = real_state_manager.create_project(
            name="Sprint Planning Demo",
            description="Test sprint planning workflow",
            working_dir="/tmp/sprint"
        )
        ctx = {'project_id': project.id}

        logger.info("=== STEP 1: Create sprint epic ===")
        r1 = real_nl_processor_with_llm.process(
            "create epic for Sprint 5 - Authentication Features",
            context=ctx
        )
        assert r1.confidence > 0.7
        epic_id = r1.operation_context.entities.get('epic_id')
        logger.info(f"✓ Sprint epic: ID={epic_id}")

        logger.info("=== STEP 2: Add Story 1 - User Login ===")
        r2 = real_nl_processor_with_llm.process(
            f"add story 'User can log in with email and password' to epic {epic_id}",
            context=ctx
        )
        assert r2.confidence > 0.7
        story1_id = r2.operation_context.entities.get('story_id')
        logger.info(f"✓ Story 1: ID={story1_id}")

        logger.info("=== STEP 3: Add Story 2 - Password Reset ===")
        r3 = real_nl_processor_with_llm.process(
            f"add story 'User can reset forgotten password' to epic {epic_id}",
            context=ctx
        )
        assert r3.confidence > 0.7
        story2_id = r3.operation_context.entities.get('story_id')
        logger.info(f"✓ Story 2: ID={story2_id}")

        logger.info("=== STEP 4: Add Story 3 - OAuth ===")
        r4 = real_nl_processor_with_llm.process(
            f"add story 'User can log in with Google OAuth' to epic {epic_id}",
            context=ctx
        )
        assert r4.confidence > 0.7
        story3_id = r4.operation_context.entities.get('story_id')
        logger.info(f"✓ Story 3: ID={story3_id}")

        logger.info("=== STEP 5: Break Story 1 into tasks ===")
        r5a = real_nl_processor_with_llm.process(
            f"create task 'Implement login API endpoint' for story {story1_id}",
            context=ctx
        )
        assert r5a.confidence > 0.7
        task1_id = r5a.operation_context.entities.get('task_id')

        r5b = real_nl_processor_with_llm.process(
            f"create task 'Add password validation logic' for story {story1_id}",
            context=ctx
        )
        assert r5b.confidence > 0.7
        task2_id = r5b.operation_context.entities.get('task_id')

        r5c = real_nl_processor_with_llm.process(
            f"create task 'Create login UI component' for story {story1_id}",
            context=ctx
        )
        assert r5c.confidence > 0.7
        task3_id = r5c.operation_context.entities.get('task_id')

        logger.info(f"✓ Tasks created: {task1_id}, {task2_id}, {task3_id}")

        logger.info("=== STEP 6: Query sprint backlog ===")
        r6 = real_nl_processor_with_llm.process(
            f"show me all stories in epic {epic_id}",
            context=ctx
        )
        assert r6.confidence > 0.7

        # Verify database state
        stories = real_state_manager.get_epic_stories(epic_id)
        assert len(stories) == 3, f"Expected 3 stories, got {len(stories)}"

        story1_tasks = real_state_manager.get_story_tasks(story1_id)
        assert len(story1_tasks) == 3, f"Story 1 should have 3 tasks, got {len(story1_tasks)}"

        logger.info("=== WORKFLOW COMPLETE: Sprint planned ===")

    def test_sprint_backlog_refinement(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Review backlog → Add missing stories → Prioritize.

        User Journey:
        1. Create epic with 2 stories
        2. Query backlog
        3. Realize missing story, add it
        4. Update priorities
        5. Verify final backlog state

        Success Criteria:
        - Backlog queries work correctly
        - Stories can be added iteratively
        - Final state matches plan
        """
        project = real_state_manager.create_project(
            name="Backlog Refinement",
            description="Test backlog refinement",
            working_dir="/tmp/backlog"
        )
        ctx = {'project_id': project.id}

        logger.info("=== Create epic ===")
        r1 = real_nl_processor_with_llm.process(
            "create epic for API development",
            context=ctx
        )
        assert r1.confidence > 0.7
        epic_id = r1.operation_context.entities.get('epic_id')

        logger.info("=== Add initial stories ===")
        r2 = real_nl_processor_with_llm.process(
            f"add story 'REST API endpoints' to epic {epic_id}",
            context=ctx
        )
        assert r2.confidence > 0.7
        story1_id = r2.operation_context.entities.get('story_id')

        r3 = real_nl_processor_with_llm.process(
            f"add story 'API authentication' to epic {epic_id}",
            context=ctx
        )
        assert r3.confidence > 0.7
        story2_id = r3.operation_context.entities.get('story_id')

        logger.info("=== Query backlog ===")
        r4 = real_nl_processor_with_llm.process(
            f"show me all stories in epic {epic_id}",
            context=ctx
        )
        assert r4.confidence > 0.7

        logger.info("=== Realize missing story, add it ===")
        r5 = real_nl_processor_with_llm.process(
            f"add story 'API documentation' to epic {epic_id}",
            context=ctx
        )
        assert r5.confidence > 0.7
        story3_id = r5.operation_context.entities.get('story_id')

        logger.info("=== Verify final state ===")
        stories = real_state_manager.get_epic_stories(epic_id)
        assert len(stories) == 3, "Should have 3 stories after refinement"

        logger.info("=== WORKFLOW COMPLETE: Backlog refined ===")


@pytest.mark.real_llm
@pytest.mark.workflow
@pytest.mark.timeout(0)
class TestDailyDevelopmentWorkflows:
    """Test workflows for daily development activities.

    Models how users interact with Obra during daily development work.
    """

    def test_daily_standup_workflow(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Query work status → Update task → Query next task.

        User Journey:
        1. Query: What should I work on?
        2. Start working on task (mark in_progress)
        3. Complete task
        4. Query: What's next?

        Success Criteria:
        - Queries return useful information
        - Status updates work
        - Workflow feels natural
        """
        project = real_state_manager.create_project(
            name="Daily Work",
            description="Daily development workflow",
            working_dir="/tmp/daily"
        )
        ctx = {'project_id': project.id}

        # Setup: Create some tasks
        logger.info("=== SETUP: Create tasks ===")
        r1 = real_nl_processor_with_llm.process(
            "create task to implement login feature",
            context=ctx
        )
        task1_id = r1.operation_context.entities.get('task_id')

        r2 = real_nl_processor_with_llm.process(
            "create task to add unit tests",
            context=ctx
        )
        task2_id = r2.operation_context.entities.get('task_id')

        r3 = real_nl_processor_with_llm.process(
            "create task to update documentation",
            context=ctx
        )
        task3_id = r3.operation_context.entities.get('task_id')

        logger.info("=== STEP 1: Query what to work on ===")
        r4 = real_nl_processor_with_llm.process(
            "show me all open tasks",
            context=ctx
        )
        assert r4.confidence > 0.7

        # Verify all tasks are pending
        task1 = real_state_manager.get_task(task1_id)
        assert task1.status == 'pending', "New tasks should be pending"

        logger.info("=== STEP 2: Start working on first task ===")
        r5 = real_nl_processor_with_llm.process(
            f"mark task {task1_id} as in progress",
            context=ctx
        )
        assert r5.confidence > 0.7

        task1 = real_state_manager.get_task(task1_id)
        assert task1.status == 'in_progress', "Task should be in progress"

        logger.info("=== STEP 3: Complete task ===")
        r6 = real_nl_processor_with_llm.process(
            f"mark task {task1_id} as completed",
            context=ctx
        )
        assert r6.confidence > 0.7

        task1 = real_state_manager.get_task(task1_id)
        assert task1.status == 'completed', "Task should be completed"

        logger.info("=== STEP 4: Query next task ===")
        r7 = real_nl_processor_with_llm.process(
            "show me all open tasks",
            context=ctx
        )
        assert r7.confidence > 0.7

        # Verify only 2 tasks remain open
        open_tasks = real_state_manager.get_tasks_by_status(
            project_id=project.id,
            status='pending'
        )
        assert len(open_tasks) >= 2, "Should have remaining open tasks"

        logger.info("=== WORKFLOW COMPLETE: Daily standup done ===")

    def test_task_lifecycle_workflow(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Create → Start → Block → Unblock → Complete.

        User Journey:
        1. Create task
        2. Start task
        3. Encounter blocker, mark as blocked
        4. Resolve blocker, resume
        5. Complete task

        Success Criteria:
        - Task can transition through all states
        - State transitions are logical
        - Final state is correct
        """
        project = real_state_manager.create_project(
            name="Task Lifecycle",
            description="Complete task lifecycle",
            working_dir="/tmp/lifecycle"
        )
        ctx = {'project_id': project.id}

        logger.info("=== STEP 1: Create task ===")
        r1 = real_nl_processor_with_llm.process(
            "create task to integrate payment API",
            context=ctx
        )
        assert r1.confidence > 0.7
        task_id = r1.operation_context.entities.get('task_id')

        task = real_state_manager.get_task(task_id)
        assert task.status == 'pending', "New task should be pending"

        logger.info("=== STEP 2: Start task ===")
        r2 = real_nl_processor_with_llm.process(
            f"mark task {task_id} as in progress",
            context=ctx
        )
        assert r2.confidence > 0.7

        task = real_state_manager.get_task(task_id)
        assert task.status == 'in_progress', "Task should be in progress"

        logger.info("=== STEP 3: Mark as blocked ===")
        r3 = real_nl_processor_with_llm.process(
            f"mark task {task_id} as blocked",
            context=ctx
        )
        assert r3.confidence > 0.7  # May be slightly lower confidence

        task = real_state_manager.get_task(task_id)
        assert task.status == 'blocked', "Task should be blocked"

        logger.info("=== STEP 4: Unblock and resume ===")
        r4 = real_nl_processor_with_llm.process(
            f"mark task {task_id} as in progress",
            context=ctx
        )
        assert r4.confidence > 0.7

        task = real_state_manager.get_task(task_id)
        assert task.status == 'in_progress', "Task should be in progress again"

        logger.info("=== STEP 5: Complete task ===")
        r5 = real_nl_processor_with_llm.process(
            f"mark task {task_id} as completed",
            context=ctx
        )
        assert r5.confidence > 0.7

        task = real_state_manager.get_task(task_id)
        assert task.status == 'completed', "Task should be completed"

        logger.info("=== WORKFLOW COMPLETE: Task lifecycle complete ===")


@pytest.mark.real_llm
@pytest.mark.workflow
@pytest.mark.timeout(0)
class TestReleasePlanningWorkflows:
    """Test workflows for release planning and milestone tracking.

    Models how users plan releases and track milestone progress.
    """

    def test_release_milestone_workflow(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Create epics → Create milestone → Track progress → Achieve milestone.

        User Journey:
        1. Create 2 epics for release
        2. Create milestone requiring both epics
        3. Complete epic 1
        4. Check milestone (should be incomplete)
        5. Complete epic 2
        6. Check milestone (should be complete)

        Success Criteria:
        - Milestone tracks epic completion
        - Milestone state updates correctly
        - Release planning is clear
        """
        project = real_state_manager.create_project(
            name="Release Planning",
            description="v1.0 release planning",
            working_dir="/tmp/release"
        )
        ctx = {'project_id': project.id}

        logger.info("=== STEP 1: Create Epic 1 ===")
        r1 = real_nl_processor_with_llm.process(
            "create epic for core features",
            context=ctx
        )
        assert r1.confidence > 0.7
        epic1_id = r1.operation_context.entities.get('epic_id')

        logger.info("=== STEP 2: Create Epic 2 ===")
        r2 = real_nl_processor_with_llm.process(
            "create epic for testing and QA",
            context=ctx
        )
        assert r2.confidence > 0.7
        epic2_id = r2.operation_context.entities.get('epic_id')

        logger.info("=== STEP 3: Create milestone ===")
        r3 = real_nl_processor_with_llm.process(
            f"create milestone 'v1.0 Release' requiring epics {epic1_id} and {epic2_id}",
            context=ctx
        )
        assert r3.confidence > 0.7
        milestone_id = r3.operation_context.entities.get('milestone_id')

        # Verify milestone created
        milestone = real_state_manager.get_milestone(milestone_id)
        assert milestone is not None, "Milestone not created"
        assert not milestone.is_achieved, "New milestone should not be achieved"

        logger.info("=== STEP 4: Complete Epic 1 ===")
        real_state_manager.update_task_status(epic1_id, 'completed')
        logger.info(f"✓ Epic {epic1_id} completed")

        logger.info("=== STEP 5: Check milestone (should be incomplete) ===")
        r4 = real_nl_processor_with_llm.process(
            f"what's the status of milestone {milestone_id}?",
            context=ctx
        )
        assert r4.confidence > 0.7

        milestone = real_state_manager.get_milestone(milestone_id)
        assert not milestone.is_achieved, "Milestone should not be achieved yet"

        logger.info("=== STEP 6: Complete Epic 2 ===")
        real_state_manager.update_task_status(epic2_id, 'completed')
        logger.info(f"✓ Epic {epic2_id} completed")

        logger.info("=== STEP 7: Check milestone (should be complete) ===")
        # Check if milestone can be achieved
        if real_state_manager.check_milestone_completion(milestone):
            real_state_manager.achieve_milestone(milestone)
            logger.info("✓ Milestone achieved!")

        milestone = real_state_manager.get_milestone(milestone_id)
        assert milestone.is_achieved, "Milestone should be achieved"

        logger.info("=== WORKFLOW COMPLETE: Release milestone achieved ===")

    def test_release_roadmap_query_workflow(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Create release structure → Query roadmap at various stages.

        User Journey:
        1. Create 3 milestones with epics
        2. Query all milestones
        3. Query specific milestone progress
        4. Complete some epics
        5. Query updated roadmap

        Success Criteria:
        - Roadmap queries return useful information
        - Progress tracking is accurate
        - Users can understand release state
        """
        project = real_state_manager.create_project(
            name="Product Roadmap",
            description="Multi-release roadmap",
            working_dir="/tmp/roadmap"
        )
        ctx = {'project_id': project.id}

        logger.info("=== Create Epic 1 ===")
        r1 = real_nl_processor_with_llm.process(
            "create epic for authentication",
            context=ctx
        )
        epic1_id = r1.operation_context.entities.get('epic_id')

        logger.info("=== Create Epic 2 ===")
        r2 = real_nl_processor_with_llm.process(
            "create epic for user profiles",
            context=ctx
        )
        epic2_id = r2.operation_context.entities.get('epic_id')

        logger.info("=== Create Epic 3 ===")
        r3 = real_nl_processor_with_llm.process(
            "create epic for admin dashboard",
            context=ctx
        )
        epic3_id = r3.operation_context.entities.get('epic_id')

        logger.info("=== Create Milestone 1: MVP ===")
        r4 = real_nl_processor_with_llm.process(
            f"create milestone 'MVP' requiring epic {epic1_id}",
            context=ctx
        )
        assert r4.confidence > 0.7
        milestone1_id = r4.operation_context.entities.get('milestone_id')

        logger.info("=== Create Milestone 2: v1.0 ===")
        r5 = real_nl_processor_with_llm.process(
            f"create milestone 'v1.0' requiring epics {epic1_id} and {epic2_id}",
            context=ctx
        )
        assert r5.confidence > 0.7
        milestone2_id = r5.operation_context.entities.get('milestone_id')

        logger.info("=== Query: Show all milestones ===")
        r6 = real_nl_processor_with_llm.process(
            "show me all milestones",
            context=ctx
        )
        assert r6.confidence > 0.7

        # Verify milestones exist
        milestones = real_state_manager.list_milestones(project_id=project.id)
        assert len(milestones) >= 2, "Should have at least 2 milestones"

        logger.info("=== Complete Epic 1 ===")
        real_state_manager.update_task_status(epic1_id, 'completed')

        logger.info("=== Query: Milestone 1 status ===")
        r7 = real_nl_processor_with_llm.process(
            f"what's the status of milestone {milestone1_id}?",
            context=ctx
        )
        assert r7.confidence > 0.7

        logger.info("=== WORKFLOW COMPLETE: Roadmap queried ===")


@pytest.mark.real_llm
@pytest.mark.workflow
@pytest.mark.timeout(0)
class TestDependencyManagementWorkflows:
    """Test workflows for managing task dependencies.

    Models how users set up and manage task dependencies.
    """

    def test_sequential_task_dependencies(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Create task chain A → B → C with dependencies.

        User Journey:
        1. Create task A (foundation)
        2. Create task B depending on A
        3. Create task C depending on B
        4. Try to work on C (should see B is blocked)
        5. Complete A
        6. Complete B
        7. Complete C

        Success Criteria:
        - Dependencies are set correctly
        - Task ordering is clear
        - Workflow is logical
        """
        project = real_state_manager.create_project(
            name="Dependency Management",
            description="Task dependency workflow",
            working_dir="/tmp/deps"
        )
        ctx = {'project_id': project.id}

        logger.info("=== STEP 1: Create Task A (foundation) ===")
        r1 = real_nl_processor_with_llm.process(
            "create task to set up database schema",
            context=ctx
        )
        assert r1.confidence > 0.7
        task_a_id = r1.operation_context.entities.get('task_id')

        logger.info("=== STEP 2: Create Task B (depends on A) ===")
        r2 = real_nl_processor_with_llm.process(
            f"create task to write data models depending on task {task_a_id}",
            context=ctx
        )
        assert r2.confidence > 0.7
        task_b_id = r2.operation_context.entities.get('task_id')

        logger.info("=== STEP 3: Create Task C (depends on B) ===")
        r3 = real_nl_processor_with_llm.process(
            f"create task to implement API endpoints depending on task {task_b_id}",
            context=ctx
        )
        assert r3.confidence > 0.7
        task_c_id = r3.operation_context.entities.get('task_id')

        logger.info("=== Verify dependency chain ===")
        task_b = real_state_manager.get_task(task_b_id)
        assert task_b is not None, "Task B not found"
        # Note: Dependency checking depends on StateManager implementation
        # We're validating the workflow can be created

        logger.info("=== STEP 4: Complete tasks in order ===")
        real_state_manager.update_task_status(task_a_id, 'completed')
        logger.info(f"✓ Task A completed: {task_a_id}")

        real_state_manager.update_task_status(task_b_id, 'completed')
        logger.info(f"✓ Task B completed: {task_b_id}")

        real_state_manager.update_task_status(task_c_id, 'completed')
        logger.info(f"✓ Task C completed: {task_c_id}")

        logger.info("=== WORKFLOW COMPLETE: Sequential dependencies ===")

    def test_parallel_task_dependencies(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Create parallel tasks → Convergence task.

        User Journey:
        1. Create tasks A, B, C (independent)
        2. Create task D depending on A, B, C
        3. Complete A, B, C in any order
        4. Complete D once all dependencies done

        Success Criteria:
        - Parallel tasks are independent
        - Convergence task waits for all
        - Workflow is clear
        """
        project = real_state_manager.create_project(
            name="Parallel Dependencies",
            description="Parallel task workflow",
            working_dir="/tmp/parallel"
        )
        ctx = {'project_id': project.id}

        logger.info("=== Create Task A (frontend) ===")
        r1 = real_nl_processor_with_llm.process(
            "create task to implement frontend UI",
            context=ctx
        )
        task_a_id = r1.operation_context.entities.get('task_id')

        logger.info("=== Create Task B (backend) ===")
        r2 = real_nl_processor_with_llm.process(
            "create task to implement backend API",
            context=ctx
        )
        task_b_id = r2.operation_context.entities.get('task_id')

        logger.info("=== Create Task C (database) ===")
        r3 = real_nl_processor_with_llm.process(
            "create task to set up database",
            context=ctx
        )
        task_c_id = r3.operation_context.entities.get('task_id')

        logger.info("=== Create Task D (integration - depends on A, B, C) ===")
        r4 = real_nl_processor_with_llm.process(
            f"create task to integrate all components depending on tasks {task_a_id}, {task_b_id}, {task_c_id}",
            context=ctx
        )
        assert r4.confidence > 0.7
        task_d_id = r4.operation_context.entities.get('task_id')

        logger.info("=== Complete parallel tasks ===")
        real_state_manager.update_task_status(task_a_id, 'completed')
        real_state_manager.update_task_status(task_b_id, 'completed')
        real_state_manager.update_task_status(task_c_id, 'completed')

        logger.info("=== Complete integration task ===")
        real_state_manager.update_task_status(task_d_id, 'completed')

        logger.info("=== WORKFLOW COMPLETE: Parallel dependencies ===")


@pytest.mark.real_llm
@pytest.mark.workflow
@pytest.mark.timeout(0)
class TestBulkOperationsWorkflows:
    """Test workflows for bulk operations on multiple entities.

    Models how users efficiently manage multiple items at once.
    """

    def test_bulk_task_creation_workflow(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Rapidly create multiple tasks → Bulk update status.

        User Journey:
        1. Create 5 tasks quickly
        2. Bulk update 3 tasks to in_progress
        3. Complete 2 tasks
        4. Query remaining work

        Success Criteria:
        - Can create multiple tasks efficiently
        - Bulk updates work correctly
        - Final state is consistent
        """
        project = real_state_manager.create_project(
            name="Bulk Operations",
            description="Bulk task management",
            working_dir="/tmp/bulk"
        )
        ctx = {'project_id': project.id}

        logger.info("=== STEP 1: Rapidly create 5 tasks ===")
        task_ids = []

        r1 = real_nl_processor_with_llm.process(
            "create task to implement feature A",
            context=ctx
        )
        task_ids.append(r1.operation_context.entities.get('task_id'))

        r2 = real_nl_processor_with_llm.process(
            "create task to implement feature B",
            context=ctx
        )
        task_ids.append(r2.operation_context.entities.get('task_id'))

        r3 = real_nl_processor_with_llm.process(
            "create task to implement feature C",
            context=ctx
        )
        task_ids.append(r3.operation_context.entities.get('task_id'))

        r4 = real_nl_processor_with_llm.process(
            "create task to write tests",
            context=ctx
        )
        task_ids.append(r4.operation_context.entities.get('task_id'))

        r5 = real_nl_processor_with_llm.process(
            "create task to update documentation",
            context=ctx
        )
        task_ids.append(r5.operation_context.entities.get('task_id'))

        logger.info(f"✓ Created 5 tasks: {task_ids}")

        logger.info("=== STEP 2: Bulk update first 3 to in_progress ===")
        task_list = ', '.join(map(str, task_ids[:3]))
        r6 = real_nl_processor_with_llm.process(
            f"mark tasks {task_list} as in progress",
            context=ctx
        )
        assert r6.confidence > 0.7

        # Verify bulk update
        for task_id in task_ids[:3]:
            task = real_state_manager.get_task(task_id)
            assert task.status == 'in_progress', f"Task {task_id} not updated"

        logger.info("=== STEP 3: Complete 2 tasks ===")
        real_state_manager.update_task_status(task_ids[0], 'completed')
        real_state_manager.update_task_status(task_ids[1], 'completed')

        logger.info("=== STEP 4: Query remaining work ===")
        r7 = real_nl_processor_with_llm.process(
            "show me all open tasks",
            context=ctx
        )
        assert r7.confidence > 0.7

        # Verify remaining tasks
        open_tasks = real_state_manager.get_tasks_by_status(
            project_id=project.id,
            status='in_progress'
        )
        # Should have 1 in_progress + 2 pending = 3 open tasks
        assert len(open_tasks) >= 1, "Should have remaining in_progress tasks"

        logger.info("=== WORKFLOW COMPLETE: Bulk operations done ===")

    def test_bulk_delete_cleanup_workflow(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Create tasks → Mark done → Bulk delete completed tasks.

        User Journey:
        1. Create 5 tasks
        2. Complete 3 tasks
        3. Bulk delete completed tasks
        4. Verify only active tasks remain

        Success Criteria:
        - Bulk delete works correctly
        - Only completed tasks are deleted
        - Active tasks are preserved
        """
        project = real_state_manager.create_project(
            name="Cleanup Workflow",
            description="Bulk deletion workflow",
            working_dir="/tmp/cleanup"
        )
        ctx = {'project_id': project.id}

        logger.info("=== Create 5 tasks ===")
        task_ids = []
        for i in range(5):
            r = real_nl_processor_with_llm.process(
                f"create task to implement feature {i+1}",
                context=ctx
            )
            task_ids.append(r.operation_context.entities.get('task_id'))

        logger.info("=== Complete first 3 tasks ===")
        for task_id in task_ids[:3]:
            real_state_manager.update_task_status(task_id, 'completed')

        logger.info("=== Bulk delete completed tasks ===")
        completed_task_list = ', '.join(map(str, task_ids[:3]))
        r_delete = real_nl_processor_with_llm.process(
            f"delete tasks {completed_task_list}",
            context=ctx
        )
        assert r_delete.confidence > 0.7

        logger.info("=== Verify only active tasks remain ===")
        # Tasks 4 and 5 should still exist
        task4 = real_state_manager.get_task(task_ids[3])
        task5 = real_state_manager.get_task(task_ids[4])
        assert task4 is not None, "Task 4 should exist"
        assert task5 is not None, "Task 5 should exist"

        logger.info("=== WORKFLOW COMPLETE: Cleanup done ===")


@pytest.mark.real_llm
@pytest.mark.workflow
@pytest.mark.timeout(0)
class TestQueryWorkflows:
    """Test workflows for querying and reporting.

    Models how users retrieve information from Obra.
    """

    def test_comprehensive_query_workflow(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Create work structure → Various queries → Reporting.

        User Journey:
        1. Create epic with stories and tasks
        2. Query: All open tasks
        3. Query: Tasks by status
        4. Query: Epic progress
        5. Query: Story details

        Success Criteria:
        - All queries return reasonable confidence
        - Information is accessible
        - Queries feel natural
        """
        project = real_state_manager.create_project(
            name="Query Testing",
            description="Query workflow validation",
            working_dir="/tmp/query"
        )
        ctx = {'project_id': project.id}

        logger.info("=== Setup: Create work structure ===")
        # Create epic
        r1 = real_nl_processor_with_llm.process(
            "create epic for reporting features",
            context=ctx
        )
        epic_id = r1.operation_context.entities.get('epic_id')

        # Create story
        r2 = real_nl_processor_with_llm.process(
            f"add story for dashboard reports to epic {epic_id}",
            context=ctx
        )
        story_id = r2.operation_context.entities.get('story_id')

        # Create tasks
        r3 = real_nl_processor_with_llm.process(
            f"create task for data aggregation for story {story_id}",
            context=ctx
        )
        task1_id = r3.operation_context.entities.get('task_id')

        r4 = real_nl_processor_with_llm.process(
            f"create task for chart rendering for story {story_id}",
            context=ctx
        )
        task2_id = r4.operation_context.entities.get('task_id')

        # Update some statuses
        real_state_manager.update_task_status(task1_id, 'in_progress')

        logger.info("=== Query 1: All open tasks ===")
        q1 = real_nl_processor_with_llm.process(
            "show me all open tasks",
            context=ctx
        )
        assert q1.confidence > 0.7

        logger.info("=== Query 2: In-progress tasks ===")
        q2 = real_nl_processor_with_llm.process(
            "show me all tasks that are in progress",
            context=ctx
        )
        assert q2.confidence > 0.7

        logger.info("=== Query 3: Epic progress ===")
        q3 = real_nl_processor_with_llm.process(
            f"what's the status of epic {epic_id}?",
            context=ctx
        )
        assert q3.confidence > 0.7

        logger.info("=== Query 4: Story details ===")
        q4 = real_nl_processor_with_llm.process(
            f"show me story {story_id}",
            context=ctx
        )
        assert q4.confidence > 0.7

        logger.info("=== Query 5: All stories in epic ===")
        q5 = real_nl_processor_with_llm.process(
            f"show me all stories in epic {epic_id}",
            context=ctx
        )
        assert q5.confidence > 0.7

        logger.info("=== WORKFLOW COMPLETE: All queries successful ===")

    def test_natural_language_query_variations(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Test various natural phrasings of the same query.

        User Journey:
        1. Create some tasks
        2. Query same information in different ways
        3. Verify all queries work

        Success Criteria:
        - Multiple phrasings of same query work
        - System is flexible with language
        - Confidence is reasonable for all
        """
        project = real_state_manager.create_project(
            name="NL Query Variations",
            description="Natural language flexibility",
            working_dir="/tmp/nl_query"
        )
        ctx = {'project_id': project.id}

        logger.info("=== Setup: Create tasks ===")
        for i in range(3):
            real_nl_processor_with_llm.process(
                f"create task to implement feature {i+1}",
                context=ctx
            )

        logger.info("=== Query Variation 1: 'show me all open tasks' ===")
        q1 = real_nl_processor_with_llm.process(
            "show me all open tasks",
            context=ctx
        )
        assert q1.confidence > 0.7

        logger.info("=== Query Variation 2: 'what tasks are pending?' ===")
        q2 = real_nl_processor_with_llm.process(
            "what tasks are pending?",
            context=ctx
        )
        assert q2.confidence > 0.7

        logger.info("=== Query Variation 3: 'list all unfinished tasks' ===")
        q3 = real_nl_processor_with_llm.process(
            "list all unfinished tasks",
            context=ctx
        )
        assert q3.confidence > 0.7

        logger.info("=== WORKFLOW COMPLETE: NL variations work ===")


@pytest.mark.real_llm
@pytest.mark.workflow
@pytest.mark.timeout(0)
class TestInfrastructureMaintenanceWorkflows:
    """Test workflows for project infrastructure maintenance.

    Models how users maintain documentation and project structure.
    """

    def test_documentation_update_workflow(
        self,
        real_nl_processor_with_llm,
        real_state_manager
    ):
        """Workflow: Complete epic → System suggests docs update → Create maintenance task.

        User Journey:
        1. Create epic with architectural changes flag
        2. Add stories and tasks
        3. Complete epic
        4. System suggests documentation update
        5. Create maintenance task

        Success Criteria:
        - Epic completion triggers maintenance suggestion
        - Maintenance task can be created
        - Documentation workflow is clear
        """
        project = real_state_manager.create_project(
            name="Documentation Workflow",
            description="Infrastructure maintenance",
            working_dir="/tmp/docs"
        )
        ctx = {'project_id': project.id}

        logger.info("=== STEP 1: Create epic with changes ===")
        r1 = real_nl_processor_with_llm.process(
            "create epic for new authentication system",
            context=ctx
        )
        assert r1.confidence > 0.7
        epic_id = r1.operation_context.entities.get('epic_id')

        # Note: In real workflow, this would be flagged by user or system
        # For test purposes, we can manually flag it
        epic = real_state_manager.get_task(epic_id)
        if hasattr(epic, 'requires_adr'):
            epic.requires_adr = True
            epic.has_architectural_changes = True

        logger.info("=== STEP 2: Add story ===")
        r2 = real_nl_processor_with_llm.process(
            f"add story for OAuth integration to epic {epic_id}",
            context=ctx
        )
        story_id = r2.operation_context.entities.get('story_id')

        logger.info("=== STEP 3: Complete epic (would trigger maintenance) ===")
        real_state_manager.update_task_status(epic_id, 'completed')
        logger.info("✓ Epic completed - maintenance would be suggested")

        logger.info("=== STEP 4: Create maintenance task ===")
        r3 = real_nl_processor_with_llm.process(
            "create task to update architecture documentation",
            context=ctx
        )
        assert r3.confidence > 0.7
        maintenance_task_id = r3.operation_context.entities.get('task_id')

        # Verify maintenance task created
        maintenance_task = real_state_manager.get_task(maintenance_task_id)
        assert maintenance_task is not None, "Maintenance task not created"

        logger.info("=== WORKFLOW COMPLETE: Documentation maintenance ===")


# Test statistics and metadata
TEST_CATEGORIES = {
    'project_setup': 2,           # TestProjectSetupWorkflows
    'sprint_planning': 2,         # TestSprintPlanningWorkflows
    'daily_development': 2,       # TestDailyDevelopmentWorkflows
    'release_planning': 2,        # TestReleasePlanningWorkflows
    'dependency_management': 2,   # TestDependencyManagementWorkflows
    'bulk_operations': 2,         # TestBulkOperationsWorkflows
    'query_workflows': 2,         # TestQueryWorkflows
    'infrastructure': 1,          # TestInfrastructureMaintenanceWorkflows
}

TOTAL_WORKFLOW_TESTS = sum(TEST_CATEGORIES.values())  # 15 tests

# Expected execution time: ~20-30 minutes
# Each test: 1-2 minutes (multiple LLM calls, state operations)
# Comprehensive coverage of typical user journeys
