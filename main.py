from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from vehiclelens.models import BurstRequest, QueryRequest
from vehiclelens.service import VehicleLens
from vehiclelens.storage import SIGNAL_UNITS


service = VehicleLens()


@asynccontextmanager
async def lifespan(app: FastAPI):
    service.start()
    try:
        yield
    finally:
        service.stop()


app = FastAPI(title="VehicleLens", version="1.0.0", lifespan=lifespan)
ROOT = Path(__file__).resolve().parent


@app.get("/api/health")
def health():
    return {"status": "ok", "telemetry_rows": service.store.telemetry_count(), **service.health()}


@app.get("/api/telemetry/latest")
def telemetry_latest():
    return {"signals": service.store.latest(), "health": service.health()}


@app.get("/api/telemetry/history")
def telemetry_history(signal: str = "battery_temp", minutes: int = Query(default=60, ge=1, le=10080)):
    if signal not in SIGNAL_UNITS:
        raise HTTPException(400, "Unsupported signal")
    return {"signal": signal, "minutes": minutes, "samples": service.store.history(signal, minutes)}


@app.get("/api/events")
def events():
    return {"events": service.store.events()}


@app.get("/api/diagnostics/dtcs")
def diagnostics():
    return {"dtcs": service.store.dtcs()}


@app.get("/api/diagnostics/components")
def components():
    return {"components": service.components()}


@app.get("/api/analytics/efficiency")
def efficiency():
    return service.analytics.efficiency()


@app.get("/api/analytics/recurrence")
def recurrence():
    return service.analytics.recurrence()


@app.get("/api/analytics/correlation")
def correlation():
    return service.analytics.correlation_graph()


@app.post("/api/query")
def query(request: QueryRequest):
    return service.queries.answer(request.question, request.use_slm)


@app.get("/api/system/resources")
def resources():
    return service.governor.snapshot()


@app.post("/api/system/burst")
def burst(request: BurstRequest):
    service.set_burst(request.enabled)
    return service.governor.snapshot()


@app.get("/api/bootstrap")
def bootstrap():
    return service.bootstrap()


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
