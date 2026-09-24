# README.md

# ADAPT — RateSense

A web-based experiment platform for studying how people perceive and judge video playback speed. FastAPI + SQLAlchemy + SQLite backend, Vanilla JS SPA frontend for participants, and a separate admin panel for researchers.

---

## Project structure

- Backend
    - app
        - **main.py** : FastAPI app entrypoint, CORS, /media static mount
        - **database.py** : SQLAlchemy engine/session
        - **model.py :** ORM models (see Database schema below)
        - **schemas.py :** Pydantic request bodies, format data from frontend
        - **params.py :** defiend phase 2-4 experiment parameters, (speed range)
        - **speed_utils.py :** generate noice and speed
        - **config_store.py** : Global admin-editable settings (total_trials)
        - **seed.py** :  store experiment materials
        - **timeutils.py :** define Timezone (Toronto)
        - **auth.py** : Admin login
        - **sanitize.py** : XSS + path-traversal defenses
        - **seed.py** : Predefined-video seeding
        - **cached_static.py** : Cache-Control headers for /media
        - **responses.py** : {success,message,data} envelope
        - **cleanup.py :** expired, abandon test data cleanup
        - **scheduler.py :** Automatic cleanup in every 24hrs
    - routers
        - **experiment.py** : Experiment lifecycle (create/resume/restart/complete/next)
        - **phase1.py** : upload phase1 video and update phase1 state
        - **demo.py** : control demo needed data(input and output)
        - **trials.py :** control phase2-4 realtest needed data(input and output)
        - **media.py** : Per-experiment media list
        - **tester.py :** Demographic/usage survey API
        - **admin.py :**  Admin panel: auth, DB browsing, CSV export, cleanup, Video Library (upload/override/delete)
    - requirements.txt
        
        required python packages, without installing those first, website can’t run
        
- Frontend
    - HTML
        - **index.html** : main website page
        - **admin.css** : admin page
    - CSS
        - **style.css :** main website decoration
        - **admin.css** : admin page decoration
    - assets
        - img : logo, background
        - demo-gif : instruction gif
    - Js
        - **api.js** :  define api, every state transfered data
        - **state.js** : save, load, clear Experiment Id in Localstorage (save data in Browser, to load user status )
        - **components.js** :  page render (every pages store in javascript to avoid users changing experiment page)
        - **router.js** : control each state and events happening (phase 1 → start, test, complete)
        - **app.js** : control page procedure (start/restart/refresh/check User Status)
        - **admin.js** : Admin panel (independent SPA)
        - pages
            - **simple.js :** home, terms, procedure, phase-n start, complete
            - **phase1.js** : Camera check, 3s "get ready" + 5s recording
            - **phaseModule.js** : Phase 2/3/4 instruction/demo/realtest
            - **tester.js :** Survey intro screen + one-question-at-a-time flow
            - **misc.js** : continue or restart dialog

---

## Setup

### Option 1 — Docker Deployment

Docker Compose is the recommended way to deploy the complete ADAPT system. It packages the frontend, backend, and PostgreSQL database into separate services and provides persistent storage for database records and media files.

#### 1. Prerequisites

Install **Docker** with Docker Compose support on the deployment server.

Verify the installation:

```bash
docker --version
docker compose version
```

#### 2. Configure Environment Variables

Create a `.env` file in the project root:

```
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_strong_password
ADMIN_TOKEN_SECRET=your_random_secret

POSTGRES_USER=adapt
POSTGRES_PASSWORD=your_database_password
POSTGRES_DB=adapt
```

> Do not commit `.env` to the repository. Keep administrator credentials and database passwords private.
> 

#### 3. Start the System

From the project root, run:

```
docker compose up -d --build
```

This will automatically:

1. Build the frontend and backend images.
2. Start the PostgreSQL database.
3. Wait for PostgreSQL to become ready.
4. Start the backend API.
5. Start the frontend web server.
6. Create persistent Docker volumes for database data and media files.

Check the running services with:

```
docker compose ps
```

#### 4. Access the System

By default:

```
Participant site: http://<server-ip>:5173/
Admin panel:      http://<server-ip>:5173/admin.html
Backend API:      http://<server-ip>:8123/
```

Replace `<server-ip>` with the IP address or hostname of the deployment server.

If the system is deployed behind a reverse proxy or domain, use the corresponding HTTPS URLs instead.

#### 5. Stop or Restart

Stop the services without removing persistent data:

```
docker compose down
```

Start them again:

```
docker compose up -d
```

To rebuild the images after code changes:

```
docker compose up -d --build
```

#### 6. Persistent Data

