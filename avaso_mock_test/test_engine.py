"""Core test engine: loads questions, runs sessions, scores results."""

import json
import random
import time
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

QUESTION_BANK_DIR = Path(__file__).parent / "question_bank"
RESULTS_DIR = Path(__file__).parent / "results"

SECTIONS = ["euc", "network", "wifi", "server", "english"]

SECTION_LABELS = {
    "euc": "EUC (End User Computing)",
    "network": "Network",
    "wifi": "Wi-Fi",
    "server": "Server",
    "english": "English",
}

SECTION_COUNTS = {
    "euc": 12,
    "network": 10,
    "wifi": 6,
    "server": 8,
    "english": 4,
}

SECTION_COLORS = {
    "euc": "cyan",
    "network": "green",
    "wifi": "yellow",
    "server": "magenta",
    "english": "blue",
}


@dataclass
class Answer:
    question_id: str
    section: str
    question_text: str
    options: dict
    correct: str
    chosen: Optional[str]
    is_correct: bool
    explanation: str
    topic: str
    elapsed_seconds: float


@dataclass
class SessionResult:
    mode: str
    section_filter: Optional[str]
    answers: list = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    def total_questions(self) -> int:
        return len(self.answers)

    def correct_count(self) -> int:
        return sum(1 for a in self.answers if a.is_correct)

    def score_pct(self) -> float:
        if not self.answers:
            return 0.0
        return self.correct_count() / self.total_questions() * 100

    def section_scores(self) -> dict:
        scores = {}
        for a in self.answers:
            sec = a.section
            if sec not in scores:
                scores[sec] = {"correct": 0, "total": 0}
            scores[sec]["total"] += 1
            if a.is_correct:
                scores[sec]["correct"] += 1
        return scores

    def wrong_answers(self) -> list:
        return [a for a in self.answers if not a.is_correct]

    def duration_seconds(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time


def load_questions(section: str) -> list:
    path = QUESTION_BANK_DIR / f"{section}.json"
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def load_all_questions() -> list:
    all_qs = []
    for section in SECTIONS:
        all_qs.extend(load_questions(section))
    return all_qs


def select_questions(mode: str, section_filter: Optional[str] = None) -> list:
    """Return a shuffled question list for the session."""
    if section_filter:
        pool = load_questions(section_filter)
        random.shuffle(pool)
        return pool  # drill: all questions in section, no count limit

    # exam / practice: draw per-section counts
    selected = []
    for section in SECTIONS:
        pool = load_questions(section)
        count = SECTION_COUNTS.get(section, 5)
        random.shuffle(pool)
        selected.extend(pool[:count])

    # Keep section order for realistic feel
    return selected


# --- Timer display (exam mode) ---

class ExamTimer:
    def __init__(self, total_seconds: int):
        self.total = total_seconds
        self.start = time.time()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._tick, daemon=True)

    def start_timer(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def remaining(self) -> int:
        elapsed = int(time.time() - self.start)
        return max(0, self.total - elapsed)

    def is_expired(self) -> bool:
        return self.remaining() <= 0

    def _tick(self):
        while not self._stop.is_set():
            time.sleep(1)

    def format_remaining(self) -> str:
        r = self.remaining()
        m, s = divmod(r, 60)
        color = "red" if r < 300 else "yellow" if r < 600 else "green"
        return f"[{color}]{m:02d}:{s:02d}[/{color}]"


# --- Question presentation ---

def present_question(
    q: dict,
    index: int,
    total: int,
    mode: str,
    timer: Optional[ExamTimer] = None,
) -> Answer:
    section = q["section"]
    color = SECTION_COLORS.get(section, "white")

    # Build header
    timer_str = f"  {timer.format_remaining()}" if timer else ""
    header = (
        f"[{color}]{SECTION_LABELS.get(section, section)}[/{color}]"
        f"  [dim]Q {index}/{total}[/dim]{timer_str}"
    )

    console.print()
    console.rule(header)
    console.print()

    question_text = Text(q["question"], style="bold white")
    console.print(question_text)
    console.print()

    options = q["options"]
    for key in sorted(options):
        console.print(f"  [{color}]{key}[/{color}]  {options[key]}")

    console.print()

    q_start = time.time()
    chosen = None
    valid = set(options.keys())

    while True:
        try:
            raw = console.input("[bold]Your answer (A/B/C/D): [/bold]").strip().upper()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Test interrupted.[/yellow]")
            raise

        if raw in valid:
            chosen = raw
            break
        if raw == "":
            console.print("[dim]Please enter A, B, C, or D.[/dim]")
        else:
            console.print(f"[red]'{raw}' is not a valid option. Enter A, B, C, or D.[/red]")

    elapsed = time.time() - q_start
    is_correct = chosen == q["correct"]

    if mode == "practice":
        _show_immediate_feedback(q, chosen, is_correct)

    return Answer(
        question_id=q["id"],
        section=section,
        question_text=q["question"],
        options=options,
        correct=q["correct"],
        chosen=chosen,
        is_correct=is_correct,
        explanation=q.get("explanation", ""),
        topic=q.get("topic", ""),
        elapsed_seconds=elapsed,
    )


def _show_immediate_feedback(q: dict, chosen: str, is_correct: bool):
    if is_correct:
        console.print(f"\n[bold green]CORRECT![/bold green]")
    else:
        console.print(
            f"\n[bold red]INCORRECT.[/bold red] "
            f"You chose [red]{chosen}[/red]. "
            f"Correct answer: [green]{q['correct']}[/green] — {q['options'][q['correct']]}"
        )
    console.print(f"[dim]{q.get('explanation', '')}[/dim]")
    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")


# --- Scoring / results ---

def show_score_summary(result: SessionResult):
    console.print()
    console.rule("[bold]SESSION RESULTS[/bold]")

    pct = result.score_pct()
    color = "green" if pct >= 75 else "red"
    status = "PASS" if pct >= 75 else "FAIL"

    console.print(
        Panel(
            f"[bold {color}]{result.correct_count()} / {result.total_questions()}  ({pct:.1f}%)  —  {status}[/bold {color}]",
            title="Overall Score",
            border_style=color,
        )
    )

    duration = int(result.duration_seconds())
    m, s = divmod(duration, 60)
    console.print(f"[dim]Time taken: {m:02d}:{s:02d}[/dim]\n")

    section_scores = result.section_scores()
    if len(section_scores) > 1:
        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        table.add_column("Section", style="dim")
        table.add_column("Score", justify="right")
        table.add_column("Pct", justify="right")
        table.add_column("Status", justify="center")

        for section in SECTIONS:
            if section not in section_scores:
                continue
            sc = section_scores[section]
            pct_sec = sc["correct"] / sc["total"] * 100 if sc["total"] else 0
            sec_color = "green" if pct_sec >= 75 else "red"
            table.add_row(
                SECTION_LABELS.get(section, section),
                f"{sc['correct']}/{sc['total']}",
                f"{pct_sec:.0f}%",
                f"[{sec_color}]{'✓' if pct_sec >= 75 else '✗'}[/{sec_color}]",
            )

        console.print(table)


def show_wrong_answer_review(result: SessionResult):
    wrong = result.wrong_answers()
    if not wrong:
        console.print("[green]No wrong answers to review. Perfect score![/green]")
        return

    console.print()
    console.rule(f"[bold]WRONG ANSWER REVIEW  ({len(wrong)} questions)[/bold]")

    for i, a in enumerate(wrong, 1):
        section = a.section
        color = SECTION_COLORS.get(section, "white")

        console.print(f"\n[bold][{color}]{i}.[/{color}][/bold] {a.question_text}")
        console.print()
        for key in sorted(a.options):
            prefix = ""
            if key == a.correct:
                prefix = "[bold green]✓[/bold green] "
            elif key == a.chosen:
                prefix = "[bold red]✗[/bold red] "
            else:
                prefix = "  "
            console.print(f"  {prefix}[{color}]{key}[/{color}]  {a.options[key]}")

        console.print()
        console.print(
            f"  You chose: [red]{a.chosen}[/red]  |  Correct: [green]{a.correct}[/green]"
        )
        console.print(f"  [dim italic]{a.explanation}[/dim italic]")
        console.print()

        if i < len(wrong):
            try:
                console.input("[dim]Press Enter for next...[/dim]")
            except (EOFError, KeyboardInterrupt):
                break


# --- Main run functions ---

def run_exam(timer_minutes: int = 60):
    questions = select_questions("exam")
    timer = ExamTimer(timer_minutes * 60)
    result = SessionResult(mode="exam", section_filter=None)

    console.print(
        Panel(
            f"[bold]EXAM MODE[/bold]\n"
            f"{len(questions)} questions  |  {timer_minutes} minutes  |  Pass mark: 75%\n"
            f"[dim]No feedback during the test. Results shown at the end.[/dim]",
            border_style="cyan",
        )
    )
    console.input("\nPress Enter to start the timer...")
    timer.start_timer()

    try:
        for i, q in enumerate(questions, 1):
            if timer.is_expired():
                console.print("\n[bold red]Time's up![/bold red]")
                break
            answer = present_question(q, i, len(questions), "exam", timer)
            result.answers.append(answer)
    except KeyboardInterrupt:
        pass

    timer.stop()
    result.end_time = time.time()

    show_score_summary(result)
    _offer_review(result)
    _save_result(result)


def run_practice(section_filter: Optional[str] = None):
    questions = select_questions("practice", section_filter)
    result = SessionResult(mode="practice", section_filter=section_filter)

    label = SECTION_LABELS.get(section_filter, "All sections") if section_filter else "All sections"
    console.print(
        Panel(
            f"[bold]PRACTICE MODE[/bold]  —  {label}\n"
            f"{len(questions)} questions  |  No timer  |  Instant feedback after each answer",
            border_style="green",
        )
    )
    console.input("\nPress Enter to begin...")

    try:
        for i, q in enumerate(questions, 1):
            answer = present_question(q, i, len(questions), "practice")
            result.answers.append(answer)
    except KeyboardInterrupt:
        pass

    result.end_time = time.time()
    show_score_summary(result)
    _offer_review(result)
    _save_result(result)


def run_drill(section: str):
    questions = select_questions("drill", section)
    if not questions:
        console.print(f"[red]No questions found for section: {section}[/red]")
        return

    random.shuffle(questions)
    result = SessionResult(mode="drill", section_filter=section)
    label = SECTION_LABELS.get(section, section)

    console.print(
        Panel(
            f"[bold]DRILL MODE[/bold]  —  {label}\n"
            f"{len(questions)} questions  |  No timer  |  Instant feedback",
            border_style="yellow",
        )
    )
    console.input("\nPress Enter to begin...")

    try:
        for i, q in enumerate(questions, 1):
            answer = present_question(q, i, len(questions), "practice")
            result.answers.append(answer)
    except KeyboardInterrupt:
        pass

    result.end_time = time.time()
    show_score_summary(result)
    _offer_review(result)
    _save_result(result)


def _offer_review(result: SessionResult):
    if not result.wrong_answers():
        return
    console.print()
    try:
        resp = console.input(
            f"Review [bold]{len(result.wrong_answers())}[/bold] wrong answers? [Y/n]: "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    if resp in ("", "y", "yes"):
        show_wrong_answer_review(result)


def _save_result(result: SessionResult):
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = RESULTS_DIR / f"result_{result.mode}_{ts}.json"

    data = {
        "mode": result.mode,
        "section_filter": result.section_filter,
        "timestamp": ts,
        "score_pct": round(result.score_pct(), 1),
        "correct": result.correct_count(),
        "total": result.total_questions(),
        "duration_seconds": int(result.duration_seconds()),
        "section_scores": result.section_scores(),
        "answers": [
            {
                "id": a.question_id,
                "section": a.section,
                "topic": a.topic,
                "correct": a.correct,
                "chosen": a.chosen,
                "is_correct": a.is_correct,
                "elapsed_seconds": round(a.elapsed_seconds, 1),
            }
            for a in result.answers
        ],
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    console.print(f"\n[dim]Results saved: {filename}[/dim]")
