import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from checks.dq_checks import run_all_checks
from llm.explainer import generate_incident_report

st.set_page_config(
    page_title="GenAI Data Quality Explainer",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 GenAI Data Quality Explainer")
st.caption("Automated SQL health checks + LLM root cause analysis for your data pipeline")

st.divider()

if st.button("▶ Run Data Quality Checks", type="primary", use_container_width=True):

    with st.spinner("Running SQL checks against PostgreSQL..."):
        results = run_all_checks()

    # ── Metrics row ──
    total = len(results)
    failed = [r for r in results if r["status"] == "FAIL"]
    passed = [r for r in results if r["status"] == "PASS"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Checks", total)
    col2.metric("Passed", len(passed), delta=f"+{len(passed)}", delta_color="normal")
    col3.metric("Failed", len(failed), delta=f"-{len(failed)}", delta_color="inverse")

    st.divider()

    # ── Two panel layout ──
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.subheader("📋 Check Results")

        for r in results:
            status_icon = "✅" if r["status"] == "PASS" else "❌"
            color = "green" if r["status"] == "PASS" else "red"

            with st.container(border=True):
                st.markdown(f"**{status_icon} {r['check_name']}**")

                cols = st.columns(2)
                cols[0].markdown(f"**Metric:** `{r['metric_label']}`")
                cols[1].markdown(f"**Value:** `{r['metric_value']}`")

                cols2 = st.columns(2)
                cols2[0].markdown(f"**Threshold:** `{r['threshold']}`")

                if r["deviation_pct"] is not None:
                    cols2[1].markdown(f"**Drift:** `{r['deviation_pct']}%`")
                elif r["baseline"] is not None:
                    cols2[1].markdown(f"**Baseline:** `{r['baseline']}`")

                st.markdown(
                    f"<span style='color:{color}; font-weight:bold;'>{r['status']}</span>",
                    unsafe_allow_html=True
                )

    with right:
        st.subheader("🤖 LLM Incident Report")

        if not failed:
            st.success("All checks passed — no incidents to report.")
        else:
            with st.spinner(f"Generating root cause analysis for {len(failed)} failure(s)..."):
                report = generate_incident_report(results)

            st.markdown(report)

            st.download_button(
                label="📥 Download Incident Report",
                data=report,
                file_name="incident_report.md",
                mime="text/markdown"
            )

else:
    st.info("Click **Run Data Quality Checks** to start the analysis.")

    st.subheader("What this system checks")
    checks_info = {
        "Freshness Check": "Data must arrive within 24 hours",
        "Null Rate Check": "customer_id null rate must stay below 5%",
        "Distribution Drift": "avg order_value must not drift >20% from 7-day baseline",
        "Duplicate Check": "Zero duplicate order_ids allowed",
        "Referential Integrity": "No orphan order_items without parent orders"
    }
    for check, description in checks_info.items():
        st.markdown(f"- **{check}** — {description}")
