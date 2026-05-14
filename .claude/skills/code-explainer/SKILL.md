---
name: code-explainer
description: "Analyzes code and produces four types of output: (1) line-by-line plain-English explanation of what the code does, (2) identification of design patterns used and where, (3) prioritized improvement suggestions with before/after snippets, (4) beginner-friendly documentation in docstring or markdown format. Use when a user asks to 'explain this code', 'document this function', 'what pattern is this?', 'how can I improve this?', or shares a code snippet and wants to understand or improve it. Works with any language."
---

# Code Explainer

## Workflow

When given code, determine which output(s) the user wants, then produce them in order:

1. **Explain** — line-by-line walkthrough
2. **Patterns** — design patterns detected (load `references/design-patterns.md` if needed)
3. **Improve** — ranked suggestions with before/after code
4. **Document** — beginner-friendly docstring or markdown docs

If the user does not specify, produce all four sections.

---

## 1. Line-by-Line Explanation

Walk through the code in logical blocks (not necessarily every single line — group trivial lines). Use plain English a junior developer can follow. Format:

````markdown
```python
def validate_token(token: str) -> bool:   # (1)
    if not token:                          # (2)
        return False
    return hmac.compare_digest(           # (3)
        token, SECRET
    )
```

1. **Function signature** — `validate_token` takes a string and returns True/False.
2. **Guard clause** — immediately returns False for empty/None tokens, avoiding wasted work.
3. **Constant-time comparison** — `hmac.compare_digest` prevents timing attacks that plain `==` would allow.
````

Rules:
- Number annotations match comments in the code block.
- Explain the *why*, not just the *what*.
- Flag anything surprising, security-relevant, or non-obvious.

---

## 2. Design Patterns

Identify patterns present and where they appear. For each:

```markdown
### Strategy Pattern
**Location:** `Sorter.__init__` (line 12) — `sort_fn` parameter
**What it does:** Swaps the sorting algorithm at runtime without changing the caller.
**Why it's used here:** Allows unit tests to inject a predictable sort without touching production logic.
```

Load `references/design-patterns.md` for the full catalog when you need to identify a pattern by name or confirm its intent.

If no named pattern applies, note the structural choices made (e.g., "guard clauses to flatten nesting", "dependency injection via constructor").

---

## 3. Improvement Suggestions

List up to 5 improvements, ranked by impact (high → low). For each:

```markdown
### [HIGH] Replace bare `except` with specific exception types
**Why:** Bare `except` catches `SystemExit` and `KeyboardInterrupt`, masking real errors.
**Before:**
```python
try:
    result = process(data)
except:
    return None
```
**After:**
```python
try:
    result = process(data)
except (ValueError, KeyError) as e:
    logger.warning("Processing failed: %s", e)
    return None
```
```

Impact levels: `[HIGH]` correctness/security/data-loss risk · `[MEDIUM]` maintainability/performance · `[LOW]` style/readability.

Do not suggest improvements that add complexity without clear benefit.

---

## 4. Beginner-Friendly Documentation

Generate documentation at a level a junior developer can use. Choose the format based on context:

- **Function/class in Python** → Google-style docstring
- **Module or file** → Markdown section with purpose, usage example, and parameter table
- **Any other language** → Markdown block comment or JSDoc as appropriate

### Python docstring example

```python
def validate_file_path(file_path: str) -> str:
    """Checks that a file path is safe to use before opening it.

    Prevents common attacks like path traversal (``../../etc/passwd``)
    and rejects files outside the allowed upload directory.

    Args:
        file_path: The path string provided by the user.

    Returns:
        The resolved absolute path as a string if all checks pass.

    Raises:
        ValueError: If the path is empty, contains ``..``, points outside
            the allowed directory, or has a disallowed file extension.
        FileNotFoundError: If the file does not exist.

    Example:
        >>> validate_file_path("/uploads/report.pdf")
        '/workspaces/project/uploads/report.pdf'
    """
```

### Markdown module doc example

```markdown
## `upload_handler.py`

Handles secure document ingestion into DocuMind.

**Main entry point:** `analyze_document(file_path)` — validates, reads, and returns metadata for a file.

| Function | What it does |
|---|---|
| `validate_file_path` | Checks the path is safe and within the upload directory |
| `read_document` | Reads the file as UTF-8 text |
| `extract_metadata` | Counts lines/words and reads filesystem stats |
| `analyze_document` | Orchestrates the above three steps |

**Quick example:**
```python
result = analyze_document("/uploads/notes.txt")
print(result["metadata"]["word_count"])  # 42
```
```

---

## Resources

- `references/design-patterns.md` — catalog of common patterns with intent and detection cues; load when identifying or explaining patterns.
