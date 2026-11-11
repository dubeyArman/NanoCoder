"""Surgical file manipulation tools with token conservation tracking."""

import os
import difflib
from typing import Tuple, Dict, Any, Optional
from nanocoder.compression.skeletonizer import ASTSkeletonizer
from nanocoder.telemetry.token_counter import estimate_tokens, TokenUsage


class FileTools:
    """Provides targeted, token-thrifty file inspection and modification."""

    def __init__(self, workspace_root: str, token_usage: TokenUsage):
        self.workspace_root = os.path.abspath(workspace_root)
        self.token_usage = token_usage

    def _resolve_path(self, relative_path: str) -> str:
        """Resolves path safely inside workspace root."""
        clean = os.path.normpath(relative_path.strip().lstrip("/\\"))
        full = os.path.abspath(os.path.join(self.workspace_root, clean))
        if not full.startswith(self.workspace_root):
            raise PermissionError(f"Access denied: Path {relative_path} is outside workspace root.")
        return full

    def read_skeleton(self, relative_path: str) -> str:
        """Reads only the high-level AST skeleton of a file instead of raw source."""
        full_path = self._resolve_path(relative_path)
        if not os.path.exists(full_path):
            return f"Error: File '{relative_path}' not found."

        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()

        skeleton, raw_tokens, skeleton_tokens = ASTSkeletonizer.skeletonize_file(code, relative_path)
        
        # Track savings: Naive agent would have sent raw_tokens into context
        saved = max(0, raw_tokens - skeleton_tokens)
        self.token_usage.tokens_saved_by_skeleton += saved
        
        return skeleton

    def read_snippet(self, relative_path: str, start_line: int, end_line: int) -> str:
        """Reads a surgical slice of lines from a file (1-indexed, inclusive)."""
        full_path = self._resolve_path(relative_path)
        if not os.path.exists(full_path):
            return f"Error: File '{relative_path}' not found."

        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        start_idx = max(1, start_line) - 1
        end_idx = min(total_lines, end_line)

        if start_idx >= total_lines:
            return f"Error: Start line {start_line} exceeds file length ({total_lines} lines)."

        sliced = lines[start_idx:end_idx]
        formatted_lines = [f"{i + start_idx + 1:4d} | {line}" for i, line in enumerate(sliced)]
        
        raw_full_tokens = estimate_tokens("".join(lines))
        snippet_tokens = estimate_tokens("".join(formatted_lines))
        
        # Naive agent reads whole file every time
        saved = max(0, raw_full_tokens - snippet_tokens)
        self.token_usage.tokens_saved_by_skeleton += saved

        header = f"# === SNIPPET: {relative_path} (Lines {start_line}-{end_line} of {total_lines}) ===\n"
        return header + "".join(formatted_lines)

    def search_replace_patch(self, relative_path: str, search_block: str, replace_block: str) -> str:
        """Applies a surgical search-and-replace micro-patch to a file.
        
        Saves massive tokens by avoiding full-file regeneration.
        """
        full_path = self._resolve_path(relative_path)
        if not os.path.exists(full_path):
            return f"Error: File '{relative_path}' not found."

        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            original_content = f.read()

        # Normalize line endings for consistent matching
        norm_search = search_block.replace("\r\n", "\n").strip()
        norm_original = original_content.replace("\r\n", "\n")

        if not norm_search:
            return "Error: search_block cannot be empty."

        matches = norm_original.count(norm_search)
        if matches == 0:
            # Try fuzzy/whitespace-flexible match fallback
            return f"Error: search_block not found in '{relative_path}'. Ensure indentation matches exactly."
        elif matches > 1:
            return f"Error: search_block matches {matches} locations in '{relative_path}'. Include more surrounding context lines to make it unique."

        norm_replace = replace_block.replace("\r\n", "\n").strip()
        new_content = norm_original.replace(norm_search, norm_replace, 1)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Generate diff representation
        diff = difflib.unified_diff(
            norm_original.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
            n=2
        )
        diff_text = "".join(diff)

        # Token savings: Naive agent outputs full file (e.g. 500 lines). We only generated replacement!
        raw_rewrite_tokens = estimate_tokens(new_content)
        patch_tokens = estimate_tokens(norm_replace)
        saved = max(0, raw_rewrite_tokens - patch_tokens)
        self.token_usage.tokens_saved_by_surgical_patch += saved

        return f"Patch successfully applied to '{relative_path}'.\n\n```diff\n{diff_text}\n```"

    def write_new_file(self, relative_path: str, content: str) -> str:
        """Creates a new file with specified content."""
        full_path = self._resolve_path(relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File '{relative_path}' created successfully ({len(content.splitlines())} lines)."
