from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import shlex
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
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


COGNEE_REQUIRED_ENV_VARS = ("COGNEE_BASE_URL", "COGNEE_API_KEY", "LLM_API_KEY")
_RECORD_BEGIN = "BLACKOUT_MEMORY_RECORD_BEGIN"
_RECORD_END = "BLACKOUT_MEMORY_RECORD_END"


class CogneeConfigurationError(RuntimeError):
    pass


class CogneeHttpError(RuntimeError):
    def __init__(self, status_code: int | None, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


class CogneeHttpClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        urlopen: Any = urllib.request.urlopen,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._urlopen = urlopen

    def remember(
        self,
        data: str,
        dataset_name: str | None = None,
        run_in_background: bool = False,
    ) -> Any:
        fields = {"data": ("blackout-memory.txt", data)}
        if dataset_name is not None:
            fields["datasetName"] = dataset_name
        fields["run_in_background"] = "true" if run_in_background else "false"
        return self._request_multipart("POST", "/api/v1/remember", fields)

    def add(self, data: str, dataset_name: str | None = None) -> Any:
        return self.remember(data, dataset_name=dataset_name)

    def recall(
        self,
        query_text: str,
        query_type: Any = None,
        datasets: list[str] | None = None,
    ) -> Any:
        body: dict[str, Any] = {
            "query": query_text,
            "searchType": str(query_type or "GRAPH_COMPLETION"),
            "topK": 50,
        }
        if datasets is not None:
            body["datasets"] = datasets
        return self._request_json("POST", "/api/v1/recall", body)

    def search(
        self,
        query_text: str,
        query_type: Any = None,
        datasets: list[str] | None = None,
    ) -> Any:
        return self.recall(query_text, query_type=query_type, datasets=datasets)

    def improve(self, dataset_name: str | None = None) -> Any:
        body: dict[str, Any] = {
            "extractionTasks": [],
            "enrichmentTasks": [],
            "data": "",
            "runInBackground": False,
            "buildGlobalContextIndex": False,
            "sessionIds": [],
        }
        if dataset_name is not None:
            body["datasetName"] = dataset_name
        try:
            return self._request_json("POST", "/api/v1/improve", body)
        except CogneeHttpError as error:
            if error.status_code == 404:
                return None
            raise

    def delete_dataset(self, dataset_name: str) -> Any:
        return self._request_json(
            "POST",
            "/api/v1/forget",
            {
                "dataset": dataset_name,
                "everything": False,
                "memoryOnly": False,
            },
        )

    def raw_data(self, dataset_name: str) -> list[str]:
        dataset_id = self._dataset_id_for_name(dataset_name)
        if dataset_id is None:
            return []

        data_items = self._request_json("GET", f"/api/v1/datasets/{dataset_id}/data", {})
        raw_data: list[str] = []
        for item in data_items or []:
            data_id = item.get("id") or item.get("dataId")
            if not data_id:
                continue
            raw_response = self._request(
                "GET",
                f"/api/v1/datasets/{dataset_id}/data/{data_id}/raw",
            )
            if raw_response is not None:
                raw_data.append(str(raw_response))
        return raw_data

    def _dataset_id_for_name(self, dataset_name: str) -> str | None:
        datasets = self._request_json("GET", "/api/v1/datasets", {})
        for dataset in datasets or []:
            name = dataset.get("name") or dataset.get("datasetName")
            dataset_id = dataset.get("id") or dataset.get("datasetId")
            if name == dataset_name and dataset_id:
                return dataset_id
        return None

    def _request_json(self, method: str, path: str, body: Mapping[str, Any]) -> Any:
        data = None if method == "GET" else json.dumps(body).encode("utf-8")
        return self._request(
            method,
            path,
            data=data,
            extra_headers={} if method == "GET" else {"Content-Type": "application/json"},
        )

    def _request_multipart(
        self, method: str, path: str, fields: Mapping[str, str | tuple[str, str]]
    ) -> Any:
        boundary = f"blackout-{uuid.uuid4().hex}"
        body_parts: list[bytes] = []
        for name, value in fields.items():
            if isinstance(value, tuple):
                filename, content = value
                body_parts.extend(
                    [
                        f"--{boundary}\r\n".encode("ascii"),
                        (
                            f'Content-Disposition: form-data; name="{name}"; '
                            f'filename="{filename}"\r\n'
                            "Content-Type: text/plain; charset=utf-8\r\n\r\n"
                        ).encode("ascii"),
                        content.encode("utf-8"),
                        b"\r\n",
                    ]
                )
                continue

            body_parts.extend(
                [
                    f"--{boundary}\r\n".encode("ascii"),
                    (
                        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                    ).encode("ascii"),
                    value.encode("utf-8"),
                    b"\r\n",
                ]
            )
        body_parts.append(f"--{boundary}--\r\n".encode("ascii"))
        return self._request(
            method,
            path,
            data=b"".join(body_parts),
            extra_headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )

    def _request(
        self,
        method: str,
        path: str,
        data: bytes | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> Any:
        request = urllib.request.Request(
            urllib.parse.urljoin(f"{self._base_url}/", path.removeprefix("/")),
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "X-Api-Key": self._api_key,
                **dict(extra_headers or {}),
            },
        )
        try:
            with self._urlopen(request, timeout=120) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")
            raise CogneeHttpError(
                error.code,
                f"Cognee HTTP request failed with status {error.code}: "
                f"{_short_error(error_body)}",
            ) from error
        except urllib.error.URLError as error:
            raise CogneeHttpError(
                None,
                f"Cognee HTTP request failed: {_short_error(str(error.reason))}",
            ) from error

        if not response_body:
            return None
        response_headers = getattr(response, "headers", {})
        response_content_type = response_headers.get("Content-Type", "")
        if "application/json" not in response_content_type:
            return response_body
        try:
            return json.loads(response_body)
        except json.JSONDecodeError:
            return response_body


class RealCogneeMemoryAdapter:
    def __init__(
        self,
        cognee_client: Any,
        dataset_prefix: str = "blackout",
    ) -> None:
        self._cognee = cognee_client
        self._dataset_prefix = dataset_prefix

    def remember_late_night_window(
        self, window: LateNightWindow, primary_demo_evidence: str
    ) -> None:
        dataset_name = self._dataset_name_for(window)
        self._remember_document(
            _cognee_document_for(window, primary_demo_evidence),
            dataset_name=dataset_name,
        )
        self._remember_document(
            _record_document(
                {
                    "record_type": "window_index",
                    "window": _window_payload(window),
                    "dataset_name": dataset_name,
                }
            ),
            dataset_name=self._index_dataset_name(),
        )

    def recall_morning_after(self) -> RecallResult:
        remembered_calls = self._remembered_calls_from_cognee()
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

        remembered_index, remembered_call = max(
            enumerate(remembered_calls),
            key=lambda indexed_call: (
                indexed_call[1].window.starts_at,
                indexed_call[0],
            ),
        )
        timeline = self._decisions_with_feedback(
            remembered_call.primary_demo_evidence,
            remembered_call.window,
        )
        prior_decisions = [
            decision
            for call_index, call in enumerate(remembered_calls)
            if call_index != remembered_index
            for decision in self._decisions_with_feedback(
                call.primary_demo_evidence,
                call.window,
            )
        ]

        return RecallResult(
            late_night_window=remembered_call.window,
            timeline=timeline,
            pattern_insights=_pattern_insights_for(timeline, prior_decisions),
            raw_evidence=_evidence_lines(remembered_call.primary_demo_evidence),
        )

    def ask_memory(self, question: str) -> AskMemoryResult:
        question_lower = question.lower()
        remembered_calls = self._remembered_calls_from_cognee()
        self._search(
            f"Ask Your Memory: {question}",
            dataset_names=[
                self._dataset_name_for(call.window) for call in remembered_calls
            ],
        )
        remembered_decisions = [
            decision
            for call in remembered_calls
            for decision in self._decisions_with_feedback(
                call.primary_demo_evidence,
                call.window,
            )
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
        improve_call = ImproveMemoryCall(decision=decision, feedback_label=feedback_label)
        self._remember_document(
            _feedback_document_for(improve_call),
            dataset_name=self._dataset_name_for_decision(decision),
        )
        self._improve_dataset(self._dataset_name_for_decision(decision))

    def improve_decision_memory_for_window(
        self,
        window: LateNightWindow,
        decision: Decision,
        feedback_label: FeedbackLabel,
    ) -> None:
        dataset_name = self._dataset_name_for(window)
        improve_call = ImproveMemoryCall(decision=decision, feedback_label=feedback_label)
        self._remember_document(
            _feedback_document_for(improve_call),
            dataset_name=dataset_name,
            run_in_background=True,
        )
        self._improve_dataset(dataset_name)

    def forget_late_night_window(self, window: LateNightWindow) -> None:
        dataset_name = self._dataset_name_for(window)
        self._remember_document(
            _record_document(
                {
                    "record_type": "forgotten_window",
                    "memory_key": window.memory_key,
                    "dataset_name": dataset_name,
                }
            ),
            dataset_name=self._index_dataset_name(),
        )
        self._delete_dataset(dataset_name)

    def _dataset_name_for(self, window: LateNightWindow) -> str:
        safe_memory_key = re.sub(r"[^A-Za-z0-9_]+", "_", window.memory_key).strip("_")
        return f"{self._dataset_prefix}_{safe_memory_key}"

    def _index_dataset_name(self) -> str:
        return f"{self._dataset_prefix}_index"

    def _dataset_name_for_decision(self, decision: Decision) -> str:
        for call in self._remembered_calls_from_cognee():
            if decision.evidence_excerpt.text in call.primary_demo_evidence:
                return self._dataset_name_for(call.window)
        return f"{self._dataset_prefix}_feedback"

    def _search(
        self,
        query_text: str,
        dataset_names: list[str] | None = None,
        search_type: str = "GRAPH_COMPLETION",
    ) -> Any:
        recall = getattr(self._cognee, "recall", None)
        if callable(recall):
            return _call_cognee_method(
                recall,
                query_text,
                query_type=_search_type(search_type),
                datasets=dataset_names or None,
            )

        return _call_cognee_method(
            self._cognee.search,
            query_text,
            query_type=_search_type(search_type),
            datasets=dataset_names or None,
        )

    def _remember_document(
        self,
        data: str,
        dataset_name: str,
        run_in_background: bool = False,
    ) -> Any:
        remember = getattr(self._cognee, "remember", None)
        if callable(remember):
            return _call_cognee_method(
                remember,
                data,
                dataset_name=dataset_name,
                run_in_background=run_in_background,
            )

        _call_cognee_method(self._cognee.add, data, dataset_name=dataset_name)
        return _call_cognee_method(self._cognee.cognify, dataset_name=dataset_name)

    def _improve_dataset(self, dataset_name: str) -> Any:
        return _call_cognee_method_with_dataset(
            self._cognee.improve,
            dataset_name,
            dataset_name_keyword="dataset_name",
        )

    def _delete_dataset(self, dataset_name: str) -> Any:
        delete_dataset = getattr(self._cognee, "delete_dataset", None)
        if callable(delete_dataset):
            return _call_cognee_method(delete_dataset, dataset_name)

        return _call_cognee_method_with_dataset(
            self._cognee.forget,
            dataset_name,
            dataset_name_keyword="dataset",
        )

    def _remembered_calls_from_cognee(self) -> list[RememberCall]:
        index_records = self._records_from_cognee_dataset(self._index_dataset_name())
        forgotten_memory_keys = {
            record["memory_key"]
            for record in index_records
            if record.get("record_type") == "forgotten_window"
        }
        windows = [
            _window_from_payload(record["window"])
            for record in index_records
            if record.get("record_type") == "window_index"
            and record["window"]["memory_key"] not in forgotten_memory_keys
        ]

        remembered_calls: list[RememberCall] = []
        seen_memory_keys: set[str] = set()
        for window in windows:
            if window.memory_key in seen_memory_keys:
                continue
            seen_memory_keys.add(window.memory_key)
            payload = self._window_payload_from_cognee(window)
            if payload is None:
                continue
            remembered_calls.append(
                RememberCall(
                    window=window,
                    primary_demo_evidence=payload["primary_demo_evidence"],
                )
            )
        return remembered_calls

    def _window_payload_from_cognee(self, window: LateNightWindow) -> dict[str, Any] | None:
        records = self._records_from_cognee_dataset(self._dataset_name_for(window))
        for record in records:
            if (
                record.get("record_type") == "late_night_window"
                and record["window"]["memory_key"] == window.memory_key
            ):
                return record
        return None

    def _feedback_by_evidence_excerpt(
        self, window: LateNightWindow
    ) -> dict[str, FeedbackLabel]:
        records = self._records_from_cognee_dataset(self._dataset_name_for(window))
        feedback: dict[str, FeedbackLabel] = {}
        for record in records:
            if record.get("record_type") == "feedback":
                feedback[record["evidence_excerpt"]] = record["feedback_label"]
        return feedback

    def _decisions_with_feedback(
        self, primary_demo_evidence: str, window: LateNightWindow
    ) -> list[Decision]:
        feedback_by_evidence_excerpt = self._feedback_by_evidence_excerpt(window)
        return [
            self._with_feedback(decision, feedback_by_evidence_excerpt)
            for decision in _decisions_from_evidence(primary_demo_evidence)
        ]

    def _with_feedback(
        self,
        decision: Decision,
        feedback_by_evidence_excerpt: dict[str, FeedbackLabel],
    ) -> Decision:
        feedback_label = feedback_by_evidence_excerpt.get(decision.evidence_excerpt.text)
        if feedback_label is None:
            return decision
        return replace(decision, feedback_label=feedback_label)

    def _records_from_cognee_dataset(self, dataset_name: str) -> list[dict[str, Any]]:
        raw_data = getattr(self._cognee, "raw_data", None)
        if callable(raw_data):
            return [
                record
                for raw_document in raw_data(dataset_name)
                for record in _records_from_search_result(raw_document)
            ]

        return _records_from_search_result(
            self._search(
                "BlackOut memory records.",
                dataset_names=[dataset_name],
                search_type="CHUNKS",
            )
        )


def build_memory_adapter_from_env(
    env: Mapping[str, str] | None = None,
    cognee_client: Any | None = None,
    load_shell_exports: bool = False,
) -> MemoryAdapter:
    configured_env = dict(env or os.environ)
    if load_shell_exports:
        configured_env = _with_shell_exports(
            configured_env,
            Path.home() / ".bashrc",
            ("BLACKOUT_MEMORY_ADAPTER", "BLACKOUT_COGNEE_DATASET_PREFIX")
            + COGNEE_REQUIRED_ENV_VARS,
        )
    adapter_name = configured_env.get("BLACKOUT_MEMORY_ADAPTER", "cognee").lower()

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
            f"{missing_list}. Set BLACKOUT_MEMORY_ADAPTER=fake only when you "
            "need deterministic local memory."
        )

    return RealCogneeMemoryAdapter(
        cognee_client=cognee_client or _build_cognee_client(configured_env),
        dataset_prefix=configured_env.get("BLACKOUT_COGNEE_DATASET_PREFIX", "blackout"),
    )


def _cognee_document_for(window: LateNightWindow, primary_demo_evidence: str) -> str:
    return _record_document(
        {
            "record_type": "late_night_window",
            "window": _window_payload(window),
            "primary_demo_evidence": primary_demo_evidence,
        }
    )


def _feedback_document_for(improve_call: ImproveMemoryCall) -> str:
    return _record_document(
        {
            "record_type": "feedback",
            "decision_summary": improve_call.decision.summary,
            "evidence_excerpt": improve_call.decision.evidence_excerpt.text,
            "feedback_label": improve_call.feedback_label,
        }
    )


def _window_payload(window: LateNightWindow) -> dict[str, str]:
    return {
        "label": window.label,
        "starts_at": window.starts_at,
        "ends_at": window.ends_at,
        "memory_key": window.memory_key,
    }


def _window_from_payload(payload: Mapping[str, str]) -> LateNightWindow:
    return LateNightWindow(
        label=payload["label"],
        starts_at=payload["starts_at"],
        ends_at=payload["ends_at"],
        memory_key=payload["memory_key"],
    )


def _record_document(record: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            _RECORD_BEGIN,
            json.dumps(record, sort_keys=True),
            _RECORD_END,
        ]
    )


