# Planning Hybrid Prompt Template

This template shows the structure of a hybrid prompt for task planning and decomposition.

## Format

```
<METADATA>
{
  "prompt_type": "planning",
  "task_id": <task_id>,
  "planning_context": {
    "planning_type": "decomposition|parallel_strategy|dependency_analysis|estimation",
    "complexity_estimate": {
      "overall_score": <0-100>,
      "estimated_tokens": <number>,
      "estimated_files": <number>,
      "estimated_duration_minutes": <number>,
      "should_decompose": <true|false>
    },
    "context": {
      "task_title": "<task_title>",
      "task_description": "<description>",
      "project_context": {
        "files": ["<file1.py>"],
        "dependencies": ["<dep1>"],
        "architecture": "<framework>"
      }
    }
  },
  "rules": [
    {
      "id": "PLAN_001",
      "name": "PARALLEL_AGENT_GUIDELINES",
      "description": "Identify independent subtasks for parallel execution",
      "severity": "medium"
    }
  ]
}
</METADATA>

<INSTRUCTION>
You are planning task execution for the Obra orchestration system.

**Planning Type**: <decomposition|parallel_strategy|dependency_analysis|estimation>

**Task Details**:
- Title: <task_title>
- Description: <task_description>
- Complexity: <complexity_score>/100
- Estimated Duration: <estimated_duration> minutes
- Should Decompose: <yes|no>

**Project Context**:
<project_details>

**Your Task**:
1. Analyze task complexity and dependencies
2. Break down into subtasks if needed
3. Identify which subtasks can run in parallel
4. Estimate time and resources for each subtask
5. Create execution plan with dependencies

**Output Format**:
<METADATA>
{
  "decomposition_needed": <true|false>,
  "subtasks": [
    {
      "subtask_id": <id>,
      "title": "<subtask_title>",
      "description": "<subtask_description>",
      "estimated_duration_minutes": <number>,
      "dependencies": [<subtask_ids>],
      "can_parallelize": <true|false>,
      "parallel_group": <group_number>,
      "complexity": <0-100>,
      "files_to_modify": ["<file1.py>"],
      "risks": ["<risk1>"]
    }
  ],
  "execution_strategy": "sequential|parallel|hybrid",
  "parallel_groups": [
    {
      "group_id": <id>,
      "subtasks": [<subtask_ids>],
      "estimated_duration_minutes": <number>
    }
  ],
  "total_estimated_duration_minutes": <number>,
  "confidence": <0.0-1.0>
}
</METADATA>

<CONTENT>
**Task Analysis**:
<complexity_and_dependency_analysis>

**Decomposition Strategy**:
<how_task_was_broken_down>

**Parallel Execution Plan**:
<which_subtasks_can_run_together>

**Risk Assessment**:
<potential_issues_and_mitigation>
</CONTENT>
</INSTRUCTION>
```

## Example

