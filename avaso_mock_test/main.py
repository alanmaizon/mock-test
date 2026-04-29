#!/usr/bin/env python3
"""AVASO L2 Desktop Support — Mock Test CLI

Usage:
  python main.py exam                      # 40-question timed exam (60 min)
  python main.py exam --time 45            # custom timer (minutes)
  python main.py practice                  # all sections, instant feedback
  python main.py practice --section euc   # practice a single section
  python main.py drill euc                 # drill all EUC questions
  python main.py drill network
  python main.py drill wifi
  python main.py drill server
  python main.py drill english
  python main.py stats                     # show past session history
"""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from test_engine import (
    run_exam,
    run_practice,
    run_drill,
    SECTIONS,
    SECTION_LABELS,
    RESULTS_DIR,
)

console = Console()

BANNER = """
[bold cyan]AVASO L2 Desktop Support — Mock Test[/bold cyan]
[dim]Practice for the TestGorilla screening[/dim]
"""

VALID_SECTIONS = SECTIONS


def cmd_exam(args):
    run_exam(timer_minutes=args.time)


def cmd_practice(args):
    section = args.section
    if section and section not in VALID_SECTIONS:
        console.print(f"[red]Unknown section '{section}'. Valid sections: {', '.join(VALID_SECTIONS)}[/red]")
        sys.exit(1)
    run_practice(section_filter=section)


def cmd_drill(args):
    section = args.section
    if section not in VALID_SECTIONS:
        console.print(f"[red]Unknown section '{section}'. Valid sections: {', '.join(VALID_SECTIONS)}[/red]")
        sys.exit(1)
    run_drill(section)


def cmd_stats(_args):
    if not RESULTS_DIR.exists():
        console.print("[dim]No results yet. Run exam, practice, or drill first.[/dim]")
        return

    result_files = sorted(RESULTS_DIR.glob("result_*.json"), reverse=True)[:10]
    if not result_files:
        console.print("[dim]No results yet.[/dim]")
        return

    table = Table(
        title="Recent Sessions (latest 10)",
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold",
    )
    table.add_column("Date/Time", style="dim")
    table.add_column("Mode")
    table.add_column("Section", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Pct", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Status", justify="center")

    for rf in result_files:
        with open(rf) as f:
            d = json.load(f)
        ts = d.get("timestamp", "?")
        ts_fmt = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}"
        mode = d.get("mode", "?")
        sec = d.get("section_filter") or "all"
        correct = d.get("correct", 0)
        total = d.get("total", 0)
        pct = d.get("score_pct", 0)
        dur = d.get("duration_seconds", 0)
        m, s = divmod(dur, 60)
        status_color = "green" if pct >= 75 else "red"
        status = f"[{status_color}]{'PASS' if pct >= 75 else 'FAIL'}[/{status_color}]"
        table.add_row(ts_fmt, mode, sec, f"{correct}/{total}", f"{pct:.1f}%", f"{m:02d}:{s:02d}", status)

    console.print(table)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AVASO L2 Mock Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # exam
    p_exam = sub.add_parser("exam", help="Timed full exam (40 questions, 60 min default)")
    p_exam.add_argument("--time", type=int, default=60, metavar="MINUTES", help="Timer in minutes (default: 60)")
    p_exam.set_defaults(func=cmd_exam)

    # practice
    p_prac = sub.add_parser("practice", help="Untimed practice with instant feedback")
    p_prac.add_argument(
        "--section",
        choices=VALID_SECTIONS,
        metavar="SECTION",
        help=f"Limit to one section: {', '.join(VALID_SECTIONS)}",
    )
    p_prac.set_defaults(func=cmd_practice)

    # drill
    p_drill = sub.add_parser("drill", help="Drill a single section (all questions, instant feedback)")
    p_drill.add_argument("section", choices=VALID_SECTIONS, metavar="SECTION")
    p_drill.set_defaults(func=cmd_drill)

    # stats
    p_stats = sub.add_parser("stats", help="Show recent session history")
    p_stats.set_defaults(func=cmd_stats)

    return parser


def main():
    console.print(Panel(BANNER, border_style="dim", padding=(0, 2)))

    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        _interactive_menu()
        return

    args.func(args)


def _interactive_menu():
    """Fallback interactive menu when no subcommand is given."""
    console.print("No command given. Choose a mode:\n")
    console.print("  [cyan]1[/cyan]  Exam      (timed, 40 questions, full feedback at end)")
    console.print("  [green]2[/green]  Practice  (no timer, instant feedback, all sections)")
    console.print("  [yellow]3[/yellow]  Drill     (pick a section, all questions, instant feedback)")
    console.print("  [dim]4[/dim]  Stats     (show past results)")
    console.print("  [dim]q[/dim]  Quit\n")

    choice = console.input("Choice: ").strip().lower()

    if choice == "1":
        run_exam()
    elif choice == "2":
        run_practice()
    elif choice == "3":
        console.print()
        for i, sec in enumerate(SECTIONS, 1):
            console.print(f"  [cyan]{i}[/cyan]  {SECTION_LABELS[sec]}")
        console.print()
        raw = console.input("Section (name or number): ").strip().lower()
        section = _resolve_section(raw)
        if not section:
            console.print(f"[red]Unknown section '{raw}'[/red]")
            return
        run_drill(section)
    elif choice == "4":
        cmd_stats(None)
    elif choice in ("q", "quit", "exit"):
        return
    else:
        console.print("[red]Invalid choice.[/red]")


def _resolve_section(raw: str) -> str:
    if raw in SECTIONS:
        return raw
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(SECTIONS):
            return SECTIONS[idx]
    except ValueError:
        pass
    for sec in SECTIONS:
        if sec.startswith(raw):
            return sec
    return None


if __name__ == "__main__":
    main()