Docker volumes are used to preserve data across container restarts and rebuilds:

```
db_data     → PostgreSQL database
media_data  → videos and self-recordings
```

Therefore, rebuilding or restarting the containers does not normally remove experiment data or uploaded media.

> **Important:** Do not use `docker compose down -v` unless you intentionally want to delete the persistent Docker volumes and their stored data.
> 

### Option 2 — Manual Development Setup

### 1. Backend

#### 1.1 Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### 1.2 Configure Environment Variables

All three are **required** — if any is missing, `verify_login()` always returns `None` and admin login is effectively disabled.

**macOS / Linux:**

```bash
export ADMIN_USERNAME=your_name
export ADMIN_PASSWORD=a_strong_password
export ADMIN_TOKEN_SECRET=some_random_string
```

**Windows PowerShell:**

```bash
$env:ADMIN_USERNAME="your_name"
$env:ADMIN_PASSWORD="a_strong_password"
$env:ADMIN_TOKEN_SECRET="some_random_string"
```

#### 1.3 Database Configuration

The application supports both **SQLite** and **PostgreSQL**:

- **SQLite (default for local development):** If `DATABASE_URL` is not provided, the application automatically uses `backend/adapt.db`.
- **PostgreSQL:** Set `DATABASE_URL` to use an external PostgreSQL database.

For Docker deployment, `docker-compose.yml` automatically starts a PostgreSQL 16 container and configures the backend to use it. No separate PostgreSQL installation is required.

> **PostgreSQL SSL:** External PostgreSQL connections may require SSL depending on the database provider. The Docker Compose PostgreSQL container uses `DB_SSLMODE=disable` because the database runs locally within the Docker network. If connecting to a managed/external PostgreSQL service, configure `DB_SSLMODE` according to that provider's requirements.
> 

> **Schema changes:** This project uses `Base.metadata.create_all()` rather than a migration tool. Changes to `models.py` are not automatically applied to existing databases. For local SQLite development, the database can be deleted and regenerated. For PostgreSQL deployments with existing data, use a proper schema migration (e.g. Alembic) rather than deleting the database.
> 

#### 1.4 Start the Backend Server

Start the FastAPI development server with:

```bash
uvicorn app.main:app --reload --host <HOST> --port <PORT>
```

Replace `<HOST>` and `<PORT>` according to your deployment environment.

For **local development**, use:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8123
```

The backend will be available at:

```
http://127.0.0.1:8123
```

On the first startup, the application initializes the database and seeds the `Media` table by scanning **`backend/app/media/`**  for supported video files.

### 2. Frontend

The frontend consists of static HTML, CSS, and JavaScript files. Serve the `frontend` directory using any HTTP web server.

#### 2.1 Start a Local Development Server

```bash
cd frontend
python3 -m http.server 5173
```

- Participant site: `http://127.0.0.1:5173/`
- Admin panel: `http://127.0.0.1:5173/admin.html`

If the frontend is hosted on another machine or server, replace `127.0.0.1:5173` with the corresponding hostname, IP address, or domain name.

#### 2.2 Configure the Backend API

The frontend communicates with the backend through the `window.ADAPT_API_BASE` configuration.

If the backend is not running at the default API endpoint, define `window.ADAPT_API_BASE` **before the other frontend scripts are loaded**:

`frontend/js/api.js` and `frontend/js/admin.js` : 

```jsx
const API_BASE = window.ADAPT_API_BASE || "http://your_backend_server/api/v1"
```

### 3. Video files

Drop `.mp4`/`.webm`/`.mov`/`.m4v` files into `backend/app/media/` **before first launch** — every video found there (except `demo_video.mp4`, which is handled specially and always seeded first) becomes part of the randomly-assigned pool automatically. There is no filename requirement; `seed.py` discovers whatever's actually in the folder. 

> `demo_video.mp4` itself must be present under that exact name. **More videos can be added later through the admin panel's Video Library uploader without restarting the server.**
> 

---

## Participant experiment flow

Home → Terms Agreement → Procedure → **Phase 1** (self-recording) → **Phase 2** (Direct Resolution) → **Phase 3** (Speed Estimation) → **Phase 4** (Threshold & Tolerance) → Completed.

Each of Phase 2–4 follows: instruction → interactive demo (not recorded) → real test (recorded) → phase complete. The backend, not the frontend, always decides the next page (`POST /experiments/{id}/next` and the various `.../complete` endpoints return `next_state`).

