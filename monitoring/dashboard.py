"""
=============================================================================
DASHBOARD — Live Terminal Monitor (Fully Integrated)
=============================================================================
Reads trade_log.json every 2 seconds and displays:
  - Recent Brain decisions (with grounding scores)
  - RAG memory stats
  - Open positions from MT5
  - Risk & System status
=============================================================================
"""

import json
import time
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich import box
from rich.columns import Columns


class LiveDashboard:
    def __init__(self, log_path: str = "trade_log.json"):
        self.console  = Console()
        self.log_path = Path(log_path)

    # ── Layout ──────────────────────────────────────────────────────────────
    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header",  size=3),
            Layout(name="main"),
            Layout(name="footer",  size=3),
        )
        layout["main"].split_row(
            Layout(name="left",  ratio=3),
            Layout(name="right", ratio=2),
        )
        layout["left"].split_column(
            Layout(name="decisions",  ratio=3),
            Layout(name="positions",  ratio=2),
        )
        layout["right"].split_column(
            Layout(name="rag_status",  ratio=2),
            Layout(name="sys_status",  ratio=3),
        )
        return layout

    # ── Load log ─────────────────────────────────────────────────────────────
    def load_logs(self) -> list:
        if not self.log_path.exists():
            return []
        try:
            with open(self.log_path, "r") as f:
                return json.load(f)
        except Exception:
            return []

    # ── Panels ───────────────────────────────────────────────────────────────
    def build_header(self) -> Panel:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return Panel(
            Text(
                f"🧠 ANTIGRAVITY AI TRADING AGENT — LIVE MONITOR   {now}",
                justify="center",
                style="bold cyan"
            ),
            style="bold blue"
        )

    def build_decisions_table(self, logs: list) -> Panel:
        table = Table(box=box.SIMPLE, expand=True, show_header=True)
        table.add_column("Time",       style="cyan",    width=10)
        table.add_column("Pair",       style="magenta", width=8)
        table.add_column("Action",     style="bold",    width=6)
        table.add_column("Conf",       justify="right", width=5)
        table.add_column("Ground",     justify="right", width=7)
        table.add_column("RAG Src",    width=10)
        table.add_column("Outcome",    width=30)

        for log in reversed(logs[-10:]):
            time_str = log.get("timestamp", "").replace("T", " ").split(".")[0][-8:]
            action   = log.get("action", "?")

            if action == "BUY":
                action_text = f"[bold green]{action}[/]"
            elif action == "SELL":
                action_text = f"[bold red]{action}[/]"
            else:
                action_text = f"[bold yellow]{action}[/]"

            grounding = log.get("grounding", {})
            g_score   = grounding.get("grounding_score", 0.0)
            g_color   = "green" if g_score >= 0.7 else "yellow" if g_score >= 0.4 else "red"
            g_text    = f"[{g_color}]{g_score:.2f}[/]"

            rag_sources = log.get("rag_sources", [])
            rag_text    = ", ".join(rag_sources[:2]) if rag_sources else "[dim]none[/]"

            outcome = log.get("outcome", "")
            if "VETOED" in outcome or "OVERRIDE" in outcome:
                outcome_text = f"[red]{outcome[:30]}[/]"
            elif "EXECUTED" in outcome:
                outcome_text = f"[green]{outcome[:30]}[/]"
            elif "HOLD" in outcome:
                outcome_text = f"[yellow]{outcome[:30]}[/]"
            else:
                outcome_text = outcome[:30]

            table.add_row(
                time_str,
                log.get("pair", "?"),
                action_text,
                f"{log.get('confidence', 0)}%",
                g_text,
                rag_text,
                outcome_text,
            )

        return Panel(
            table,
            title="[bold]📊 Recent Brain Decisions (with Grounding Score)[/]",
            border_style="blue"
        )

    def build_rag_status(self, logs: list) -> Panel:
        """Show RAG memory stats extracted from trade log."""
        grounded_count   = sum(1 for l in logs if l.get("grounding", {}).get("is_grounded", False))
        overridden_count = sum(1 for l in logs if l.get("grounding", {}).get("final_action") == "HOLD"
                               and l.get("grounding", {}).get("original_action") != "HOLD")
        total_decisions  = len(logs)

        # Average grounding score
        scores   = [l.get("grounding", {}).get("grounding_score", 0.0) for l in logs if l.get("grounding")]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Count unique RAG sources used
        all_sources = []
        for l in logs:
            all_sources.extend(l.get("rag_sources", []))
        unique_sources = len(set(all_sources))

        color = "green" if avg_score >= 0.7 else "yellow" if avg_score >= 0.4 else "red"

        text = (
            f"[bold]RAG Memory System[/]\n\n"
            f"Avg Grounding Score:  [{color}]{avg_score:.2f}/1.00[/]\n"
            f"Grounded decisions:   [green]{grounded_count}/{total_decisions}[/]\n"
            f"Hallucination blocks: [red]{overridden_count}[/] overrides\n"
            f"Unique RAG sources:   [cyan]{unique_sources}[/] citations\n\n"
            f"[dim]DB updates every trade cycle[/]"
        )
        return Panel(text, title="[bold]🧠 RAG Grounding Status[/]", border_style="cyan")

    def build_system_status(self, logs: list) -> Panel:
        """Build system status panel."""
        # Get stats from recent logs
        recent = logs[-20:] if logs else []
        buys   = sum(1 for l in recent if l.get("action") == "BUY" and "EXECUTED" in l.get("outcome", ""))
        sells  = sum(1 for l in recent if l.get("action") == "SELL" and "EXECUTED" in l.get("outcome", ""))
        holds  = sum(1 for l in recent if l.get("action") == "HOLD")
        vetoes = sum(1 for l in recent if "VETOED" in l.get("outcome", ""))

        providers = set(l.get("llm_provider", "") for l in recent if l.get("llm_provider"))
        provider_str = ", ".join(providers) if providers else "N/A"

        status_text = (
            "[bold green]● System Online[/]\n\n"
            f"[bold]Last 20 decisions:[/]\n"
            f"  BUYs executed:  [green]{buys}[/]\n"
            f"  SELLs executed: [red]{sells}[/]\n"
            f"  HOLDs:          [yellow]{holds}[/]\n"
            f"  Risk vetoes:    [bold red]{vetoes}[/]\n\n"
            f"[bold]LLM Providers:[/]\n  {provider_str}\n\n"
            f"[bold]Risk Rules:[/]\n"
            f"  Max 2-3 trades/day\n"
            f"  2% risk per trade\n"
            f"  5% max drawdown\n"
            f"  Min 1.5 R:R ratio\n\n"
            f"[dim]Scanning every 15 minutes[/]"
        )
        return Panel(status_text, title="[bold]⚙️ System Status[/]", border_style="magenta")

    def build_positions_panel(self) -> Panel:
        """Show open positions (reads from MT5 if available)."""
        table = Table(expand=True, box=box.SIMPLE)
        table.add_column("Pair",    style="magenta")
        table.add_column("Side",    style="bold")
        table.add_column("Lots",    justify="right")
        table.add_column("PnL",     justify="right")
        table.add_column("Status")

        # Try to get real positions from MT5
        try:
            import MetaTrader5 as mt5
            if mt5.initialize():
                positions = mt5.positions_get()
                if positions:
                    for p in positions:
                        side  = "[green]BUY[/]"  if p.type == 0 else "[red]SELL[/]"
                        pnl_c = "green" if p.profit >= 0 else "red"
                        table.add_row(
                            p.symbol,
                            side,
                            f"{p.volume:.2f}",
                            f"[{pnl_c}]${p.profit:.2f}[/]",
                            "🟢 Open"
                        )
                else:
                    table.add_row("—", "No open positions", "", "", "")
                mt5.shutdown()
            else:
                table.add_row("MT5 not connected", "", "", "", "")
        except Exception:
            table.add_row("MT5 unavailable", "", "", "", "")

        return Panel(table, title="[bold]📈 Open Positions[/]", border_style="green")

    def build_footer(self) -> Panel:
        return Panel(
            "[dim]Press Ctrl+C to exit dashboard | Bot continues running in background | "
            "trade_log.json updates every cycle[/]",
            style="dim"
        )

    # ── Main run loop ─────────────────────────────────────────────────────────
    def run(self):
        layout = self.generate_layout()

        with Live(layout, refresh_per_second=0.5, screen=True):
            while True:
                logs = self.load_logs()

                layout["header"].update(self.build_header())
                layout["decisions"].update(self.build_decisions_table(logs))
                layout["positions"].update(self.build_positions_panel())
                layout["rag_status"].update(self.build_rag_status(logs))
                layout["sys_status"].update(self.build_system_status(logs))
                layout["footer"].update(self.build_footer())

                time.sleep(2)


if __name__ == "__main__":
    dashboard = LiveDashboard()
    try:
        dashboard.run()
    except KeyboardInterrupt:
        print("\nExited dashboard.")
