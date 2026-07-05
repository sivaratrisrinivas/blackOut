from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, tzinfo
from typing import Protocol

from blackout.seed_demo import SEED_DEMO_WINDOWS


DecisionCategory = str
FeedbackLabel = str
DECISION_CATEGORIES = {
    "purchase",
    "message",
    "note",
    "commit",
    "plan",
    "subscription",
    "other",
}
FEEDBACK_LABELS = ("Regret", "Fine", "Funny", "Worth it")
ASK_YOUR_MEMORY_PROMPTS = (
    "What decisions did you find?",
    "What looks worth reviewing this morning?",
    "Which Evidence Excerpts should I inspect first?",
)
_EVIDENCE_LINE = re.compile(r"^(?P<timestamp>\d{2}:\d{2}) - (?P<source>[^:]+): (?P<body>.+)$")
_AMOUNT = re.compile(r"\$\d+(?:\.\d{2})?")
_TIME = re.compile(
    r"(?<!\d)(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*"
    r"(?P<period>[AaPp]\.?\s?[Mm]\.?)?(?!\d)"
)


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
    feedback_label: FeedbackLabel | None = None


@dataclass(frozen=True)
class PatternInsight:
    status: str
    summary: str
    current_decision: Decision
    related_prior_decisions: list[Decision]


@dataclass(frozen=True)
class RecallResult:
    late_night_window: LateNightWindow
    timeline: list[Decision]
    pattern_insights: list[PatternInsight]
    raw_evidence: list[str]


@dataclass(frozen=True)
class AskMemoryResult:
    question: str
    answer: str
    evidence: list[str]


@dataclass(frozen=True)
class RememberCall:
    window: LateNightWindow
    primary_demo_evidence: str


@dataclass(frozen=True)
class ImproveMemoryCall:
    decision: Decision
    feedback_label: FeedbackLabel


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

    def ask_memory(self, question: str) -> AskMemoryResult:
        pass

    def improve_decision_memory(
        self, decision: Decision, feedback_label: FeedbackLabel
    ) -> None:
        pass

    def improve_decision_memory_for_window(
        self,
        window: LateNightWindow,
        decision: Decision,
        feedback_label: FeedbackLabel,
    ) -> None:
        pass

    def forget_late_night_window(self, window: LateNightWindow) -> None:
        pass


class BookishContextProvider(Protocol):
    def supplement_for(self, source: str, body: str) -> str | None:
        pass


class NullBookishContextProvider:
    def supplement_for(self, source: str, body: str) -> str | None:
        return None


