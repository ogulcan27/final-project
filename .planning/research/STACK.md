# Stack Research

**Domain:** AI-powered trading-practice workstation (FinAlly), single container, single user, beginner audience
**Researched:** 2026-10-19
**Overall confidence:** HIGH on versions (read live from the npm and PyPI registries today); MEDIUM on a few runtime behaviours flagged below

Scope: only the parts still to be built. The existing backend (FastAPI 0.143.1, uv, Python 3.12, simulator, Massive poller, PriceCache, SSE) is not re-researched. Do not touch it.

## Recommended Stack

### Core Technologies (frontend)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Next.js | 16.4.2 (`latest`) | App Router, static export | Current stable. `output: 'export'` is a first-class mode. Requires Node >=20.9. Turbopack is the default bundler, nothing to configure. | HIGH |
| React / react-dom | 19.3.1 | UI | Required by Next 16. | HIGH |
| TypeScript | 6.0.3 (pin `~6.0`) | Types | Next 16.4 officially documents TS 7 (7.0.2 is `latest`) but only via the project-local `tsc` CLI and marked `experimental.useTypeScriptCli`; TS 7 has no JS compiler API, so editor plugins and typescript-eslint may lag. Take the boring path: 6.0.x. Moving to `typescript@^7` later is a one-line change. | MEDIUM |
| Tailwind CSS | 4.3.3 | Styling, dark theme | v4 is CSS-first: no `tailwind.config.js`. Theme colours live in `@theme {}` inside `globals.css`. | HIGH |
| @tailwindcss/postcss | 4.3.3 | Tailwind integration for Next | Official Next.js install path (Next uses PostCSS; the Vite plugin is not applicable). Needs `postcss` 8.5.x. | HIGH |
| lightweight-charts | 5.2.1 (Apache-2.0) | Main price chart, P&L chart, trade markers | Canvas, built for streaming financial time series, `update()` per tick is cheap. v5 has a first-class markers plugin (see API below). Tiny deps (`fancy-canvas`). | HIGH |
| d3-hierarchy | 3.1.2 (+ `@types/d3-hierarchy` 3.1.7) | Treemap layout math | Lightweight Charts has no treemap. Use only the layout function (`treemap()` + `squarify`), render rectangles as absolutely positioned `<div>`s. ~40 lines, full control of P&L colouring, tooltips and beginner explanations, no second charting library. | MEDIUM (design call, not a doc fact) |
| zustand | 5.0.15 | Client store for live prices, portfolio, selected ticker | SSE writes ~2 Hz for 10 tickers; a selector-based store prevents the whole tree re-rendering and makes the flash-on-change logic trivial. ~1 KB. | MEDIUM |

### Core Technologies (backend additions)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| stdlib `sqlite3` | Python 3.12 built-in | Persistence | See "SQLite decision" below. No dependency, plain SQL schema from PLAN.md section 7. | HIGH |
| LiteLLM | 1.106.0 (released 2026-10-18; requires Python >=3.10,<3.15) | LLM client, OpenRouter | Mandated by PLAN.md. `uv add litellm pydantic`. Pulls `openai` 2.54.0 as a transitive. | HIGH |
| Pydantic | 2.14.1 (already locked, transitive) | Structured-output schema | Declare it explicitly in `pyproject.toml` since app code now imports it directly. | HIGH |

