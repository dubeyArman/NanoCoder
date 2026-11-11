"""High-density repository indexing for minimal token footprint."""

import os
import ast
from typing import List, Dict


class RepoIndexer:
    """Generates an ultra-compact map of repo structure and key symbols."""

    EXCLUDE_DIRS = {
        ".git", "__pycache__", "venv", ".venv", "env", "node_modules",
        ".pytest_cache", ".ruff_cache", ".mypy_cache", "dist", "build", ".egg-info"
    }

    EXCLUDE_EXTS = {
        ".pyc", ".pyo", ".pyd", ".png", ".jpg", ".jpeg", ".ico", ".svg",
        ".lock", ".log", ".tmp", ".cache"
    }

    @classmethod
    def index_repository(cls, workspace_root: str, max_files: int = 40) -> str:
        """Creates a compact index of files and top-level definitions."""
        lines: List[str] = []
        file_count = 0

        for root, dirs, files in os.walk(workspace_root):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in cls.EXCLUDE_DIRS and not d.startswith(".")]

            rel_root = os.path.relpath(root, workspace_root)
            if rel_root == ".":
                depth = 0
            else:
                depth = rel_root.count(os.sep) + 1

            indent = "  " * depth
            if rel_root != ".":
                lines.append(f"{indent}📁 {os.path.basename(root)}/")

            for file in sorted(files):
                if file.startswith(".") or any(file.endswith(ext) for ext in cls.EXCLUDE_EXTS):
                    continue

                file_count += 1
                if file_count > max_files:
                    lines.append(f"{indent}  ... [+{len(files) - file_count} more files]")
                    break

                rel_file_path = os.path.join(rel_root, file) if rel_root != "." else file
                full_file_path = os.path.join(root, file)

                # If Python file, extract quick top-level symbols
                symbols_summary = ""
                if file.endswith(".py"):
                    symbols_summary = cls._extract_top_symbols(full_file_path)

                if symbols_summary:
                    lines.append(f"{indent}  📄 {file} {symbols_summary}")
                else:
                    lines.append(f"{indent}  📄 {file}")

        return "\n".join(lines) if lines else "Empty repository."

    @staticmethod
    def _extract_top_symbols(py_path: str) -> str:
        """Extracts class and top-level function names in < 20 tokens."""
        try:
            with open(py_path, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
            classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
            funcs = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
            parts = []
            if classes:
                parts.append(f"Classes: {', '.join(classes[:3])}")
            if funcs:
                parts.append(f"Funcs: {', '.join(funcs[:4])}")
            if parts:
                return f"({'; '.join(parts)})"
        except Exception:
            pass
        return ""
