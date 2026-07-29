"""
=============================================================================
DASHBOARD — Live Terminal Monitor
=============================================================================
Provides a beautiful, live-updating terminal UI showing:
- Current active trades & PnL
- Recent LLM Brain decisions
- Active strategies and their confidence scores
- System status (Risk limits, Drawdown)
=============================================================================
"""

import os
import json
import time
from pathlib import Path
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich import box

class LiveDashboard:
    def __init__(self, log_path: str = "trade_log.json"):
        self.console = Console()
        self.log_path = Path(log_path)
        
    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        layout["left"].split_column(
            Layout(name="decisions", ratio=2),
            Layout(name="trades", ratio=1)
        )
        return layout

    def load_logs(self) -> list:
        if not self.log_path.exists():
            return []
        try:
            with open(self.log_path, "r") as f:
                return json.load(f)
        except:
            return []

    def build_header(self) -> Panel:
        return Panel(
            Text("🧠 ANTIGRAVITY TRADING AI — LIVE MONITOR", justify="center", style="bold cyan"),
            style="bold blue"
        )

    def build_decisions_table(self, logs: list) -> Panel:
        table = Table(box=box.SIMPLE, expand=True)
        table.add_column("Time", style="cyan")
        table.add_column("Pair", style="magenta")
        table.add_column("Action", style="bold")
        table.add_column("Conf", justify="right")
        table.add_column("Strategy", style="dim")
        table.add_column("Outcome")

        for log in reversed(logs[-8:]):  # Show last 8
            time_str = log.get("timestamp", "").split("T")[-1][:8]
            action = log.get("action", "")
            
            if action == "BUY":
                action_styled = f"[bold green]{action}[/]"
            elif action == "SELL":
                action_styled = f"[bold red]{action}[/]"
            else:
                action_styled = f"[bold yellow]{action}[/]"
                
            outcome = log.get("outcome", "")
            if "VETOED" in outcome:
                outcome_styled = f"[red]{outcome}[/]"
            elif "EXECUTED" in outcome:
                outcome_styled = f"[green]{outcome}[/]"
            else:
                outcome_styled = outcome

            table.add_row(
                time_str,
                log.get("pair", ""),
                action_styled,
                f"{log.get('confidence', 0)}%",
                log.get("strategy_used", ""),
                outcome_styled
            )

        return Panel(table, title="[bold]Recent Brain Decisions[/]", border_style="blue")

    def build_system_status(self) -> Panel:
        # In a real scenario, this would read from a shared state file or DB.
        # For now, we mock the status display.
        status_text = (
            "[bold green]System Online[/]\n\n"
            "Mode: [bold yellow]DEMO[/]\n"
            "LLM: [bold cyan]Groq (Llama 3.3)[/]\n"
            "RAG: [bold green]Active[/]\n"
            "Risk Limit: 2.0% per trade\n"
            "Max Drawdown: 5.0%\n\n"
            "[dim]Auto-scanning 5 pairs every 15m[/]"
        )
        return Panel(status_text, title="[bold]System Status[/]", border_style="cyan")

    def run(self):
        layout = self.generate_layout()
        
        with Live(layout, refresh_per_second=1, screen=True):
            while True:
                logs = self.load_logs()
                
                layout["header"].update(self.build_header())
                layout["decisions"].update(self.build_decisions_table(logs))
                layout["right"].update(self.build_system_status())
                
                # Mock open trades panel
                trades_table = Table(expand=True)
                trades_table.add_column("ID")
                trades_table.add_column("Pair")
                trades_table.add_column("Side")
                trades_table.add_column("PnL", justify="right")
                trades_table.add_row("No active trades", "", "", "")
                layout["trades"].update(Panel(trades_table, title="[bold]Open Positions[/]", border_style="green"))
                
                layout["footer"].update(Panel("Press Ctrl+C to exit dashboard (bot runs in background)", style="dim"))
                
                time.sleep(2)

if __name__ == "__main__":
    dashboard = LiveDashboard()
    try:
        dashboard.run()
    except KeyboardInterrupt:
        print("\nExited dashboard.")