class FakeMemoryAdapter:
    def __init__(self, bookish_context: BookishContextProvider | None = None) -> None:
        self.remember_calls: list[RememberCall] = []
        self.improve_calls: list[ImproveMemoryCall] = []
        self.forget_calls: list[LateNightWindow] = []
        self.ask_memory_calls: list[str] = []
        self._feedback_by_evidence_excerpt: dict[str, FeedbackLabel] = {}
        self._forgotten_memory_keys: set[str] = set()
        self._bookish_context = bookish_context or NullBookishContextProvider()

    def remember_late_night_window(
        self, window: LateNightWindow, primary_demo_evidence: str
    ) -> None:
        self._forgotten_memory_keys.discard(window.memory_key)
        self.remember_calls.append(
            RememberCall(
                window=window,
                primary_demo_evidence=primary_demo_evidence,
            )
        )

    def recall_morning_after(self) -> RecallResult:
        remembered_calls = [
            call
            for call in self.remember_calls
            if call.window.memory_key not in self._forgotten_memory_keys
        ]
        if not self.remember_calls:
            evidence = "03:12 - BeanForge receipt: espresso machine, $249"

            decision = self._with_feedback(
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
            )

            return RecallResult(
                late_night_window=LateNightWindow(
                    label="Most recent late-night window",
                    starts_at="00:00",
                    ends_at="05:00",
                    memory_key="late-night-window:most-recent",
                ),
                timeline=[decision],
                pattern_insights=[],
                raw_evidence=[evidence],
            )

        if not remembered_calls:
            return RecallResult(
                late_night_window=LateNightWindow(
                    label="No remembered Late-Night Window",
                    starts_at="",
                    ends_at="",
                    memory_key="late-night-window:none",
                ),
                timeline=[],
                pattern_insights=[],
                raw_evidence=[],
            )

        remembered_index, remembered_window = max(
            enumerate(remembered_calls),
            key=lambda indexed_call: (
                indexed_call[1].window.starts_at,
                indexed_call[0],
            ),
        )
        raw_evidence = _evidence_lines(remembered_window.primary_demo_evidence)
        timeline = [
            self._with_feedback(
                _decision_from_evidence_line(line, self._bookish_context)
            )
            for line in raw_evidence
        ]
        prior_decisions = [
            decision
            for call_index, call in enumerate(remembered_calls)
            if call_index != remembered_index
            for decision in self._decisions_with_feedback(call.primary_demo_evidence)
        ]

        return RecallResult(
            late_night_window=remembered_window.window,
            timeline=timeline,
            pattern_insights=_pattern_insights_for(timeline, prior_decisions),
            raw_evidence=raw_evidence,
        )

    def ask_memory(self, question: str) -> AskMemoryResult:
        self.ask_memory_calls.append(question)
        remembered_decisions = self._remembered_decisions()
        question_lower = question.lower()

        return _ask_memory_result_for(
            question,
            _decisions_matching_question(question_lower, remembered_decisions),
        )

    def improve_decision_memory(
        self, decision: Decision, feedback_label: FeedbackLabel
    ) -> None:
        self.improve_calls.append(
            ImproveMemoryCall(decision=decision, feedback_label=feedback_label)
        )
        self._feedback_by_evidence_excerpt[
            decision.evidence_excerpt.text
        ] = feedback_label

    def improve_decision_memory_for_window(
        self,
        window: LateNightWindow,
        decision: Decision,
        feedback_label: FeedbackLabel,
    ) -> None:
        self.improve_decision_memory(decision, feedback_label)

    def forget_late_night_window(self, window: LateNightWindow) -> None:
        self.forget_calls.append(window)
        self._forgotten_memory_keys.add(window.memory_key)

    def _decisions_with_feedback(self, primary_demo_evidence: str) -> list[Decision]:
        return [
            self._with_feedback(decision)
            for decision in _decisions_from_evidence(
                primary_demo_evidence,
                bookish_context=self._bookish_context,
            )
        ]

    def _remembered_decisions(self) -> list[Decision]:
        remembered_calls = [
            call
            for call in self.remember_calls
            if call.window.memory_key not in self._forgotten_memory_keys
        ]
        if not remembered_calls:
            return []

        _, remembered_window = max(
            enumerate(remembered_calls),
            key=lambda indexed_call: (
                indexed_call[1].window.starts_at,
                indexed_call[0],
            ),
        )

        return self._decisions_with_feedback(remembered_window.primary_demo_evidence)

    def _with_feedback(self, decision: Decision) -> Decision:
        feedback_label = self._feedback_by_evidence_excerpt.get(
            decision.evidence_excerpt.text
        )
        if feedback_label is None:
            return decision
        return replace(decision, feedback_label=feedback_label)


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

    def suggested_ask_memory_prompts(
        self,
        recall_result: RecallResult | None = None,
    ) -> list[str]:
        result = recall_result or self._memory.recall_morning_after()
        return _ask_memory_prompts_for(result.timeline)

    def ask_your_memory(self, question: str) -> AskMemoryResult:
        return self._memory.ask_memory(question)

    def apply_feedback_label(
        self, decision: Decision, feedback_label: FeedbackLabel
    ) -> RecallResult:
        self._validate_feedback_label(feedback_label)

        self._memory.improve_decision_memory(
            decision=decision,
            feedback_label=feedback_label,
        )
        return self._memory.recall_morning_after()

    def record_feedback_label(
        self,
        window: LateNightWindow,
        decision: Decision,
        feedback_label: FeedbackLabel,
    ) -> Decision:
        self._validate_feedback_label(feedback_label)
        self._memory.improve_decision_memory_for_window(
            window=window,
            decision=decision,
            feedback_label=feedback_label,
        )
        return replace(decision, feedback_label=feedback_label)

    def forget_late_night_window(self, window: LateNightWindow) -> RecallResult:
        self._memory.forget_late_night_window(window)
        return self._memory.recall_morning_after()

    def _validate_feedback_label(self, feedback_label: FeedbackLabel) -> None:
        if feedback_label not in FEEDBACK_LABELS:
            raise ValueError(
                "Feedback Label must be one of Regret, Fine, Funny, or Worth it."
            )


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
    lines = [line.strip() for line in primary_demo_evidence.splitlines()]
    normalized: list[str] = []
    pending_chunk: list[str] = []

    def flush_pending_chunk() -> None:
        if not pending_chunk:
            return
        normalized_line = _normalized_evidence_line_for(pending_chunk)
        if normalized_line:
            normalized.append(normalized_line)
        pending_chunk.clear()

    for line in lines:
        if not line or line.startswith("Late-Night Window:"):
            flush_pending_chunk()
            continue

        if _EVIDENCE_LINE.match(line):
            flush_pending_chunk()
            normalized.append(line)
            continue

        if _TIME.search(line):
            flush_pending_chunk()
            pending_chunk.append(line)
            continue

        if pending_chunk:
            pending_chunk.append(line)

    flush_pending_chunk()
    return normalized


