# AssetFlow — Login & Dashboard (Screens 1 & 2)

A working slice of AssetFlow: React frontend + Flask backend, wired to a
real database, implementing the Login/Signup screen and the Dashboard
home screen from the mockup.

```
assetflow/
├── backend/     Flask API + SQLAlchemy models + seed script
└── frontend/    React (Vite) app
```

## What's implemented

**Backend (Flask)**
- `POST /api/auth/signup` — creates an Employee account only (no role
  selection at signup, matching the spec: roles are assigned later by
  an Admin from the Employee Directory).
- `POST /api/auth/login` — email/password login, returns a JWT.
- `GET /api/auth/me` — resolve the current user from the token.
- `GET /api/dashboard/kpis` — the 6 KPI cards (Available, Allocated,
  Maintenance Today, Active Bookings, Pending Transfers, Upcoming
  Returns).
- `GET /api/dashboard/overdue` — overdue allocations, shown separately
  per the spec.
- `GET /api/dashboard/activity` — recent activity feed.

Models mirror the table/column names in the Postgres schema delivered
earlier (`departments`, `employees`, `assets`, `asset_allocations`,
`resource_bookings`, `transfer_requests`, `maintenance_requests`,
`notifications`), using DB-agnostic column types so the same models
run against SQLite (dev) or Postgres (set `DATABASE_URL`) unchanged.

**Frontend (React + Vite)**
- `/login` — sign in / sign up, matches the wireframe's copy ("Sign up
  creates an employee account, admin roles assigned later").
- `/dashboard` — sidebar nav, KPI grid, overdue-returns banner, quick
  actions, recent activity + overdue panels, all live from the API.
- Token stored in `localStorage`, protected routing via `AuthContext`.

## Running it

**Backend**
```bash
cd backend
pip install -r requirements.txt
python seed.py        # creates assetflow.db with demo data
python app.py          # runs on http://localhost:5000
```
Demo login: `admin@assetflow.com` / `password123`

To point at Postgres instead of the SQLite dev file, set:
```bash
export DATABASE_URL=postgresql://user:pass@host:5432/assetflow
```
(This works against the `assetflow_schema.sql` schema delivered
earlier, since table/column names match — you'd run that DDL directly
instead of `db.create_all()` for the full production schema with all
constraints, triggers, and views.)

**Frontend**
```bash
cd frontend
npm install
npm run dev             # runs on http://localhost:5173
```
`frontend/.env` points `VITE_API_BASE` at `http://localhost:5000/api`
— update it if the backend runs elsewhere.

## Design notes

- Palette: ink navy (`#14213d`) for the sidebar/headings, a muted
  forest-teal accent (`#2f6d5c`) for primary actions and "available/
  verified" states, warm off-white background — steers away from the
  generic cream+terracotta/dark+neon defaults toward something that
  reads as operational software, not a marketing page.
- Type: Space Grotesk for headings, Inter for body text, IBM Plex Mono
  for anything that's inventory data — asset tags, KPI numbers, the
  activity timestamps — so numbers and tags read like scanned/tracked
  data rather than generic UI copy.
- Both screens verified end-to-end against the running Flask API (not
  mocked data) before delivery.
