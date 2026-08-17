# Environment
- Use `uv` for executing Python
- Use `ty check` for Python type checking and language server. Run after every change on a Python file.
- Use `ruff check` for Python linting. Run after every change on a Python file.
- If a CLI tool such as `ty` or `ruff` is not installed in the environment, run it on demand with `uvx`, e.g. `uvx ty check <path>` or `uvx ruff check <path>`. This executes the package in an isolated ephemeral environment without adding it to the project.

# Validation
- When you make a change to the logic of the report a new report must be generated retrieving fresh data from the network and the HTML generated report should be checked against the expected values.