def _decisions_from_evidence(
    primary_demo_evidence: str,
    bookish_context: BookishContextProvider | None = None,
) -> list[Decision]:
    return [
        _decision_from_evidence_line(line, bookish_context)
        for line in _evidence_lines(primary_demo_evidence)
    ]


def _pattern_insights_for(
    current_decisions: list[Decision],
    prior_decisions: list[Decision],
) -> list[PatternInsight]:
    insights: list[PatternInsight] = []

    for decision in current_decisions:
        related = [
            prior_decision
            for prior_decision in prior_decisions
            if _is_similar_prior_decision(decision, prior_decision)
        ]
        if related:
            insights.append(
                PatternInsight(
                    status=_pattern_status_for(decision, related),
                    summary=_pattern_summary_for(decision, related),
                    current_decision=decision,
                    related_prior_decisions=related,
                )
            )

    return insights


def _is_similar_prior_decision(
    current_decision: Decision, prior_decision: Decision
) -> bool:
    if current_decision.category != prior_decision.category:
        return False

    current_names = set(current_decision.people_or_vendors)
    prior_names = set(prior_decision.people_or_vendors)
    return bool(current_names.intersection(prior_names))


def _pattern_summary_for(decision: Decision, related: list[Decision]) -> str:
    shared_names = [
        name
        for name in decision.people_or_vendors
        if any(name in prior.people_or_vendors for prior in related)
    ]
    if shared_names:
        return (
            f"{shared_names[0]} {decision.category}s appeared in this "
            "Late-Night Window and a prior one."
        )
    return (
        f"Similar {decision.category} Decisions appeared in this "
        "Late-Night Window and prior ones."
    )


def _pattern_status_for(decision: Decision, related: list[Decision]) -> str:
    if decision.feedback_label == "Regret" or any(
        prior.feedback_label == "Regret" for prior in related
    ):
        return "confirmed regret"
    return "possible risk"


def _ask_memory_result_for(question: str, decisions: list[Decision]) -> AskMemoryResult:
    if not decisions:
        return AskMemoryResult(
            question=question,
            answer="I could not find remembered Decisions for that question.",
            evidence=[],
        )

    decision_summaries = [_ask_memory_sentence_for(decision) for decision in decisions]
    return AskMemoryResult(
        question=question,
        answer=" ".join(decision_summaries),
        evidence=[decision.evidence_excerpt.text for decision in decisions],
    )


def _decisions_matching_question(
    question_lower: str,
    remembered_decisions: list[Decision],
) -> list[Decision]:
    if "buy" in question_lower or "bought" in question_lower:
        return [
            decision
            for decision in remembered_decisions
            if decision.category == "purchase"
        ]

    if "emotion" in question_lower or "message" in question_lower:
        return [
            decision
            for decision in remembered_decisions
            if decision.category == "message" and decision.regret_signals
        ]

    if "cancel" in question_lower:
        return [
            decision
            for decision in remembered_decisions
            if decision.category == "subscription"
            or any("cancel" in signal for signal in decision.regret_signals)
        ]

    if any(word in question_lower for word in ["book", "poem", "poetry", "read"]):
        return [
            decision
            for decision in remembered_decisions
            if decision.source_type in {"book", "poetry"}
        ]

    if "plan" in question_lower or "calendar" in question_lower:
        return [
            decision
            for decision in remembered_decisions
            if decision.category == "plan"
        ]

    if "note" in question_lower:
        return [
            decision
            for decision in remembered_decisions
            if decision.category == "note"
        ]

    return remembered_decisions