### Supporting Libraries (frontend)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Vitest | 5.0.5 | Unit/component test runner | Always. Needs Node `^22.12 \|\| ^24 \|\| >=26` (host here is Node 26.2, fine). |
| vite | 8.3.4 | Peer of Vitest, required by plugin-react | Dev dependency only. Not used for the app build (Next builds the app). |
| @vitejs/plugin-react | 6.1.2 | JSX transform in Vitest | v6 peers on `vite ^8`, hence vite 8 above. |
| jsdom | 30.1.3 | DOM for Vitest | Needs Node `^22.22.2 \|\| ^24.15 \|\| >=26`. Use jsdom, not happy-dom: fewer surprises with Testing Library. |
| @testing-library/react | 16.3.3 | Component rendering | Peer: `@testing-library/dom ^10` and `@types/react-dom` must be installed explicitly. |
| @testing-library/dom | 10.4.2 | Peer of RTL | Install explicitly (RTL 16 no longer bundles it). |
| @testing-library/jest-dom | 7.0.1 | `toBeInTheDocument` etc. | Import `@testing-library/jest-dom/vitest` in the setup file. Needs Node >=22. |
| @testing-library/user-event | 14.6.8 | Click/typing simulation | Trade bar, chat input, watchlist add/remove tests. |
| @vitest/coverage-v8 | 5.0.5 | Coverage | Optional; version must equal Vitest's. |
| @playwright/test | 1.64.1 | E2E | Lives in `test/` with its own `package.json`, not in `frontend/`. |
| @types/node | 26.6.5 -> use `^24` | Node typings | Match the Node major used in Docker, not the newest. |
| @types/react / @types/react-dom | 19.3.0 / 19.3.0 | React typings | Required for TS. |
| eslint / eslint-config-next | 10.13.0 / 16.4.2 | Lint | Optional. Next 16 no longer has `next lint`; run `eslint` directly. Skip if time-boxed. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv 0.12.x | Python deps | Always `uv add` / `uv run`. |
| Docker `node:24-slim` | Frontend build stage | Not Node 20. Node 20 reached EOL 2026-04-30 (Node release schedule). Node 22 (EOL 2027-04-30) is also fine. Next 16.4 supports Node >=20.9, so this is a safe deviation from PLAN.md "Node 20 slim". |
| Docker `python:3.12-slim` | Runtime stage | Unchanged from PLAN.md. LiteLLM supports 3.12. |
| `mcr.microsoft.com/playwright:v1.64.1-noble` | Playwright container for `docker-compose.test.yml` | Image tag must equal the `@playwright/test` version exactly (tag verified to exist on MCR). |

## Decisions in Detail

### Next.js static export: configuration and caveats (HIGH, from official docs updated 2026-08-09)

```ts
// frontend/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",          // emits ./out
  images: { unoptimized: true }, // only matters if next/image is used; prefer plain <img>/SVG
};
export default nextConfig;
```

Caveats that will bite this project:

1. **Output dir is `frontend/out`.** Dockerfile copies `out/` to the Python stage's `static/`.
2. **Unsupported with `output: 'export'`:** rewrites, redirects, headers, cookies, Proxy (formerly middleware), Server Actions, ISR, default image loader, dynamic routes without `generateStaticParams`. The app is a single page (`/`), so none are needed. Do not create dynamic routes.
3. **No dev proxy via `rewrites`.** Because rewrites are unsupported in export mode, `next dev` cannot proxy `/api/*` to FastAPI through config in the same file. Two options: (a) use the function form of `next.config.ts` and add `rewrites()` only when `phase === PHASE_DEVELOPMENT_SERVER` (dev proxy to `http://localhost:8020`, the user's test-server port), or (b) skip `next dev` entirely and rebuild + let FastAPI serve. Recommend (a). Confidence MEDIUM: pattern follows from the docs but was not executed here; verify in the first frontend phase.
4. **Every component touching `window`, `EventSource`, `localStorage` or the chart library must be a Client Component (`'use client'`) and access browsers APIs inside `useEffect`**, because Client Components are prerendered to HTML at build time. `new EventSource(...)` at module scope or in render breaks `next build`.
5. **Call `/api/*` with relative URLs** (same origin in production). Do not fetch at build time (the backend is not running during `next build`).
6. **Serving from FastAPI:** mount `StaticFiles(directory="static", html=True)` at `/` AFTER all `/api` routes so it does not shadow them. Next also emits `404.html`; with a single route nothing else is needed. `trailingSlash` can stay default.
7. **Fonts:** `next/font/google` downloads at build time (needs network in the Docker build stage and bakes the font in). Acceptable, but a system monospace stack (`ui-monospace, "SF Mono", Menlo, Consolas`) avoids the dependency and fits the terminal look.

### Tailwind v4 style (HIGH, from official Next.js install guide)

```bash
npm install tailwindcss @tailwindcss/postcss postcss
```

```js
// frontend/postcss.config.mjs
const config = { plugins: { "@tailwindcss/postcss": {} } };
export default config;
```

```css
/* frontend/app/globals.css */
@import "tailwindcss";

@theme {
  --color-bg: #0d1117;
  --color-panel: #161b22;
  --color-border: #30363d;
  --color-accent: #ecad0a;     /* amber */
  --color-primary: #209dd7;    /* blue */
  --color-submit: #753991;     /* purple */
  --color-up: #3fb950;
  --color-down: #f85149;
}
```

Each `--color-*` becomes utilities (`bg-panel`, `text-accent`, `border-border`). Do NOT create `tailwind.config.js`, do not use `@tailwind base/components/utilities` directives (v3 style), do not install `autoprefixer` (v4 handles prefixing). Price flash: a CSS class with `transition: background-color 500ms` toggled from React; no animation library.

### Charting library choice (HIGH for LWC capability, MEDIUM for the treemap/sparkline split)

Recommendation: **TradingView Lightweight Charts 5.2.1 for the main chart and P&L chart; d3-hierarchy + divs for the treemap; hand-written SVG `<polyline>` for sparklines. Do not add Recharts.**

| Need | Tool | Reason |
|------|------|--------|
| Main ticker chart (area/line, live ticks) | LWC `AreaSeries` | `series.update({time, value})` per SSE tick; canvas, smooth at 2 Hz. |
| P&L chart (portfolio value over time) | LWC `AreaSeries` or `LineSeries` | Same API, data from `/api/portfolio/history`. |
| Buy/sell markers on both charts | LWC `createSeriesMarkers` | Verified in official API docs (see below). Recharts has no equivalent; would be hand-built `ReferenceDot`s. |
| Sparklines (10 in watchlist) | Inline SVG polyline | 10 extra chart instances with canvases and resize observers is overkill for a 60x20 px line; an SVG polyline from the last N prices is about 15 lines and trivially testable in jsdom. |
| Treemap heatmap | d3-hierarchy `treemap()` + absolutely positioned divs | LWC cannot do treemaps. Recharts' `Treemap` works with a custom `content` renderer, but pulls in Recharts plus redux-toolkit/immer/react-redux transitives for one chart; colour by P&L needs a custom renderer anyway. |

Lightweight Charts v5 API (all verified against official docs):

```ts
import { createChart, AreaSeries, createSeriesMarkers } from "lightweight-charts";

const chart = createChart(el, { autoSize: true, layout: { background: { color: "#0d1117" }, textColor: "#8b949e" } });
const series = chart.addSeries(AreaSeries, { lineColor: "#209dd7" });     // v5: addSeries(Type, opts), NOT addAreaSeries
const markers = createSeriesMarkers(series, []);                           // v5: markers are a plugin
markers.setMarkers([
  { time: tradeTs, position: "belowBar", shape: "arrowUp",   color: "#3fb950", text: "BUY 10 @190.12" },
  { time: tradeTs2, position: "aboveBar", shape: "arrowDown", color: "#f85149", text: "SELL 5" },
]);
// cleanup in useEffect return: chart.remove()
```

Marker fields: `time`, `position`, `shape`, `color` required; `id`, `text`, `size` (default 1), `price` (only for the price-position variant) optional. `setMarkers([])` clears.

Rules the implementer must know (partly from memory of the library, MEDIUM):
- `time` for intraday data is `UTCTimestamp` in **seconds**, strictly ascending and unique. SSE ticks arrive every 500 ms, so two ticks share a second: bucket by `Math.floor(ts)` and let `update()` overwrite the latest point rather than appending.
- A marker should reference a time that exists in the series data; trade markers should use the trade's executed second, and the price series should have a point at or near that second (the post-trade SSE tick provides it). Verify behaviour for markers with times outside the data range in the charts phase.
- No official React wrapper is needed. Use `useRef` + `useEffect`, create once, `update()` on new data, `chart.remove()` on cleanup (React Strict Mode double-mounts in dev, so the cleanup must be correct).
- v4 to v5 breaking changes already reflected above: `addSeries(AreaSeries)`, `createSeriesMarkers`, watermark moved to a plugin (unused here).
- Library is Apache-2.0 with a TradingView attribution requirement; leave the default attribution logo on and ship the NOTICE text if distributing. (Confidence MEDIUM, from memory.)
- Canvas does not exist in jsdom: in Vitest, `vi.mock("lightweight-charts")` and test only that data and markers are passed to the API.

### SQLite access: stdlib `sqlite3` (HIGH)

Decision: **stdlib `sqlite3`, plain SQL, sync functions, no ORM.**

| Option | Verdict | Why |
|--------|---------|-----|
| stdlib `sqlite3` | **Use** | Zero dependency; schema is six tables written in PLAN.md as plain SQL; DB operations are microsecond-scale on a local file. Matches "simple, no overengineering" and the existing codebase map ("no ORM declared"). |
| aiosqlite 0.22.1 | Not needed | A thread-per-connection wrapper around the same sqlite3. Buys nothing here: one user, tiny queries. Adds async-everywhere ceremony for beginners. |
| SQLModel 0.0.48 | Avoid | Pre-1.0, ORM and session layer for six tables; hides the SQL that this learning project wants visible; schema/seed lives in `backend/db/` as SQL per PLAN.md. |

How to use it without foot-guns:
- Declare route handlers that touch the DB as plain `def` (not `async def`); FastAPI runs them in its threadpool. For background/async callers (30 s snapshot task, chat flow), wrap with `await asyncio.to_thread(fn, ...)`.
- Open a short-lived connection per call (`sqlite3.connect(path, isolation_level=None)`, `row_factory = sqlite3.Row`), do not share one connection across threads.
- Execute trades inside `BEGIN IMMEDIATE ... COMMIT` so cash and position updates plus the `trades` insert are atomic and two concurrent requests (manual trade plus chat trade) cannot interleave.
- `PRAGMA busy_timeout=5000`. `PRAGMA journal_mode=WAL` is fine on the Docker named volume (`finally-data:/app/db`); avoid WAL if the user bind-mounts a Windows host folder (known WAL/shared-memory problems across the Windows/Linux boundary). Default journal mode is acceptable at this scale; WAL is optional.
- Lazy init: `CREATE TABLE IF NOT EXISTS` plus seed when `users_profile` is empty. Tests use `:memory:` or a `tmp_path` file.

### LiteLLM + OpenRouter structured outputs (HIGH on request shape, tested; MEDIUM on live model behaviour)

Version: **litellm 1.106.0**. OpenRouter lists `nvidia/nemotron-3-super-120b-a12b:free` with `response_format` and `structured_outputs` in supported parameters, context 262144, one endpoint (provider Nvidia), pricing 0 (checked on the OpenRouter models API today). A paid, non-free sibling `nvidia/nemotron-3-super-120b-a12b` also exists (cheap) if the free tier's daily limit becomes a blocker.

I verified the wire format by pointing LiteLLM 1.106.0 at a local capture server (no API key used). For this call:

```python
from litellm import acompletion
MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
EXTRA_BODY = {"provider": {"require_parameters": True}}
resp = await acompletion(model=MODEL, messages=messages, response_format=ChatReply, extra_body=EXTRA_BODY)
reply = ChatReply.model_validate_json(resp.choices[0].message.content)
```

the HTTP body contained exactly:
- `response_format: {"type": "json_schema", "json_schema": {"name": "ChatReply", "strict": true, "schema": {...}}}` with `additionalProperties: false` added and every property listed under `required` (including fields that have defaults)
- `provider: {"require_parameters": true}` merged at top level (so `extra_body` works as the project skill says)
- `usage: {"include": true}` added by LiteLLM

Implementation guidance:
- **Use `acompletion` (async) inside FastAPI**, not blocking `completion`, so the SSE price stream is not stalled during a multi-second LLM call.
- Model the schema from PLAN.md section 9 with Pydantic: `message: str`, `trades: list[TradeAction]`, `watchlist_changes: list[WatchlistChange]`, with `side: Literal["buy","sell"]` and `action: Literal["add","remove"]`. Because strict mode marks every field required, the model must emit empty arrays; tell the system prompt so.
- LiteLLM emits `$defs`/`$ref` for nested models. If the NVIDIA endpoint rejects or mishandles `$ref` (unverified), flatten by inlining the nested models in the schema or fall back to `response_format={"type": "json_object"}` plus a prompt-embedded schema. Test this live once early; this is the single largest unknown (see PITFALLS).
- Nemotron 3 Super is a reasoning model (`reasoning` in its supported parameters). Give a generous `max_tokens` so reasoning does not consume the budget before the JSON is emitted, and treat empty `content` as a failed call to report to the user. (MEDIUM: inferred from the model's capabilities, not observed.)
- Free tier: 50 requests/day on a free key and prompts may be logged by the provider (from the project skill). Everything except the manual LLM smoke test must run with `LLM_MOCK=true`.
- `LLM_MOCK`: implement as a function returning a deterministic `ChatReply` parsed from simple keywords in the user message (for example "buy N TICKER"), so the E2E "AI executes a trade" scenario is real. Do not use LiteLLM's `mock_response` for this; a plain Python branch is simpler and has no import cost.
- LiteLLM imports slowly (seconds). Import it lazily inside the live-call path so app start and mock-mode tests stay fast.
- Key comes from the process environment (`OPENROUTER_API_KEY`); never read `.env` in code paths agents inspect.

### Frontend test runner: Vitest 5 + React Testing Library (HIGH)

```ts
// frontend/vitest.config.mts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", setupFiles: ["./vitest.setup.ts"], globals: true },
});
```

```ts
// frontend/vitest.setup.ts
import "@testing-library/jest-dom/vitest";
```

Notes: Next's own `tsconfig` sets `"jsx": "preserve"`; Vitest handles TSX itself via plugin-react, so no conflict. Exclude `test/` (Playwright) from Vitest's `include` so the two runners never collide. Next's docs also describe Vitest setup; the above is the minimal version. Server Components do not exist in this app (everything is `'use client'`), which removes the one area Vitest cannot test.

### Playwright (HIGH)

`@playwright/test` 1.64.1 (published 2026-10-19 window; package `modified` today). Pin the exact version in `test/package.json` and use image `mcr.microsoft.com/playwright:v1.64.1-noble` in `docker-compose.test.yml`; mismatched package and browser image versions are the common failure. Use `baseURL: "http://app:8000"` inside compose; run the app service with `LLM_MOCK=true`. Locally against a dev server use port 8020 per user preference.

## Installation

```bash
# Backend (from backend/)
uv add litellm pydantic

# Frontend (from frontend/)
npm install next@16.4.2 react@19.3.1 react-dom@19.3.1 lightweight-charts@5.2.1 d3-hierarchy@3.1.2 zustand@5.0.15
npm install -D typescript@~6.0.3 @types/node@^24 @types/react@19.3.0 @types/react-dom@19.3.0 @types/d3-hierarchy@3.1.7 \
  tailwindcss@4.3.3 @tailwindcss/postcss@4.3.3 postcss@^8.5 \
  vitest@5.0.5 vite@^8.3 @vitejs/plugin-react@6.1.2 jsdom@30.1.3 \
  @testing-library/react@16.3.3 @testing-library/dom@^10 @testing-library/jest-dom@7.0.1 @testing-library/user-event@14.6.8

# E2E (from test/)
npm install -D @playwright/test@1.64.1
npx playwright install   # only outside the Playwright Docker image
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Lightweight Charts 5 | Recharts 3.10.1 | If markers/zoom/streaming were not needed and you wanted one declarative library for every chart including treemap. Here markers and live updates are core value, so LWC wins. |
| d3-hierarchy + divs | Recharts `Treemap` | If you prefer zero hand-written layout code and accept the Recharts dependency tree. Acceptable fallback if the d3 approach takes longer than expected. |
| SVG sparkline | LWC per row | If sparklines later need crosshair/tooltip. |
| stdlib sqlite3 | aiosqlite | If the app becomes multi-user/high write concurrency. Not this project. |
| zustand | React context + `useSyncExternalStore` | If avoiding any extra dependency matters more than convenience. |
| TypeScript 6.0.3 | TypeScript 7.0.2 | After the toolchain (editor plugin, eslint) is confirmed to work; Next 16.4 documents support. |
| Vitest + jsdom | happy-dom | Faster, but more API gaps with Testing Library. |
| Playwright container | Playwright installed in app image | Never; PLAN.md keeps browsers out of the production image. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Tailwind v3 patterns (`tailwind.config.js`, `@tailwind base`, autoprefixer) | v4 is CSS-first; mixing styles produces silent no-ops | `@import "tailwindcss"` + `@theme` |
| `chart.addAreaSeries()` / `series.setMarkers()` | Removed in Lightweight Charts v5 | `chart.addSeries(AreaSeries, ...)`, `createSeriesMarkers(series, ...)` |
| Pages Router, `next export` | Legacy; `next export` removed in Next 14 | App Router with `output: 'export'` |
| `next/image` with default loader, Server Actions, Route Handlers using Request, `rewrites` in export builds | Unsupported with static export (build error) | Plain `<img>`/SVG, `fetch('/api/...')` to FastAPI |
| SWR/TanStack Query for the SSE-fed data | Request/response caches do not model a push stream | `EventSource` -> zustand store; plain `fetch` for portfolio/trade/chat |
| SQLModel / SQLAlchemy | Overkill, hides SQL | stdlib `sqlite3` |
| Blocking `litellm.completion` in an `async def` route | Freezes event loop and SSE for the duration of the LLM call | `await litellm.acompletion(...)` |
| Node 20 in the Docker build stage | EOL since 2026-04-30 | `node:24-slim` (or 22) |
| Lightweight Charts v4 docs / StackOverflow answers | API differs from v5 | Official v5 docs |
| Playwright package/image version mismatch | Browser binaries not found | Same version in `package.json` and image tag |
| Reading `.env` into agent context | Project rule | Pass via `--env-file` / `uv run --env-file ../.env` |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| next 16.4.2 | react / react-dom ^19, Node >=20.9 | TypeScript 7 only via `tsc` CLI path, experimental. |
| vitest 5.0.5 | vite ^6.4 / ^7 / ^8, Node ^22.12 / ^24 / >=26 | Will not run on Node 20. Run frontend unit tests on the host or in Node 22+, not in a Node 20 container. |
| @vitejs/plugin-react 6.1.2 | vite ^8 only | Hence vite 8.3.4 as dev dependency. |
| jsdom 30.1.3 | Node ^22.22.2 / ^24.15 / >=26 | Stricter than Vitest itself. |
| @testing-library/react 16.3.3 | @testing-library/dom ^10, React 18/19 | Install `@testing-library/dom` explicitly. |
| @testing-library/jest-dom 7.0.1 | vitest >=0.32, Node >=22 | Use the `/vitest` entry. |
| @tailwindcss/postcss 4.3.3 | tailwindcss 4.3.3, postcss ^8.5 | Keep both Tailwind packages on the same version. |
| litellm 1.106.0 | Python >=3.10,<3.15 | Fine with 3.12. Pulls openai 2.54.0. |
| @playwright/test 1.64.1 | image `playwright:v1.64.1-noble` | Must match exactly. |

## Sources

- npm registry (`npm view`, 2026-10-19): versions, engines and peerDependencies for next, react, typescript, tailwindcss, @tailwindcss/postcss, lightweight-charts, recharts, vitest, vite, @vitejs/plugin-react, jsdom, @testing-library/*, @playwright/test, zustand, d3-hierarchy - HIGH
- PyPI JSON API (2026-10-19): litellm 1.106.0, aiosqlite 0.22.1, sqlmodel 0.0.48, pydantic 2.14.1, uvicorn 0.54.0 - HIGH
- https://nextjs.org/docs/app/guides/static-exports (lastUpdated 2026-08-09) - supported/unsupported features, config - HIGH
- https://nextjs.org/docs/app/api-reference/config/typescript (lastUpdated 2026-08-25) - TypeScript 7 support is CLI-only - HIGH
- https://tailwindcss.com/docs/installation/framework-guides/nextjs - v4 Next.js install, `@import "tailwindcss"` - HIGH
- https://tradingview.github.io/lightweight-charts/docs/api/functions/createSeriesMarkers and `.../interfaces/SeriesMarkerBase` and `.../docs/migrations/from-v4-to-v5` - markers plugin API, v5 migration - HIGH
- OpenRouter models API (`/api/v1/models`, `/models/nvidia/nemotron-3-super-120b-a12b:free/endpoints`) - model supports `response_format`, `structured_outputs`, free, 262k context, 100% 1-day uptime - HIGH
- Local experiment (scratchpad, litellm 1.106.0 against a capture server): confirmed request body shape for Pydantic `response_format` plus `extra_body` provider routing - HIGH for request shape; not a live OpenRouter call (no key available in the environment)
- Node release schedule (github.com/nodejs/Release schedule.json): Node 20 EOL 2026-04-30, 22 EOL 2027-04-30, 24 EOL 2028-04-30 - HIGH
- Project skill `.claude/skills/openrouter` - call pattern and free-tier limits (50 requests/day) - HIGH (project-authored)
- Context7 MCP was not authenticated in this session, so docs were read from official sites directly. Items labelled "from memory" (LWC attribution, marker time matching, strict-mode `$ref` handling by the NVIDIA endpoint, reasoning-token behaviour) are MEDIUM/LOW and should be spiked.

---
*Stack research for: FinAlly remaining platform (frontend, persistence, LLM chat, Docker, tests)*
*Researched: 2026-10-19*
