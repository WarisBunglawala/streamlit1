# Vortex hosted-app query tester

A test app for the Vortex hosted-app data path. It sends SQL to
`POST /api/v1/app/query` and renders the result.

The app holds **no Snowflake credentials**. It only has a Vortex-issued token scoped to itself;
Vortex runs the query under this app's own Snowflake role and returns the rows.

## What it checks

- Whether the `VORTEX_*` variables were injected into the container at deploy time
- Whether the app can reach the Vortex API at all
- Which Snowflake role the query actually ran as
- Whether results were silently truncated at the row limit
- What each failure actually means (role not granted, token revoked, concurrency cap, and so on)

## Required environment variables

Injected automatically by Vortex when the app is deployed:

| Variable | Example |
|---|---|
| `VORTEX_API_URL` | `https://vortex.example.com/api/v1` |
| `VORTEX_APP_ID` | `59` |
| `VORTEX_APP_TOKEN` | 64-character token, never displayed by the app |

If any are missing, the app says so and disables the Run button — that usually means the runner
image's entrypoint is not expanding `APP_ENV_VARS`.

## Running locally

```powershell
pip install -r requirements.txt

$env:VORTEX_API_URL="http://localhost/api/v1"
$env:VORTEX_APP_ID="59"
$env:VORTEX_APP_TOKEN="<token>"

streamlit run app.py
```

Generate a token for a local app with `provisionApp.js` in the control panel API repo.