def _ask_memory_prompts_for(decisions: list[Decision]) -> list[str]:
    prompts: list[str] = []
    categories = {decision.category for decision in decisions}
    source_types = {decision.source_type for decision in decisions}

    if "purchase" in categories:
        prompts.append("What did I buy after midnight?")
    if source_types.intersection({"book", "poetry"}):
        prompts.append("Which book or poem showed up last night?")
    if "message" in categories:
        prompts.append("Did I message anyone emotionally risky?")
    if "subscription" in categories:
        prompts.append("What should I cancel today?")
    if "plan" in categories:
        prompts.append("What plans did I make after midnight?")
    if "note" in categories and len(prompts) < 3:
        prompts.append("What notes did I leave for morning me?")

    for fallback in ASK_YOUR_MEMORY_PROMPTS:
        if len(prompts) >= 3:
            break
        if fallback not in prompts:
            prompts.append(fallback)

    return prompts[:3]


def _ask_memory_sentence_for(decision: Decision) -> str:
    subject = decision.summary
    if subject.startswith("Bought "):
        subject = subject.removeprefix("Bought ")
        sentence = f"You bought {subject} at {decision.timestamp}"
    elif subject.startswith("Texted "):
        subject = subject.removeprefix("Texted ")
        sentence = f"You texted {subject} at {decision.timestamp}"
    elif subject.startswith("Flagged subscription follow-up: "):
        subject = subject.removeprefix("Flagged subscription follow-up: ")
        sentence = f"You flagged this to cancel today: {subject} at {decision.timestamp}"
    else:
        sentence = f"{decision.summary} at {decision.timestamp}"

    if decision.amount:
        sentence = f"{sentence} for {decision.amount}"
    return f"{sentence}."


