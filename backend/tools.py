"""
tools.py
--------
Built-in tools the assistant can use:
  - calculator      : evaluate math expressions
  - read_file       : read a local file
  - write_file      : write content to a local file
  - list_files      : list files in a folder
  - web_search      : DuckDuckGo search (online only)
  - get_datetime    : current date and time
"""

import os
import math
from datetime import datetime
from backend.router import is_online


# ─── Helper: safe math evaluator ────────────────────────────────────────────

def _safe_eval(expr: str) -> str:
    allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    allowed.update({"abs": abs, "round": round, "pow": pow})
    try:
        result = eval(expr, {"__builtins__": {}}, allowed)  # noqa: S307
        return str(result)
    except Exception as e:
        return f"Error: {e}"


# ─── Tool definitions ────────────────────────────────────────────────────────

def calculator(expression: str) -> str:
    """Evaluate a mathematical expression and return the result."""
    return _safe_eval(expression)


def read_file(path: str) -> str:
    """Read and return the contents of a local file."""
    try:
        with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {path}"
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(args: str) -> str:
    """
    Write content to a file.
    Input format: 'filepath|||content'
    """
    if "|||" not in args:
        return "Error: use format 'filepath|||content'"
    path, content = args.split("|||", 1)
    try:
        os.makedirs(os.path.dirname(os.path.expanduser(path)) or ".", exist_ok=True)
        with open(os.path.expanduser(path), "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def list_files(folder: str = ".") -> str:
    """List all files in a folder."""
    try:
        items = os.listdir(os.path.expanduser(folder))
        return "\n".join(sorted(items)) if items else "(empty folder)"
    except Exception as e:
        return f"Error: {e}"


def get_datetime(_: str = "") -> str:
    """Return current date and time."""
    return datetime.now().strftime("%A, %d %B %Y  %I:%M %p")


def web_search(query: str) -> str:
    """Search the web using DuckDuckGo (only available when online)."""
    if not is_online():
        return "Web search is not available in offline mode."
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=4))
        if not results:
            return "No results found."
        output = []
        for r in results:
            output.append(f"**{r['title']}**\n{r['body']}\nSource: {r['href']}\n")
        return "\n---\n".join(output)
    except Exception as e:
        return f"Search error: {e}"


# ─── Registry: maps tool name → (function, description) ─────────────────────

TOOL_REGISTRY: dict[str, dict] = {
    "calculator": {
        "fn": calculator,
        "description": "Evaluate math. Input: a math expression like '2 ** 10' or 'sqrt(144)'",
    },
    "read_file": {
        "fn": read_file,
        "description": "Read a local file. Input: file path like '~/notes.txt'",
    },
    "write_file": {
        "fn": write_file,
        "description": "Write to a file. Input: 'filepath|||content'",
    },
    "list_files": {
        "fn": list_files,
        "description": "List files in a directory. Input: folder path",
    },
    "get_datetime": {
        "fn": get_datetime,
        "description": "Get the current date and time. No input needed.",
    },
    "web_search": {
        "fn": web_search,
        "description": "Search the web (online only). Input: search query",
    },
}
