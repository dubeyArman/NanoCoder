"""NanoCoder core autonomous agent loop with strict token conservation."""

import re
import os
from typing import Dict, Any, Optional, Callable, List
from nanocoder.telemetry.token_counter import TokenUsage, estimate_tokens
from nanocoder.compression.context_manager import ContextManager
from nanocoder.compression.skeletonizer import ASTSkeletonizer
from nanocoder.compression.output_distiller import OutputDistiller
from nanocoder.tools.file_tools import FileTools
from nanocoder.tools.terminal_tools import TerminalTools
from nanocoder.tools.repo_indexer import RepoIndexer
from nanocoder.providers.base import BaseProvider
from nanocoder.providers.gemini_provider import GeminiProvider
from nanocoder.providers.mock_provider import MockProvider


class NanoCoderAgent:
    """Autonomous software engineering agent designed for minimum token footprint."""

    SYSTEM_PROMPT = """You are NanoCoder, an elite, ultra-token-thrifty coding agent.
Your primary objective is to solve engineering tasks using the absolute minimum tokens possible.

Follow these strict rules:
1. Always inspect skeletons first (`read_skeleton`) before reading code.
2. Read ONLY the specific lines you need using `read_snippet(file_path, start_line, end_line)`.
3. NEVER rewrite entire files. Apply surgical micro-patches with `search_replace_patch(file_path, search_block, replace_block)`.
4. Run tests with `run_command(command)`. Outputs are automatically distilled to failure points.
5. When finished, emit `COMPLETE: <concise summary>`.

Format your response strictly as:
THOUGHT: <1-2 sentences of reasoning>
ACTION: <tool_name>(<arguments>)
OR
THOUGHT: <1-2 sentences of reasoning>
COMPLETE: <summary of resolution>"""

    def __init__(
        self,
        workspace_root: str,
        provider: Optional[BaseProvider] = None,
        max_steps: int = 8,
        on_step_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.workspace_root = os.path.abspath(workspace_root)
        self.max_steps = max_steps
        self.on_step_callback = on_step_callback
        
        # Telemetry & Token Accounting
        self.token_usage = TokenUsage()
        
        # Tools & Compressors
        self.file_tools = FileTools(self.workspace_root, self.token_usage)
        self.terminal_tools = TerminalTools(self.workspace_root, self.token_usage)
        self.context_manager = ContextManager(self.token_usage)
        
        # Provider selection
        self.provider = provider or MockProvider(self.token_usage)
        
        # History
        self.step_history: List[Dict[str, Any]] = []

    def solve(self, task_description: str) -> Dict[str, Any]:
        """Runs the autonomous coding loop on the given objective."""
        # 1. Index workspace symbols compactly
        repo_index = RepoIndexer.index_repository(self.workspace_root)
        
        # 2. Setup context manager
        self.context_manager.set_system_prompt(self.SYSTEM_PROMPT)
        self.context_manager.set_repo_map(repo_index)
        self.context_manager.set_user_task(task_description)

        status = "in_progress"
        final_summary = ""

        for step in range(1, self.max_steps + 1):
            # Assemble ultra-compact prompt
            prompt = self.context_manager.assemble_prompt(step)

            # Generate step completion
            response_text = self.provider.generate(prompt)

            # Parse thought, action, or complete
            thought, action, is_complete = self._parse_llm_response(response_text)

            step_data = {
                "step": step,
                "thought": thought,
                "action": action,
                "is_complete": is_complete,
                "result": "",
                "tokens_snapshot": self.token_usage.to_dict()
            }

            if is_complete:
                final_summary = action
                status = "completed"
                step_data["result"] = f"Task completed: {action}"
                self.step_history.append(step_data)
                if self.on_step_callback:
                    self.on_step_callback(step_data)
                break

            # Execute tool action
            tool_result = self._dispatch_action(action)
            step_data["result"] = tool_result

            # Summarize result for execution ledger
            action_name = action.split("(")[0].strip() if "(" in action else action
            args_summary = action[len(action_name):].strip()
            if len(args_summary) > 60:
                args_summary = args_summary[:57] + "...)"
            
            first_line_res = tool_result.strip().splitlines()[0] if tool_result.strip() else "OK"
            if len(first_line_res) > 70:
                first_line_res = first_line_res[:67] + "..."

            # Record into compact ledger and sliding window
            self.context_manager.record_step(step, action_name, args_summary, first_line_res)
            self.context_manager.add_turn({
                "thought": thought,
                "call": action,
                "result": tool_result[:400] # Cap observation length
            })

            self.step_history.append(step_data)
            if self.on_step_callback:
                self.on_step_callback(step_data)

        if status != "completed":
            status = "max_steps_reached"
            final_summary = f"Reached maximum allowed steps ({self.max_steps})."

        return {
            "status": status,
            "summary": final_summary,
            "steps": len(self.step_history),
            "history": self.step_history,
            "telemetry": self.token_usage.to_dict()
        }

    def _parse_llm_response(self, text: str) -> Tuple[str, str, bool]:
        """Parses THOUGHT, ACTION, or COMPLETE tokens."""
        thought = ""
        action = ""
        is_complete = False

        thought_match = re.search(r'THOUGHT:\s*(.*?)(?=ACTION:|COMPLETE:|$)', text, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()

        complete_match = re.search(r'COMPLETE:\s*(.*)', text, re.DOTALL | re.IGNORECASE)
        if complete_match:
            action = complete_match.group(1).strip()
            is_complete = True
            return thought, action, is_complete

        action_match = re.search(r'ACTION:\s*(.*)', text, re.DOTALL | re.IGNORECASE)
        if action_match:
            action = action_match.group(1).strip()

        if not action and not is_complete:
            # Fallback if unformatted text
            action = "run_command(command='pytest')"

        return thought, action, is_complete

    def _dispatch_action(self, action_str: str) -> str:
        """Safely parses and executes tool function calls."""
        try:
            # Match read_skeleton(file_path="...")
            if action_str.startswith("read_skeleton"):
                m = re.search(r'file_path=["\'](.*?)["\']', action_str)
                path = m.group(1) if m else action_str.split("(")[1].strip(")\"' ")
                return self.file_tools.read_skeleton(path)

            # Match read_snippet(file_path="...", start_line=..., end_line=...)
            elif action_str.startswith("read_snippet"):
                pm = re.search(r'file_path=["\'](.*?)["\']', action_str)
                sm = re.search(r'start_line=(\d+)', action_str)
                em = re.search(r'end_line=(\d+)', action_str)
                
                path = pm.group(1) if pm else ""
                start = int(sm.group(1)) if sm else 1
                end = int(em.group(1)) if em else 30
                return self.file_tools.read_snippet(path, start, end)

            # Match search_replace_patch(file_path="...", search_block=..., replace_block=...)
            elif action_str.startswith("search_replace_patch"):
                # Handle triple quotes or double quotes
                pm = re.search(r'file_path=["\'](.*?)["\']', action_str)
                path = pm.group(1) if pm else ""
                
                # Match search_block
                s_match = re.search(r"search_block=['\"]{1,3}(.*?)['\"]{1,3},\s*replace_block=", action_str, re.DOTALL)
                r_match = re.search(r"replace_block=['\"]{1,3}(.*?)['\"]{1,3}\s*\)?$", action_str, re.DOTALL)
                
                if s_match and r_match:
                    search_b = s_match.group(1)
                    replace_b = r_match.group(1)
                    return self.file_tools.search_replace_patch(path, search_b, replace_b)
                else:
                    return f"Error: Failed to parse search_block and replace_block arguments in {action_str}"

            # Match run_command(command="...")
            elif action_str.startswith("run_command"):
                cm = re.search(r'command=["\'](.*?)["\']', action_str, re.DOTALL)
                cmd = cm.group(1) if cm else action_str.split("(")[1].strip(")\"' ")
                return self.terminal_tools.run_command(cmd)

            # Match write_new_file
            elif action_str.startswith("write_new_file"):
                pm = re.search(r'file_path=["\'](.*?)["\']', action_str)
                cm = re.search(r'content=["\']{1,3}(.*?)["\']{1,3}\)?$', action_str, re.DOTALL)
                if pm and cm:
                    return self.file_tools.write_new_file(pm.group(1), cm.group(1))
                return "Error: Could not parse write_new_file parameters."

            else:
                return f"Error: Unknown tool action '{action_str}'"

        except Exception as e:
            return f"Error executing tool action: {str(e)}"
