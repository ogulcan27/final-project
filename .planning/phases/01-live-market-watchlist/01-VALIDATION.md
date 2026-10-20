---
phase: "1"
slug: "live-market-watchlist"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-19"
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Backend: pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`); Frontend: Vitest 5.0.5 (node env, pure-logic tests) |
| **Config file** | `backend/pyproject.toml`; `frontend/vitest.config.mts` (Wave 0 installs) |
| **Quick run command** | `cd backend && uv run pytest -q` (plus `cd frontend && npx vitest run && npx tsc --noEmit` once the frontend exists) |
| **Full suite command** | `cd backend && uv run pytest -q` then `cd frontend && npm run build` then the container smoke script (port 8020) |
| **Estimated runtime** | ~5 seconds backend, ~60 seconds with frontend build, ~90 seconds with container smoke |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest -q` (and `npx vitest run` once the frontend exists)
- **After every plan wave:** Run backend suite + `npm run build` + `npx tsc --noEmit`
- **Before `/gsd-verify-work`:** Full suite must be green, container smoke green, then end-of-phase human visual check of success criteria 1-5
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Filled in by the planner/executor per task. Requirement-to-test map from research:

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| DATA-01 | Probe 200 with prices selects `MassiveSource` | unit (MockTransport) | `uv run pytest tests/market/test_probe.py -q` | ❌ W0 | ⬜ pending |
| DATA-02 | 401/403/429/timeout/empty/bad body fall back; reason never contains the key | unit | `uv run pytest tests/market/test_probe.py -q` | ❌ W0 | ⬜ pending |
| DATA-03 | status carries `source` and `note`; badge label helper | unit + Vitest | `uv run pytest tests/market/test_status.py -q`; `npx vitest run` | ❌ W0 | ⬜ pending |
| DATA-04 | stale after threshold (injected clock); stale flip pushes an event | unit | `uv run pytest tests/market/test_status.py tests/market/test_stream.py -q` | ❌ W0 | ⬜ pending |
| DATA-05 | Simulator `prev_close` = session start; LIVE uses `prevDay.c` | unit | `uv run pytest tests/market -q` | partial | ⬜ pending |
| DATA-06 | One batched event per version with all tickers + status | unit + real HTTP | `uv run pytest tests/market/test_stream.py -q` | rewrite | ⬜ pending |
| DATA-08 | `/api/health` returns `status`, `source`, `note` matching SSE status | API | `uv run pytest tests/test_app.py -q` | rewrite | ⬜ pending |
| DB-01 | Fresh DB: 6 tables incl. `trades.realized_pnl`, seed $10,000 + 10 tickers | unit (tmp_path) | `uv run pytest tests/db -q` | ❌ W0 | ⬜ pending |
| DB-02 | Second init does not reseed; removed ticker stays removed; foreign schema raises | unit | `uv run pytest tests/db -q` | ❌ W0 | ⬜ pending |
| DB-05 | `db/finally.db` ignored, `.env.example` present with no values | shell | `git check-ignore -q db/finally.db && test -f .env.example` | ❌ W0 | ⬜ pending |
| WATCH-01 | History buffer windowed, capped, deduped, dropped on removal | Vitest | `npx vitest run src/shared/history.test.ts` | ❌ W0 | ⬜ pending |
| WATCH-02 | `direction` to flash decision | Vitest + human visual | `npx vitest run` | ❌ W0 | ⬜ pending |
| WATCH-03 | Bad format 400; duplicate 409; LIVE no-data rejection; simulated accepts well-formed | API | `uv run pytest tests/test_watchlist_api.py -q` | ❌ W0 | ⬜ pending |
| WATCH-04 | Delete removes + stops tracking; 404 when absent; survives restart | API | `uv run pytest tests/test_watchlist_api.py -q` | ❌ W0 | ⬜ pending |
| UI-01 | Theme tokens with the three hex values | shell | `grep -c "ecad0a\|209dd7\|753991" frontend/src/app/globals.css` | ❌ W0 | ⬜ pending |
| UI-03 | Connection state transitions incl. red after timer and CLOSED | Vitest | `npx vitest run src/hooks` | ❌ W0 | ⬜ pending |
| OPS-01 | Image builds; `/`, `/_next/*`, `/api/health`, SSE answer; restart keeps data | container smoke | smoke script (port 8020) | manual script | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py` — `DB_PATH` to `tmp_path`, delete `MASSIVE_API_KEY`
- [ ] `backend/tests/db/test_connection.py` — schema, seed once, no reseed, guard
- [ ] `backend/tests/market/test_probe.py`, `test_status.py`; rewrite `test_stream.py`; update `test_app.py`
- [ ] `backend/tests/test_watchlist_api.py` — routes through `httpx.ASGITransport` with the lifespan
- [ ] Frontend: `npm install`, `vitest.config.mts`, tests for `history`, connection-state and flash-decision helpers
- [ ] `uv add pydantic`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Flash green/red fades ~500ms | WATCH-02 | Visual timing | Open http://localhost:8020, watch price cells on ticks |
| Dark terminal layout | UI-01 | Visual | Inspect page against PLAN.md colors |
| Dot yellow → red → green on restart | UI-03 | Needs container kill/restart | Stop container, watch dot, restart, confirm green without reload |
| Badge hover reason, never the key | DATA-03 | Visual tooltip | Hover badge with no key and with a bad key |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