- **Real HTML5 video** with live `playbackRate` control drives every interactive trial; nothing is simulated.
- **Mouse and touch both work** on Phase 2/3's drag interaction and Phase 4's tap-to-mark interaction, so the experiment runs on phones and tablets, not just desktop. A few iOS Safari–specific fixes matter here:
    - `<video>` elements get `pointer-events: none` in CSS — iOS Safari otherwise intercepts touches on `<video>` for its own native gestures (long-press "Save Video", AirPlay, etc.) *before* the app's own touch handlers ever see them, which is what makes dragging feel unresponsive or "stuck" on iOS specifically.
    - `video.playbackRate` writes during a drag are throttled to once per animation frame (`requestAnimationFrame`) rather than on every raw `touchmove` — flooding iOS's native playback-rate pipeline with updates makes audio/visible speed lag behind the finger instead of tracking it live.
    - `preservesPitch` is set on the unprefixed, `webkit`prefixed, *and* `moz`prefixed property names together, since some iOS/WebKit versions silently ignore the unprefixed one and keep running (latency-inducing) pitch-correction DSP even though it was asked to turn off.
    - Phase 4's second tap calls `preventDefault()` on `touchend` to suppress the browser's follow-up synthetic `click`, which would otherwise double-count a single physical tap as two clicks.
- **Audio plays on every phase except Phase 4** : base on original version of ADAPT on Toush Designer
- **Resume works after closing the browser**: LocalStorage stores only `experimentId`; everything else (current phase, current trial, current state) is re-fetched from the backend on load.

---

## Demographic survey

A separate 10-question survey (age, gender, occupation, viewing habits, etc.):

- Opens with an **intro screen** explaining the survey's purpose and expected length before any question is shown — only on a participant's first visit (`current_question === 0`). Clicking its "Next" button just advances to question 1 locally; nothing is submitted to the backend from the intro screen itself.
- Rendered **one question at a time** rather than one long form. Each "Next" click submits only that question's answer and waits for the backend to confirm before advancing — nothing is lost if the participant closes the tab mid-survey.
- Resume works the same way as the rest of the app: on load, the frontend asks the backend `GET /survey/{experiment_id}` which question to render, based on `AppState.experimentId` (LocalStorage). A participant resuming mid-survey lands straight back on their question — the intro screen is *not* shown again.
- Free-text "Other: ___" answers are sanitized both client-side (defense-in-depth) and server-side (the real trust boundary).

---

## Admin panel

`admin.html` is a completely separate mini-app from the participant site — different auth model, different navigation pattern (list → detail, not a state machine), and it's never loaded by participants.

