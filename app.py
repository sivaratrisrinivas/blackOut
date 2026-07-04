import streamlit as st

from blackout.workflow import BlackOutWorkflow, FakeMemoryAdapter


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
    result = workflow.morning_after_recall()

    st.subheader("Decision timeline")
    for decision in result.timeline:
        st.markdown(f"**{decision.timestamp}** - {decision.summary}")
        st.caption(
            f"{decision.category} - {decision.source_type} - "
            f"{', '.join(decision.people_or_vendors)}"
        )
        if decision.amount:
            st.write(f"Amount: {decision.amount}")
        for signal in decision.regret_signals:
            st.warning(signal)
        st.caption(f"Evidence: {decision.evidence_excerpt.text}")

    st.subheader("Pattern insights")
    for insight in result.pattern_insights:
        st.info(f"{insight.status.title()}: {insight.summary}")
        for prior_decision in insight.related_prior_decisions:
            names = ", ".join(prior_decision.people_or_vendors)
            context = f"{prior_decision.timestamp} - {prior_decision.summary}"
            if prior_decision.amount:
                context = f"{context} ({prior_decision.amount})"
            if names:
                context = f"{context} - {names}"
            st.caption(context)

    with st.expander("Raw evidence"):
        for evidence in result.raw_evidence:
            st.code(evidence)
