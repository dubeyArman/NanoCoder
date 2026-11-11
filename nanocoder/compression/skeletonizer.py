"""AST Skeletonizer for source code compression.

Extracts high-level architectural skeletons (classes, methods, signatures, docstrings,
and line number markers) while removing function/method bodies. Achieves 80-95%
token reduction compared to reading raw source files.
"""

import ast
import re
from typing import Tuple, List, Optional
from nanocoder.telemetry.token_counter import estimate_tokens


class ASTSkeletonizer:
    """Extracts compact architectural skeletons from source code files."""

    @staticmethod
    def skeletonize_python(code: str, filepath: str = "") -> Tuple[str, int, int]:
        """Skeletonizes Python source code.
        
        Returns:
            Tuple of (skeleton_code, raw_tokens, skeleton_tokens)
        """
        raw_tokens = estimate_tokens(code)
        
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Fallback to regex skeletonizer if file has syntax error
            return ASTSkeletonizer._skeletonize_fallback(code, filepath)

        lines = code.splitlines()
        skeleton_lines: List[str] = [
            f"# === SKELETON: {filepath} ({len(lines)} lines) ===",
            "# Use 'read_snippet' for exact lines if needed.",
        ]

        def get_docstring_summary(node) -> Optional[str]:
            doc = ast.get_docstring(node)
            if doc:
                first_line = doc.strip().splitlines()[0].strip()
                if len(first_line) > 80:
                    first_line = first_line[:77] + "..."
                return f'"""{first_line}"""'
            return None

        def format_args(args: ast.arguments) -> str:
            parts = []
            # Positional & Keyword args
            for a in args.args:
                annotation = f": {ast.unparse(a.annotation)}" if a.annotation else ""
                parts.append(f"{a.arg}{annotation}")
            if args.vararg:
                parts.append(f"*{args.vararg.arg}")
            for a in args.kwonlyargs:
                annotation = f": {ast.unparse(a.annotation)}" if a.annotation else ""
                parts.append(f"{a.arg}{annotation}")
            if args.kwarg:
                parts.append(f"**{args.kwarg.arg}")
            return ", ".join(parts)

        # Process top-level imports compactly
        imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                names = ", ".join(alias.name for alias in node.names)
                imports.append(f"import {names}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = ", ".join(alias.name for alias in node.names)
                imports.append(f"from {module} import {names}")

        if imports:
            skeleton_lines.append("# Imports:")
            # Compress long import lists to first 5 + summary if excessive
            if len(imports) > 6:
                skeleton_lines.extend(imports[:4])
                skeleton_lines.append(f"# ... +{len(imports) - 4} more imports")
            else:
                skeleton_lines.extend(imports)
            skeleton_lines.append("")

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                bases = f"({', '.join(ast.unparse(b) for b in node.bases)})" if node.bases else ""
                start_l = getattr(node, 'lineno', 1)
                end_l = getattr(node, 'end_lineno', start_l)
                skeleton_lines.append(f"class {node.name}{bases}:  # Lines {start_l}-{end_l}")
                
                doc = get_docstring_summary(node)
                if doc:
                    skeleton_lines.append(f"    {doc}")
                
                # Check for class attributes or methods
                has_items = False
                for subnode in node.body:
                    if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        has_items = True
                        fn_start = getattr(subnode, 'lineno', start_l)
                        fn_end = getattr(subnode, 'end_lineno', fn_start)
                        ret = f" -> {ast.unparse(subnode.returns)}" if subnode.returns else ""
                        fn_args = format_args(subnode.args)
                        async_prefix = "async " if isinstance(subnode, ast.AsyncFunctionDef) else ""
                        skeleton_lines.append(f"    {async_prefix}def {subnode.name}({fn_args}){ret}:  # L{fn_start}-L{fn_end}")
                        
                        fdoc = get_docstring_summary(subnode)
                        if fdoc:
                            skeleton_lines.append(f"        {fdoc}")
                        skeleton_lines.append("        ...")
                    elif isinstance(subnode, ast.AnnAssign):
                        has_items = True
                        target = ast.unparse(subnode.target)
                        annotation = ast.unparse(subnode.annotation)
                        skeleton_lines.append(f"    {target}: {annotation}")
                
                if not has_items:
                    skeleton_lines.append("    ...")
                skeleton_lines.append("")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_start = getattr(node, 'lineno', 1)
                fn_end = getattr(node, 'end_lineno', fn_start)
                ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                fn_args = format_args(node.args)
                async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                skeleton_lines.append(f"{async_prefix}def {node.name}({fn_args}){ret}:  # Lines {fn_start}-{fn_end}")
                doc = get_docstring_summary(node)
                if doc:
                    skeleton_lines.append(f"    {doc}")
                skeleton_lines.append("    ...")
                skeleton_lines.append("")

            elif isinstance(node, ast.Assign):
                # Only keep global UPPERCASE constants or important config
                for t in node.targets:
                    name = ast.unparse(t)
                    if name.isupper():
                        skeleton_lines.append(f"{name} = {ast.unparse(node.value)}")

        skeleton_text = "\n".join(skeleton_lines).strip()
        skeleton_tokens = estimate_tokens(skeleton_text)
        return skeleton_text, raw_tokens, skeleton_tokens

    @staticmethod
    def _skeletonize_fallback(code: str, filepath: str = "") -> Tuple[str, int, int]:
        """Regex-based fallback skeletonizer for non-Python or syntax-invalid files."""
        raw_tokens = estimate_tokens(code)
        lines = code.splitlines()
        skeleton_lines = [
            f"# === OUTLINE: {filepath} ({len(lines)} lines) ===",
        ]
        
        # Regex to capture function/class declarations in TS, JS, Python, Go
        sig_pattern = re.compile(
            r'^\s*(export\s+)?(default\s+)?(class|interface|function|def|type|func|struct)\s+([A-Za-z0-9_]+)',
            re.MULTILINE
        )

        for idx, line in enumerate(lines, 1):
            if sig_pattern.search(line):
                skeleton_lines.append(f"{line.rstrip()}  # Line {idx}")
            elif line.startswith(("import ", "from ", "export ", "const ", "var ", "let ")) and idx < 20:
                # Keep first few imports/exports
                skeleton_lines.append(line.rstrip())

        if len(skeleton_lines) <= 2:
            # If nothing matched, take first 25 lines + summary
            skeleton_lines = lines[:25]
            skeleton_lines.append(f"# ... [Truncated {len(lines) - 25} lines]")

        skeleton_text = "\n".join(skeleton_lines)
        skeleton_tokens = estimate_tokens(skeleton_text)
        return skeleton_text, raw_tokens, skeleton_tokens

    @classmethod
    def skeletonize_file(cls, code: str, filepath: str) -> Tuple[str, int, int]:
        """Skeletonizes source file according to its extension."""
        if filepath.endswith(".py"):
            return cls.skeletonize_python(code, filepath)
        return cls._skeletonize_fallback(code, filepath)
