"""
Network probe for hosted apps.

Answers one question only: can this container reach the Vortex API over the
network at all? It deliberately targets an endpoint that already exists on every
environment, so it needs no credentials and none of the hosted-app query code
deployed.

Reading the result:
  - ANY HTTP status back (200, 401, 404 - does not matter) = the path works
  - "Could not connect" = the path is blocked, before anything HTTP happens

Deploy this by pointing the hosted app's "App file" at probe.py instead of app.py.
"""

import time

import requests
import streamlit as st

# Requires a login, so an unauthenticated call returns a clean JSON 401 rather
# than anything environment-specific. Present on every Vortex deployment.
DEFAULT_PATH = "/api/v1/systemInfo/version"

st.set_page_config(page_title="Vortex Network Probe", layout="centered")
st.title("Vortex network probe")
st.caption("Checks whether this container can reach the Vortex API. No credentials needed.")

base = st.text_input("Vortex base URL", placeholder="https://your-vortex-domain")
path = st.text_input("Path", DEFAULT_PATH)

if st.button("Check connectivity", type="primary", disabled=not base):
    url = f"{base.rstrip('/')}{path}"
    st.write(f"Calling `{url}`")

    started = time.perf_counter()
    try:
        # allow_redirects=False so a redirect to a login page is visible as a
        # redirect rather than being silently followed.
        response = requests.get(url, timeout=15, allow_redirects=False)
    except requests.exceptions.RequestException as error:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        st.error(f"Could not connect after {elapsed_ms} ms")
        st.code(str(error))
        st.warning(
            "No HTTP response at all. The container cannot reach the load balancer - "
            "check the subnet route to the NAT gateway, the task's security group egress, "
            "and the load balancer's inbound rules."
        )
        st.stop()

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    st.success(f"Reached Vortex - HTTP {response.status_code} in {elapsed_ms} ms")
    st.info("Any status code here means the network path works. The status itself does not matter.")

    location = response.headers.get("Location")
    if location:
        st.warning(f"Redirected to: {location}")
        st.caption("A redirect towards a login provider would mean an ALB auth rule is intercepting this path.")

    with st.expander("Response body"):
        st.code(response.text[:1000] or "(empty)")

    with st.expander("Response headers"):
        st.json(dict(response.headers))
