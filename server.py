import sys
from pathlib import Path

from flask import Flask, jsonify, request

src_path = Path(__file__).resolve().parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

from blackout.workflow import BlackOutWorkflow, FEEDBACK_LABELS
from blackout.cognee_adapter import FakeMemoryAdapter

app = Flask(__name__)
_workflow: BlackOutWorkflow | None = None


def get_workflow() -> BlackOutWorkflow:
    global _workflow
    if _workflow is None:
        _workflow = BlackOutWorkflow(memory=FakeMemoryAdapter())
    return _workflow


def decision_index(result, evidence_text: str) -> int | None:
    for i, d in enumerate(result.timeline):
        if d.evidence_excerpt.text == evidence_text:
            return i
    return None


@app.route("/")
def index():
    return jsonify({
        "service": "BlackOut API",
        "ui": "Run the Next.js frontend from ./frontend.",
    })


@app.route("/api/load-demo", methods=["POST"])
def api_load_demo():
    wf = get_workflow()
    wf.load_seed_demo_dataset()
    result = wf.morning_after_recall()
    prompts = wf.suggested_ask_memory_prompts()
    return jsonify({
        "success": True,
        "recall": _serialize_recall(result),
        "prompts": prompts,
    })


@app.route("/api/remember", methods=["POST"])
def api_remember():
    data = request.get_json() or {}
    evidence = data.get("evidence", "").strip()
    if not evidence:
        return jsonify({"success": False, "error": "No evidence provided"}), 400
    wf = get_workflow()
    wf.remember_evidence(primary_evidence=evidence)
    result = wf.morning_after_recall()
    prompts = wf.suggested_ask_memory_prompts()
    return jsonify({
        "success": True,
        "recall": _serialize_recall(result),
        "prompts": prompts,
    })


@app.route("/api/recall", methods=["POST"])
def api_recall():
    wf = get_workflow()
    result = wf.morning_after_recall()
    prompts = wf.suggested_ask_memory_prompts()
    return jsonify({
        "success": True,
        "recall": _serialize_recall(result),
        "prompts": prompts,
    })


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.get_json() or {}
    evidence_text = data.get("evidence_text", "")
    label = data.get("label", "")
    if not evidence_text or label not in FEEDBACK_LABELS:
        return jsonify({"success": False, "error": "Invalid feedback"}), 400
    wf = get_workflow()
    result = wf.morning_after_recall()
    idx = decision_index(result, evidence_text)
    if idx is None:
        return jsonify({"success": False, "error": "Decision not found"}), 404
    decision = result.timeline[idx]
    result = wf.apply_feedback_label(decision, label)
    return jsonify({
        "success": True,
        "recall": _serialize_recall(result),
    })


@app.route("/api/forget", methods=["POST"])
def api_forget():
    data = request.get_json() or {}
    memory_key = data.get("memory_key", "")
    if not memory_key:
        return jsonify({"success": False, "error": "No memory_key"}), 400
    wf = get_workflow()
    result = wf.morning_after_recall()
    window = result.late_night_window
    if window.memory_key != memory_key:
        return jsonify({"success": False, "error": "Window mismatch"}), 400
    result = wf.forget_late_night_window(window)
    return jsonify({
        "success": True,
        "recall": _serialize_recall(result),
        "forgotten": True,
    })


@app.route("/api/ask", methods=["POST"])
def api_ask():
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"success": False, "error": "No question"}), 400
    wf = get_workflow()
    result = wf.ask_your_memory(question)
    return jsonify({
        "success": True,
        "answer": result.answer,
        "evidence": result.evidence,
    })


@app.route("/api/prompts", methods=["GET"])
def api_prompts():
    wf = get_workflow()
    return jsonify({
        "success": True,
        "prompts": wf.suggested_ask_memory_prompts(),
    })


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global _workflow
    _workflow = BlackOutWorkflow(memory=FakeMemoryAdapter())
    return jsonify({"success": True})


def _serialize_recall(result):
    return {
        "window": {
            "label": result.late_night_window.label,
            "starts_at": result.late_night_window.starts_at,
            "ends_at": result.late_night_window.ends_at,
            "memory_key": result.late_night_window.memory_key,
        },
        "timeline": [
            {
                "timestamp": d.timestamp,
                "summary": d.summary,
                "category": d.category,
                "source_type": d.source_type,
                "people_or_vendors": d.people_or_vendors,
                "amount": d.amount,
                "regret_signals": d.regret_signals,
                "evidence_excerpt": d.evidence_excerpt.text,
                "feedback_label": d.feedback_label,
            }
            for d in result.timeline
        ],
        "pattern_insights": [
            {
                "status": p.status,
                "summary": p.summary,
                "current_decision_excerpt": p.current_decision.evidence_excerpt.text,
                "related_prior_decisions": [
                    {
                        "timestamp": d.timestamp,
                        "summary": d.summary,
                        "amount": d.amount,
                        "people_or_vendors": d.people_or_vendors,
                        "feedback_label": d.feedback_label,
                    }
                    for d in p.related_prior_decisions
                ],
            }
            for p in result.pattern_insights
        ],
        "raw_evidence": result.raw_evidence,
    }


if __name__ == "__main__":
    import os
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
