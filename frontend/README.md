# FinAlly Frontend

Next.js (App Router, TypeScript, Tailwind v4) single-page trading terminal, built as a static export to `out/` and served by the FastAPI backend.

```bash
npm install
npm run dev     # http://localhost:3000, proxies /api to http://localhost:8000
npm run build   # static export -> out/
npm test        # Vitest + React Testing Library
```

Layout: `src/app/page.tsx` (terminal), `src/components/` (UI panels), `src/hooks/usePriceStream.ts` (SSE), `src/lib/` (API client, formatting, portfolio math, treemap layout).
