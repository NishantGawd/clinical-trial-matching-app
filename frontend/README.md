# Clinical Trial Matching Engine — Frontend

Enterprise SaaS frontend for the multi-agent Clinical Trial Matching Engine backend
(`main.py` / `nodes.py` / `ml_scoring.py`). Built with Next.js 14 (App Router),
TypeScript, Tailwind CSS, Radix UI primitives, Recharts, and Framer Motion.

## Requirements

- Node.js 18.18+ (or 20+)
- The FastAPI backend (`main.py`) running locally, by default at `http://localhost:8000`

## Setup

```bash
npm install
cp .env.local.example .env.local   # edit NEXT_PUBLIC_API_BASE_URL if your backend runs elsewhere
npm run dev
```

Open http://localhost:3000. Make sure the backend is running first:

```bash
# in the backend directory
uvicorn main:app --reload --port 8000
```

CORS is already enabled for all origins in `main.py`, so no backend changes are required.

## What's here

```
app/
  page.tsx                         Marketing landing page (hero, features, CTA into the app)
  layout.tsx, globals.css          Root layout, fonts, design tokens

  (app)/                           Route group for the authenticated application shell
    layout.tsx                       Wraps AppShell (nav, compliance banner, status pill)
    dashboard/page.tsx               Executive Clinical Dashboard (metric ribbon + match workspace)
    explore/page.tsx                 Cohort & Protocol Explorer (paginated, filterable, preview drawer)
    match/[patientId]/[trialId]/     Shareable deep-link to a single match's diagnostic report

components/
  marketing/*                     Landing page sections (hero, feature grid, how-it-works, trust, CTA)
  workspace/MatchWorkspace.tsx    Patient/trial selectors, run button, live agent visualizer
  diagnostic/MatchReportView.tsx  4-quadrant match diagnostic deep-dive
  diagnostic/FrailtyRadar.tsx     Recharts radar of the extracted feature vector
  diagnostic/*                    Calibration accordion, audit trail, dropout gauge, interventions,
                                   alternative-trial pivot panel
  dashboard/*                     Metric ribbon, live multi-agent swarm stepper
  explore/CohortExplorer.tsx      Data table + instant preview drawer
  layout/*                        App shell, compliance banner, theme provider
  ui/*                            Hand-built shadcn-style primitives (button, card, dialog, tabs, ...)

lib/
  api.ts                          Typed fetch client for every /api/* endpoint in main.py
  utils.ts, constants.ts

types/clinical.ts                 TypeScript mirror of the Pydantic schemas in agents/nodes.py
hooks/                            useHealthCheck, usePatients, useTrials
```

**Routing note:** `/` is now a public marketing page — it never calls the backend. The actual
application (everything that talks to `main.py`) lives at `/dashboard`, `/explore`, and
`/match/[patientId]/[trialId]`, all wrapped by the app shell in `app/(app)/layout.tsx`. The
`(app)` folder name is a Next.js route group — it doesn't appear in the URL.

## A note on error messages

`ApiRequestError` (in `lib/api.ts`) intentionally separates a short, user-safe `.message` (what
gets shown on screen — no hostnames, ports, or endpoint paths) from a verbose `.debugDetail`
string. If you're debugging a connection issue yourself, log `err.debugDetail` in the browser
console rather than relying on what the UI displays to end users.


## Notes on the live agent visualizer

`POST /api/match` in `main.py` returns a single JSON payload once the whole
LangGraph swarm finishes — there is no streaming/SSE endpoint for per-node
progress. `AgentSwarmStepper` therefore shows a cosmetic staged progression
through the known topology (`Retrieval & Cache -> Inclusion/Exclusion
(concurrent) -> Critic Auditor -> Synthesis & ML Scoring`) while the request
is in flight, and resolves every node to "done" the instant the real response
arrives. If `execution_mode` comes back as `DETERMINISTIC_FAST_PATH`, a note
is shown explaining that the safety pre-filter bypassed the full reasoning
swarm (see `evaluate_fast_path_rules` in the backend).

## Notes on the audit trail (Quadrant B)

`FinalMatchSummary` (the `data` object of a match response) only exposes one
consolidated `match_summary` string plus `inclusion_status` /
`exclusion_status` labels — the per-agent `inclusion_reasoning` /
`exclusion_reasoning` text in `nodes.py` is internal to the LangGraph state
and isn't part of the API contract. The UI reflects that honestly: two status
cards for the PASS/FAIL and CLEARED/DISQUALIFIED decisions, plus the single
synthesized rationale — rather than fabricating two separate reasoning texts.

## Production build

```bash
npm run build
npm run start
```
