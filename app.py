import streamlit as st

from blackout.workflow import BlackOutWorkflow, FakeMemoryAdapter


def build_workflow() -> BlackOutWorkflow:
    return BlackOutWorkflow(memory=FakeMemoryAdapter())


st.set_page_config(page_title="BlackOut")
st.title("BlackOut")

workflow = build_workflow()

if st.button("What did I do last night?", type="primary"):
    result = workflow.morning_after_recall()

    st.subheader("Decision timeline")
    for decision in result.timeline:
        st.markdown(f"**{decision.timestamp}** - {decision.summary}")
        st.caption(
            f"{decision.category} - {', '.join(decision.people_or_vendors)}"
        )
        if decision.amount:
            st.write(f"Amount: {decision.amount}")
        for signal in decision.regret_signals:
            st.warning(signal)
        st.caption(f"Evidence: {decision.evidence_excerpt.text}")

    st.subheader("Pattern insights")
    for insight in result.pattern_insights:
        st.info(insight)

    with st.expander("Raw evidence"):
        for evidence in result.raw_evidence:
            st.code(evidence)
