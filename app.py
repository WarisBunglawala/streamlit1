"""
Vortex hosted-app query tester.

Proves the hosted-app data path end to end: the container reads the credentials
Vortex injected at deploy time, calls POST /api/v1/app/query, and renders the
result. It holds no Snowflake credentials of its own and never sees any — the
query runs under the app's own Snowflake role, on Vortex's side.

Credentials come strictly from the environment, exactly as a real customer app
would read them. To run it locally, set the three variables in your shell.
"""

import json
import os
import time

import requests
import streamlit as st

API_URL = os.environ.get("VORTEX_API_URL")
APP_ID = os.environ.get("VORTEX_APP_ID")
APP_TOKEN = os.environ.get("VORTEX_APP_TOKEN")

# Mirrors DEFAULT_ROW_LIMIT / MAX_ROW_LIMIT in service/appQueryService.js.
DEFAULT_LIMIT = 100
MAX_LIMIT = 10000

# Comfortably above the server's own 60s statement timeout, so a slow query
# surfaces Vortex's error rather than the client giving up first.
REQUEST_TIMEOUT_SECONDS = 90

NOT_SET = "NOT SET"

PRESETS = {
    "Identity check": "SELECT CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_WAREHOUSE()",
    "List tables": "SHOW TABLES",
    "Connectivity only": "SELECT 1 AS test",
}

# What each status actually means for whoever is looking at this screen.
STATUS_HINTS = {
    400: "The query failed. Quote the correlation ID below to find the real error in the Vortex server log.",
    401: "Token is invalid, expired or revoked. Redeploy the app to mint a new one.",
    403: "This app's Snowflake role is not available or has not been granted access yet. "
    "Ask your workspace administrator to grant it.",
    413: "The result set is too large to return. Lower the row limit.",
    422: "The request was rejected before running: the query is empty, or the limit is outside 1-10000.",
    429: "Too many queries in flight for this app at once. Retry in a moment.",
    500: "Vortex could not validate the token. Check the server log.",
}

st.set_page_config(page_title="Vortex Query Tester", layout="wide")
st.title("Vortex hosted-app query tester")
st.caption("Runs SQL through Vortex using this app's own identity. No Snowflake credentials live here.")


# ---------------------------------------------------------------------------
# 1. Connection
# ---------------------------------------------------------------------------
st.subheader("1. Connection")

# The token is never rendered — this page is readable by anyone who can open the
# app, which is the same reason the runner entrypoint must not print env vars.
st.table(
    [
        {"Variable": "VORTEX_API_URL", "Status": API_URL or NOT_SET},
        {"Variable": "VORTEX_APP_ID", "Status": APP_ID or NOT_SET},
        {
            "Variable": "VORTEX_APP_TOKEN",
            "Status": f"present ({len(APP_TOKEN)} chars)" if APP_TOKEN else NOT_SET,
        },
    ]
)

ready = bool(API_URL and APP_ID and APP_TOKEN)

if ready:
    # Derived the same way Vortex derives it, so the admin knows what to grant
    # against — and so the identity preset below can be checked against it.
    st.info(f"Expected Snowflake role: **VORTEX_APP_{APP_ID}**")
else:
    st.error(
        "This app was started without its Vortex credentials. They are injected at deploy time via "
        "AppEnvVars — if they are missing, the runner image's entrypoint is not expanding them."
    )


# ---------------------------------------------------------------------------
# 2. Query
# ---------------------------------------------------------------------------
st.subheader("2. Query")

if "sql" not in st.session_state:
    st.session_state.sql = PRESETS["Identity check"]

preset_columns = st.columns(len(PRESETS))
for column, (label, sql) in zip(preset_columns, PRESETS.items()):
    if column.button(label, use_container_width=True):
        st.session_state.sql = sql

query = st.text_area("SQL", key="sql", height=140)
limit = st.number_input("Row limit", min_value=1, max_value=MAX_LIMIT, value=DEFAULT_LIMIT, step=50)

run = st.button("Run query", type="primary", disabled=not ready)


# ---------------------------------------------------------------------------
# 3. Result
# ---------------------------------------------------------------------------
def show_failure(status_code, payload):
    """Render a failed call. Vortex returns two different error shapes."""
    if isinstance(payload, dict) and payload.get("errors"):
        # 422 from express-validator: a list of messages, with no `message` key.
        detail = " / ".join(str(error) for error in payload["errors"])
    elif isinstance(payload, dict):
        detail = payload.get("message") or "No message returned."
    else:
        detail = str(payload)

    st.error(f"HTTP {status_code} — {detail}")

    hint = STATUS_HINTS.get(status_code)
    if hint:
        st.warning(hint)

    # The only link to the real Snowflake error, which is deliberately kept
    # server-side rather than returned to app code.
    if isinstance(payload, dict) and payload.get("correlationId"):
        st.caption(f"Correlation ID: `{payload['correlationId']}`")


if run:
    st.subheader("3. Result")

    started = time.perf_counter()
    try:
        response = requests.post(
            f"{API_URL.rstrip('/')}/app/query",
            headers={
                "Authorization": f"Bearer {APP_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"query": query, "limit": int(limit)},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as error:
        # Never reached Vortex at all — a network path problem, not auth or SQL.
        st.error(f"Could not reach Vortex: {error}")
        st.warning(
            "The request never got a response. Check that this container can reach the Vortex API "
            "over the network, and that VORTEX_API_URL is correct."
        )
        st.stop()

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    try:
        payload = response.json()
    except ValueError:
        payload = response.text

    if response.ok and isinstance(payload, dict) and payload.get("success"):
        data = payload.get("data") or {}
        rows = data.get("rows") or []
        columns = data.get("columns") or []

        metric_columns = st.columns(4)
        metric_columns[0].metric("Status", response.status_code)
        metric_columns[1].metric("Rows", data.get("rowCount", len(rows)))
        metric_columns[2].metric("Row limit", data.get("rowLimit", "-"))
        metric_columns[3].metric("Time", f"{elapsed_ms} ms")

        # Snowflake truncates at ROWS_PER_RESULTSET without saying so, which makes
        # a capped page look exactly like a complete answer.
        if data.get("truncated"):
            st.warning(
                f"Results were truncated at the row limit ({data.get('rowLimit')}). "
                "This is not the full result set — raise the limit or narrow the query."
            )

        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("Query succeeded and returned no rows.")

        with st.expander("Columns"):
            st.table([{"Name": c.get("name"), "Type": c.get("type")} for c in columns])

        with st.expander("Raw response"):
            st.code(json.dumps(payload, indent=2, default=str), language="json")
    else:
        show_failure(response.status_code, payload)

        with st.expander("Raw response"):
            body = json.dumps(payload, indent=2, default=str) if isinstance(payload, dict) else str(payload)
            st.code(body, language="json")
