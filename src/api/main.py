"""FastAPI contract (APP-001).

Routes cover the judge flow: health, replay/state, insights, evidence and
personalization. All numbers come from the deterministic pipeline.
"""

from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from src.pipeline import MatchRun, receipt_payload, run_pipeline_from_dir

DATA_DIR = os.getenv("MATCHSENSE_DATA_DIR", "data/synthetic")
DEFAULT_MATCH = "MATCH-001"

app = FastAPI(
    title="MatchSense AI",
    version="0.1.0",
    description=(
        "Evidence-grounded football match intelligence. Analytics determines what "
        "happened, evidence proves why, and the narrative layer only explains it."
    ),
)


@lru_cache(maxsize=8)
def _run(match_id: str) -> MatchRun:
    try:
        return run_pipeline_from_dir(DATA_DIR, match_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "matchsense-ai", "data_dir": DATA_DIR}


@app.get("/matches/{match_id}/summary")
def summary(match_id: str = DEFAULT_MATCH) -> dict:
    return _run(match_id).summary()


@app.get("/matches/{match_id}/state")
def match_state(match_id: str = DEFAULT_MATCH) -> dict:
    run = _run(match_id)
    return {
        "match_id": run.match_id,
        "home_team": run.meta.home_team,
        "away_team": run.meta.away_team,
        "home_goals": run.meta.home_goals,
        "away_goals": run.meta.away_goals,
        "event_count": len(run.events),
        "data_version": run.meta.data_version,
        "seed": run.meta.seed,
    }


@app.get("/matches/{match_id}/insights")
def insights(match_id: str = DEFAULT_MATCH) -> list[dict]:
    run = _run(match_id)
    return [
        {
            "insight_id": insight.detection.insight_id,
            "team_id": insight.detection.team_id,
            "type": insight.detection.type,
            "start_minute": insight.detection.start_minute,
            "end_minute": insight.detection.end_minute,
            "confidence": insight.detection.confidence,
            "signals": insight.detection.triggered_signal_names,
            "claim": insight.verified.claim if insight.verified else None,
            "verification_status": insight.bundle.verification_status,
        }
        for insight in run.insights
    ]


@app.get("/matches/{match_id}/insights/{insight_id}/evidence")
def evidence(match_id: str, insight_id: str) -> dict:
    for receipt in receipt_payload(_run(match_id)):
        if receipt["insight_id"] == insight_id:
            return receipt
    raise HTTPException(status_code=404, detail=f"insight {insight_id} not found")


@app.get("/matches/{match_id}/insights/{insight_id}/narrative")
def narrative(
    match_id: str,
    insight_id: str,
    audience: str = Query("analyst", pattern="^(fan|analyst|broadcast)$"),
) -> dict:
    run = _run(match_id)
    for insight in run.insights:
        if insight.detection.insight_id != insight_id:
            continue
        output = insight.narratives.get(audience)
        if output is None:
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "no approved narrative for this audience",
                    "verification_status": insight.bundle.verification_status,
                    "reason": insight.critic_reason or "narrative rejected",
                },
            )
        return output.model_dump()
    raise HTTPException(status_code=404, detail=f"insight {insight_id} not found")


@app.get("/matches/{match_id}/receipts")
def receipts(match_id: str = DEFAULT_MATCH) -> list[dict]:
    return receipt_payload(_run(match_id))
