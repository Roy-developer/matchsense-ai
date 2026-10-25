"""Dependency-free API smoke test, so CI needs no shell heredoc quoting."""

from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from src.api.main import app

PATHS = (
    "/health",
    "/matches/MATCH-001/summary",
    "/matches/MATCH-001/state",
    "/matches/MATCH-001/insights",
    "/matches/MATCH-001/receipts",
)


def main() -> int:
    client = TestClient(app)

    for path in PATHS:
        status = client.get(path).status_code
        if status != 200:
            print(f"FAIL {path} -> {status}")
            return 1
        print(f"OK   {path} -> {status}")

    insights = client.get("/matches/MATCH-001/insights").json()
    if not insights:
        print("FAIL no insights returned")
        return 1

    insight_id = insights[0]["insight_id"]
    for suffix in ("evidence", "narrative?audience=fan"):
        path = f"/matches/MATCH-001/insights/{insight_id}/{suffix}"
        status = client.get(path).status_code
        if status != 200:
            print(f"FAIL {path} -> {status}")
            return 1
        print(f"OK   {path} -> {status}")

    print(f"\nAPI smoke test passed for {len(insights)} insights")
    return 0


if __name__ == "__main__":
    sys.exit(main())
