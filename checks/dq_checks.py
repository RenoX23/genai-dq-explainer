import os
from sqlalchemy import create_engine, text
from datetime import datetime

# Works locally (.env) AND on Streamlit Cloud (st.secrets)
try:
    import streamlit as st
    DB_HOST = st.secrets["DB_HOST"]
    DB_PORT = st.secrets["DB_PORT"]
    DB_NAME = st.secrets["DB_NAME"]
    DB_USER = st.secrets["DB_USER"]
    DB_PASSWORD = st.secrets["DB_PASSWORD"]
except Exception:
    from dotenv import load_dotenv
    load_dotenv()
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
)

def run_check(check_name, sql, threshold, metric_label, baseline_sql=None):
    """Execute a single DQ check and return structured result."""
    with engine.connect() as conn:
        result = conn.execute(text(sql)).scalar()

        baseline = None
        deviation = None
        if baseline_sql:
            baseline = conn.execute(text(baseline_sql)).scalar()
            if result is not None and baseline and baseline != 0:
                deviation = round((float(result) - float(baseline)) / float(baseline) * 100, 2)
            elif result is None:
                # No data in current window — treat as 100% drop, automatic FAIL
                deviation = -100.0

        passed = False
        if deviation is not None:
            passed = abs(deviation) <= threshold
        else:
            passed = float(result) <= threshold

        return {
            "check_name": check_name,
            "status": "PASS" if passed else "FAIL",
            "metric_label": metric_label,
            "metric_value": round(float(result), 4) if result else 0,
            "threshold": threshold,
            "baseline": round(float(baseline), 4) if baseline else None,
            "deviation_pct": deviation,
            "checked_at": datetime.utcnow().isoformat()
        }


def check_freshness():
    """Check 1 — Data is no older than 24 hours."""
    sql = """
        SELECT EXTRACT(EPOCH FROM (NOW() - MAX(order_purchase_timestamp)))/3600
        FROM orders
    """
    return run_check(
        check_name="Freshness Check",
        sql=sql,
        threshold=24,
        metric_label="hours_since_last_record"
    )


def check_null_rate():
    """Check 2 — Null rate on customer_id must be below 5%."""
    sql = """
        SELECT COUNT(*) FILTER (WHERE customer_id IS NULL)::FLOAT / COUNT(*)
        FROM orders
    """
    return run_check(
        check_name="Null Rate Check — customer_id",
        sql=sql,
        threshold=0.05,
        metric_label="null_rate"
    )


def check_distribution_drift():
    """Check 3 — Average order_value must not drift more than 20% from baseline."""
    current_sql = """
        SELECT AVG(order_value)
        FROM orders
        WHERE order_purchase_timestamp >= NOW() - INTERVAL '4 days'
    """
    baseline_sql = """
        SELECT AVG(order_value)
        FROM orders
        WHERE order_purchase_timestamp >= NOW() - INTERVAL '8 days'
          AND order_purchase_timestamp < NOW() - INTERVAL '4 days'
    """
    return run_check(
        check_name="Distribution Drift Check — order_value",
        sql=current_sql,
        threshold=20,
        metric_label="avg_order_value",
        baseline_sql=baseline_sql
    )
def check_duplicates():
    """Check 4 — Zero duplicate order_ids allowed."""
    sql = """
        SELECT COUNT(*) - COUNT(DISTINCT order_id)
        FROM orders
    """
    return run_check(
        check_name="Duplicate Check — order_id",
        sql=sql,
        threshold=0,
        metric_label="duplicate_count"
    )


def check_referential_integrity():
    """Check 5 — No orphan order_items without a parent order."""
    sql = """
        SELECT COUNT(*)
        FROM order_items oi
        LEFT JOIN orders o ON oi.order_id = o.order_id
        WHERE o.order_id IS NULL
    """
    return run_check(
        check_name="Referential Integrity Check — order_items → orders",
        sql=sql,
        threshold=0,
        metric_label="orphan_count"
    )


def run_all_checks():
    """Run all 5 checks and return structured payload."""
    checks = [
        check_freshness,
        check_null_rate,
        check_distribution_drift,
        check_duplicates,
        check_referential_integrity
    ]

    results = []
    for check in checks:
        result = check()
        results.append(result)
        status_icon = "✅" if result["status"] == "PASS" else "❌"
        print(f"{status_icon} {result['check_name']}: {result['status']} "
              f"| {result['metric_label']}={result['metric_value']}")

    failed = [r for r in results if r["status"] == "FAIL"]
    print(f"\nSummary: {len(failed)}/{len(results)} checks failed")

    return results


if __name__ == "__main__":
    import json
    results = run_all_checks()
    print("\n--- JSON Payload ---")
    print(json.dumps(results, indent=2))