def _records_from_search_result(search_result: Any) -> list[dict[str, Any]]:
    if search_result is None:
        return []
    if isinstance(search_result, dict):
        records: list[dict[str, Any]] = []
        for value in search_result.values():
            records.extend(_records_from_search_result(value))
        return records
    elif isinstance(search_result, str):
        text = search_result
    elif isinstance(search_result, list | tuple):
        records: list[dict[str, Any]] = []
        for item in search_result:
            records.extend(_records_from_search_result(item))
        return records
    else:
        text = str(search_result)

    records = []
    pattern = re.compile(
        rf"{re.escape(_RECORD_BEGIN)}\s*(?P<json>{{.*?}})\s*{re.escape(_RECORD_END)}",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        try:
            records.append(json.loads(match.group("json")))
        except json.JSONDecodeError:
            continue
    return records


def _search_type(name: str) -> Any:
    try:
        from cognee import SearchType
    except ImportError:
        return name

    return getattr(SearchType, name, name)


def _build_cognee_client(configured_env: Mapping[str, str]) -> Any:
    return CogneeHttpClient(
        base_url=configured_env["COGNEE_BASE_URL"],
        api_key=configured_env["COGNEE_API_KEY"],
    )


def _import_cognee_client() -> Any:
    try:
        import cognee
    except ImportError as error:
        raise CogneeConfigurationError(
            "Cognee memory requires the cognee Python package to be installed."
        ) from error

    return cognee


def _with_shell_exports(
    env: Mapping[str, str],
    shell_file: Path,
    names: tuple[str, ...],
) -> dict[str, str]:
    configured_env = dict(env)
    missing_names = {name for name in names if not configured_env.get(name)}
    if not missing_names or not shell_file.exists():
        return configured_env

    for line in shell_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("export "):
            continue
        try:
            parts = shlex.split(stripped)
        except ValueError:
            continue
        for assignment in parts[1:]:
            name, separator, value = assignment.partition("=")
            if separator and name in missing_names:
                configured_env[name] = value
                missing_names.discard(name)
        if not missing_names:
            break

    return configured_env


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
        fallback_kwargs = dict(kwargs)
        changed = False
        for optional_keyword in ("datasets", "run_in_background"):
            if optional_keyword in fallback_kwargs:
                fallback_kwargs.pop(optional_keyword)
                changed = True

        if not changed:
            raise

        return _run_cognee_call(method(*args, **fallback_kwargs))


def _call_cognee_method_with_dataset(
    method: Any,
    dataset_name: str,
    dataset_name_keyword: str,
) -> Any:
    try:
        parameters = inspect.signature(method).parameters
    except (TypeError, ValueError):
        parameters = {}

    if dataset_name_keyword in parameters:
        return _call_cognee_method(method, **{dataset_name_keyword: dataset_name})
    if "dataset" in parameters:
        return _call_cognee_method(method, dataset=dataset_name)

    return _call_cognee_method(method, **{dataset_name_keyword: dataset_name})


def _short_error(message: str) -> str:
    compact = " ".join(message.split())
    if len(compact) > 240:
        return f"{compact[:237]}..."
    return compact