def _decision_from_evidence_line(
    line: str,
    bookish_context: BookishContextProvider | None = None,
) -> Decision:
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
    summary = _summary_for(category, source, body)
    supplement = (bookish_context or NullBookishContextProvider()).supplement_for(
        source,
        body,
    )
    if supplement:
        summary = f"{summary} ({supplement})"

    return Decision(
        timestamp=timestamp,
        summary=summary,
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
    if "book" in source_lower or "poetry" in source_lower or "poem" in source_lower:
        return "note"
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
    if "poetry" in source_lower or "poem" in source_lower:
        return "poetry"
    if "book" in source_lower:
        return "book"
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
        if "book" in source.lower():
            return f"Saved book note: {clean_body}"
        if "poetry" in source.lower() or "poem" in source.lower():
            return f"Saved poetry note: {clean_body}"
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


def _normalized_evidence_line_for(chunk: list[str]) -> str | None:
    timestamp = _normalized_timestamp_for("\n".join(chunk))
    if timestamp is None:
        return None

    source, body = _source_and_body_for(chunk)
    body = _clean_body(body)
    if not body:
        return None
    return f"{timestamp} - {source}: {body}"


def _normalized_timestamp_for(text: str) -> str | None:
    match = _TIME.search(text)
    if not match:
        return None

    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    period = match.group("period")
    if period:
        normalized_period = period.lower().replace(".", "").replace(" ", "")
        if normalized_period == "am" and hour == 12:
            hour = 0
        elif normalized_period == "pm" and hour != 12:
            hour += 12

    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _source_and_body_for(chunk: list[str]) -> tuple[str, str]:
    text = "\n".join(chunk)
    lower_text = text.lower()
    first_line = chunk[0]
    remainder = _remove_first_time(first_line).strip(" -,:")
    non_time_lines = [_remove_first_time(line).strip(" -,:") for line in chunk]
    non_time_lines = [line for line in non_time_lines if line]

    chat_name = _chat_name_for(first_line)
    if chat_name:
        return f"Text to {chat_name}", _best_chat_body(non_time_lines, chat_name)

    if _looks_like_receipt(lower_text):
        vendor = _field_value(chunk, ("merchant", "vendor", "store", "seller"))
        vendor = vendor or _receipt_vendor_from_lines(chunk) or "Unknown vendor"
        item = _field_value(chunk, ("item", "product", "title", "book"))
        item = item or _first_meaningful_line(non_time_lines, {
            "order",
            "placed",
            "merchant",
            "vendor",
            "store",
            "seller",
            "total",
            "amount",
            "receipt",
        })
        amount = _amount_for(text)
        body = item or "purchase"
        if amount:
            body = f"{body}, {amount}"
        return f"{vendor} receipt", _sentence(body)

    if _looks_bookish(lower_text):
        source = "Poetry note" if "poem" in lower_text or "poetry" in lower_text else "Book note"
        body = _field_value(chunk, ("book note", "poem", "poetry", "book", "title"))
        body = body or _first_meaningful_line(non_time_lines, {"book note", "note"})
        return source, body or remainder or text

    if "calendar" in lower_text or "starts" in lower_text or "meeting" in lower_text:
        body = _field_value(chunk, ("title", "event", "meeting"))
        body = body or _first_meaningful_line(non_time_lines, {"starts", "calendar"})
        return "Calendar", body or remainder or text

    if "commit" in lower_text or "branch" in lower_text or "github" in lower_text:
        body = _field_value(chunk, ("commit", "message"))
        body = body or _first_meaningful_line(non_time_lines, {"commit", "github"})
        return "Git commit", body or remainder or text

    if "todo" in lower_text or "task" in lower_text or "cancel" in lower_text:
        body = _field_value(chunk, ("todo", "task", "title"))
        body = body or _first_meaningful_line(non_time_lines, {"todo", "task"})
        return "Todoist", body or remainder or text

    if "note" in lower_text:
        body = _field_value(chunk, ("note", "title"))
        body = body or _first_meaningful_line(non_time_lines, {"note"})
        return "Notes app", body or remainder or text

    return "Evidence", remainder or " ".join(non_time_lines)


def _remove_first_time(text: str) -> str:
    return _TIME.sub("", text, count=1)


def _chat_name_for(line: str) -> str | None:
    match = re.match(
        r"^(?P<name>[A-Z][A-Za-z .'-]{1,40}),?\s+"
        r"\d{1,2}:\d{2}\s*(?:[AaPp]\.?\s?[Mm]\.?)?",
        line,
    )
    if not match:
        return None
    name = match.group("name").strip()
    if name.lower() in {"starts", "ends", "order placed", "placed", "title"}:
        return None
    return name


def _best_chat_body(lines: list[str], chat_name: str) -> str:
    useful_lines = [line for line in lines if line != chat_name]
    return " ".join(useful_lines).strip()


def _looks_like_receipt(text: str) -> bool:
    return any(word in text for word in ["receipt", "order", "merchant", "vendor", "store", "total"]) or bool(_AMOUNT.search(text))


def _looks_bookish(text: str) -> bool:
    return any(word in text for word in ["book", "read", "reading", "poem", "poetry", "novel"])


def _field_value(lines: list[str], labels: tuple[str, ...]) -> str | None:
    for line in lines:
        for label in labels:
            match = re.match(
                rf"^{re.escape(label)}\s*[:=-]\s*(?P<value>.+)$",
                _remove_first_time(line).strip(),
                flags=re.IGNORECASE,
            )
            if match:
                return match.group("value").strip()
    return None


def _receipt_vendor_from_lines(lines: list[str]) -> str | None:
    for line in lines:
        cleaned = _remove_first_time(line).strip(" -,:")
        if not cleaned or ":" in cleaned:
            continue
        if "receipt" in cleaned.lower():
            return cleaned.lower().replace("receipt", "").strip().title()
    return None


def _first_meaningful_line(lines: list[str], ignored_words: set[str]) -> str | None:
    for line in lines:
        lower_line = line.lower()
        if any(lower_line.startswith(word) for word in ignored_words):
            continue
        if _AMOUNT.fullmatch(line):
            continue
        return line
    return None


def _clean_body(body: str) -> str:
    return " ".join(body.split()).strip()


def _sentence(body: str) -> str:
    body = body.strip()
    if not body:
        return body
    if body[-1] in ".!?":
        return body
    return f"{body}."
