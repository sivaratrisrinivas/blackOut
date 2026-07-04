import os
from datetime import datetime

import pytest

from blackout.cognee_adapter import build_memory_adapter_from_env
from blackout.workflow import BlackOutWorkflow


@pytest.mark.skipif(
    os.environ.get("BLACKOUT_RUN_COGNEE_SMOKE") != "1"
    or not os.environ.get("LLM_API_KEY"),
    reason=(
        "Set BLACKOUT_RUN_COGNEE_SMOKE=1 and LLM_API_KEY to run the live Cognee "
        "smoke path."
    ),
)
def test_live_cognee_memory_lifecycle_smoke():
    pytest.importorskip("cognee")
    adapter = build_memory_adapter_from_env(
        env={
            **os.environ,
            "BLACKOUT_MEMORY_ADAPTER": "cognee",
            "BLACKOUT_COGNEE_DATASET_PREFIX": "blackout_smoke",
        }
    )
    workflow = BlackOutWorkflow(memory=adapter)

    remembered_window = workflow.remember_evidence(
        primary_evidence=(
            "Late-Night Window: Cognee smoke\n"
            "00:12 - ShopSwift receipt: novelty keyboard, $129."
        ),
        current_time=datetime.fromisoformat("2026-07-04T09:30:00+05:30"),
    )
    result = workflow.morning_after_recall()
    answer = workflow.ask_your_memory("What did I buy after midnight?")
    updated_result = workflow.apply_feedback_label(result.timeline[0], "Regret")
    forgotten_result = workflow.forget_late_night_window(remembered_window)

    assert result.timeline
    assert answer.evidence
    assert updated_result.timeline[0].feedback_label == "Regret"
    assert forgotten_result.timeline == []
