# Environment
- Use `uv` for executing Python
- Use `ty check` for Python type checking and language server. Run after every change on a Python file.
- Use `ruff check` for Python linting. Run after every change on a Python file.

# Validation
- When you make a change to the logic of the report a new report must be generated retrieving fresh data from the network and the HTML generated report should be checked against the expected values.
- For quick UI / report-logic iteration without network access, generate a local test report from deterministic mock data: `uv run python scripts/generate_test_report.py`. It writes mock cache data into `data/` and runs the real `generate_report` pipeline, producing `reports/daily_report.html`.