**Login & sessions**: a custom username/password form (deliberately *not* the browser's native HTTP Basic Auth dialog, which would clash with the SPA UI). On success, the backend issues a **signed JWT** (`HS256`, signed with `ADMIN_TOKEN_SECRET`, containing the admin username as `sub` and an `exp` claim), valid for **60 minutes** from issuance. The token is stored in `sessionStorage` (cleared when the tab closes) and sent as `X-Admin-Token` on every subsequent admin request. Once it expires, `require_admin()` rejects it with 401 and the admin panel's own 401 handler clears the stored token and shows the login form again with "Your session expired." — no separate refresh-token flow; the admin just logs back in.

**Experiment list & detail**: browse every experiment, its status, current state, self-recording metadata, and full trial-by-trial results — no need to open a separate DB tool.

**Export CSV**: `experiment_data.csv` with one row per trial. and joined with that experiment's survey answers so demographics are available on every row without a manual join.

**Cleanup Expired**: manually trigger the 24-hour expiration cleanup process.

The cleanup process:

- Deletes expired self-recordings.
- Preserves all trial and experiment data.
- Deletes experiments with an **expired** or **abandoned** status only when the experiment stage is “terms-agreement”.

The system also runs this cleanup process automatically every **24 hours**, and the cleanup interval can be modified in `backend/app/scheduler.py`

**Video Library**: the researcher-facing control center for experiment videos and pacing —

- **Trials per phase**: set how many predefined videos get randomly assigned to each *new* experiment (default 5; the participant's own self-recording is always added on top). Applies going forward only — experiments already in progress keep whatever count they started with.
- **Upload a new video**: add to the pool, effective for the next experiment created.
- **Per-video Phase 3/4 parameter overrides**: pin a specific `actual_speed` (Phase 3) or `direction`/`delay_ms`/`tick_ms` (Phase 4) for a video — applies to *every* experiment (past and future) that draws that video, since these are stored on the video itself.
- **Deactivate / Activate**: hide a video from future random assignment without touching its file or any historical data it's already part of.
- **Delete**: only allowed for a video that was *never* actually used by any experiment (checked against `ExperimentMedia`/`ExperimentTrial`); otherwise the API returns a 409 telling you to deactivate instead.
- The demo video is always listed first and cannot be deactivated or deleted through this UI.

**Experiment detail → Self-Recording Parameters**: unlike the 5 shared predefined videos, each experiment's self-recorded video is unique to that experiment, so its Phase 3/4 overrides are edited per-experiment, right on that experiment's detail page.

---

## How experiment parameters are decided

Each experiment uses **N + 1 videos per phase**, where:

- **N** = the admin-configured `total_trials`
- **+1** = the participant's self-recorded video

The same video order is maintained across **Phase 2, Phase 3, and Phase 4**, as specified in SRS §5.

### Parameter Resolution

For each video slot, the backend determines the experiment parameters when `GET /trials/next` is called.

The resolution process is:

```
Is an admin override set?
        │
   ┌────┴────┐
  Yes       No / NULL
   │            │
   ▼            ▼
Use the      Compute the value
override     deterministically
                  │
                  ▼
        seed = SHA-256(
            experimentID + phase + trialKey
        )
                  │
                  ▼
        random.Random(seed)
                  │
                  ▼
        choice(...) / random()
```

When no override is configured, the parameter is generated **deterministically** using a seed derived from:

```
experimentID + phase + trialKey
```

The seed is generated using SHA-256 and passed to Python's `random.Random()`.

This ensures that requesting the same trial again — for example, after refreshing the page during a trial — produces the **same parameter value** rather than generating a new random value.

At the same time, these automatically generated values are **not persisted to the database**. They are only stored when an administrator explicitly sets an override.

### Parameter Override Storage

Overrides are stored according to their scope:

| Scope | Database Storage | Editable From |
| --- | --- | --- |
| A predefined video, shared across all experiments | `Media.*_override` columns | Video Library |
| A self-recording belonging to a specific experiment | `SelfRecording.*_override` columns | Experiment Detail page |

This means that modifying a `Media` override affects the corresponding predefined video wherever it is used, while a `SelfRecording` override only affects that specific experiment's self-recording.

### Default Parameter Generation

When no override is configured, the default parameter values are generated from the project's parameter definitions and utility functions:

- **Parameter ranges:** `/backend/app/params.py`
- **Parameter generation utilities:** `/backend/app/speed_utils.py`

`params.py` defines the valid parameter ranges, while `speed_utils.py` contains the logic used to generate parameter values from those ranges.

Therefore, the overall behavior is:

```
Admin Override
      │
      ├── Set → Use stored override
      │
      └── NULL
           │
           ▼
     Deterministic generation
           │
           ├── Parameter range → params.py
           │
           └── Generation logic → speed_utils.py
```

> **Key principle:** Experiment parameters are reproducible by default, but are only persisted when explicitly overridden by an administrator.
> 

---

## Video delivery & caching

Predefined videos are **not hardcoded** — `seed.py` scans `backend/app/media/` on first startup (empty DB only) and creates one `Media` row per video file found there, using the actual filename. The demo video is the one exception: identified by the fixed name `demo_video.mp4`, always seeded first. Videos uploaded later via the admin Video Library get a random filename prefix and are picked up the same way `get_predefined_media()` always has (it filters by "not the demo video" + "not deactivated," never by a fixed name list).

Because the same 5–6 videos repeat across every phase (Phase 2, 3, and 4 each run the participant through all of them), and each phase transition rebuilds the whole page — destroying and recreating the `<video>` element even when the `src` is identical to one just shown — the browser would otherwise re-request the same video bytes from the server many times over in a single experiment. `cached_static.py` wraps the `/media` static mount to send:

- `Cache-Control: public, max-age=604800, immutable` for predefined/demo videos, so the browser reuses its local copy without even contacting the server again after the first load, and
- `Cache-Control: no-store` for self-recordings (`media/recordings/`), since those can be deleted server-side at any time and must never be served stale from a participant's own disk cache.

---

## API overview

Base URL: `/api/v1`. Every response follows:

```json
{ "success": true,  "message": "...", "data": {...} }
{ "success": false, "message": "...", "error_code": "..." }
```

### Participant (no auth required)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/experiments` | Create a new experiment, randomly assign videos |
| GET | `/experiments/{id}` | Resume: current state/phase/trial/status |
| POST | `/experiments/{id}/restart` | Restart (deletes self-recording, keeps history) |
| POST | `/experiments/{id}/complete` | Mark complete, delete self-recording |
| POST | `/experiments/{id}/next` | State-machine-driven next page |
| GET | `/experiments/{id}/media` | This experiment's assigned videos |
| POST | `/phase1/upload` | Upload the 5-second self-recording |
| POST | `/phase1/complete` | Finish Phase 1 |
| GET | `/demo?phase=N&experiment_id=` | Demo video + phase-specific practice parameters |
| POST | `/demo/complete` | Finish demo (never recorded in trial data) |
| GET | `/trials/next?experiment_id=&phase=` | Next trial's video + parameters |
| POST | `/trials` | Submit one trial's result |
| GET | `/survey/{experiment_id}` | Survey resume: which question to show next |
| POST | `/survey/{experiment_id}/answer` | Submit one survey answer |

### Admin (requires `X-Admin-Token` header — a JWT, expires after 60 minutes)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/admin/login` | Exchange credentials for a JWT |
| GET | `/admin/experiments` | List all experiments |
| GET | `/admin/experiments/{id}` | Full detail: media, self-recording, trials |
| GET | `/admin/media` | List all videos + their global overrides |
| PUT | `/admin/media/{id}/params` | Set/clear a video's global override |
| POST | `/admin/media/upload` | Add a new predefined video |
| POST | `/admin/media/{id}/deactivate` | Hide from future random assignment |
| POST | `/admin/media/{id}/activate` | Undo a deactivation |
| DELETE | `/admin/media/{id}` | Permanently delete (only if never used) |
| PUT | `/admin/experiments/{id}/self-recording/params` | Set that experiment's self-recording override |
| GET | `/admin/settings` | Current `total_trials` + available video count |
| PUT | `/admin/settings` | Change `total_trials` (applies to future experiments) |
| GET | `/admin/export-csv` | Download all trial data joined with survey answers |
| POST | `/admin/cleanup` | Expire and clean up 24h+ stale experiments |

---

## Database schema

SQLite, `backend/adapt.db`. No migration tool — see the setup note above.

| Table | Purpose |
| --- | --- |
| `media` | Videos (predefined + demo), with `is_active` and global Phase 3/4 overrides |
| `experiments` | One row per participant session; `current_state`/`current_phase`/`current_trial` drive resume |
| `self_recordings` | Uploaded Phase 1 video, with per-experiment Phase 3/4 overrides |
| `experiment_media` | Which videos (and in what order) belong to one experiment |
| `experiment_trials` | Every real (non-demo) trial result across Phase 2–4 |
| `survey_responses` | One row per experiment; demographic/usage answers, `current_question` for resume |
| `app_config` | Singleton row; currently just `total_trials` |

## Database structure

![image.png](image.png)

---

## Security notes

- **Admin auth** uses a custom JWT scheme (not HTTP Basic) specifically to avoid the browser's native login popup interfering with the SPA's own login form. Tokens are signed `HS256` JWTs (`sub` = admin username, `exp` = issuance + 60 minutes) and are rejected once expired — `require_admin()` checks both the signature and the `sub` claim against the currently-configured `ADMIN_USERNAME` on every request, so rotating `ADMIN_TOKEN_SECRET` invalidates every outstanding token immediately, even ones that haven't hit their 60-minute expiry yet. All three admin environment variables are required with no fallback defaults; put the admin panel behind HTTPS in any real deployment.
- **XSS**: the only free-text input anywhere in the app is the survey's "Other: ___" fields. `backend/app/sanitize.py`'s `sanitize_text()` strips HTML tags and escapes remaining special characters **before storage**, so every future render site (including the admin panel's `innerHTML`based tables) is protected automatically, not just whichever one remembers to escape. The frontend does the same client-side as a UX nicety — the backend is the real trust boundary, since client-side JS can always be bypassed.
- **Path traversal**: uploaded video filenames are never trusted directly. `sanitize_filename()` strips directory components and unsafe characters, and every stored file gets a random prefix so an upload can never overwrite an existing file.
- **Mass assignment**: the survey answer endpoint uses `setattr()` to write to a dynamic field name, but only after checking that field against a fixed whitelist (`SURVEY_FIELDS`) — an attacker can't use it to overwrite `experiment_id` or other non-survey columns.

---

## Known limitations

- No migration tool (Alembic etc.) — any schema change requires deleting `backend/adapt.db` in development, or a manual `ALTER TABLE` in a deployment with real data.
- Admin JWTs expire after 60 minutes with no refresh-token flow — a long admin session just means logging back in once the hour is up. Adjust `ACCESS_TOKEN_EXPIRE_MINUTES` in `auth.py` if that cadence doesn't suit your workflow.
- Video files aren't distributed with this repository and must be added manually (or via the admin Video Library uploader) before experiments can actually play anything.