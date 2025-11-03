# Complex Task Ideas for Iterative Obra Testing

These tasks are designed to require multiple iterations (3-10 cycles) to complete, showcasing the Obra↔Claude iterative loop.

---

## ⭐ Task 1: CSV Processing CLI Tool (Recommended - Already in script)

**Complexity:** Medium-High
**Expected Iterations:** 3-5
**Files:** 4-5 Python files + tests + sample data

**Why this is good:**
- Requires architectural planning (multiple modules)
- Clear validation criteria (does it work with test data?)
- Natural progression: basic structure → error handling → tests → edge cases
- Easy to verify success (run the tool!)

**Prompt already included in `run_obra_iterative.py`**

---

## Task 2: Web Scraper with Rate Limiting

**Complexity:** High
**Expected Iterations:** 4-7
**Files:** 5-6 Python files + tests + config

```python
USER_PROMPT = """
Build a web scraper called 'webscraper' that extracts article titles and URLs from a news website.

Requirements:

1. Core functionality:
   - Fetch HTML from specified URL
   - Parse HTML to extract article titles and links
   - Save results to JSON file
   - Support pagination (multiple pages)

2. Architecture:
   - Main script: scraper.py
   - HTTP client module: http_client.py (with retry logic)
   - HTML parser module: parser.py
   - Rate limiter module: rate_limiter.py
   - Storage module: storage.py

3. Features:
   - Configurable rate limiting (requests per second)
   - Automatic retry on HTTP errors (with exponential backoff)
   - User-agent rotation
   - Respect robots.txt
   - Command-line interface with argparse

4. Quality requirements:
   - Comprehensive error handling (network errors, parsing errors, etc.)
   - Unit tests for each module (use pytest)
   - Integration test with mock HTTP responses
   - Proper logging (use Python logging module)
   - Type hints and docstrings
   - Configuration file (YAML or JSON)

5. Example usage:
   python scraper.py --url "https://example.com/news" --pages 3 --rate-limit 2 --output articles.json
"""
```

**Why this is challenging:**
- Multiple failure modes (network, parsing, rate limits)
- Requires coordination between modules
- Testing requires mocking
- Configuration management adds complexity

---

## Task 3: Data Pipeline with Validation

**Complexity:** Medium-High
**Expected Iterations:** 4-6
**Files:** 6-7 Python files + tests + schemas

```python
USER_PROMPT = """
Build a data processing pipeline that validates, transforms, and aggregates data from CSV files.

Requirements:

1. Pipeline stages:
   - Stage 1: Read CSV files from input directory
   - Stage 2: Validate data against JSON schema
   - Stage 3: Clean/transform data (handle missing values, normalize formats)
   - Stage 4: Aggregate data (group by, sum, average)
   - Stage 5: Write results to output CSV

2. Architecture:
   - Main pipeline: pipeline.py
   - Data reader module: reader.py
   - Validation module: validator.py (use jsonschema library)
   - Transformation module: transformer.py
   - Aggregation module: aggregator.py
   - Writer module: writer.py

3. Features:
   - Configurable pipeline via YAML config
   - Detailed error reporting (which rows failed validation, why)
   - Progress tracking (log progress for large files)
   - Dry-run mode (validate without writing output)

4. Quality requirements:
   - Comprehensive error handling
   - Unit tests for each stage (use pytest)
   - Integration test with sample data
   - Generate data quality report (CSV with validation results)
   - Type hints and docstrings

5. Include:
   - sample_input.csv (test data with some invalid rows)
   - schema.json (validation schema)
   - config.yaml (pipeline configuration)
"""
```

**Why this is challenging:**
- Clear stages that can be implemented incrementally
- Validation errors will trigger iterations
- Integration between components needs testing
- Quality report provides measurable success criteria

---

## Task 4: REST API with Database

**Complexity:** High
**Expected Iterations:** 5-8
**Files:** 8-10 Python files + tests + database

```python
USER_PROMPT = """
Build a REST API for a simple task management system using Flask and SQLite.

Requirements:

1. API Endpoints:
   - POST /tasks - Create new task
   - GET /tasks - List all tasks (with filtering)
   - GET /tasks/<id> - Get specific task
   - PUT /tasks/<id> - Update task
   - DELETE /tasks/<id> - Delete task

2. Architecture:
   - Main app: app.py (Flask application)
   - Database module: database.py (SQLAlchemy models)
   - API routes module: routes.py
   - Validation module: validators.py
   - Error handlers module: errors.py

3. Task model:
   - id (auto-generated)
   - title (required, max 200 chars)
   - description (optional)
   - status (pending/in_progress/completed)
   - priority (1-5)
   - created_at, updated_at (auto-managed)

4. Features:
   - Input validation (use marshmallow or pydantic)
   - Proper HTTP status codes
   - Error responses in JSON format
   - Pagination for list endpoint
   - Filtering by status and priority

5. Quality requirements:
   - Comprehensive error handling
   - Unit tests for each endpoint (use pytest + Flask test client)
   - Integration tests for full CRUD workflow
   - Database migrations (use Alembic or Flask-Migrate)
   - API documentation (docstrings with examples)
   - Sample requests in README

6. Include:
   - requirements.txt (Flask, SQLAlchemy, etc.)
   - Example curl commands to test the API
"""
```

**Why this is challenging:**
- Many components to implement
- Database integration adds complexity
- Testing requires request mocking
- CRUD operations must all work correctly
- Will naturally take multiple iterations to get all endpoints working

---

## Task 5: Log Analyzer CLI Tool

**Complexity:** Medium
**Expected Iterations:** 3-5
**Files:** 5-6 Python files + tests + sample logs

