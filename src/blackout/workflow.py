from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
from typing import Protocol

from blackout.seed_demo import SEED_DEMO_WINDOWS


DecisionCategory = str
DECISION_CATEGORIES = {
    "purchase",
    "message",
    "note",
    "commit",
    "plan",
    "subscription",
    "other",
}
_EVIDENCE_LINE = re.compile(r"^(?P<timestamp>\d{2}:\d{2}) - (?P<source>[^:]+): (?P<body>.+)$")
_AMOUNT = re.compile(r"\$\d+(?:\.\d{2})?")


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
        if not self.remember_calls:
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

        _, remembered_window = max(
            enumerate(self.remember_calls),
            key=lambda indexed_call: (
                indexed_call[1].window.starts_at,
                indexed_call[0],
            ),
        )
        raw_evidence = _evidence_lines(remembered_window.primary_demo_evidence)

        return RecallResult(
            late_night_window=remembered_window.window,
            timeline=[_decision_from_evidence_line(line) for line in raw_evidence],
            pattern_insights=[],
            raw_evidence=raw_evidence,
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

    def remember_evidence(
        self,
        primary_evidence: str,
        current_time: datetime | None = None,
    ) -> LateNightWindow:
        now = current_time or datetime.now().astimezone()
        window_date = _most_recent_completed_window_date(now)
        window = _late_night_window(
            label=_evidence_label(primary_evidence),
            window_date=window_date,
            timezone=now.tzinfo,
        )

        self._memory.remember_late_night_window(
            window=window,
            primary_demo_evidence=primary_evidence,
        )

        return window

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
    return _late_night_window(
        label=label,
        window_date=window_date,
        timezone=timezone,
    )


def _late_night_window(
    label: str,
    window_date: date,
    timezone: tzinfo | None,
) -> LateNightWindow:
    starts_at = datetime.combine(window_date, time(hour=0), tzinfo=timezone)
    ends_at = datetime.combine(window_date, time(hour=5), tzinfo=timezone)

    return LateNightWindow(
        label=label,
        starts_at=starts_at.isoformat(),
        ends_at=ends_at.isoformat(),
        memory_key=f"late-night-window:{window_date.isoformat()}",
    )


def _evidence_label(primary_evidence: str) -> str:
    for line in primary_evidence.splitlines():
        if line.startswith("Late-Night Window:"):
            return line.removeprefix("Late-Night Window:").strip()
    return "Pasted late-night window"


def _evidence_lines(primary_demo_evidence: str) -> list[str]:
    return [
        line.strip()
        for line in primary_demo_evidence.splitlines()
        if _EVIDENCE_LINE.match(line.strip())
    ]


def _decision_from_evidence_line(line: str) -> Decision:
    match = _EVIDENCE_LINE.match(line)
    if not match:
        return Decision(
            timestamp="",
            summary=line,
            category="other",
            source_type="evidence",
            people_or_vendors=[],
            amount=None,
            regret_signals=[],
            evidence_excerpt=EvidenceExcerpt(text=line),
        )

    timestamp = match.group("timestamp")
    source = match.group("source")
    body = match.group("body")
    category = _category_for(source, body)

    return Decision(
        timestamp=timestamp,
        summary=_summary_for(category, source, body),
        category=category,
        source_type=_source_type_for(source),
        people_or_vendors=_people_or_vendors_for(source, body),
        amount=_amount_for(body),
        regret_signals=_regret_signals_for(category, body),
        evidence_excerpt=EvidenceExcerpt(text=line),
    )


def _category_for(source: str, body: str) -> DecisionCategory:
    source_lower = source.lower()
    body_lower = body.lower()

    if "receipt" in source_lower:
        return "purchase"
    if source_lower.startswith("text"):
        return "message"
    if "cancel" in body_lower and "subscription" in body_lower:
        return "subscription"
    if "calendar" in source_lower:
        return "plan"
    if "commit" in source_lower:
        return "commit"
    if "note" in source_lower:
        return "note"
    return "other"


def _source_type_for(source: str) -> str:
    source_lower = source.lower()
    if "receipt" in source_lower:
        return "receipt"
    if source_lower.startswith("text"):
        return "message"
    if "todoist" in source_lower:
        return "task"
    if "notes" in source_lower or "note" in source_lower:
        return "note"
    if "calendar" in source_lower:
        return "calendar"
    return "evidence"


def _people_or_vendors_for(source: str, body: str) -> list[str]:
    names: list[str] = []
    receipt_vendor = source.removesuffix(" receipt").strip()
    if receipt_vendor != source:
        names.append(receipt_vendor)

    if source.startswith("Text to "):
        names.append(source.removeprefix("Text to ").strip())

    for name in re.findall(r"\b[A-Z][a-z]+\b", body):
        if name not in names and name not in {"I", "Tomorrow", "Unless"}:
            names.append(name)

    return names


def _amount_for(body: str) -> str | None:
    match = _AMOUNT.search(body)
    if not match:
        return None
    return match.group(0)


def _summary_for(category: DecisionCategory, source: str, body: str) -> str:
    clean_body = body.strip().strip('"')
    if category == "purchase":
        vendor = source.removesuffix(" receipt").strip()
        item = _AMOUNT.sub("", body).strip(" .,:")
        return f"Bought {item} from {vendor}"
    if category == "message":
        recipient = source.removeprefix("Text to ").strip()
        return f"Texted {recipient}: {clean_body}"
    if category == "subscription":
        return f"Flagged subscription follow-up: {clean_body}"
    if category == "note":
        return f"Wrote note: {clean_body}"
    if category == "plan":
        return f"Made plan: {clean_body}"
    if category == "commit":
        return f"Made commit: {clean_body}"
    return clean_body


def _regret_signals_for(category: DecisionCategory, body: str) -> list[str]:
    signals: list[str] = []
    amount = _amount_for(body)

    if category == "purchase":
        signals.append("purchase after midnight")
        if amount and int(amount.removeprefix("$").split(".")[0]) > 100:
            signals.append("amount over $100")
    if category == "message" and any(
        phrase in body.lower() for phrase in ["again", "replaying", "closure"]
    ):
        signals.append("emotionally loaded message after midnight")
    if category == "subscription" and "cancel" in body.lower():
        signals.append("subscription needs follow-up")

    return signals
