# FinAlly E2E tests

Playwright specs in `e2e/` run serially against one app instance with `LLM_MOCK=true` and a fresh database.

Against a local app (default `BASE_URL=http://localhost:8000`):

```bash
npm install && npx playwright install chromium
npx playwright test
```

In Docker (from the project root):

```bash
docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright
docker compose -f test/docker-compose.test.yml down -v
```
