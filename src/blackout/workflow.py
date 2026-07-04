from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
from typing import Protocol

from blackout.seed_demo import SEED_DEMO_WINDOWS


DecisionCategory = str


@dataclass(frozen=True)
class LateNightWindow:
    label: str
    starts_at: str
    ends_at: str
    memory_key: str


@dataclass(frozen=True)
class EvidenceExcerpt:
    text: str


@dataclass(frozen=True)
class Decision:
    timestamp: str
    summary: str
    category: DecisionCategory
    source_type: str
    people_or_vendors: list[str]
    amount: str | None
    regret_signals: list[str]
    evidence_excerpt: EvidenceExcerpt


@dataclass(frozen=True)
class RecallResult:
    late_night_window: LateNightWindow
    timeline: list[Decision]
    pattern_insights: list[str]
    raw_evidence: list[str]


@dataclass(frozen=True)
class RememberCall:
    window: LateNightWindow
    primary_demo_evidence: str


@dataclass(frozen=True)
class SeedDemoLoadResult:
    loaded_window_count: int
    most_recent_window: LateNightWindow


class MemoryAdapter(Protocol):
    def remember_late_night_window(
        self, window: LateNightWindow, primary_demo_evidence: str
    ) -> None:
        pass

    def recall_morning_after(self) -> RecallResult:
        pass


class FakeMemoryAdapter:
    def __init__(self) -> None:
        self.remember_calls: list[RememberCall] = []

    def remember_late_night_window(
        self, window: LateNightWindow, primary_demo_evidence: str
    ) -> None:
        self.remember_calls.append(
            RememberCall(
                window=window,
                primary_demo_evidence=primary_demo_evidence,
            )
        )

    def recall_morning_after(self) -> RecallResult:
        evidence = "03:12 - BeanForge receipt: espresso machine, $249"

        return RecallResult(
            late_night_window=LateNightWindow(
                label="Most recent late-night window",
                starts_at="00:00",
                ends_at="05:00",
                memory_key="late-night-window:most-recent",
            ),
            timeline=[
                Decision(
                    timestamp="03:12",
                    summary="Bought a 3am espresso machine",
                    category="purchase",
                    source_type="receipt",
                    people_or_vendors=["BeanForge"],
                    amount="$249",
                    regret_signals=["high spend after midnight"],
                    evidence_excerpt=EvidenceExcerpt(text=evidence),
                )
            ],
            pattern_insights=[
                "Similar late-night purchases showed up in prior windows."
            ],
            raw_evidence=[evidence],
        )


class BlackOutWorkflow:
    def __init__(self, memory: MemoryAdapter) -> None:
        self._memory = memory

    def load_seed_demo_dataset(
        self, current_time: datetime | None = None
    ) -> SeedDemoLoadResult:
        now = current_time or datetime.now().astimezone()
        most_recent_date = _most_recent_completed_window_date(now)

        windows = [
            _seed_late_night_window(
                label=seed_window["label"],
                days_before_most_recent=seed_window["days_before_most_recent"],
                most_recent_date=most_recent_date,
                timezone=now.tzinfo,
            )
            for seed_window in SEED_DEMO_WINDOWS
        ]

        for window, seed_window in zip(windows, SEED_DEMO_WINDOWS):
            self._memory.remember_late_night_window(
                window=window,
                primary_demo_evidence=seed_window["primary_demo_evidence"],
            )

        return SeedDemoLoadResult(
            loaded_window_count=len(windows),
            most_recent_window=windows[0],
        )

    def morning_after_recall(self) -> RecallResult:
        return self._memory.recall_morning_after()


def _most_recent_completed_window_date(current_time: datetime) -> date:
    if current_time.timetz() >= time(hour=5, tzinfo=current_time.tzinfo):
        return current_time.date()
    return (current_time - timedelta(days=1)).date()


def _seed_late_night_window(
    label: str,
    days_before_most_recent: int,
    most_recent_date: date,
    timezone: tzinfo | None,
) -> LateNightWindow:
    window_date = most_recent_date - timedelta(days=days_before_most_recent)
    starts_at = datetime.combine(window_date, time(hour=0), tzinfo=timezone)
    ends_at = datetime.combine(window_date, time(hour=5), tzinfo=timezone)

    return LateNightWindow(
        label=label,
        starts_at=starts_at.isoformat(),
        ends_at=ends_at.isoformat(),
        memory_key=f"late-night-window:{window_date.isoformat()}",
    )
