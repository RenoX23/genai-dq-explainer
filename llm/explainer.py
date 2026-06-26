import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

try:
    import streamlit as st
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    from dotenv import load_dotenv
    load_dotenv()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0.2
)

SYSTEM_PROMPT = """You are a senior data engineer doing root cause analysis on data quality failures in a PostgreSQL-backed e-commerce pipeline.

For each failed check, follow this exact reasoning chain:
1. State precisely what metric failed and by exactly how much (use the numbers)
2. Name the SPECIFIC upstream mechanism that causes this failure type — not "pipeline issue" but the actual mechanism: late cron job, missing NOT NULL constraint, double-firing Kafka consumer, broken FK cascade, upstream API returning nulls on optional fields, ETL job reprocessing a partition twice, etc.
3. Give a CONCRETE fix: actual SQL command, specific config change, or exact monitoring rule

FORBIDDEN phrases — never use these:
- "Investigate pipeline logs"
- "Validate data source"
- "Review data ingestion"
- "data processing error"
- "ingestion issue"

These are non-answers. Replace them with specific mechanisms and specific SQL or config fixes."""

USER_TEMPLATE = """
Failed data quality checks from the orders pipeline:

{failed_checks_json}

Write an incident report. For each failed check, reason from the actual numbers to a specific cause and fix.

## Incident Report — {checked_at}

### [Check Name]
**What failed:** [exact metric value, exact threshold, exact gap]
**Root cause hypothesis:** [specific mechanism — name the exact failure mode]
**Suggested fix:** [SQL command or specific config change, not a generic instruction]

---
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", USER_TEMPLATE)
])

chain = prompt | llm | StrOutputParser()


def generate_incident_report(check_results: list) -> str:
    """Takes check results, filters failures, generates LLM incident report."""
    import json
    from datetime import datetime

    failed = [r for r in check_results if r["status"] == "FAIL"]

    if not failed:
        return "## All checks passed. No incidents to report."

    report = chain.invoke({
        "failed_checks_json": json.dumps(failed, indent=2),
        "checked_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    })

    return report


if __name__ == "__main__":
    # Test with live check results
    import sys
    sys.path.append(".")
    from checks.dq_checks import run_all_checks

    print("Running DQ checks...")
    results = run_all_checks()

    print("\nGenerating incident report...\n")
    report = generate_incident_report(results)
    print(report)
