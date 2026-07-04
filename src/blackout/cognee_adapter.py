from __future__ import annotations

import asyncio
import inspect
import os
import re
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from blackout.workflow import (
    AskMemoryResult,
    Decision,
    FeedbackLabel,
    FakeMemoryAdapter,
    ImproveMemoryCall,
    LateNightWindow,
    MemoryAdapter,
    RecallResult,
    RememberCall,
    _ask_memory_result_for,
    _decisions_from_evidence,
    _evidence_lines,
    _pattern_insights_for,
)


COGNEE_REQUIRED_ENV_VARS = ("LLM_API_KEY",)


class CogneeConfigurationError(RuntimeError):
    pass


class RealCogneeMemoryAdapter:
    def __init__(
        self,
        cognee_client: Any,
        dataset_prefix: str = "blackout",
    ) -> None:
        self._cognee = cognee_client
        self._dataset_prefix = dataset_prefix
        self._remembered_calls: list[RememberCall] = []
        self._feedback_by_evidence_excerpt: dict[str, FeedbackLabel] = {}
        self._improve_calls: list[ImproveMemoryCall] = []

    def remember_late_night_window(
        self, window: LateNightWindow, primary_demo_evidence: str
    ) -> None:
        dataset_name = self._dataset_name_for(window)
        _call_cognee_method(
            self._cognee.add,
            _cognee_document_for(window, primary_demo_evidence),
            dataset_name=dataset_name,
        )
        _call_cognee_method(self._cognee.cognify, dataset_name=dataset_name)
        self._remembered_calls.append(
            RememberCall(window=window, primary_demo_evidence=primary_demo_evidence)
        )

    def recall_morning_after(self) -> RecallResult:
        self._search(
            "Morning-After Recall: recall remembered Decisions, Evidence "
            "Excerpts, and prior late-night patterns."
        )

        if not self._remembered_calls:
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

        remembered_index, remembered_call = max(
            enumerate(self._remembered_calls),
            key=lambda indexed_call: (
                indexed_call[1].window.starts_at,
                indexed_call[0],
            ),
        )
        timeline = self._decisions_with_feedback(remembered_call.primary_demo_evidence)
        prior_decisions = [
            decision
            for call_index, call in enumerate(self._remembered_calls)
            if call_index != remembered_index
            for decision in self._decisions_with_feedback(call.primary_demo_evidence)
        ]

        return RecallResult(
            late_night_window=remembered_call.window,
            timeline=timeline,
            pattern_insights=_pattern_insights_for(timeline, prior_decisions),
            raw_evidence=_evidence_lines(remembered_call.primary_demo_evidence),
        )

    def ask_memory(self, question: str) -> AskMemoryResult:
        self._search(f"Ask Your Memory: {question}")
        question_lower = question.lower()
        remembered_decisions = [
            decision
            for call in self._remembered_calls
            for decision in self._decisions_with_feedback(call.primary_demo_evidence)
        ]

        if "buy" in question_lower or "bought" in question_lower:
            decisions = [
                decision
                for decision in remembered_decisions
                if decision.category == "purchase"
            ]
            return _ask_memory_result_for(question, decisions)

        if "emotion" in question_lower or "message" in question_lower:
            decisions = [
                decision
                for decision in remembered_decisions
                if decision.category == "message" and decision.regret_signals
            ]
            return _ask_memory_result_for(question, decisions)

        if "cancel" in question_lower:
            decisions = [
                decision
                for decision in remembered_decisions
                if decision.category == "subscription"
                or any("cancel" in signal for signal in decision.regret_signals)
            ]
            return _ask_memory_result_for(question, decisions)

        return _ask_memory_result_for(question, remembered_decisions)

    def improve_decision_memory(
        self, decision: Decision, feedback_label: FeedbackLabel
    ) -> None:
        self._feedback_by_evidence_excerpt[
            decision.evidence_excerpt.text
        ] = feedback_label
        self._improve_calls.append(
            ImproveMemoryCall(decision=decision, feedback_label=feedback_label)
        )
        _call_cognee_method(
            self._cognee.add,
            _feedback_document_for(decision, feedback_label),
            dataset_name=self._dataset_name_for_decision(decision),
        )
        _call_cognee_method(
            self._cognee.improve,
            dataset_name=self._dataset_name_for_decision(decision),
        )

    def forget_late_night_window(self, window: LateNightWindow) -> None:
        dataset_name = self._dataset_name_for(window)
        _call_cognee_method(self._cognee.delete_dataset, dataset_name)
        self._remembered_calls = [
            call
            for call in self._remembered_calls
            if call.window.memory_key != window.memory_key
        ]

    def _dataset_name_for(self, window: LateNightWindow) -> str:
        safe_memory_key = re.sub(r"[^A-Za-z0-9_]+", "_", window.memory_key).strip("_")
        return f"{self._dataset_prefix}_{safe_memory_key}"

    def _dataset_name_for_decision(self, decision: Decision) -> str:
        for call in self._remembered_calls:
            if decision.evidence_excerpt.text in call.primary_demo_evidence:
                return self._dataset_name_for(call.window)
        return f"{self._dataset_prefix}_feedback"

    def _search(self, query_text: str) -> Any:
        dataset_names = [
            self._dataset_name_for(call.window) for call in self._remembered_calls
        ]
        return _call_cognee_method(
            self._cognee.search,
            query_text,
            query_type=_search_type("GRAPH_COMPLETION"),
            datasets=dataset_names or None,
        )

    def _decisions_with_feedback(self, primary_demo_evidence: str) -> list[Decision]:
        return [
            self._with_feedback(decision)
            for decision in _decisions_from_evidence(primary_demo_evidence)
        ]

    def _with_feedback(self, decision: Decision) -> Decision:
        feedback_label = self._feedback_by_evidence_excerpt.get(
            decision.evidence_excerpt.text
        )
        if feedback_label is None:
            return decision
        return replace(decision, feedback_label=feedback_label)


