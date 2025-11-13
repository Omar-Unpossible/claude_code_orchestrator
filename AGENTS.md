# Repository Guidelines

## Project Structure & Module Organization
Core runtime lives in `src/`: `core` (config/models), `orchestration`, `agents`, `llm`, `monitoring`, and `utils`, with entry points `orchestrator.py`, `cli.py`, and `interactive.py`. Tests mirror modules inside `tests/` using `test_*.py`. Config is stored in `config/` (edit `config/config.yaml` for database, agent, and LLM profiles). Prompts live in `prompts/`, templates in `templates/`, helper scripts in `scripts/`, and `docs/` hosts ADRs and guides. Use `examples/` for runnable presets and `docker-compose.yml` for container launches.

## Build, Test, and Development Commands
`pip install -r requirements-dev.txt` installs pytest, pylint, mypy, and black. Primary workflows:

```bash
pytest                         # unit + default markers
pytest -m "" --cov=src         # full suite incl. slow tests with coverage
pylint src/ && mypy src/       # static analysis + typing (target ≥9.0 score)
black src/ tests/              # auto-format to house style
python -m src.cli run --project 1   # orchestrator CLI loop
python run_obra_iterative.py        # sample iterative run with quality gating
```

## Coding Style & Naming Conventions
Python 3.10+, 4-space indentation, exhaustive type hints on public functions, and descriptive docstrings for orchestration boundaries. Modules/functions use `snake_case`, classes `PascalCase`, config keys stay `lower_snake`. Run `black --check` before committing; follow pylint guidance and only disable rules inline with justification. Prefer dataclasses in `core/models`, and keep prompt text in `prompts/` rather than inline strings.

## Testing Guidelines
Pytest discovers `test_*.py` under `tests/`. Default runs skip `slow`, so mark longer suites explicitly (`@pytest.mark.slow`). Keep tests deterministic—mock LLM calls unless verifying Ollama connectivity. Generate coverage via `pytest --cov=src --cov-report=term-missing`; aim ≥85% overall to maintain the README dashboard. New fixtures belong in `tests/conftest.py`, and test names should describe behavior (`test_execute_task_assigns_breakpoints`). Attach markers (`unit`, `integration`, `mock`, `requires_ollama`) to help CI filtering.

## Commit & Pull Request Guidelines
Commits follow Conventional Commits (`feat:`, `fix:`, `docs:`) as reflected in `git log`. Keep subject lines ≤72 characters, with bodies that mention validation (`Tests: pytest -m "" --cov=src`). PRs must link issues or ADRs, summarize orchestration impact, call out config/schema changes, and include lint/test output. Provide screenshots or logs when altering CLI or interactive UX. Avoid bundling prompt updates with runtime logic unless a shared ADR justifies it.

## Security & Configuration Tips
Never commit secrets; point sensitive values from `.env` files referenced inside `config/config.yaml` (e.g., `llm.base_url`). Inspect `alembic` migrations before applying and back up `orchestrator.db` prior to `alembic upgrade head`. When using Docker, put overrides in `docker-compose.override.yml` so the baseline remains reproducible for other contributors.