```
<METADATA>
{
  "prompt_type": "planning",
  "task_id": 145,
  "planning_context": {
    "planning_type": "decomposition",
    "complexity_estimate": {
      "overall_score": 78,
      "estimated_tokens": 12000,
      "estimated_files": 6,
      "estimated_duration_minutes": 180,
      "should_decompose": true
    },
    "context": {
      "task_title": "Implement complete e-commerce checkout system",
      "task_description": "Build a complete checkout flow including cart management, payment processing (Stripe integration), order creation, email notifications, and inventory updates. Must handle edge cases like payment failures, stock depletion, and concurrent orders.",
      "project_context": {
        "files": ["src/cart/", "src/payments/", "src/orders/", "src/inventory/"],
        "dependencies": ["stripe", "celery", "redis"],
        "architecture": "Django REST API"
      }
    }
  },
  "rules": [
    {
      "id": "PLAN_001",
      "name": "PARALLEL_AGENT_GUIDELINES",
      "description": "Identify independent subtasks for parallel execution",
      "severity": "medium"
    },
    {
      "id": "PLAN_002",
      "name": "DEPENDENCY_ANALYSIS",
      "description": "Map all dependencies before parallel execution",
      "severity": "high"
    }
  ]
}
</METADATA>

<INSTRUCTION>
You are planning task execution for the Obra orchestration system.

**Planning Type**: decomposition

**Task Details**:
- Title: Implement complete e-commerce checkout system
- Description: Build checkout flow with cart, payments, orders, notifications, inventory
- Complexity: 78/100 (HIGH)
- Estimated Duration: 180 minutes
- Should Decompose: YES

**Project Context**:
- Framework: Django REST API
- Modules: cart, payments, orders, inventory
- Dependencies: stripe, celery, redis
- Architecture: Microservices with async task queue

**Your Task**:
Break this complex task into manageable subtasks, identify parallel execution opportunities, and create an execution plan.

**Output Format**:
<METADATA>
{
  "decomposition_needed": true,
  "subtasks": [...],
  "execution_strategy": "hybrid",
  "parallel_groups": [...],
  "total_estimated_duration_minutes": 120
}
</METADATA>

<CONTENT>
...analysis...
</CONTENT>
</INSTRUCTION>
```

