"""Command-line interface for NanoCoder with Rich formatting and live telemetry."""

import os
import sys
import argparse
from typing import Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

from nanocoder.agent import NanoCoderAgent
from nanocoder.providers.gemini_provider import GeminiProvider
from nanocoder.providers.openai_provider import OpenAIProvider
from nanocoder.providers.mock_provider import MockProvider


def main():
    parser = argparse.ArgumentParser(description="NanoCoder: The Minimal-Token Autonomous Coding Agent")
    parser.add_argument("--task", type=str, default="", help="Coding task or bug description")
    parser.add_argument("--workspace", type=str, default="demo_workspace", help="Path to workspace directory")
    parser.add_argument("--provider", type=str, choices=["gemini", "openai", "mock"], default="mock", help="Inference provider")
    parser.add_argument("--model", type=str, default="gemini-3.8-flash", help="Model name for API providers")
    parser.add_argument("--max-steps", type=int, default=8, help="Max agent loop steps")
    args = parser.parse_args()

    console = Console()

    # Welcome Banner
    banner_text = """[bold cyan]⚡ NanoCoder: Minimal-Token Autonomous Coding Agent[/bold cyan]
[dim]Global AI Hackathon | Theme: AI Agents & Intelligent Systems[/dim]
[italic]Solving software engineering tasks with >80% less token consumption.[/italic]"""
    console.print(Panel(banner_text, border_style="cyan"))

    task_desc = args.task
    if not task_desc:
        console.print("[bold yellow]No task specified. Defaulting to Demo Bugfix Task:[/bold yellow]")
        task_desc = "Fix ZeroDivisionError in app/calculator.py divide function to raise ValueError('Division by zero is undefined')"
        console.print(f"[white]Objective: {task_desc}[/white]\n")

    workspace = os.path.abspath(args.workspace)
    if not os.path.exists(workspace):
        console.print(f"[bold red]Error: Workspace '{workspace}' does not exist.[/bold red]")
        sys.exit(1)

    console.print(f"[bold green]Workspace:[/bold green] {workspace}")
    console.print(f"[bold green]Provider:[/bold green] {args.provider.upper()} ({args.model if args.provider != 'mock' else 'Deterministic Simulator'})\n")

    # Step callback for live terminal streaming
    def on_step(step_data: Dict[str, Any]):
        step_num = step_data["step"]
        thought = step_data["thought"]
        action = step_data["action"]
        result = step_data["result"]
        is_complete = step_data["is_complete"]

        console.print(f"\n[bold magenta]─── Step {step_num} ───[/bold magenta]")
        if thought:
            console.print(f"[bold yellow]Thought:[/bold yellow] {thought}")
        
        if is_complete:
            console.print(f"[bold green]✔ COMPLETE:[/bold green] {action}")
        else:
            console.print(f"[bold cyan]Action:[/bold cyan] [italic]{action}[/italic]")
            if result:
                # If diff or snippet, render nicely
                if "```diff" in result:
                    diff_content = result.split("```diff")[1].split("```")[0].strip()
                    console.print("[bold green]Applied Diff:[/bold green]")
                    console.print(Syntax(diff_content, "diff", theme="monokai", line_numbers=True))
                else:
                    preview = "\n".join(result.strip().splitlines()[:6])
                    if len(result.strip().splitlines()) > 6:
                        preview += f"\n... [+{len(result.strip().splitlines()) - 6} more lines collapsed by distiller]"
                    console.print(Panel(preview, title="Observation (Distilled)", border_style="dim"))

    # Select Provider
    token_usage_dummy = None
    if args.provider == "gemini":
        try:
            from nanocoder.telemetry.token_counter import TokenUsage
            u = TokenUsage()
            provider = GeminiProvider(u, model_name=args.model)
        except Exception as e:
            console.print(f"[bold red]Failed to init Gemini Provider: {e}[/bold red]")
            console.print("[yellow]Falling back to Mock Provider for instant demo.[/yellow]")
            from nanocoder.telemetry.token_counter import TokenUsage
            provider = MockProvider(TokenUsage())
    elif args.provider == "openai":
        try:
            from nanocoder.telemetry.token_counter import TokenUsage
            u = TokenUsage()
            provider = OpenAIProvider(u, model_name=args.model)
        except Exception as e:
            console.print(f"[bold red]Failed to init OpenAI Provider: {e}[/bold red]")
            console.print("[yellow]Falling back to Mock Provider for instant demo.[/yellow]")
            from nanocoder.telemetry.token_counter import TokenUsage
            provider = MockProvider(TokenUsage())
    else:
        from nanocoder.telemetry.token_counter import TokenUsage
        provider = MockProvider(TokenUsage())

    agent = NanoCoderAgent(
        workspace_root=workspace,
        provider=provider,
        max_steps=args.max_steps,
        on_step_callback=on_step
    )

    with console.status("[bold green]NanoCoder agent is actively thinking & executing...", spinner="dots"):
        result = agent.solve(task_desc)

    # Telemetry Final Report
    t = result["telemetry"]
    table = Table(title="[bold green]⚡ NanoCoder Token & Cost Telemetry[/bold green]", border_style="green")
    table.add_column("Metric", style="bold white")
    table.add_column("Standard Agent", style="red", justify="right")
    table.add_column("NanoCoder", style="bold green", justify="right")
    table.add_column("Efficiency Gain", style="bold cyan", justify="right")

    table.add_row(
        "Total Tokens Consumed",
        f"{t['naive_total_tokens']:,}",
        f"{t['total_tokens']:,}",
        f"{t['percentage_saved']} reduction"
    )
    table.add_row(
        "Estimated Cost (USD)",
        t['cost_naive_usd'],
        t['cost_nanocoder_usd'],
        f"{t['cost_naive_usd']} -> {t['cost_nanocoder_usd']}"
    )

    console.print("\n")
    console.print(table)
    
    # Breakdown of Savings
    b = t["savings_breakdown"]
    breakdown_panel = f"""[bold yellow]Token Savings by Architecture Engine:[/bold yellow]
• [cyan]AST Skeleton Pruning:[/cyan] {b['skeleton_pruning']:,} tokens saved
• [cyan]Terminal Distillation:[/cyan] {b['output_distillation']:,} tokens saved
• [cyan]Rolling History Compaction:[/cyan] {b['history_compaction']:,} tokens saved
• [cyan]Surgical Diff Patching:[/cyan] {b['surgical_diff_patch']:,} tokens saved"""
    console.print(Panel(breakdown_panel, border_style="yellow"))

    console.print(f"\n[bold green]✔ Status:[/bold green] {result['status'].upper()} in {result['steps']} steps.")
    console.print(f"[dim]{result['summary']}[/dim]\n")


if __name__ == "__main__":
    main()
