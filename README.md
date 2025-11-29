# Canvas Grade Converter

Local-first web app to turn Canvas gradebook exports into a template-aligned CSV with weighted categories, extra credit, replacement rules, and letter-grade conversion.

## Stack
- Frontend: Vite + Vue 3 + Tailwind (DaisyUI)
- Backend: FastAPI (Python 3.11)
- Data: In-memory processing; SQLite only for reusable templates (future)
- Containers: Docker Compose (frontend + backend)

## Run (Docker only)
```bash
# From repo root
./start.sh up          # builds and starts frontend (5173) + backend (8000)
./start.sh down        # stop services

# Frontend build check
cd config && docker compose run --rm frontend npm run build

# Backend tests (none yet; add under backend/)
cd config && docker compose run --rm backend pytest -q
```

## Development flow
1) Plan in `todo.md` (per feature).  
2) Build small, modular changes (frontend components, backend routers/services).  
3) Validate:
   - Backend/frontend tests in Docker.
   - UI via Chrome DevTools MCP: navigate upload → review → categories → scale → results; capture snapshots; confirm centered primary area, minimal vertical scroll, and clear primary action.  
4) Commit/push only when both functional and visual checks pass.

## Backend structure
- `app/main.py` – app factory, CORS, router inclusion, lifespan cleanup
- `app/api/routes.py` – FastAPI routes (health, upload, calculate, export, session)
- `app/models/schemas.py` – Pydantic schemas and default grading scale
- `app/core/session.py` – in-memory session store and cleanup
- `app/services/parser.py` – CSV parsing and session population
- `app/services/grading.py` – grade calculation and CSV export

## Frontend notes
- Primary surfaces should be centered and use available horizontal space; avoid excessive gutters.
- Minimize vertical scrolling with tabs/sticky headers where possible.
- Keep a single focal action per view with succinct helper text.

## Privacy
- CSVs processed in memory only.
- Sessions cleared on server restart or timeout.
