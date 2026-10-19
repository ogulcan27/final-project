#!/usr/bin/env bash
# Start the FinAlly container. Pass --build to force an image rebuild.
set -euo pipefail

IMAGE=finally
CONTAINER=finally
URL=http://localhost:8000

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "No .env found, copying .env.example"
  cp .env.example .env
fi

if [[ "${1:-}" == "--build" ]] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker build -t "$IMAGE" .
fi

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$CONTAINER" \
  -v finally-data:/app/db \
  -p 8000:8000 \
  --env-file .env \
  "$IMAGE" >/dev/null

echo "Waiting for FinAlly to start..."
for _ in $(seq 120); do
  curl -sf "$URL/api/health" >/dev/null && break
  sleep 0.5
done
if ! curl -sf "$URL/api/health" >/dev/null; then
  echo "FinAlly did not become healthy within 60s. Check: docker logs $CONTAINER"
  exit 1
fi

echo "FinAlly is running at $URL"

if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
fi