```python
USER_PROMPT = """
Build a command-line tool called 'loganalyzer' that analyzes server log files.

Requirements:

1. Core functionality:
   - Parse log files (Apache/Nginx format)
   - Extract metrics (request count, response codes, top URLs, errors)
   - Generate summary report
   - Export to JSON or CSV

2. Architecture:
   - Main script: loganalyzer.py
   - Parser module: log_parser.py
   - Analyzer module: analyzer.py
   - Reporter module: reporter.py

3. Analysis features:
   - Total requests
   - Requests per minute/hour
   - Status code distribution (200, 404, 500, etc.)
   - Top 10 requested URLs
   - Top 10 IPs by request count
   - Error rate (4xx, 5xx percentage)

4. Command syntax:
   loganalyzer --file access.log --format json --output report.json
   loganalyzer --file access.log --format text --top 20

5. Quality requirements:
   - Handle large files efficiently (streaming, not load all in memory)
   - Comprehensive error handling
   - Unit tests for parser and analyzer
   - Integration test with sample log file
   - Type hints and docstrings
   - Progress bar for large files (use tqdm)

6. Include:
   - sample_access.log (realistic test data)
   - Example output showing what the report looks like
"""
```

**Why this is challenging:**
- Real-world problem with measurable output
- Parsing logic can be tricky (regex patterns)
- Multiple output formats require abstraction
- Performance considerations (large files)
- Report generation provides clear success criteria

---

## Task 6: Configuration Manager Library

**Complexity:** Medium-High
**Expected Iterations:** 4-6
**Files:** 6-7 Python files + tests + examples

```python
USER_PROMPT = """
Build a Python library called 'configmanager' for managing application configuration from multiple sources.

Requirements:

1. Core functionality:
   - Load config from YAML, JSON, TOML files
   - Load config from environment variables
   - Merge configs with priority order
   - Validate config against schema
   - Provide type-safe config access

2. Architecture:
   - Main module: config_manager.py
   - Loaders: yaml_loader.py, json_loader.py, toml_loader.py, env_loader.py
   - Validator: schema_validator.py
   - Merger: config_merger.py

3. Features:
   - Hierarchical config (nested dictionaries)
   - Environment variable override (e.g., APP_DATABASE_HOST)
   - Config validation with JSON Schema
   - Default values
   - Immutable config (frozen after load)

4. Usage example:
   ```python
   from configmanager import ConfigManager

   config = ConfigManager()
   config.add_file('default.yaml')
   config.add_file('local.yaml')  # Overrides defaults
   config.add_env_vars(prefix='APP_')
   config.validate('schema.json')
   config.freeze()

   db_host = config.get('database.host')
   db_port = config.get('database.port', default=5432)
   ```

5. Quality requirements:
   - Comprehensive error handling (file not found, invalid format, etc.)
   - Unit tests for each loader (use pytest)
   - Unit tests for merger and validator
   - Integration test with real config files
   - Type hints and docstrings
   - Full documentation with examples

6. Include:
   - example_default.yaml
   - example_schema.json
   - example_usage.py (demonstrates the API)
"""
```

**Why this is challenging:**
- Library design (reusable API)
- Multiple input formats
- Complex merging logic
- Schema validation adds complexity
- Good test coverage is critical for libraries

---

## Recommendation

**Start with Task 1 (CSV Tool)** - it's already in `run_obra_iterative.py` and provides the best balance of:
- ✅ Clear requirements
- ✅ Multiple modules to implement
- ✅ Natural progression (basic → error handling → tests)
- ✅ Easy to verify (run it with test data)
- ✅ Will take 3-5 iterations

**Then try Task 5 (Log Analyzer)** for a different domain but similar complexity.

**Save Task 4 (REST API)** for when you want to test 5-8 iterations with a more complex task.

---

## Adjusting Complexity

You can make any task **easier** by:
- Reducing number of modules
- Removing test requirements
- Simplifying features (no edge cases)

You can make any task **harder** by:
- Adding more modules
- Requiring integration tests
- Adding performance requirements
- Requiring documentation generation
- Adding CI/CD configuration

---

## Expected Iteration Pattern

**Iteration 1:** Basic structure, maybe 1-2 modules
- Quality: 0.3-0.5
- Issues: "Missing modules X, Y, Z. No tests. No error handling."

**Iteration 2:** More modules, basic functionality working
- Quality: 0.5-0.7
- Issues: "Tests missing for module X. Error handling incomplete. Edge cases not handled."

**Iteration 3:** Tests added, error handling improved
- Quality: 0.7-0.85
- Issues: "Integration test missing. Docstrings incomplete. Edge case X not handled."

**Iteration 4 (if needed):** Polish, edge cases, full test coverage
- Quality: 0.85-0.95
- Issues: "Minor: Could add more example usage. Otherwise complete."

---

## Running the Test

```bash
source venv/bin/activate
python run_obra_iterative.py
```

**Expected output:**
```
ITERATION 1/3
[1/5] First iteration - no context yet
[1/5] Obra enhancing your prompt...
✓ Enhanced (10.4s)
[1/5] Claude Code executing task...
✓ Response received (45.2s, 3421 chars)
[1/5] Obra validating results...
✓ Validated (2.1s)
  Completed: False
  Quality: 0.45
  Issues: Missing test_calculator.py, No error handling for division by zero
[1/5] Decision making...
⚠️ RETRY - Quality 0.45 < 0.75 or incomplete
  Continuing to iteration 2...

ITERATION 2/3
[2/5] Context built from 1 previous iteration(s)
...
```

The log file will contain full details of all iterations.
