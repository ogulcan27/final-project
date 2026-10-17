"""Live terminal trading board fed by the FinAlly SSE stream.

Usage: uv run scripts/watch_prices.py [base_url]
"""

import json
import sys
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

BARS = "▁▂▃▄▅▆▇█"
SPARK_LEN = 40
ARROWS = {"up": ("▲", "green"), "down": ("▼", "red"), "flat": ("•", "white")}


@dataclass
class TickerStats:
    """Session statistics for one ticker, accumulated since the viewer started."""

    first: float
    prev_close: float
    last: dict = field(default_factory=dict)
    high: float = 0.0
    low: float = float("inf")
    ticks: int = 0
    history: deque = field(default_factory=lambda: deque(maxlen=SPARK_LEN))

    def update(self, p: dict) -> None:
        price = p["price"]
        self.last = p
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.ticks += 1
        self.history.append(price)


def sparkline(values: deque) -> str:
    """Map values to unicode block characters scaled between their min and max."""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    return "".join(BARS[int((v - lo) / span * (len(BARS) - 1))] for v in values)


def pct(a: float, b: float) -> float:
    return (a - b) / b * 100 if b else 0.0


def color(value: float) -> str:
    return "green" if value >= 0 else "red"


def build_table(stats: dict[str, TickerStats]) -> Table:
    """Main board: one row per ticker."""
    table = Table(expand=True, header_style="bold #ecad0a", border_style="grey37")
    for name, justify in [
        ("Ticker", "left"), ("Last", "right"), ("", "center"), ("Chg", "right"),
        ("Day %", "right"), ("Session %", "right"), ("High", "right"),
        ("Low", "right"), ("Range", "right"), ("Trend", "left"), ("Ticks", "right"),
    ]:
        table.add_column(name, justify=justify, no_wrap=True)
    for ticker in sorted(stats):
        s = stats[ticker]
        p = s.last
        arrow, tick_color = ARROWS.get(p["direction"], ARROWS["flat"])
        chg = p["price"] - p["previous_price"]
        day = p["change_pct"]
        session = pct(p["price"], s.first)
        trend_color = color(s.history[-1] - s.history[0])
        table.add_row(
            f"[bold #209dd7]{ticker}[/]",
            f"[bold {tick_color}]{p['price']:,.2f}[/]",
            f"[{tick_color}]{arrow}[/]",
            f"[{tick_color}]{chg:+.2f}[/]",
            f"[{color(day)}]{day:+.2f}%[/]",
            f"[{color(session)}]{session:+.2f}%[/]",
            f"{s.high:,.2f}",
            f"{s.low:,.2f}",
            f"{s.high - s.low:,.2f}",
            f"[{trend_color}]{sparkline(s.history)}[/]",
            f"[grey50]{s.ticks}[/]",
        )
    return table


def build_summary(stats: dict[str, TickerStats], started: datetime) -> Panel:
    """Header panel: market breadth, top movers, and session clock."""
    if not stats:
        return Panel("Waiting for prices...", title="FinAlly Terminal")
    by_day = sorted(stats.items(), key=lambda kv: kv[1].last["change_pct"])
    up = sum(1 for _, s in by_day if s.last["change_pct"] >= 0)
    best, worst = by_day[-1], by_day[0]
    elapsed = str(datetime.now() - started).split(".")[0]
    text = (
        f"[green]Advancers {up}[/]  [red]Decliners {len(stats) - up}[/]   "
        f"Top: [bold green]{best[0]} {best[1].last['change_pct']:+.2f}%[/]   "
        f"Worst: [bold red]{worst[0]} {worst[1].last['change_pct']:+.2f}%[/]   "
        f"[grey50]Session {elapsed}  |  {datetime.now():%H:%M:%S}[/]"
    )
    return Panel(text, title="[bold #ecad0a]FinAlly Terminal[/]", border_style="#753991")


def render(stats: dict[str, TickerStats], started: datetime) -> Group:
    return Group(build_summary(stats, started), build_table(stats))


def main(base_url: str) -> None:
    """Consume the SSE stream and redraw the board on every event."""
    stats: dict[str, TickerStats] = {}
    started = datetime.now()
    with Live(render(stats, started), auto_refresh=False, screen=True) as live:
        with httpx.stream("GET", f"{base_url}/api/stream/prices", timeout=None) as resp:
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                p = json.loads(line[5:])
                s = stats.setdefault(p["ticker"], TickerStats(p["price"], p["prev_close"]))
                s.update(p)
                live.update(render(stats, started), refresh=True)


if __name__ == "__main__":
    try:
        main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000")
    except KeyboardInterrupt:
        pass
