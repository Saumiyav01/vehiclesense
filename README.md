# VehicleLens

Offline vehicle-intelligence prototype: synthetic CAN ingestion, time-series
storage, rule-based event correlation, matched-baseline efficiency analytics,
and a guarded natural-language query interface. Runs fully local — no Docker,
no cloud services.

The original `vehicle-sense.html` frontend (layout, Three.js digital twin,
Chart.js telemetry, navigation) is preserved and served from `static/`, with
every panel wired to live backend data.

## Stack

Python 3.12 · FastAPI/Uvicorn · DuckDB (telemetry) · SQLite (events, event
links, DTCs) · Pandas/NumPy (analytics) · psutil (resource governor) ·
vanilla JavaScript frontend.

## Run on Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 — `run.ps1` contains the same commands.

Run the tests:

```powershell
python -m unittest discover -s tests -v
```

Reproduce the benchmark (writes `benchmark_results.json`):

```powershell
python scripts\workload_test.py
```

## Structure

```
main.py                  FastAPI entry: API routes + static files
vehiclelens/
  config.py              Settings (rates, paths, SLM locations)
  models.py              Pydantic request/plan models, signal whitelist
  storage.py             DuckDB telemetry + SQLite events/DTCs, latest cache
  simulator.py           Synthetic CAN generator, seeding, ingestion thread
  analytics.py           Incident detection, recurrence, efficiency attribution
  query.py               Deterministic intent routing, plan validation
  slm.py                 Optional llama.cpp (Qwen2.5-0.5B GGUF) planner
  governor.py            CPU/RAM/ingestion/latency monitor, load shedding
  service.py             Orchestration
static/index.html        Preserved dashboard, wired to the APIs
scripts/workload_test.py Measured synthetic-workload benchmark
tests/test_core.py       5 unit tests
```

## APIs

| Endpoint | Purpose |
|---|---|
| `GET /api/bootstrap` | One-shot payload for all panels |
| `GET /api/health` | Health, telemetry row count |
| `GET /api/telemetry/latest` | Latest values per signal (cache-backed) |
| `GET /api/telemetry/history?signal=&minutes=` | Bucketed time series |
| `GET /api/events` | Correlated event timeline |
| `GET /api/diagnostics/dtcs` | Stored diagnostic trouble codes |
| `GET /api/diagnostics/components` | Live component key/values |
| `GET /api/analytics/efficiency` | Matched-baseline attribution |
| `GET /api/analytics/recurrence` | Cross-trip abnormality scan |
| `GET /api/analytics/correlation` | Event graph (nodes/edges) |
| `POST /api/query` | Natural-language query (`{"question": ..., "use_slm": bool}`) |
| `GET /api/system/resources` | Measured CPU/RAM/ingestion/latency, governor state |
| `POST /api/system/burst` | Toggle 5,000 msg/s burst target |

## Query engine — no LLM SQL, ever

`/api/query` never generates or executes SQL from a model. Intent is routed
by deterministic templates; an optional SLM may only propose a JSON query
plan that is validated by Pydantic against a signal whitelist and fixed
intent/aggregation enums — anything invalid falls back to the deterministic
router. Every response includes the validated plan and
`"sql_generated_by_llm": false`.

### Optional on-device SLM (llama.cpp + Qwen2.5-0.5B)

Not bundled. To enable, install llama.cpp and a GGUF model, then set:

```powershell
$env:VEHICLELENS_LLAMA_BIN="C:\path\to\llama-cli.exe"
$env:VEHICLELENS_MODEL_PATH="C:\path\to\qwen2.5-0.5b-instruct-q4_k_m.gguf"
```

If the binary or model is missing, times out, or emits invalid JSON, the
deterministic planner answers instead; the dashboard reports the fallback
status honestly. The resource governor sheds SLM inference first under
pressure (CPU > 75%, system RAM > 85%, ingestion > 300 msg/s, query p95 >
1.5 s).

## Measured results (`benchmark_results.json`, this machine, 2026-10-31)

Real measurements from `scripts/workload_test.py` — not targets:

- Bootstrap payload: 31.0 ms; 5,070 seeded telemetry rows; 5 correlated events; 1 DTC; 24 matched baseline trips.
- Query latency over 20 mixed natural-language queries: mean 6.95 ms, max 21.81 ms (deterministic path).
- Normal ingestion: measured 120.0 msg/s against a 120 msg/s target.
- Burst ingestion: measured 1,457 msg/s against the 5,000 msg/s target — the shortfall is honest CPU saturation of this 4 GB test sandbox, not a cap.
- Governor during burst: SLM shedding active (`CPU above 75%`, `ingestion above 300 msg/s`).
- Governor after burst: recovered to `Normal`, SLM re-allowed, ingestion back to 120.8 msg/s.
- Unit tests: 5/5 passing (incident/DTC detection, ≥20 matched trips, structured answers for all four templates, plan whitelist rejection, governor shedding).

Browser-verified (Chromium, desktop 1440px and mobile 390px): zero console
errors, zero failed requests, no mobile horizontal overflow, all visible
touch targets ≥ 44 px, assistant round-trip, event replay, and burst
shedding all exercised live.

## Notes and limits

- All vehicle data is simulated; the thermal incident (high load → coolant
  flow drop → pack temperature rise → DTC P0A7E) is seeded so correlation
  and recurrence analytics have real signal to work on.
- Efficiency attribution is associational (matched trips + least squares +
  bootstrap interval), not a causal diagnosis.
- The Dockerfile exists only for the platform preview; local Windows use
  needs nothing but Python 3.12.
