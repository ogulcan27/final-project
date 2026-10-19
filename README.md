# FinAlly — AI Trading Workstation

An AI-powered trading terminal with simulated money. It streams live prices, lets you trade a $10,000 virtual portfolio, and has an AI chat assistant that can analyze positions and place trades for you.

Capstone project for an agentic AI coding course. The app is built by coding agents that coordinate through the docs in `planning/`.

The full specification is in [planning/PLAN.md](planning/PLAN.md).

## Features

- Live price stream (SSE) with green/red flash and sparklines
- Market orders with instant fill (no fees, simulated cash)
- Portfolio heatmap, P&L chart and positions table
- AI chat that can trade and manage the watchlist
- Built-in market simulator, or real data through the Massive (Polygon.io) API

## Tech Stack

| Layer    | Choice                                                     |
|----------|------------------------------------------------------------|
| Frontend | Next.js + TypeScript (static export), Tailwind CSS         |
| Backend  | FastAPI, managed with `uv`                                 |
| Database | SQLite (`db/finally.db`)                                   |
| AI       | LiteLLM -> OpenRouter, `nvidia/nemotron-3-super-120b-a12b:free`, Structured Outputs |
| Runtime  | Single Docker container on port 8000                       |

## Quick Start

Requires Docker.

1. Copy `.env.example` to `.env` and set your key:

   ```bash
   OPENROUTER_API_KEY=your-key   # required for AI chat
   MASSIVE_API_KEY=              # optional, empty = simulator
   LLM_MOCK=false                # true = mock AI replies for tests
   ```

2. Start the app:

   ```bash
   ./scripts/start_mac.sh          # macOS / Linux
   ./scripts/start_windows.ps1     # Windows PowerShell
   ```

   The image is built on first run; pass `--build` (`-Build` on Windows) to rebuild.

3. Open http://localhost:8000

Stop with `./scripts/stop_mac.sh` or `./scripts/stop_windows.ps1`. Data persists in the `finally-data` Docker volume. `docker compose up --build` also works.

The free model allows 50 requests per day. Use `LLM_MOCK=true` during development.

## Project Layout

```
frontend/   Next.js app
backend/    FastAPI app (uv project)
planning/   Specs and agent docs
scripts/    Start/stop scripts
test/       Playwright E2E tests
db/         SQLite volume mount
```

## License

See [LICENSE](LICENSE).
