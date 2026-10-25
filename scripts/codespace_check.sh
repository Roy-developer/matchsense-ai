#!/usr/bin/env bash
# One-shot verification for a fresh GitHub Codespace.
# Usage: bash scripts/codespace_check.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== python ==="
python --version

echo "\n=== dependencies ==="
python -c "import pydantic, fastapi, streamlit, pandas; print('runtime deps OK')"

echo "\n=== generate deterministic match ==="
python -m scripts.generate_match

echo "\n=== determinism check (regenerate, compare) ==="
cp data/synthetic/match_001.jsonl /tmp/match_a.jsonl
python -m scripts.generate_match > /dev/null
if cmp -s /tmp/match_a.jsonl data/synthetic/match_001.jsonl; then
  echo "PASS: same seed produced a byte-identical match"
else
  echo "FAIL: generation is not deterministic"
  exit 1
fi

echo "\n=== tests ==="
python -m pytest -q

echo "\n=== vertical slice ==="
python -m scripts.run_demo | head -30

echo "\n=== API smoke test ==="
python - <<'PY'
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)
checks = {
    "/health": 200,
    "/matches/MATCH-001/summary": 200,
    "/matches/MATCH-001/state": 200,
    "/matches/MATCH-001/insights": 200,
    "/matches/MATCH-001/receipts": 200,
}
for path, expected in checks.items():
    status = client.get(path).status_code
    assert status == expected, f"{path} -> {status}"
    print(f"OK  {path} -> {status}")

insights = client.get("/matches/MATCH-001/insights").json()
assert insights, "no insights returned"
first = insights[0]["insight_id"]
assert client.get(f"/matches/MATCH-001/insights/{first}/evidence").status_code == 200
assert client.get(
    f"/matches/MATCH-001/insights/{first}/narrative", params={"audience": "fan"}
).status_code == 200
print(f"OK  evidence + narrative for {first}")
PY

echo "\n=== docker build ==="
if command -v docker >/dev/null 2>&1; then
  docker build -t matchsense-ai:dev .
  echo "PASS: docker image built"

  echo "\n=== docker run: health endpoint ==="
  docker run -d --name matchsense-test -p 8000:8000 matchsense-ai:dev
  for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8000/health > /dev/null; then
      echo "PASS: container health endpoint responded"
      break
    fi
    sleep 2
  done
  curl -s http://127.0.0.1:8000/health
  echo
  docker rm -f matchsense-test > /dev/null

  echo "\n=== docker run: streams dashboard ==="
  docker run -d --name matchsense-ui -p 8501:8501 matchsense-ai:dev \
    streamlit run src/ui/app.py --server.address 0.0.0.0 --server.port 8501
  for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8501/healthz > /dev/null; then
      echo "PASS: dashboard container responded"
      break
    fi
    sleep 2
  done
  docker rm -f matchsense-ui > /dev/null
else
  echo "SKIP: docker not available in this environment"
fi

echo "\n=== ALL CHECKS PASSED ==="