**Expected Response**:
```
<METADATA>
{
  "decomposition_needed": true,
  "subtasks": [
    {
      "subtask_id": 1,
      "title": "Implement cart management module",
      "description": "Add/remove items, update quantities, calculate totals, apply discounts",
      "estimated_duration_minutes": 25,
      "dependencies": [],
      "can_parallelize": true,
      "parallel_group": 1,
      "complexity": 35,
      "files_to_modify": ["src/cart/models.py", "src/cart/views.py", "tests/test_cart.py"],
      "risks": ["Concurrent cart updates"]
    },
    {
      "subtask_id": 2,
      "title": "Implement inventory management",
      "description": "Check stock, reserve items, handle stock depletion",
      "estimated_duration_minutes": 30,
      "dependencies": [],
      "can_parallelize": true,
      "parallel_group": 1,
      "complexity": 45,
      "files_to_modify": ["src/inventory/models.py", "src/inventory/services.py", "tests/test_inventory.py"],
      "risks": ["Race conditions in stock updates", "Overselling items"]
    },
    {
      "subtask_id": 3,
      "title": "Integrate Stripe payment processing",
      "description": "Create payment intents, handle webhooks, process refunds",
      "estimated_duration_minutes": 35,
      "dependencies": [],
      "can_parallelize": true,
      "parallel_group": 1,
      "complexity": 50,
      "files_to_modify": ["src/payments/stripe_integration.py", "src/payments/webhooks.py", "tests/test_payments.py"],
      "risks": ["Stripe API changes", "Webhook replay attacks", "Failed payments"]
    },
    {
      "subtask_id": 4,
      "title": "Create order management system",
      "description": "Create orders, track status, handle cancellations",
      "estimated_duration_minutes": 30,
      "dependencies": [1, 2, 3],
      "can_parallelize": false,
      "parallel_group": 2,
      "complexity": 40,
      "files_to_modify": ["src/orders/models.py", "src/orders/services.py", "tests/test_orders.py"],
      "risks": ["Order state consistency"]
    },
    {
      "subtask_id": 5,
      "title": "Implement email notifications",
      "description": "Send order confirmation, payment receipts, failure notifications",
      "estimated_duration_minutes": 20,
      "dependencies": [4],
      "can_parallelize": false,
      "parallel_group": 3,
      "complexity": 25,
      "files_to_modify": ["src/notifications/email_service.py", "templates/emails/"],
      "risks": ["Email delivery failures"]
    },
    {
      "subtask_id": 6,
      "title": "Integrate checkout flow orchestration",
      "description": "Coordinate cart → payment → inventory → order → notification flow",
      "estimated_duration_minutes": 25,
      "dependencies": [1, 2, 3, 4, 5],
      "can_parallelize": false,
      "parallel_group": 4,
      "complexity": 55,
      "files_to_modify": ["src/checkout/orchestrator.py", "tests/test_checkout_integration.py"],
      "risks": ["Transaction rollback complexity", "Partial failure scenarios"]
    }
  ],
  "execution_strategy": "hybrid",
  "parallel_groups": [
    {
      "group_id": 1,
      "subtasks": [1, 2, 3],
      "estimated_duration_minutes": 35,
      "description": "Independent modules - cart, inventory, payments (parallel)"
    },
    {
      "group_id": 2,
      "subtasks": [4],
      "estimated_duration_minutes": 30,
      "description": "Order system (depends on group 1)"
    },
    {
      "group_id": 3,
      "subtasks": [5],
      "estimated_duration_minutes": 20,
      "description": "Notifications (depends on orders)"
    },
    {
      "group_id": 4,
      "subtasks": [6],
      "estimated_duration_minutes": 25,
      "description": "Checkout orchestration (integration)"
    }
  ],
  "total_estimated_duration_minutes": 110,
  "confidence": 0.82,
  "notes": "Parallel execution of group 1 saves ~60 minutes vs sequential (35 min vs 90 min)"
}
</METADATA>

<CONTENT>
**Task Analysis**:

This is a HIGH complexity task (78/100) with multiple independent modules that can benefit from decomposition and parallel execution:

1. **Independent Modules** (can parallelize):
   - Cart management (no external dependencies)
   - Inventory management (standalone logic)
   - Stripe payment integration (external API)

2. **Dependent Modules** (must be sequential):
   - Order system (needs cart, inventory, payments)
   - Notifications (needs order system)
   - Checkout orchestration (integrates everything)

**Decomposition Strategy**:

Break into 6 subtasks arranged in 4 execution groups:

**Group 1 (PARALLEL)** - 35 minutes (vs 90 sequential):
- Subtask 1: Cart management
- Subtask 2: Inventory management
- Subtask 3: Stripe integration

These modules have NO shared files and NO shared dependencies, perfect for parallel execution by 3 agents.

**Group 2 (SEQUENTIAL)** - 30 minutes:
- Subtask 4: Order management (requires all Group 1 modules)

**Group 3 (SEQUENTIAL)** - 20 minutes:
- Subtask 5: Email notifications (requires orders)

**Group 4 (SEQUENTIAL)** - 25 minutes:
- Subtask 6: Checkout orchestration (integration testing)

**Parallel Execution Plan**:

1. **Deploy 3 agents** for Group 1 (cart, inventory, payments)
   - Duration: 35 min (max of the three)
   - Savings: 55 minutes vs sequential

2. **Single agent** for Group 2 (orders) - 30 min
3. **Single agent** for Group 3 (notifications) - 20 min
4. **Single agent** for Group 4 (orchestration) - 25 min

**Total Duration**: 110 minutes (vs 180 sequential = 39% faster)

**Risk Assessment**:

1. **Concurrent cart updates**: Use Redis locks in cart module
2. **Inventory overselling**: Implement atomic stock reservations
3. **Stripe webhooks**: Add idempotency keys
4. **Transaction rollbacks**: Design compensation logic in orchestrator
5. **Partial failures**: Implement saga pattern for distributed transactions

**Mitigation**:
- Add integration tests for concurrent scenarios
- Use database transactions for atomic operations
- Implement retry logic with exponential backoff
- Add monitoring for payment webhook delivery

**Confidence**: 82% - The decomposition is clean with clear boundaries, but checkout orchestration (subtask 6) may reveal integration issues that require iteration.
</CONTENT>
```

## Best Practices

1. **Analyze dependencies first** - Can't parallelize dependent tasks
2. **Look for shared files** - File conflicts block parallelization
3. **Estimate accurately** - Use complexity heuristics
4. **Identify risks** - What could go wrong in each subtask?
5. **Group by independence** - Tasks with no dependencies go together
6. **Calculate savings** - Show time saved by parallelization
7. **Plan integration** - How do subtasks come together?
8. **Consider rollback** - What if a subtask fails mid-execution?
