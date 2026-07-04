from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


DecisionCategory = str


@dataclass(frozen=True)
class LateNightWindow:
    label: str
    starts_at: str
    ends_at: str


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


class MemoryAdapter(Protocol):
    def recall_morning_after(self) -> RecallResult:
        pass


class FakeMemoryAdapter:
    def recall_morning_after(self) -> RecallResult:
        evidence = "03:12 - BeanForge receipt: espresso machine, $249"

        return RecallResult(
            late_night_window=LateNightWindow(
                label="Most recent late-night window",
                starts_at="00:00",
                ends_at="05:00",
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

    def morning_after_recall(self) -> RecallResult:
        return self._memory.recall_morning_after()

