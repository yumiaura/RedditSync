# Code Style Guidelines (Python)

> **Standard:** follow **PEP 8** strictly.  
> **Single deviation from PEP 8:** **maximum line length — 99 characters** (for code, comments, and docstrings). This is an **internally accepted team standard**.

---

## Base Settings
- Encoding: **UTF-8**  
- End of line: **LF**  
- Indentation: **4 spaces**, tabs are prohibited  
- Strip trailing whitespace; ensure **exactly one newline at EOF**

## Imports
- Order: standard library, third-party, then local
- Use **absolute** imports; one module per line
- Do not use `from x import *`
- Separate import groups with **one** blank line

## Naming
- **functions, variables:** `snake_case`  
- **Classes, Exceptions:** `CapWords`  
- **constants:** `UPPER_CASE`  
- **private/internal:** prefix with `_name`  
- Module names: short, `lowercase_with_underscores`

## Whitespace & Expressions
- Around binary operators: `a + b`, `x == y`; do not column-align operators
- Space after commas: `func(a, b, c)`
- No spaces inside brackets/parentheses: `list[1]`, `func(a, b)`  
- Slices: `seq[i:j]` (no extra spaces like `seq[i : j]`)
- Quotes: prefer **double quotes** (`"..."`) by default; be consistent

## Blank Lines
- **Two** blank lines between top-level declarations
- **One** blank line between methods inside a class
- Avoid excessive blank lines (no multiple consecutive blank lines)

## Docstrings & Comments
- Docstrings use **triple double quotes** `"""..."""`, written **in English**
- One-line docstrings stay on one line: `"""Return cached value."""`
- Multi-line docstrings: short summary, blank line, then details  
- Document parameters/returns/exceptions (`Args:`, `Returns:`, `Raises:` or Google/NumPy style — choose one and be consistent)
- Comments explain **why**, not **what**; keep them up to date

## Type Annotations
- Add where reasonable: parameters and return types
- Prefer modern forms: `list[int]`, `dict[str, Any]`, `X | None`
- Avoid `Any` when practical
- For larger contracts, use `Protocol`, `TypedDict`, `NewType` where appropriate

## Code Organization
- Functions and modules should have a **single, narrow responsibility**; prefer **small, reusable** building blocks
- **Prefer functional programming:**  
  avoid creating **unnecessary classes** when a **simple function** suffices  
  (pure functions, explicit inputs/outputs, minimal hidden state)
- Use early returns instead of deep nesting
- Don’t cram too much into single expressions—split into well-named steps

## Exceptions & Error Logic
- Raise exceptions at the point of failure; don’t swallow them silently
- Catch locally and convert to domain-specific exceptions when needed
- Error messages are **in English**, concise and informative

## Formatting & Linting Tooling
- **Black** (configured with `line-length = 99`) — auto-formatting
- **Ruff** — linting (including PEP 8 rules), `line-length = 99`
- **isort** — import sorting (profile `black`, `line_length = 99`)
- **mypy** — static type checking (adopt incrementally)

### Example `pyproject.toml`
```toml
[tool.black]
line-length = 99
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 99

[tool.ruff]
line-length = 99
target-version = "py311"
select = ["E", "F", "W", "I", "UP", "B"]
ignore = ["E203"]  # compatibility with Black

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true
disallow_untyped_defs = true
```

---

## Intentional PEP 8 Deviation
- **Line length: 99 characters** (PEP 8 suggests 79/72). This is an **internally accepted team standard** and is mandatory for all new and modified files.
