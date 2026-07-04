import streamlit as st

from blackout.workflow import FEEDBACK_LABELS, BlackOutWorkflow, FakeMemoryAdapter


def build_workflow() -> BlackOutWorkflow:
    if "memory_adapter" not in st.session_state:
        st.session_state["memory_adapter"] = FakeMemoryAdapter()

    return BlackOutWorkflow(memory=st.session_state["memory_adapter"])


st.set_page_config(page_title="BlackOut")
st.title("BlackOut")

workflow = build_workflow()

pasted_evidence = st.text_area(
    "Paste Evidence",
    height=160,
    placeholder=(
        "Late-Night Window: Pasted evidence\n"
        "00:12 - ShopSwift receipt: novelty keyboard, $129.\n"
        "01:05 - Text to Priya: \"I can totally redesign the slides by breakfast.\""
    ),
)

if st.button("Remember Pasted Evidence"):
    if pasted_evidence.strip():
        remembered_window = workflow.remember_evidence(
            primary_evidence=pasted_evidence.strip()
        )
        st.success("Remembered pasted Evidence for Morning-After Recall.")
        st.caption(
            f"Late-Night Window: {remembered_window.starts_at} to "
            f"{remembered_window.ends_at}"
        )
    else:
        st.warning("Paste Evidence before remembering it.")

if st.button("Load Seed Demo Mode"):
    seed_result = workflow.load_seed_demo_dataset()
    st.success(
        f"Loaded {seed_result.loaded_window_count} separable Late-Night Windows."
    )
    st.caption(
        "Most recent completed window: "
        f"{seed_result.most_recent_window.starts_at} to "
        f"{seed_result.most_recent_window.ends_at}"
    )

if st.button("What did I do last night?", type="primary"):
    st.session_state["recall_result"] = workflow.morning_after_recall()

if "recall_result" in st.session_state:
    result = st.session_state["recall_result"]

    if "forget_confirmation" in st.session_state:
        st.success(st.session_state.pop("forget_confirmation"))

    st.subheader("Late-Night Window")
    st.write(f"{result.late_night_window.label}")
    st.caption(
        f"{result.late_night_window.starts_at} to {result.late_night_window.ends_at}"
    )

    can_forget_window = bool(result.late_night_window.starts_at)
    confirm_forget = st.checkbox(
        "Confirm forgetting this entire Late-Night Window",
        key=f"confirm-forget-{result.late_night_window.memory_key}",
        disabled=not can_forget_window,
    )
    if st.button(
        "Forget this Late-Night Window",
        disabled=not can_forget_window or not confirm_forget,
        type="secondary",
    ):
        forgotten_window = result.late_night_window
        st.session_state["recall_result"] = workflow.forget_late_night_window(
            forgotten_window
        )
        st.session_state["forget_confirmation"] = (
            f"Forgot Late-Night Window: {forgotten_window.starts_at} to "
            f"{forgotten_window.ends_at}."
        )
        st.rerun()

    st.subheader("Decision timeline")
    for index, decision in enumerate(result.timeline):
        st.markdown(f"**{decision.timestamp}** - {decision.summary}")
        st.caption(
            f"{decision.category} - {decision.source_type} - "
            f"{', '.join(decision.people_or_vendors)}"
        )
        if decision.amount:
            st.write(f"Amount: {decision.amount}")
        for signal in decision.regret_signals:
            st.warning(signal)
        if decision.feedback_label:
            st.success(f"Feedback Label: {decision.feedback_label}")
        st.caption(f"Evidence: {decision.evidence_excerpt.text}")

        feedback_columns = st.columns(len(FEEDBACK_LABELS))
        for label, column in zip(FEEDBACK_LABELS, feedback_columns):
            if column.button(label, key=f"feedback-{index}-{label}"):
                st.session_state["recall_result"] = workflow.apply_feedback_label(
                    decision,
                    label,
                )
                st.toast("Memory updated. Tomorrow-you gets a slightly clearer map.")
                st.rerun()

    st.subheader("Pattern insights")
    for insight_index, insight in enumerate(result.pattern_insights):
        st.info(f"{insight.status.title()}: {insight.summary}")
        for prior_index, prior_decision in enumerate(insight.related_prior_decisions):
            names = ", ".join(prior_decision.people_or_vendors)
            context = f"{prior_decision.timestamp} - {prior_decision.summary}"
            if prior_decision.amount:
                context = f"{context} ({prior_decision.amount})"
            if names:
                context = f"{context} - {names}"
            if prior_decision.feedback_label:
                context = f"{context} - {prior_decision.feedback_label}"
            st.caption(context)

            prior_feedback_columns = st.columns(len(FEEDBACK_LABELS))
            for label, column in zip(FEEDBACK_LABELS, prior_feedback_columns):
                if column.button(
                    label,
                    key=f"prior-feedback-{insight_index}-{prior_index}-{label}",
                ):
                    st.session_state["recall_result"] = workflow.apply_feedback_label(
                        prior_decision,
                        label,
                    )
                    st.toast(
                        "Memory updated. Prior pattern filed with nuance."
                    )
                    st.rerun()

    with st.expander("Raw evidence"):
        for evidence in result.raw_evidence:
            st.code(evidence)
