"""Example: Using ParallelAgentCoordinator for parallel task execution.

This example demonstrates how to use ParallelAgentCoordinator to execute
multiple subtasks in parallel with multiple Claude Code agents.
"""

from datetime import datetime
from typing import List

from src.core.config import Config
from src.core.state import StateManager
from src.orchestration.parallel_agent_coordinator import ParallelAgentCoordinator
from src.orchestration.subtask import SubTask
from src.plugins.registry import AgentRegistry


def create_example_subtasks(parent_task_id: int) -> List[SubTask]:
    """Create example subtasks for demonstration.

    Returns:
        List of SubTask instances with different parallel groups
    """
    return [
        # Parallel Group 1: Can execute in parallel
        SubTask(
            subtask_id=1,
            parent_task_id=parent_task_id,
            title="Implement User model",
            description="Create User model with SQLAlchemy ORM, including fields for username, email, password_hash, created_at, updated_at",
            estimated_complexity=30.0,
            estimated_duration_minutes=45,
            dependencies=[],
            parallelizable=True,
            parallel_group=1,
            status="pending",
            created_at=datetime.now()
        ),
        SubTask(
            subtask_id=2,
            parent_task_id=parent_task_id,
            title="Implement Product model",
            description="Create Product model with SQLAlchemy ORM, including fields for name, description, price, stock, created_at, updated_at",
            estimated_complexity=30.0,
            estimated_duration_minutes=45,
            dependencies=[],
            parallelizable=True,
            parallel_group=1,
            status="pending",
            created_at=datetime.now()
        ),
        SubTask(
            subtask_id=3,
            parent_task_id=parent_task_id,
            title="Implement Order model",
            description="Create Order model with SQLAlchemy ORM, including relationships to User and Product, fields for total, status, created_at",
            estimated_complexity=40.0,
            estimated_duration_minutes=60,
            dependencies=[],
            parallelizable=True,
            parallel_group=1,
            status="pending",
            created_at=datetime.now()
        ),

        # Parallel Group 2: Sequential (runs after Group 1)
        SubTask(
            subtask_id=4,
            parent_task_id=parent_task_id,
            title="Run model tests",
            description="Run all unit tests for User, Product, and Order models to verify correctness",
            estimated_complexity=20.0,
            estimated_duration_minutes=15,
            dependencies=[1, 2, 3],  # Depends on models being created
            parallelizable=False,
            parallel_group=2,  # Different group
            status="pending",
            created_at=datetime.now()
        )
    ]


def main():
    """Main example function."""
    # 1. Load configuration
    config = Config.load()

    # 2. Initialize StateManager
    state_manager = StateManager(
        database_url=config.get('database.url', 'sqlite:///obra.db')
    )
    state_manager.initialize_database()

    # 3. Create a project and task
    project = state_manager.create_project(
        name="E-commerce API",
        description="Build a RESTful API for e-commerce platform",
        working_directory="/workspace/ecommerce"
    )

    task = state_manager.create_task(
        project_id=project.id,
        task_data={
            'title': 'Implement database models',
            'description': 'Create SQLAlchemy models for User, Product, and Order',
            'status': 'pending',
            'assignee': 'claude_code'
        }
    )

    # 4. Create subtasks
    subtasks = create_example_subtasks(parent_task_id=task.id)

    # 5. Initialize agent factory
    def create_agent():
        """Create a new agent instance."""
        agent_type = config.get('agent.type', 'claude_code_local')
        agent_class = AgentRegistry.get(agent_type)
        agent = agent_class()

        # Initialize with config
        agent_config = config.get('agent.config', {})
        agent.initialize(agent_config)

        return agent

    # 6. Initialize ParallelAgentCoordinator
    coordinator = ParallelAgentCoordinator(
        state_manager=state_manager,
        agent_factory=create_agent,
        config={
            'max_parallel_agents': 5,
            'agent_timeout_seconds': 600,  # 10 minutes
            'retry_failed_agents': True,
            'max_retries': 2,
            'parallelization_strategy': 'file_based'
        }
    )

    # 7. Execute subtasks in parallel
    print(f"\nExecuting {len(subtasks)} subtasks in parallel...")
    print("=" * 60)

    results = coordinator.execute_parallel(
        subtasks=subtasks,
        parent_task=task,
        context={
            'project_id': project.id,
            'agent_config': config.get('agent.config', {})
        }
    )

    # 8. Display results
    print("\nExecution Results:")
    print("=" * 60)

    for result in results:
        status = result['status']
        status_emoji = "✅" if status == "completed" else "❌" if status == "failed" else "⏱️"

        print(f"\n{status_emoji} Subtask {result['subtask_id']}: {status.upper()}")
        print(f"   Duration: {result['duration_seconds']:.2f}s")

        if status == "completed":
            response = result['result']
            print(f"   Response: {response[:100]}..." if len(response) > 100 else f"   Response: {response}")
        elif status == "failed":
            print(f"   Error: {result['error']}")
        elif status == "timeout":
            print(f"   Error: Timed out")

    # 9. Summary statistics
    print("\n" + "=" * 60)
    print("Summary:")
    total_duration = sum(r['duration_seconds'] for r in results)
    max_duration = max(r['duration_seconds'] for r in results)
    successful = sum(1 for r in results if r['status'] == 'completed')
    failed = sum(1 for r in results if r['status'] == 'failed')
    timed_out = sum(1 for r in results if r['status'] == 'timeout')

    print(f"  Total Results: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Timed Out: {timed_out}")
    print(f"  Sequential Time: {total_duration:.2f}s")
    print(f"  Parallel Time: {max_duration:.2f}s")
    print(f"  Speedup: {total_duration / max_duration:.2f}x" if max_duration > 0 else "  Speedup: N/A")

    # 10. Retrieve parallel attempts from StateManager
    print("\n" + "=" * 60)
    print("Parallel Attempts Logged:")

    attempts = state_manager.get_parallel_attempts(task_id=task.id)
    for attempt in attempts:
        print(f"\n  Attempt ID: {attempt.id}")
        print(f"    Agents: {attempt.num_agents}")
        print(f"    Success: {attempt.success}")
        print(f"    Duration: {attempt.total_duration_seconds:.2f}s")
        print(f"    Speedup: {attempt.speedup_factor:.2f}x" if attempt.speedup_factor else "    Speedup: N/A")
        print(f"    Strategy: {attempt.parallelization_strategy}")
        if attempt.failure_reason:
            print(f"    Failure: {attempt.failure_reason}")


if __name__ == '__main__':
    # Run example
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