def build_memory_adapter_from_env(
    env: Mapping[str, str] | None = None,
    cognee_client: Any | None = None,
) -> MemoryAdapter:
    configured_env = env or os.environ
    adapter_name = configured_env.get("BLACKOUT_MEMORY_ADAPTER", "fake").lower()

    if adapter_name in {"", "fake"}:
        return FakeMemoryAdapter()

    if adapter_name != "cognee":
        raise CogneeConfigurationError(
            "BLACKOUT_MEMORY_ADAPTER must be 'fake' or 'cognee'."
        )

    missing_names = [
        name for name in COGNEE_REQUIRED_ENV_VARS if not configured_env.get(name)
    ]
    if missing_names:
        missing_list = ", ".join(missing_names)
        raise CogneeConfigurationError(
            "Cognee memory requires environment variable(s): "
            f"{missing_list}. Set BLACKOUT_MEMORY_ADAPTER=cognee only in a "
            "configured environment."
        )

    return RealCogneeMemoryAdapter(
        cognee_client=cognee_client or _import_cognee_client(),
        dataset_prefix=configured_env.get("BLACKOUT_COGNEE_DATASET_PREFIX", "blackout"),
    )


def _cognee_document_for(window: LateNightWindow, primary_demo_evidence: str) -> str:
    return "\n".join(
        [
            f"Late-Night Window: {window.label}",
            f"Starts at: {window.starts_at}",
            f"Ends at: {window.ends_at}",
            f"Memory key: {window.memory_key}",
            "Evidence:",
            primary_demo_evidence,
        ]
    )


def _feedback_document_for(decision: Decision, feedback_label: FeedbackLabel) -> str:
    return "\n".join(
        [
            "Feedback Label applied to Decision",
            f"Decision: {decision.summary}",
            f"Evidence Excerpt: {decision.evidence_excerpt.text}",
            f"Feedback Label: {feedback_label}",
        ]
    )


def _search_type(name: str) -> Any:
    try:
        from cognee import SearchType
    except ImportError:
        return name

    return getattr(SearchType, name, name)


def _import_cognee_client() -> Any:
    try:
        import cognee
    except ImportError as error:
        raise CogneeConfigurationError(
            "Cognee memory requires the cognee Python package to be installed."
        ) from error

    return cognee


def _run_cognee_call(result: Any) -> Any:
    if not inspect.isawaitable(result):
        return result

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(result)

    raise RuntimeError("Cognee async calls require a synchronous Streamlit context.")


def _call_cognee_method(method: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return _run_cognee_call(method(*args, **kwargs))
    except TypeError:
        if "datasets" not in kwargs:
            raise

        fallback_kwargs = dict(kwargs)
        fallback_kwargs.pop("datasets")
        return _run_cognee_call(method(*args, **fallback_kwargs))
