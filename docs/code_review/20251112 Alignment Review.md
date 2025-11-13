 Alignment Review

  - The core orchestration loop is implemented as advertised: Orchestrator wires StateManager, agents, prompt generator, validation, decision engine, complexity estimator, etc., matching the “local LLM supervises
    Claude Code” design in the README (README.md:1-23, src/orchestrator.py:60-145). Continuous decisioning, quality gating, and max-turn handling live where the system design doc says they should (docs/architecture/
    system_design.md:7-189).
  - Command-line tooling like run_obra.py demonstrates the intended workflow (prompt enhancement → Claude execution → validation), proving the components can collaborate to deliver semi-autonomous work when plumbed together
    manually (run_obra.py:1-210).

  Gaps vs. Desired Workflow

  - Interactive mode routes “natural language” input to cmd_to_orch, which only calls NLCommandProcessor rather than the orchestrator loop; nothing ever reaches Orchestrator.execute_task from that entry point (src/
    interactive.py:200-242, src/interactive.py:700-731). This contradicts the desired “prompt → orchestrator → implementer LLM” path.
  - The NL pipeline itself is a rigid CRUD classifier: it forces every message through operation/entity/identifier/parameter stages and rejects anything outside that schema (src/nl/nl_command_processor.py:291-404, src/nl/
    types.py:22-157). When classification fails, users get errors instead of the orchestrator improvising or asking for clarification, so the workflow stalls at step one.
  - Even when the pipeline succeeds, execution goes straight to CommandExecutor/StateManager (create/update/delete/query) without involving the orchestrator, meaning no prompt optimization, implementer invocation, or multi-
    turn guidance occurs (src/nl/command_executor.py:123-220). The orchestrator’s validation and retry machinery are bypassed entirely for NL-sourced commands.
  - Safety promises from ADR-016 are only partially realized: destructive operations require confirmation, but the TODO comment notes confirmations aren’t actually handled, so the pipeline just returns an error for updates/
    deletes instead of escalating via orchestrator breakpoints (src/nl/command_executor.py:158-171). This is another sign the NL path is isolated from the system’s main control logic.

  Opportunities

  - Unify the entry point so every prompt is turned into an orchestrator-managed task; the current split between NLCommandProcessor and orchestrator logic is the primary blocker to delivering the documented workflow.
  - Reuse ADR-016 components as helper tools the orchestrator can invoke when it decides a structured CRUD change is required, rather than as a mandatory gate that prevents the orchestrator from even seeing many user
    intents.
  - Invest in confirmation/breakpoint handling within the orchestrator rather than leaving TODOs in the isolated command executor; that keeps all safety checks consistent with the rest of the decision loop.