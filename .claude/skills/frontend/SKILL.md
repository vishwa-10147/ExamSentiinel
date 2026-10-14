---
name: frontend
description: Conventions for the ExamSentinel Next.js 14 frontend — pages, API calls, auth/roles, Monaco, styling and verification. Use before adding or changing anything under frontend/.
allowed-tools: Bash, Read, Edit
---

# Frontend conventions

## Structure

- App Router pages in `frontend/app/<role>/…` (`admin`, `candidate`, `proctor`, `reviewer`, `exam`).
  Role layouts wrap pages with `components/Sidebar.tsx`; add nav entries there (typed `navItems`).
- All HTTP goes through `services/apiClient.ts` (`get/post/put/delete/upload`) or a typed service on
  top of it (`examService`, `proctoringService`, `practiceService`). Never hard-code a host:
  the base URL is `NEXT_PUBLIC_API_URL` (localhost:8000 in dev). It's **build-time** — Docker images
  need it as a build arg.
- Auth tokens live in localStorage; `contexts/AuthContext.tsx` exposes `user`. Only
  `app/admin/layout.tsx` enforces roles client-side — the API is the real guard, so every endpoint
  must check roles server-side.

## Patterns

- Monaco: `dynamic(() => import("@monaco-editor/react"), { ssr: false })`; theme from
  `useTheme().resolvedTheme` (`vs-dark` / `light`).
- Toasts: `react-hot-toast` (a global `<Toaster/>` is in `app/layout.tsx`).
- Styling: Tailwind with `dark:` variants (theme is class-based); cards are
  `rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800`.
- Untrusted text (problem statements etc.) renders through `components/practice/Markdown.tsx`,
  which builds React elements — never `dangerouslySetInnerHTML`.
- localStorage is for conveniences only (drafts, last language); wrap access in try/catch.
- Proctoring event names sent from the browser must exist in the backend allow-list
  (`DEFAULT_RISK_WEIGHTS`) and in `ProctoringEventType` — see `/ai-proctoring`.

## Verify

```bash
cd frontend && npx tsc --noEmit          # must exit 0
cd frontend && npm run build             # all pages must build (stop `npm run dev` first: both use .next)
```
Then open the page in the browser pane as the right role (demo users: `seed_admin.py`) and check
the network panel for non-2xx calls.

## Browser tests (Playwright)

```bash
cd frontend && npx playwright install chromium          # once
PLAYWRIGHT_BASE_URL=http://localhost:3000 npx playwright test --workers=1
```
- `tests/roles.spec.ts` needs the backend on :8000 with demo users + practice problems (and Piston); it skips
  when the API is down. Logins revoke each other's sessions, so it runs serially.
- **Never run two `next dev` servers on one `.next` folder.** With `PLAYWRIGHT_BASE_URL` set the config starts no
  server of its own; without it, it starts one on :3110 — stop the :3000 dev server first. Symptom of a clash:
  pages stuck on "Checking access…" and 404s for `/_next/static/chunks/*.js`. Fix: stop servers, `rm -rf .next`.
- Monaco: set code with `window.monaco.editor.getModels()[0].setValue(...)` — typing triggers auto-indent.
