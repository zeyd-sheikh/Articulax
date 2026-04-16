# Articulax — Complete Project Code Explanation

## Table of Contents

1. [What Articulax Is](#1-what-articulax-is)
2. [Technology Stack](#2-technology-stack)
3. [File Structure — Every File Explained](#3-file-structure--every-file-explained)
4. [How to Install and Run](#4-how-to-install-and-run)
5. [Environment Variables](#5-environment-variables)
6. [Database Schema — All 7 Tables in Detail](#6-database-schema--all-7-tables-in-detail)
7. [Authentication System](#7-authentication-system)
8. [Route Map — Every URL in the App](#8-route-map--every-url-in-the-app)
9. [The Complete Session Flow — End to End](#9-the-complete-session-flow--end-to-end)
10. [File-by-File Code Walkthrough](#10-file-by-file-code-walkthrough)
11. [Scoring Engine — Every Formula Explained](#11-scoring-engine--every-formula-explained)
12. [External API Integrations](#12-external-api-integrations)
13. [Error Handling and Resilience](#13-error-handling-and-resilience)
14. [Data Flow Diagrams](#14-data-flow-diagrams)
15. [CSS Architecture](#15-css-architecture)
16. [What raw_metrics_json Stores](#16-what-raw_metrics_json-stores)
17. [Recent UI and Dashboard Refinements](#17-recent-ui-and-dashboard-refinements)

---

## 1. What Articulax Is

Articulax is a Flask web application that lets university students practice timed oral communication sessions and receive automated scoring and feedback. The user picks a topic, audience, and tone on the dashboard, then speaks into their microphone for a chosen duration (1–5 minutes). The app records the audio entirely in the browser, uploads it to the Flask server when the timer ends, transcribes it via AssemblyAI, scores the transcript against a five-skill rubric using deterministic Python formulas, generates written feedback via Cohere's LLM, saves everything to a MySQL database, and displays the results on a dedicated results page.

The app currently implements **Communication Mode** only. Interview and Presentation modes are shown as disabled placeholders in the UI for future expansion.

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | Python 3.10+ / Flask | HTTP routes, server-side validation, business logic |
| Templating | Jinja2 (built into Flask) | Server-side HTML rendering with template inheritance |
| Frontend | Vanilla JavaScript | Audio recording, timer, upload, DOM manipulation |
| Styling | Plain CSS | Single stylesheet, no preprocessor or framework |
| Database | MySQL 8.x | Persistent storage via `mysql-connector-python` |
| Transcription | AssemblyAI REST API | Speech-to-text with word-level timestamps and confidence |
| Embeddings | Cohere `embed-v4.0` | Semantic similarity between topic and transcript |
| Feedback | Cohere `command-a-03-2025` | Structured JSON feedback generation via LLM |
| Auth | Flask `session` (signed cookie) | Stateless server-side session tracking |
| Password hashing | Werkzeug `generate_password_hash` | scrypt-based hashing |

No frontend frameworks (React, Vue, etc.), no job queues (Celery, Redis), no WebSockets, no external NLP libraries (spaCy, NLTK, textstat) are used. All text analysis is implemented with Python's standard library and regex.

---

## 3. File Structure — Every File Explained

```
Articulax-main/
├── app.py                              ← Main Flask application
├── schema.sql                          ← Complete database schema for fresh setup
├── requirements.txt                    ← Python package dependencies
├── .env                                ← Environment variables (DB creds, API keys)
├── .gitignore                          ← Git exclusion rules
├── PROJECT_BREAKDOWN.md                ← This file
│
├── migrations/
│   └── final_phase.sql                 ← ALTER TABLE migration for existing databases
│
├── services/
│   ├── __init__.py                     ← Empty file that makes services/ a Python package
│   ├── text_analysis.py                ← Deterministic NLP helpers (tokenization, fillers, readability, etc.)
│   ├── transcription_service.py        ← AssemblyAI REST integration (upload → transcribe → poll)
│   ├── cohere_service.py               ← Cohere V2 SDK (embeddings + structured feedback)
│   └── scoring_service.py              ← Five-skill rubric scoring engine
│
├── templates/
│   ├── base.html                       ← Shared layout (header, nav, CSS link, body block)
│   ├── home.html                       ← Public landing page
│   ├── about.html                      ← Public about/how-it-works page
│   ├── register.html                   ← User registration form
│   ├── login.html                      ← User login form
│   ├── dashboard.html                  ← Session setup form + recent sessions list
│   ├── session.html                    ← Live recording page (mic, timer, hidden fields)
│   └── results.html                    ← Score breakdown, feedback, transcript display
│
├── static/
│   ├── css/
│   │   └── styles.css                  ← All CSS for the entire application
│   └── js/
│       ├── microphone.js               ← Audio recording, timer, upload, cancel logic
│       ├── dashboard_chart.js          ← SVG score trend rendering from DB-backed score history
│       ├── register.js                 ← Client-side password match validation
│       └── login.js                    ← Client-side empty password check
│
└── uploads/
    ├── .gitkeep                        ← Placeholder so Git tracks the directory
    └── audio/                          ← Saved .webm audio files from sessions
```

### What `.gitignore` excludes

```
.venv/           ← Python virtual environment
__pycache__/     ← Compiled Python bytecode
.env             ← Secrets (API keys, DB password)
uploads/         ← User audio files
testing.html     ← Local test file
.DS_Store        ← macOS metadata
```

---

## 4. How to Install and Run

### Prerequisites

- Python 3.10 or newer
- MySQL 8.x server running locally
- A working microphone (for recording sessions)
- API keys for AssemblyAI and Cohere (already in `.env`)

### Step-by-step setup

```bash
# 1. Clone the repository
git clone https://github.com/zeyd-sheikh/Articulax.git
cd Articulax

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 3. Install all Python dependencies
pip install -r requirements.txt
```

This installs six packages: `Flask`, `Werkzeug`, `python-dotenv`, `mysql-connector-python`, `requests`, `cohere` (plus their transitive dependencies).

```bash
# 4. Create the MySQL database and all tables
# (Adjust the mysql path if it's not on your system PATH)
/usr/local/mysql/bin/mysql -u root -p < schema.sql
```

This creates the `articulax` database and all 7 tables from scratch with the correct columns and constraints.

If you already have the database from an earlier version of the project, run the migration instead:

```bash
/usr/local/mysql/bin/mysql -u root -p < migrations/final_phase.sql
```

The migration adds `raw_metrics_json` to `session_artifacts` and the five per-skill feedback columns to `com_session_feedback`.

```bash
# 5. Edit .env if your MySQL credentials differ
# The file is already present with default values

# 6. Start the Flask development server
python app.py
```

The server starts at `http://127.0.0.1:5000` in debug mode with auto-reload enabled.

---

## 5. Environment Variables

All environment variables live in `.env` at the project root. They are loaded once at application startup by `load_dotenv()` on line 20 of `app.py`. Every variable is read via `os.getenv()` wherever it's needed.

| Variable | Example Value | Where It's Used |
|---|---|---|
| `DB_HOST` | `localhost` | `app.py` → `get_db_connection()` |
| `DB_PORT` | `3306` | `app.py` → `get_db_connection()` |
| `DB_USER` | `root` | `app.py` → `get_db_connection()` |
| `DB_PASSWORD` | `WARMACHINEROX` | `app.py` → `get_db_connection()` |
| `DB_NAME` | `articulax` | `app.py` → `get_db_connection()` |
| `SECRET_KEY` | `muabestschool` | `app.py` → `app.secret_key` (signs Flask session cookies) |
| `ASSEMBLYAI_API_KEY` | 32-char hex string | `app.py` → passed to `transcribe_audio_file()` |
| `COHERE_API_KEY` | 40-char string | `services/cohere_service.py` → `cohere.ClientV2(api_key=...)` |

`SECRET_KEY` is used by Flask to cryptographically sign session cookies. If someone obtains this key they can forge sessions. `ASSEMBLYAI_API_KEY` authenticates all REST calls to AssemblyAI's transcription API. `COHERE_API_KEY` authenticates the Cohere V2 SDK for embeddings and chat.

---

## 6. Database Schema — All 7 Tables in Detail

The schema is defined in `schema.sql`. The database is named `articulax`.

### Table 1: `users`

Stores every registered account. One row per user.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `user_id` | `INT` | `AUTO_INCREMENT PRIMARY KEY` | Unique user identifier |
| `first_name` | `VARCHAR(50)` | `NOT NULL` | User's first name |
| `last_name` | `VARCHAR(50)` | `NOT NULL` | User's last name |
| `email` | `VARCHAR(100)` | `NOT NULL UNIQUE` | Email address (must be unique across all users) |
| `username` | `VARCHAR(50)` | `NOT NULL UNIQUE` | Login username (must be unique) |
| `account_password` | `VARCHAR(500)` | `NOT NULL` | Werkzeug scrypt hash of the password |
| `join_time` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | When the account was created |

**Written to by:** `POST /register` route in `app.py`.
**Read by:** `user_exists()` (registration duplicate check), `get_user_by_username()` (login lookup).

### Table 2: `resumes`

Reserved for a future Interview mode feature. **Not used by Communication mode.** Present in the schema for forward compatibility.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `resume_id` | `INT` | `AUTO_INCREMENT PRIMARY KEY` | Unique resume identifier |
| `user_id` | `INT` | `NOT NULL UNIQUE, FK → users(user_id)` | One resume per user |
| `file_path` | `TEXT` | `NOT NULL` | Server path to uploaded resume file |
| `file_name` | `VARCHAR(225)` | `NOT NULL` | Original filename |
| `upload_time` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Upload timestamp |

### Table 3: `sessions`

The top-level parent table for all session modes. One row per completed session of any type (Communication, Interview, or Presentation). In the current implementation, only Communication sessions are created.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `session_id` | `INT` | `AUTO_INCREMENT PRIMARY KEY` | Unique session identifier |
| `user_id` | `INT` | `NOT NULL, FK → users(user_id)` | Which user owns this session |
| `mode` | `VARCHAR(25)` | `NOT NULL, CHECK IN ('Communication','Interview','Presentation')` | Session type |
| `score` | `INT` | `CHECK (score >= 0 AND score <= 100)` | Overall weighted score |
| `start_time` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | When the session was saved |
| `end_time` | `TIMESTAMP` | `NULL` | Not currently populated |

The `UNIQUE (session_id, mode)` constraint exists for potential future composite foreign keys.

**Written to by:** `persist_completed_communication_session()` — first INSERT in the transaction, `cursor.lastrowid` captures the auto-generated `session_id` used by all subsequent inserts.
**Read by:** `get_recent_communication_sessions()` (dashboard list), `get_communication_session_result()` (results page).

### Table 4: `session_artifacts`

Stores the full transcript, the audio file path, and all raw scoring metrics. One row per session.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `artifact_id` | `INT` | `AUTO_INCREMENT PRIMARY KEY` | Unique artifact identifier |
| `session_id` | `INT` | `NOT NULL UNIQUE, FK → sessions(session_id)` | One artifact per session |
| `transcript_text` | `TEXT` | `NOT NULL` | Full transcript from AssemblyAI |
| `audio_file_path` | `TEXT` | `NOT NULL` | Absolute path to the `.webm` file in `uploads/audio/` |
| `raw_metrics_json` | `LONGTEXT` | `NULL` | JSON string of all computed metrics (see Section 16) |

**Written to by:** Last INSERT in `persist_completed_communication_session()`.
**Read by:** `get_communication_session_result()` via `LEFT JOIN session_artifacts sa ON s.session_id = sa.session_id`.

### Table 5: `com_sessions`

Communication-mode-specific settings chosen by the user on the dashboard. One row per communication session.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `session_id` | `INT` | `PRIMARY KEY, FK → sessions(session_id)` | Links to parent session |
| `mode` | `VARCHAR(25)` | `NOT NULL DEFAULT 'Communication', CHECK (mode = 'Communication')` | Always 'Communication' |
| `topic` | `VARCHAR(150)` | `NOT NULL` | The topic the user spoke about |
| `audience` | `VARCHAR(20)` | `NOT NULL, CHECK IN ('Kids','General','Professional')` | Target audience |
| `tone` | `VARCHAR(20)` | `NOT NULL, CHECK IN ('Formal','Persuasive','Casual')` | Desired speaking tone |
| `duration` | `INT` | `NOT NULL` | Session length in minutes (1, 2, 3, or 5) |

**Written to by:** Second INSERT in `persist_completed_communication_session()`.
**Read by:** Joined in both `get_recent_communication_sessions()` and `get_communication_session_result()`.

### Table 6: `com_session_scores`

Five integer scores (0–100) for the rubric categories. One row per communication session.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `session_id` | `INT` | `PRIMARY KEY, FK → com_sessions(session_id)` | Links to com_sessions |
| `clarity_score` | `INT` | `NOT NULL, CHECK 0–100` | How clearly the user spoke |
| `confidence_score` | `INT` | `NOT NULL, CHECK 0–100` | How confidently (few fillers, smooth delivery) |
| `structure_score` | `INT` | `NOT NULL, CHECK 0–100` | How well-organized the speech was |
| `relevance_score` | `INT` | `NOT NULL, CHECK 0–100` | How on-topic the content was |
| `vocabulary_score` | `INT` | `NOT NULL, CHECK 0–100` | Word variety and audience-appropriate language |

**Written to by:** Third INSERT in `persist_completed_communication_session()`.
**Read by:** `get_communication_session_result()` via `LEFT JOIN com_session_scores css`.

### Table 7: `com_session_feedback`

Written feedback text for the overall session and per-skill. One row per communication session.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `session_id` | `INT` | `PRIMARY KEY, FK → com_sessions(session_id)` | Links to com_sessions |
| `feedback` | `TEXT` | nullable | Overall feedback paragraph |
| `clarity_feedback` | `TEXT` | `NULL` | Feedback specific to clarity |
| `confidence_feedback` | `TEXT` | `NULL` | Feedback specific to confidence |
| `structure_feedback` | `TEXT` | `NULL` | Feedback specific to structure |
| `relevance_feedback` | `TEXT` | `NULL` | Feedback specific to relevance |
| `vocabulary_feedback` | `TEXT` | `NULL` | Feedback specific to vocabulary |

**Written to by:** Fourth INSERT in `persist_completed_communication_session()`. Content comes from either Cohere's structured JSON output or the deterministic Python fallback.
**Read by:** `get_communication_session_result()` via `LEFT JOIN com_session_feedback cf`.

### Entity Relationship Diagram

```
users
  │
  │ user_id (1-to-many)
  ▼
sessions ──────────────────── session_artifacts
  │    session_id (1-to-1)         session_id (1-to-1, UNIQUE)
  │                                stores: transcript_text, audio_file_path, raw_metrics_json
  │ session_id (1-to-1)
  ▼
com_sessions
  │    session_id (PK)
  │    stores: topic, audience, tone, duration
  │
  ├──────────────────── com_session_scores
  │  session_id (1-to-1)     stores: clarity, confidence, structure, relevance, vocabulary
  │
  └──────────────────── com_session_feedback
     session_id (1-to-1)     stores: overall + per-skill feedback text
```

Every completed communication session creates exactly **one row in each of these 5 tables** (`sessions`, `session_artifacts`, `com_sessions`, `com_session_scores`, `com_session_feedback`), all within a single MySQL transaction. If any INSERT fails, the entire transaction is rolled back, so the database never contains partial data for a session.

---

## 7. Authentication System

### Overview

Authentication uses Flask's built-in `session` object, which is a cryptographically signed cookie stored in the user's browser. The cookie is signed with `SECRET_KEY` from `.env`, so its contents cannot be tampered with. There is no token-based auth, no OAuth, and no third-party auth library.

### Registration Flow

**Route:** `POST /register` (handled by `register()` in `app.py` lines 269–303)

1. The form in `register.html` submits six fields via POST: `first_name`, `last_name`, `email`, `username`, `password`, `confirm_password`
2. **Client-side validation** (`static/js/register.js`): Before the form submits, JavaScript checks if `password === confirm_password`. If not, it prevents submission and shows an `alert("Passwords do not match.")`
3. **Server-side validation** (`app.py` lines 280–285):
   - All six fields must be non-empty
   - `password` must equal `confirm_password`
   - Neither `email` nor `username` can already exist in the `users` table (checked by `user_exists()` which runs `SELECT user_id FROM users WHERE email = %s OR username = %s`)
4. If validation fails, the server re-renders `register.html` with `error` set to a message like "All fields are required." or "Email or username already exists."
5. If validation passes:
   - Password is hashed: `hashed_password = generate_password_hash(password)` — Werkzeug uses scrypt by default, producing a string like `scrypt:32768:8:1$salt$hash`
   - A new row is inserted into `users`: `INSERT INTO users (first_name, last_name, email, username, account_password) VALUES (%s, %s, %s, %s, %s)`
   - The user is redirected to `/login`

### Login Flow

**Route:** `POST /login` (handled by `login()` in `app.py` lines 306–329)

1. The form in `login.html` submits `username` and `password` via POST
2. **Client-side validation** (`static/js/login.js`): Checks that the password field is not empty. If it is, prevents submission and shows `alert("Password is required.")`
3. **Server-side validation**:
   - Both fields must be non-empty
   - `get_user_by_username(username)` runs `SELECT user_id, username, account_password FROM users WHERE username = %s`
   - If no user found → error "Invalid username or password."
   - `check_password_hash(user["account_password"], password)` verifies the submitted password against the stored scrypt hash
   - If hash doesn't match → error "Invalid username or password." (same message to prevent username enumeration)
4. On success:
   - `session["user_id"] = user["user_id"]` — stores the user's database ID in the Flask session cookie
   - `session["username"] = user["username"]` — stores the username
   - Redirects to `/dashboard`

### Session Cookie Mechanics

Flask's `session` is a dictionary that gets serialized, signed with `SECRET_KEY`, and stored as a cookie in the browser. On every request, Flask reads the cookie, verifies the signature, and deserializes it back into `session`. This means the server itself is stateless — all user identity info is in the cookie.

### The `current_user()` Helper

```python
def current_user():
    if "user_id" not in session:
        return None
    return {"user_id": session["user_id"], "username": session["username"]}
```

Every protected route calls `current_user()` first. If it returns `None`, the user is not logged in:
- HTML page routes redirect to `/login`
- The `POST /complete-session` API route returns `{"success": false, "error": "Unauthorized"}` with HTTP 401

### Logout

**Route:** `POST /logout` (line 501)

`session.clear()` removes all data from the session cookie, then redirects to `/login`. The logout button in the nav bar is a `<form method="POST">` with a submit button, not a simple link, because it performs a state-changing action.

### Data Isolation Between Users

The results query (`get_communication_session_result`) always includes `AND s.user_id = %s` in its WHERE clause, using the `user_id` from the session cookie. This means User A cannot see User B's results even if User A manually enters `/results?session_id=<B's session>` in the URL — the query returns `None` and the route redirects to the dashboard.

---

## 8. Route Map — Every URL in the App

| Method | URL | Endpoint Name | Auth Required | Purpose |
|---|---|---|---|---|
| `GET` | `/` | `home` | No | Landing page with hero section and mode cards |
| `GET` | `/about` | `about` | No | How-it-works explainer page |
| `GET` | `/register` | `register` | No | Show registration form |
| `POST` | `/register` | `register` | No | Process registration, create user in DB |
| `GET` | `/login` | `login` | No | Show login form |
| `POST` | `/login` | `login` | No | Verify credentials, set session cookie |
| `GET` | `/dashboard` | `dashboard` | Yes → `/login` | Show recent sessions + session setup form |
| `GET` | `/session` | `session_start` | Yes → `/login` | Show live session page (read-only, no DB write) |
| `POST` | `/complete-session` | `complete_session` | Yes → 401 JSON | Receive audio + process + persist + return session_id |
| `GET` | `/results` | `results` | Yes → `/login` | Display saved results for a specific session_id |
| `POST` | `/logout` | `logout` | No (just clears) | Clear session cookie, redirect to login |
| `GET` | `/static/<path>` | `static` | No | Flask's built-in static file serving |

### How Routes Connect to Templates

```
GET /           → renders home.html
GET /about      → renders about.html
GET /register   → renders register.html
GET /login      → renders login.html
GET /dashboard  → renders dashboard.html   (with username, recent_sessions, score_history)
GET /session    → renders session.html      (with topic, audience, tone, duration)
GET /results    → renders results.html      (with result dict from 5-table JOIN)
```

`POST /complete-session` does NOT render a template — it returns JSON. The browser JavaScript handles the response.

---

## 9. The Complete Session Flow — End to End

### Phase 1: Setup on the Dashboard

1. User navigates to `/dashboard` (must be logged in, otherwise redirected to `/login`)
2. The `dashboard()` route calls **two** read queries:
   - `get_recent_communication_sessions(user_id, limit=5)` for the right-side recent cards
   - `get_communication_score_history(user_id, limit=20)` for the score chart points (chronological)

   Recent sessions query:
   ```sql
   SELECT s.session_id, cs.topic, s.score, s.start_time
   FROM sessions s
   JOIN com_sessions cs ON s.session_id = cs.session_id
   WHERE s.user_id = %s AND s.mode = 'Communication'
   ORDER BY s.start_time DESC
   LIMIT 5
   ```
   Score history query:
   ```sql
   SELECT s.session_id, s.score, s.start_time
   FROM sessions s
   WHERE s.user_id = %s
     AND s.mode = 'Communication'
     AND s.score IS NOT NULL
   ORDER BY s.start_time ASC
   LIMIT %s
   ```
3. The template `dashboard.html` renders three sections:
   - **Mode tabs** at the top (Communication active, Interview and Presentation disabled)
   - **Dashboard top area**: an SVG Score Over Time chart (left, 2fr) and a Recent Sessions list (right, 1fr). Each recent session is a clickable `<a>` link to `/results?session_id=<id>`
   - **Setup form** at the bottom: topic text input, three `<select>` dropdowns (audience, tone, duration), and a "Continue to Session" submit button
4. The setup form uses `method="GET"` and `action="{{ url_for('session_start') }}"`, so submitting produces a URL like: `/session?topic=Transportation&audience=General&tone=Casual&duration=1`
5. `dashboard.html` embeds `score_history` as JSON in:
   ```html
   <script id="score_history_data" type="application/json">{{ score_history|tojson }}</script>
   ```
   then loads `static/js/dashboard_chart.js`, which parses the JSON, coerces score values with `Number(item.score)`, and draws the all-time trend into `<svg id="score_chart_svg">`. If fewer than two points exist, it shows the empty-state message.

### Phase 2: The Live Session Page

5. The `GET /session` route (`session_start()` in `app.py`) validates all four query parameters server-side:
   - `topic`: must be non-empty string
   - `audience`: must be exactly `"Kids"`, `"General"`, or `"Professional"`
   - `tone`: must be exactly `"Formal"`, `"Persuasive"`, or `"Casual"`
   - `duration`: must be a string that parses to a positive integer
   - If ANY validation fails → redirect back to `/dashboard`
6. On success, `session.html` is rendered with Jinja variables `{{ topic }}`, `{{ audience }}`, `{{ tone }}`, `{{ duration }}`
7. The template displays:
   - Read-only text inputs showing the chosen settings
   - Four **hidden `<input>` elements** with `id="session_topic"`, `id="session_audience"`, `id="session_tone"`, `id="session_duration"` — these are what JavaScript reads when building the upload FormData
   - A microphone status box
   - Action buttons: Enable Microphone, Start Session (disabled), Back to Dashboard, Cancel Session (hidden)
   - An error paragraph `<p id="session_error" hidden>` for displaying errors
   - A session status card (hidden) with status text and timer display
8. **Nothing is written to the database during this phase.** The session page is purely a render of the settings passed via URL.

### Phase 3: Microphone Permission and Recording Start

All browser-side logic lives in `static/js/microphone.js`, loaded with `defer` at the bottom of `session.html`.

9. **Page initialization** (lines 260–274):
   - `setInitialTimer()` reads the duration from `#session_duration`, multiplies by 60, and displays it as `MM:SS`
   - `showPreSessionButtons()` shows: Enable Microphone, Start Session (disabled), Back to Dashboard; hides Cancel Session
   - Event listeners are attached to the three buttons

10. **User clicks "Enable Microphone"** → `requestMicPermission()` (lines 98–118):
    - Calls `navigator.mediaDevices.getUserMedia({ audio: true })`
    - On success: stores the `MediaStream` in `stream`, sets mic status to "Microphone ready.", enables the Start button, disables the Enable button
    - On failure: shows appropriate error message ("permission denied", "no microphone found", or "could not access")

11. **User clicks "Start Session"** → `beginSession()` (lines 121–178):
    - Guards: returns if `stream` is null or `sessionStarted` is already true
    - Sets `isCanceled = false`, clears `recordedChunks = []`
    - **MIME type selection** via `chooseSupportedMimeType()` (lines 26–39): tests in order `audio/webm;codecs=opus`, `audio/webm`, `audio/ogg;codecs=opus`, `audio/mp4` using `MediaRecorder.isTypeSupported()`. Returns the first supported type, or `null` if none
    - Creates `new MediaRecorder(stream, { mimeType: chosenMimeType })`. If that throws (some browsers reject certain types), falls back to `new MediaRecorder(stream)` with no explicit type
    - Attaches two event handlers:
      - `dataavailable`: pushes each `event.data` chunk into `recordedChunks[]`
      - `stop`: calls `handleRecordingComplete()`
    - Calls `mediaRecorder.start()` — recording begins
    - Sets `sessionStarted = true`, shows the status box with "Recording in progress...", switches to active-session buttons (only Cancel visible)
    - Starts a 1-second `setInterval` countdown timer

### Phase 4: Timer Expiry → Automatic Upload

12. **Each second** the interval fires (lines 161–177):
    - Decrements `secondsRemaining` by 1
    - Updates the timer display with `formatTime()`
    - **When it reaches 0:**
      - Displays "00:00"
      - Calls `stopCountdown()` (clears the interval)
      - Updates status to "Recording complete. Processing..."
      - Calls `mediaRecorder.stop()` — this triggers the `stop` event
      - Calls `stopMediaTracks()` — stops all tracks on the MediaStream and sets `stream = null`, releasing the microphone

13. **The `stop` event fires** → `handleRecordingComplete()` (lines 180–204):
    - **Cancel check**: if `isCanceled` is `true`, returns immediately without uploading (this is how cancel prevents upload — see Phase 5)
    - **Empty check**: if `recordedChunks` is empty, shows error "No audio was recorded", resets to pre-session state
    - Builds a `Blob` from all chunks: `new Blob(recordedChunks, { type: mimeForBlob })`
    - **Size check**: if blob is 0 bytes, shows error
    - Calls `showProcessingState()` — hides Cancel button, shows "Processing your session... This may take a little while."
    - Calls `uploadCompletedSession(blob, mimeForBlob)`

14. **`uploadCompletedSession()`** (lines 206–241):
    - Determines file extension from MIME (`.webm`, `.ogg`, or `.mp4`)
    - Creates a filename like `session_1713200000000.webm`
    - Builds a `FormData` object with 5 fields:
      ```
      formData.append("audio", blob, filename)       ← the audio Blob as a file
      formData.append("topic", sessionTopicInput.value)
      formData.append("audience", sessionAudienceInput.value)
      formData.append("tone", sessionToneInput.value)
      formData.append("duration", sessionDurationInput.value)
      ```
    - Sends: `fetch("/complete-session", { method: "POST", body: formData })`
    - **On success JSON** (`data.success === true`): redirects to `/results?session_id=<id>`
    - **On failure JSON** (`data.success === false`): shows `data.error` in the error paragraph, resets to pre-session state
    - **On network error** (fetch throws): shows "Network error" message

### Phase 5: Cancel Session (Alternative Path)

If the user clicks "Cancel Session" during recording:

15. `cancelSession()` (lines 244–256):
    - Sets `isCanceled = true` — this is the critical flag
    - Calls `stopCountdown()`
    - Calls `mediaRecorder.stop()` — this fires the `stop` event, which calls `handleRecordingComplete()`
    - Calls `stopMediaTracks()` — releases the mic
    - Sets `sessionStarted = false`, clears `recordedChunks`
    - Redirects to `/dashboard`

16. When `handleRecordingComplete()` fires (from the `stop` event), it sees `isCanceled === true` on line 181 and **returns immediately** without building a Blob or uploading. No data is sent to the server. No database rows are created.

### Phase 6: Server-Side Processing

The `POST /complete-session` route in `app.py` (lines 379–481) runs synchronously — the user waits for the entire pipeline to complete.

#### Step 6a — Authentication check (line 381–383)
```python
user = current_user()
if user is None:
    return jsonify({"success": False, "error": "Unauthorized"}), 401
```

#### Step 6b — Server-side validation (lines 385–403)
Re-validates every field even though the browser validated them too:
- `topic`: must be non-empty and ≤150 characters
- `audience`: must be in `{"Kids", "General", "Professional"}`
- `tone`: must be in `{"Formal", "Persuasive", "Casual"}`
- `duration`: must parse to a positive integer
- `audio`: must be present in `request.files` with a non-empty filename

Each validation failure returns a specific 400 JSON error.

#### Step 6c — Save audio file to disk (lines 407–422)
1. Reads the MIME type from `audio.content_type`
2. Maps it to a file extension via `extension_for_mime()` (e.g., `audio/webm` → `.webm`)
3. Generates a unique filename: `{user_id}_{uuid4_hex}.webm` (e.g., `1_a3f8c921b4e04d..webm`)
4. Sanitizes with `secure_filename()` and saves to `uploads/audio/`
5. Checks that the saved file is non-zero bytes; if empty, deletes it and returns a 400 error

#### Step 6d — Transcription via AssemblyAI (lines 424–440)
Calls `transcribe_audio_file(file_path, api_key)` from `services/transcription_service.py`. This function:
1. Uploads the audio bytes to `POST https://api.assemblyai.com/v2/upload` → receives an `upload_url`
2. Submits a transcription job to `POST /v2/transcript` with `{ audio_url, speech_models: ["universal-3-pro", "universal-2"], language_detection: true }` → receives a `transcript_id`
3. Polls `GET /v2/transcript/{id}` every 3 seconds for up to 300 seconds until `status == "completed"`
4. Normalizes the response into: `{ text, confidence, words: [{ text, start, end, confidence }], status, raw_response }`

If transcription fails → logged with `logging.exception()` → returns 502 JSON error.
If transcript text is empty or under 5 characters → returns 422 "No speech was detected."

#### Step 6e — Scoring (lines 442–452)
Calls `score_communication_session(topic, audience, tone, duration, transcript_payload)` from `services/scoring_service.py`. Detailed in Section 11.

Returns:
```python
{
    "overall_score": 83,
    "clarity": 81,
    "confidence": 78,
    "structure": 85,
    "relevance": 86,
    "vocabulary": 79,
    "transcript_text": "...",
    "raw_metrics": { ... },
    "low_sample_flags": [],
}
```

#### Step 6f — Feedback generation via Cohere (lines 454–458)
Calls `generate_feedback_json(topic, audience, tone, duration, transcript_text, scores, raw_metrics, low_sample_flags)` from `services/cohere_service.py`. Detailed in Section 12.

Returns a dict with keys: `overall_feedback`, `clarity_feedback`, `confidence_feedback`, `structure_feedback`, `relevance_feedback`, `vocabulary_feedback`, `strengths`, `improvements`.

If Cohere fails for any reason, falls back to deterministic Python feedback.

#### Step 6g — Database persistence (lines 460–481)
Calls `persist_completed_communication_session()` which opens a database connection and runs 5 INSERTs in one transaction:

1. `INSERT INTO sessions (user_id, mode, score)` → captures `session_id = cursor.lastrowid`
2. `INSERT INTO com_sessions (session_id, topic, audience, tone, duration)`
3. `INSERT INTO com_session_scores (session_id, clarity_score, confidence_score, structure_score, relevance_score, vocabulary_score)`
4. `INSERT INTO com_session_feedback (session_id, feedback, clarity_feedback, confidence_feedback, structure_feedback, relevance_feedback, vocabulary_feedback)`
5. `INSERT INTO session_artifacts (session_id, transcript_text, audio_file_path, raw_metrics_json)`

Then `conn.commit()`. If any insert fails → `conn.rollback()` → 500 JSON error, no partial data.

#### Step 6h — Response (line 481)
```python
return jsonify({"success": True, "session_id": session_id})
```

### Phase 7: Results Page

17. JavaScript receives the JSON, sees `data.success === true`, and redirects: `window.location.href = "/results?session_id=" + data.session_id`

18. The `GET /results` route (lines 484–498):
    - Validates `session_id` is a digit string
    - Calls `get_communication_session_result(int(session_id), user["user_id"])` which runs a 5-table JOIN query (lines 129–147):
      ```sql
      SELECT s.*, cs.*, css.*, cf.*, sa.transcript_text, sa.audio_file_path
      FROM sessions s
      JOIN com_sessions cs ON s.session_id = cs.session_id
      LEFT JOIN com_session_scores css ON cs.session_id = css.session_id
      LEFT JOIN com_session_feedback cf ON cs.session_id = cf.session_id
      LEFT JOIN session_artifacts sa ON s.session_id = sa.session_id
      WHERE s.session_id = %s AND s.user_id = %s AND s.mode = 'Communication'
      ```
    - If no result (wrong session_id or wrong user) → redirect to dashboard
    - Otherwise renders `results.html` with the full `result` dict

19. `results.html` displays:
    - Session topic as heading, date and mode as subtext
    - **Session details grid**: audience, tone, duration (3 items in a flex row)
    - **Overall score** in a large circle
    - **Overall feedback** paragraph
    - **Score breakdown** card: 5 metric rows (Clarity, Confidence, Structure, Relevance, Vocabulary)
    - **Skill Feedback** section (only shown if any per-skill feedback exists): up to 5 blocks each with a heading and paragraph
    - **Transcript** section: full transcript text in a scrollable box (max-height 300px)
    - **Navigation actions**: "Back to Dashboard" and "Start New Session" (both link to `/dashboard`)

---

## 10. File-by-File Code Walkthrough

### `app.py` — The Flask Application (544 lines)

This is the central file. It contains the Flask app, all routes, database functions, and the orchestration logic.

**Lines 1–19 — Imports:**
- Flask components: `Flask`, `render_template`, `request`, `redirect`, `url_for`, `session`, `jsonify`
- Werkzeug: `generate_password_hash`, `check_password_hash`, `secure_filename`
- Standard library: `os`, `json`, `uuid`, `logging`, `traceback`, `pathlib.Path`
- Internal services: `transcribe_audio_file`, `score_communication_session`, `generate_feedback_json`
- `load_dotenv()` is called to load `.env`

**Lines 22–30 — App setup:**
- `BASE_DIR`: resolved path to the project root
- `UPLOAD_DIR`: `uploads/audio/` — auto-created with `mkdir(parents=True, exist_ok=True)`
- `app.secret_key` from `SECRET_KEY` env var
- `MAX_CONTENT_LENGTH = 50 * 1024 * 1024` (50 MB) — Flask rejects uploads larger than this

**Lines 35–42 — `get_db_connection()`:**
Opens a new MySQL connection using credentials from environment variables. Every database function opens its own connection, uses it, and closes it. There is no connection pool.

**Lines 47–77 — Auth helpers:**
- `user_exists(email, username)` — checks for duplicate email or username during registration
- `get_user_by_username(username)` — fetches user row for login verification
- `current_user()` — returns `{user_id, username}` dict or `None`

**Lines 81–91 — `extension_for_mime()`:**
Maps MIME type strings to file extensions. Falls back to `.webm` for unknown types.

**Lines 96–123 — `get_recent_communication_sessions()`:**
Dashboard query. JOINs `sessions` and `com_sessions`, filters by user and mode, orders by `start_time DESC`, returns up to 5 items.

**Lines 126–183 — `get_communication_session_result()`:**
Results page query. JOINs all 5 tables with LEFT JOINs (scores/feedback/artifacts might not exist for edge cases). Returns a dict with every field the results template needs. The `AND s.user_id = %s` clause enforces data isolation.

**Lines 188–254 — `persist_completed_communication_session()`:**
Transactional write. Opens connection, runs 5 INSERTs in order, commits. On failure, rolls back and re-raises. Always closes cursor and connection in `finally`.

**Lines 259–266 — Public routes:**
`GET /` → `home.html`, `GET /about` → `about.html`. No auth required.

**Lines 269–329 — Auth routes:**
`GET/POST /register` and `GET/POST /login`. Both validate server-side, display errors via template re-render, and redirect on success.

**Lines 332–376 — Dashboard and Session routes:**
`GET /dashboard` queries recent sessions and renders the setup form. `GET /session` validates query params and renders the live session page. Neither writes to the database.

**Lines 379–481 — `POST /complete-session`:**
The core pipeline. See Phase 6 in Section 9 above for the complete walkthrough.

**Lines 484–504 — Results and Logout:**
`GET /results` loads from DB and renders. `POST /logout` clears the session.

### `services/__init__.py` (0 lines)

Empty file. Its sole purpose is to make `services/` a Python package so that `from services.text_analysis import ...` works.

### `services/text_analysis.py` (325 lines)

Contains all deterministic text-analysis helpers used by the scoring engine. No API calls, no external NLP libraries — only Python `re` and `math`.

**Constants (lines 11–68):**
- `STOPWORDS`: set of ~90 common English function words (articles, prepositions, pronouns, etc.)
- `FILLER_WORDS_SINGLE`: `{"um", "uh", "ah", "er", "hmm", "hm", "like"}`
- `FILLER_PHRASES_MULTI`: multi-word fillers like `"you know"`, `"sort of"`, `"kind of"`, `"i mean"`, `"basically"`, `"actually"`, `"literally"`, `"right"`, `"okay so"`
- `TRANSITION_PHRASES`: `["first", "next", "then", "for example", "because", "however", "finally", "overall"]`
- `TONE_CUE_MATCHES`: per-tone dict of phrases that indicate alignment (e.g., Formal: "therefore", "however", "moreover"; Persuasive: "should", "must", "important"; Casual: "gonna", "wanna", "cool")
- `TONE_CUE_CONFLICTS`: per-tone dict of phrases that indicate misalignment (e.g., Formal conflicts: "gonna", "wanna", contractions; Casual conflicts: "moreover", "furthermore")

**`clamp(x)`**: Constrains a float to [0, 100]. Used by every scoring formula.

**`tokenize_words(text)`**: Uses `re.findall(r"[a-z']+", text.lower())` to extract lowercase word tokens. Apostrophes are kept so contractions like `don't` stay as one token.

**`content_words(tokens)`**: Filters out stopwords and single-character tokens. These are the "meaningful" words used for vocabulary metrics.

**`count_filler_words(text)`**: Two-pass counting. First counts multi-word phrases (via regex `\b...\b`), then counts single filler words from the tokenized text. This avoids double-counting — e.g., "you know" is counted as one filler phrase, and the individual words aren't counted again as singles because "you" and "know" aren't in `FILLER_WORDS_SINGLE`.

**`split_sentences(text, words)`**: Two strategies:
1. **Primary**: split on punctuation `.!?` with regex `(?<=[.!?])\s+`. If this produces ≥3 parts, use them.
2. **Fallback**: if word-level timestamps are available, split at pause gaps > 1.2 seconds between consecutive words. Each segment becomes a "sentence."
3. If neither produces good results, returns the original text as a single-element list (never an empty list).

**`sentence_lengths(sentences)`**: Returns a list of word counts per sentence.

**`stddev(values)`**: Population standard deviation using `math.sqrt`. Returns 0 if fewer than 2 values.

**`extract_topic_keywords(topic)`**: Heuristic keyword extraction:
1. Lowercase and tokenize the topic string
2. Remove stopwords and tokens under 3 characters
3. Generate bigrams from adjacent informative tokens
4. Combine bigrams + unigrams, deduplicate, sort longest first (bigrams preferred)
5. Return 5–10 keywords

**`keyword_coverage(topic_keywords, transcript_text)`**: For each keyword, checks if it appears in the transcript. Uses exact match first, then tries simple morphological variants (`_simple_variants()`: plural/singular, -ing removal, -ed removal, -tion→-te). Returns `(covered_count, total_count)`.

**`tone_alignment_score_parts(transcript_text, tone)`**: Counts how many `TONE_CUE_MATCHES` phrases appear (matches) and how many `TONE_CUE_CONFLICTS` phrases appear (conflicts) for the given tone. Returns `(matches, conflicts)`.

**`estimate_syllables(word)`**: Counts vowel groups (`aeiouy`) in the word, subtracts 1 for silent trailing 'e', returns at least 1. This is a rough approximation but works well enough for Flesch-Kincaid.

**`flesch_kincaid_grade(text)`**: Implements the Flesch-Kincaid Grade Level formula: `0.39 × (words/sentences) + 11.8 × (syllables/words) - 15.59`. Returns `None` if the text has fewer than 10 words (too unreliable).

**`cosine_similarity(vec_a, vec_b)`**: Pure Python dot product divided by the product of magnitudes, using `math.sqrt`. No numpy dependency. Used by `cohere_service.py` to compare embedding vectors.

### `services/transcription_service.py` (102 lines)

Handles all communication with AssemblyAI's REST API using the `requests` library. No AssemblyAI SDK is used — all calls are explicit HTTP requests.

**`upload_audio_to_assemblyai(file_path, api_key)`** (lines 12–24):
- Opens the local file in binary mode
- Sends `POST https://api.assemblyai.com/v2/upload` with `authorization: <api_key>` header and the file bytes as the request body
- Returns the `upload_url` from the JSON response (a CDN URL that AssemblyAI can read from)

**`submit_transcription_job(upload_url, api_key)`** (lines 27–45):
- Sends `POST /v2/transcript` with JSON payload:
  ```json
  {
      "audio_url": "<CDN url>",
      "speech_models": ["universal-3-pro", "universal-2"],
      "language_detection": true
  }
  ```
- `speech_models` is **required** by AssemblyAI's current API. `universal-3-pro` is the primary model; `universal-2` is fallback.
- `language_detection: true` lets AssemblyAI auto-detect the spoken language rather than assuming English.
- Returns the `transcript_id`

**`poll_transcription_result(transcript_id, api_key)`** (lines 48–73):
- Polls `GET /v2/transcript/{id}` every 3 seconds
- If `status == "completed"` → returns the full JSON response
- If `status == "error"` → raises `RuntimeError` with the error message
- If 300 seconds pass without completion → raises `TimeoutError`

**`transcribe_audio_file(file_path, api_key)`** (lines 77–101):
- End-to-end orchestrator: upload → submit → poll → normalize
- Normalizes the raw AssemblyAI response into a consistent dict:
  ```python
  {
      "text": "full transcript string",
      "confidence": 0.93,  # overall confidence 0.0–1.0
      "words": [
          {"text": "hello", "start": 120, "end": 380, "confidence": 0.99},
          ...
      ],
      "status": "completed",
      "raw_response": { ... }  # full AssemblyAI response for debugging
  }
  ```
- Word timestamps are in milliseconds. `start` is when the word begins, `end` is when it ends.

### `services/cohere_service.py` (210 lines)

Uses the Cohere V2 Python SDK for two distinct purposes: semantic embeddings and structured feedback generation.

**`get_cohere_client()`**: Creates a `cohere.ClientV2` using the `COHERE_API_KEY` from environment variables.

**`embed_topic_and_transcript(topic, transcript)`** (lines 17–44):
- Embeds the topic string with `input_type="search_query"` and the transcript (first 2048 chars) with `input_type="search_document"` using `embed-v4.0` model
- Both use `embedding_types=["float"]` and `output_dimension=1024`
- The Cohere V2 API uses a structured input format: `inputs=[{"content": [{"type": "text", "text": ...}]}]`
- Extracts the float vectors from `response.embeddings.float_[0]`
- Computes cosine similarity using the pure-Python function from `text_analysis.py`
- Returns a float in [0.0, 1.0]

**`generate_feedback_json(...)`** (lines 69–89):
- Wraps `_call_cohere_feedback()` in a try/except
- If Cohere fails for **any** reason (network, rate limit, parsing, validation), catches the exception and calls `_deterministic_fallback()` instead
- This means the session **always completes** even if Cohere is down

**`_call_cohere_feedback(...)`** (lines 92–153):
- Builds a detailed prompt that includes: topic, audience, tone, duration, first 1500 chars of transcript, all numeric scores, key metrics (WPM, fillers, transitions, lexical diversity), and any low-sample-size flags
- Uses `response_format` with a JSON schema to enforce the exact output structure:
  ```json
  {
      "overall_feedback": "string",
      "clarity_feedback": "string",
      "confidence_feedback": "string",
      "structure_feedback": "string",
      "relevance_feedback": "string",
      "vocabulary_feedback": "string",
      "strengths": ["string"],
      "improvements": ["string"]
  }
  ```
- Parses the response text as JSON and validates all required keys are present

**`_deterministic_fallback(scores, topic, audience, tone)`** (lines 166–209):
- Generates feedback without any API call, based purely on the numeric scores
- For each skill: score ≥ 85 → "strong, keep refining"; score ≥ 65 → "solid, room for improvement"; below → "needs work"
- Builds strengths list from skills scoring ≥ 75 and improvements list from skills below 75

### `services/scoring_service.py` (375 lines)

The heart of the scoring system. All numeric scores are computed here — the LLM never decides a number.

See Section 11 for the complete formula-by-formula breakdown.

### `schema.sql` (89 lines)

Creates the `articulax` database and all 7 tables. Used for fresh installations. Includes all CHECK constraints, FOREIGN KEYs, and DEFAULT values.

### `migrations/final_phase.sql` (11 lines)

An ALTER TABLE migration for databases that already exist from an earlier version:
- Adds `raw_metrics_json LONGTEXT NULL` to `session_artifacts`
- Adds five `TEXT NULL` feedback columns to `com_session_feedback`

### `requirements.txt` (6 lines)

```
Flask
Werkzeug
python-dotenv
mysql-connector-python
requests
cohere
```

No version pins — installs latest compatible versions. `requests` is used by `transcription_service.py` for AssemblyAI REST calls. `cohere` is the V2 SDK used by `cohere_service.py`.

### `templates/base.html` (37 lines)

The shared layout template. All other templates extend it with `{% extends 'base.html' %}`.

**Structure:**
- `<head>`: charset, viewport, title block (`{% block title %}`), CSS link, head block
- `<header>`: sticky top nav bar with brand link "Articulax", nav links (Home, About)
  - **Logged in**: shows Dashboard link and Logout button (as a `<form method="POST">`)
  - **Not logged in**: shows Login link and Register button
  - Uses `{% if session.get('user_id') %}` to decide which nav items to show
- `<main>`: `{% block body %}{% endblock %}` — content area

### `templates/home.html` (39 lines)

The public landing page. Extends `base.html`.

- Hero section: heading "Practice speaking with structure, feedback, and progress tracking."
- If logged in: "Go to Dashboard" button. If not: "Get Started" (register) and "Login" buttons.
- Info grid: three cards for Communication (active), Interview (disabled, 65% opacity), Presentation (disabled)

### `templates/about.html` (32 lines)

Public how-it-works page. Three steps: Choose a mode → Start a session → Review feedback.

### `templates/register.html` (30 lines)

Registration form with 6 inputs: first name, last name, email, username, password, confirm password. All are `required`. Server-side errors displayed via `{% if error %}<p class="error-text">{{ error }}</p>{% endif %}`. Loads `register.js` for client-side password matching.

### `templates/login.html` (25 lines)

Login form with 2 inputs: username and password. Loads `login.js` for client-side empty-password check.

### `templates/dashboard.html` (123 lines)

Three sections:
1. **Mode tabs**: Communication (active), Interview (disabled), Presentation (disabled)
2. **Dashboard top** (grid: 2fr chart + 1fr recent):
   - Score trend chart rendered via SVG
   - Embedded `score_history` JSON script payload
   - "All Time" only label (filter tabs removed by design choice)
   - Recent sessions list: iterates `{% for item in recent_sessions %}`, each item is an `<a>` link to `/results?session_id=<id>` showing topic, date, score
3. **Setup form**: `<form method="GET" action="{{ url_for('session_start') }}">` with topic text input, 3 dropdowns (audience, tone, duration), submit button

### `static/js/dashboard_chart.js` (105 lines)

Dedicated dashboard chart renderer:

- Reads and parses JSON from `#score_history_data`
- Normalizes score values using `Number(item.score)` before filtering finite values
- Draws a simple, dependency-free SVG chart:
  - horizontal grid lines at 0/25/50/75/100
  - trend polyline
  - point circles with tooltip titles (`date: score`)
- Shows `#score_chart_empty` when fewer than 2 data points are available
- Uses neutral charcoal palette colors to match the updated visual design

### `templates/session.html` (66 lines)

The live recording page. Shows selected settings as read-only, 4 hidden inputs for JS, mic status box, action buttons, error paragraph, and session status card with timer.

### `templates/results.html` (122 lines)

Displays: topic heading, date, session details grid (audience/tone/duration), overall score circle, overall feedback, score breakdown (5 metric rows), per-skill feedback section (conditionally rendered if feedback text exists), full transcript in a scrollable box, and two action buttons.

### `static/js/microphone.js` (275 lines)

See Phase 3–5 in Section 9 for the complete logic walkthrough.

### `static/js/register.js` (16 lines)

Attaches a `submit` event listener to the registration form. If password !== confirm_password, prevents submission and shows an `alert()`. This is a client-side convenience check — the server validates independently.

### `static/js/login.js` (12 lines)

Attaches a `submit` event listener to the login form. If the password field is empty, prevents submission and shows an `alert()`.

### `static/css/styles.css` (798 lines)

See Section 15 for the CSS architecture breakdown.

---

## 11. Scoring Engine — Every Formula Explained

All scoring lives in `services/scoring_service.py`. The orchestrator is `score_communication_session()` which calls `build_base_metrics()` once, then passes the metrics dict to five scoring functions.

### Step 1: Build Base Metrics

`build_base_metrics(topic, audience, tone, transcript_payload)` computes every metric that the five rubric functions need. This avoids redundant computation.

**Speaking duration:**
```python
speaking_ms = words[-1]["end"] - words[0]["start"]
speaking_seconds = speaking_ms / 1000.0
speaking_minutes = speaking_seconds / 60.0   # or 0.001 if zero to avoid division errors
```

**Average word confidence:**
```python
avg_word_confidence = mean of all word.confidence values
# Fallback: if no word data, use transcript-level confidence
# Fallback: if no confidence at all, use 0.85
```

**Pause gaps:**
For every pair of consecutive words i and i+1:
```python
gap_seconds = (words[i+1]["start"] - words[i]["end"]) / 1000.0
```
These gaps are then classified:
- **Clarity long pauses**: gap > 1.2 seconds
- **Hesitation pauses**: 0.8 ≤ gap ≤ 1.5 seconds
- **Confidence long pauses**: gap > 1.5 seconds

**Words per minute (WPM):**
```python
wpm = total_words / speaking_minutes
```

**Filler word count**: calls `count_filler_words(text)` from `text_analysis.py`

**Continuous speech segments**: Words are grouped into segments separated by gaps > 0.8 seconds. For each segment, the duration in seconds is `(last_word.end - first_word.start) / 1000`. The average segment length indicates fluency.

**Sentence-related metrics**: Calls `split_sentences()`, `sentence_lengths()`, `stddev()`.

**Transition phrases**: Regex counts of each phrase in the `TRANSITION_PHRASES` list.

**Topic keywords and coverage**: Calls `extract_topic_keywords()` and `keyword_coverage()`.

**Tone alignment**: Calls `tone_alignment_score_parts()`.

**Readability**: Calls `flesch_kincaid_grade()`.

**Vocabulary metrics**:
```python
c_words = content_words(tokens)        # tokens minus stopwords
unique_content = set(c_words)
lexical_diversity = len(unique_content) / len(c_words)
repeated = count of content words appearing > 2 times
```

### Step 2: The Five Scoring Functions

Every subscore uses `clamp()` to constrain values to [0, 100].

#### Clarity (weight: 30% of overall)

Variables:
- `A` = average word confidence (0.0–1.0)
- `WPM` = words per minute
- `LPM` = clarity long pauses per minute of speaking
- `ALPD` = average clarity long pause duration in seconds

Subscores:
```
Intelligibility = 100 × A
  → Perfect confidence (1.0) = 100. If ASR struggled (0.7) = 70.

Pace = clamp(100 - 2 × |WPM - 140|)
  → Ideal pace is 140 WPM. Every 1 WPM deviation costs 2 points.
  → At 90 WPM: 100 - 2×50 = 0. At 160 WPM: 100 - 2×20 = 60.

LongPauseControl = clamp(100 × (1 - LPM / 6))
  → 0 long pauses per min = 100. 6+ per min = 0.

PauseDurationControl = clamp(100 × (1 - max(ALPD - 1.2, 0) / 2.0))
  → If avg pause duration is ≤1.2s, score is 100. At 3.2s: 100×(1-1.0) = 0.
```

Final formula:
```
Clarity = 0.40×Intelligibility + 0.30×Pace + 0.20×LongPauseControl + 0.10×PauseDurationControl
```

#### Confidence (weight: 20% of overall)

Variables:
- `F100` = filler words as percentage of total words (`fillers × 100 / words`)
- `HPM` = hesitation pauses (0.8–1.5s) per minute
- `LPM` = long pauses (>1.5s) per minute
- `ASL` = average continuous speech segment length in seconds

Subscores:
```
FillerScore = clamp(100 × (1 - F100 / 8))
  → 0% fillers = 100. 8%+ fillers = 0.

HesitationScore = clamp(100 × (1 - HPM / 12))
  → 0 hesitations/min = 100. 12+ per min = 0.

LongPauseScore = clamp(100 × (1 - LPM / 6))
  → 0 long pauses/min = 100. 6+ per min = 0.

ContinuityScore = clamp(100 × (ASL / 12))
  → 12+ second avg segments = 100. 0 seconds = 0.
```

Final formula:
```
Confidence = 0.45×FillerScore + 0.25×HesitationScore + 0.20×LongPauseScore + 0.10×ContinuityScore
```

#### Structure (weight: 20% of overall)

Variables:
- `TP100` = transition phrases as percentage of total words
- `S` = total sentence count
- `AS` = average sentence length in words
- `SLSD` = standard deviation of sentence lengths

Subscores:
```
TransitionScore = clamp(100 × (TP100 / 3))
  → 3% of words are transitions = 100. 0% = 0.

SentenceCountScore = clamp(100 × (S / 6))
  → 6+ sentences = 100. 0 = 0.

SentenceLengthBalance = clamp(100 - 4 × |AS - 18|)
  → Ideal average sentence is 18 words. Every word off costs 4 points.

SentenceConsistency = clamp(100 - 2 × SLSD)
  → Low variation = high score. Stddev of 50 = 0.
```

Final formula:
```
Structure = 0.50×TransitionScore + 0.20×SentenceCountScore + 0.20×SentenceLengthBalance + 0.10×SentenceConsistency
```

#### Relevance (weight: 20% of overall)

Variables:
- `SIM` = Cohere embedding cosine similarity (0.0–1.0)
- `KC` = keyword coverage ratio (covered / total)
- `TA` = tone alignment ratio (matches / (matches + conflicts))

Subscores:
```
PromptSimilarity = 100 × SIM
  → Semantic similarity between topic and transcript via Cohere embed-v4.0

KeywordCoverage = 100 × KC
  → Fraction of extracted topic keywords found in transcript

ToneAlignment = 100 × TA
  → Ratio of tone-matching phrases to total tone-relevant phrases
```

Final formula:
```
Relevance = 0.55×PromptSimilarity + 0.35×KeywordCoverage + 0.10×ToneAlignment
```

**Fallbacks:**
- If keyword list is empty → `KeywordCoverage = PromptSimilarity`
- If Cohere embeddings fail → `PromptSimilarity = KeywordCoverage` (100 × the ratio)
- If tone is not one of the three supported → `ToneAlignment = 100`

#### Vocabulary (weight: 10% of overall)

Variables:
- `LD` = lexical diversity (unique content words / total content words)
- `REP100` = repeated non-stopwords as percentage of total words
- `GRADE` = Flesch-Kincaid grade level
- `Dist` = distance from grade to audience target range

Audience target grade ranges:
- Kids: grades 3–6
- General: grades 7–10
- Professional: grades 10–14

```python
if grade < low:     dist = low - grade
elif grade > high:  dist = grade - high
else:               dist = 0
```

Subscores:
```
LexicalDiversity = clamp(100 × (LD / 0.60))
  → Diversity of 0.60+ = 100. 0 = 0.

RepetitionControl = clamp(100 × (1 - REP100 / 20))
  → 0% repetition = 100. 20%+ = 0.

AudienceFit = clamp(100 - 20 × Dist)
  → Grade within range = 100. 5 grades off = 0.
```

Final formula:
```
Vocabulary = 0.40×LexicalDiversity + 0.25×RepetitionControl + 0.35×AudienceFit
```

### Step 3: Overall Score

```
Overall = Clarity×0.30 + Confidence×0.20 + Structure×0.20 + Relevance×0.20 + Vocabulary×0.10
```

All scores are `round()`ed to integers for display and database storage. Raw float values are preserved in `raw_metrics_json`.

### Low Sample Flags

If `total_words < 20` → flag `"very_short_transcript"`.
If `speaking_seconds < 15` → flag `"very_short_duration"`.
These flags are included in `raw_metrics_json` and communicated to Cohere's feedback prompt so it can acknowledge the limited data.

---

## 12. External API Integrations

### AssemblyAI (Transcription)

**Used in:** `services/transcription_service.py`
**Auth:** API key passed as `authorization` header
**Protocol:** Direct REST calls via `requests`, no SDK

| Step | HTTP Call | Purpose |
|---|---|---|
| 1 | `POST /v2/upload` | Upload audio bytes, get CDN URL |
| 2 | `POST /v2/transcript` | Submit job with `speech_models` and `language_detection` |
| 3 | `GET /v2/transcript/{id}` | Poll every 3s until `status == "completed"` |

**What we get back:** Full transcript text, per-word timestamps (`start`/`end` in ms), per-word confidence (0.0–1.0), overall confidence.

**Why word timestamps matter:** They are used to compute pause gaps, speaking duration, WPM, hesitation pauses, long pauses, and continuous speech segments. Without them, the scoring engine would only have text, and most of the rubric couldn't function.

### Cohere (Embeddings + Feedback)

**Used in:** `services/cohere_service.py`
**Auth:** API key via `cohere.ClientV2(api_key=...)`
**Protocol:** Cohere V2 Python SDK

#### Embedding Call (for relevance scoring)

| Parameter | Value |
|---|---|
| Model | `embed-v4.0` |
| Topic input_type | `search_query` |
| Transcript input_type | `search_document` |
| Output dimension | 1024 |
| Embedding types | `["float"]` |

Two separate embed calls (one for topic, one for transcript first 2048 chars). The resulting 1024-float vectors are compared with cosine similarity.

#### Feedback Chat Call

| Parameter | Value |
|---|---|
| Model | `command-a-03-2025` |
| Response format | `json_object` with enforced JSON schema |
| Schema | 8 required fields (overall + 5 skills + strengths + improvements) |

The prompt provides all the context the LLM needs: topic, audience, tone, duration, transcript excerpt, all numeric scores, key metrics, and any low-sample flags.

---

## 13. Error Handling and Resilience

### Processing pipeline failures

| Failure Point | HTTP Status | User-Facing Message | Backend Action |
|---|---|---|---|
| Audio save fails | 500 | "Failed to save audio file." | `logging.exception()`, no DB write |
| Audio file is 0 bytes | 400 | "Audio file is empty." | File deleted from disk |
| AssemblyAI transcription fails | 502 | "We could not process your recording. Please try again." | `logging.exception()`, audio kept on disk for debugging |
| Transcript empty/too short (<5 chars) | 422 | "No speech was detected clearly enough to score this session." | No DB write |
| Scoring fails | 500 | "Scoring failed. Please try again." | `logging.exception()` |
| Cohere embeddings fail | — | (no error shown) | Falls back to keyword coverage ratio for relevance. Session continues. |
| Cohere feedback fails | — | (no error shown) | Falls back to deterministic Python feedback. Session continues. |
| DB insert fails | 500 | "Failed to save session results." | `conn.rollback()`, `logging.exception()` |

### Key resilience design decisions

1. **Cohere is never a hard dependency.** Both embedding and feedback calls are wrapped in try/except with fallbacks. A session will always complete even if Cohere is entirely down.
2. **The DB transaction is all-or-nothing.** Five INSERTs happen in one transaction. If any fails, `conn.rollback()` ensures zero partial rows exist.
3. **All exceptions are logged.** Every `except Exception` block in `complete_session()` calls `logging.exception()` so the full traceback appears in the Flask console for debugging.
4. **Client-side errors are visible.** If the server returns `success: false`, JavaScript displays the `error` message in the `#session_error` paragraph on the session page and resets the UI to pre-session state so the user can try again.

---

## 14. Data Flow Diagrams

### Complete Session Data Flow

```
[Browser: dashboard.html]
     │
     │  User fills form, clicks "Continue to Session"
     │  GET /session?topic=...&audience=...&tone=...&duration=...
     ▼
[Flask: session_start()]
     │
     │  Validates params, renders session.html
     ▼
[Browser: session.html + microphone.js]
     │
     │  1. Enable Microphone → getUserMedia()
     │  2. Start Session → MediaRecorder.start()
     │  3. Timer counts down → chunks accumulate
     │  4. Timer hits 0 → MediaRecorder.stop()
     │  5. Build Blob → FormData → fetch POST /complete-session
     ▼
[Flask: complete_session()]
     │
     ├─→ Save audio to uploads/audio/
     │
     ├─→ [AssemblyAI API]
     │      POST /v2/upload    → upload_url
     │      POST /v2/transcript → transcript_id
     │      GET  /v2/transcript/{id} (poll) → { text, words, confidence }
     │
     ├─→ [scoring_service.py]
     │      build_base_metrics() → metrics dict
     │      score_clarity(m) → int
     │      score_confidence(m) → int
     │      score_structure(m) → int
     │      score_relevance(m, similarity) → int   ← uses Cohere similarity
     │      score_vocabulary(m) → int
     │      overall = weighted sum → int
     │
     ├─→ [Cohere API]
     │      embed() × 2 → cosine similarity for relevance
     │      chat() → structured JSON feedback
     │      (fallback: deterministic Python feedback)
     │
     ├─→ [MySQL: single transaction]
     │      INSERT sessions
     │      INSERT com_sessions
     │      INSERT com_session_scores
     │      INSERT com_session_feedback
     │      INSERT session_artifacts
     │      COMMIT
     │
     └─→ Return JSON { success: true, session_id: 123 }
            │
            ▼
[Browser: microphone.js]
     │
     │  window.location.href = "/results?session_id=123"
     ▼
[Flask: results()]
     │
     │  5-table JOIN query → result dict
     │  Render results.html
     ▼
[Browser: results.html]
     Displays scores, feedback, transcript
```

### Database Write Order

```
persist_completed_communication_session():
     │
     ├─1─→ INSERT INTO sessions (user_id, mode, score)
     │      → session_id = cursor.lastrowid
     │
     ├─2─→ INSERT INTO com_sessions (session_id, topic, audience, tone, duration)
     │
     ├─3─→ INSERT INTO com_session_scores (session_id, 5 scores)
     │
     ├─4─→ INSERT INTO com_session_feedback (session_id, 6 text fields)
     │
     ├─5─→ INSERT INTO session_artifacts (session_id, transcript, path, json)
     │
     └───→ COMMIT (or ROLLBACK on any error)
```

### Database Read Patterns

```
Dashboard:
  get_recent_communication_sessions():
    sessions JOIN com_sessions
    WHERE user_id = ? AND mode = 'Communication'
    ORDER BY start_time DESC LIMIT 5

Results:
  get_communication_session_result():
    sessions
    JOIN com_sessions
    LEFT JOIN com_session_scores
    LEFT JOIN com_session_feedback
    LEFT JOIN session_artifacts
    WHERE session_id = ? AND user_id = ?
```

---

## 15. CSS Architecture

All styles live in a single file: `static/css/styles.css` (798 lines). There is no preprocessor (Sass/Less), no CSS framework (Bootstrap/Tailwind), and no CSS-in-JS.

### Design system

- **Font**: system UI stack (`-apple-system`, BlinkMacSystemFont, `"Segoe UI"`, Helvetica, Arial, sans-serif)
- **Page background**: `#f5f5f7` (very light gray)
- **Card background**: `#ffffff`
- **Primary text**: `#1f1f1f`
- **Heading/primary accent**: `#1f2329` (charcoal)
- **Secondary text**: `#666a73` / `#4b5059`
- **Border**: `#d9dde3` / `#e0e3e8`
- **Primary button**: `#1f2329` (hover: `#111418`)
- **Muted button**: `#eceff3` with text `#2b3138`
- **Error tone**: `#a3392b` (muted red)
- **Border radius**: mostly 10–14px
- **Cards**: white background, soft border, subtle `0 2px 8px rgba(0,0,0,0.04)` shadow
- **Theme direction**: light UI with dark accents (not dark mode)

### Style sections

| Lines | Section | Purpose |
|---|---|---|
| 1–15 | Reset/Base | Global reset, system font stack, light background, base text rendering |
| 17–77 | Layout + Header/Nav | Sticky header, compact nav spacing, refined link states |
| 79–114 | Page structure + Card baseline | Section spacing, heading hierarchy, softened cards |
| 116–170 | Buttons | Unified charcoal primary + muted secondary system |
| 171–210 | Home/About card grid | Shared informational cards and disabled states |
| 211–270 | Auth + input controls | Refined spacing, focus rings, read-only field styling |
| 271–325 | Dashboard tabs and headers | Mode tabs, card headers, typography balance |
| 326–390 | Chart visuals | Clean chart container and empty-state style |
| 392–430 | Recent sessions | Clickable card feel with subtle hover feedback |
| 432–462 | Legacy topic helpers | Retained helpers for compatibility/reuse |
| 463–532 | Setup + session control panel blocks | Setup area, form grid, microphone status container |
| 534–653 | Results page payoff styles | Score circle, metric rows, transcript readability |
| 655–677 | Responsive behavior | Under-900px grid collapsing and header stacking |
| 679–697 | Live session status + timer | Centered status card and prominent timer |
| 699–761 | Session details + skill feedback | Report-like detail and feedback formatting |
| 763–786 | Filter tab utility styles | Kept for optional future use |
| 788–797 | Session cancel button tone | Muted danger-adjacent style without harsh red |

### Responsive behavior

At viewport widths under 900px:
- Dashboard grid, results grid, info grid, and form grid collapse from multi-column to single-column
- Card header changes from row to column
- Topic rows and forms stack vertically

---

## 16. What raw_metrics_json Stores

Every completed session writes a JSON string to `session_artifacts.raw_metrics_json`. This captures all intermediate computation values for debugging, future threshold tuning, and transparency.

```json
{
    "total_words": 102,
    "speaking_seconds": 58.4,
    "speaking_minutes": 0.9733,
    "average_word_confidence": 0.9365,
    "wpm": 104.8,
    "clarity_long_pauses": 3,
    "clarity_long_pause_seconds": 5.21,
    "confidence_hesitation_pauses": 2,
    "confidence_long_pauses": 1,
    "average_speech_segment_length": 7.32,
    "filler_words": 4,
    "transition_phrases": 3,
    "total_sentences": 6,
    "average_sentence_length": 17.0,
    "sentence_length_stddev": 4.52,
    "topic_keywords": ["climate change", "global agriculture", "impact", ...],
    "covered_topic_keywords": 5,
    "keyword_coverage_ratio": 0.625,
    "tone_matches": 2,
    "tone_conflicts": 3,
    "readability_grade": 7.8,
    "unique_content_words": 42,
    "total_content_words": 58,
    "repeated_non_stopwords": 3,
    "lexical_diversity": 0.7241,
    "cohere_similarity": 0.8234,
    "low_sample_flags": []
}
```

| Field | What It Means | Used By |
|---|---|---|
| `total_words` | Regex-tokenized word count | Confidence, Structure, Vocabulary denominators |
| `speaking_seconds` / `speaking_minutes` | Time span from first to last word | WPM, per-minute metrics |
| `average_word_confidence` | Mean of AssemblyAI word.confidence values | Clarity: Intelligibility subscore |
| `wpm` | Words per minute | Clarity: Pace subscore |
| `clarity_long_pauses` | Count of gaps > 1.2s | Clarity: LongPauseControl |
| `clarity_long_pause_seconds` | Total seconds of clarity long pauses | Clarity: PauseDurationControl |
| `confidence_hesitation_pauses` | Count of gaps 0.8–1.5s | Confidence: HesitationScore |
| `confidence_long_pauses` | Count of gaps > 1.5s | Confidence: LongPauseScore |
| `average_speech_segment_length` | Mean segment duration in seconds | Confidence: ContinuityScore |
| `filler_words` | Total filler count | Confidence: FillerScore |
| `transition_phrases` | Total transition count | Structure: TransitionScore |
| `total_sentences` | Number of sentences | Structure: SentenceCountScore |
| `average_sentence_length` | Mean words per sentence | Structure: SentenceLengthBalance |
| `sentence_length_stddev` | Stddev of sentence lengths | Structure: SentenceConsistency |
| `topic_keywords` | Extracted keyword list | Relevance: KeywordCoverage |
| `covered_topic_keywords` | How many keywords found in transcript | Relevance: KeywordCoverage |
| `keyword_coverage_ratio` | covered / total | Relevance (and fallback for PromptSimilarity) |
| `tone_matches` | Tone-aligned phrases found | Relevance: ToneAlignment |
| `tone_conflicts` | Tone-conflicting phrases found | Relevance: ToneAlignment |
| `readability_grade` | Flesch-Kincaid grade level | Vocabulary: AudienceFit |
| `unique_content_words` | Distinct content words | Vocabulary: LexicalDiversity |
| `total_content_words` | All content words (with repeats) | Vocabulary: LexicalDiversity |
| `repeated_non_stopwords` | Content words appearing >2 times | Vocabulary: RepetitionControl |
| `lexical_diversity` | unique / total content words | Vocabulary: LexicalDiversity |
| `cohere_similarity` | Cosine similarity from Cohere embeddings | Relevance: PromptSimilarity |
| `low_sample_flags` | List of warning flags | Communicated to feedback prompt |

---

## 17. Recent UI and Dashboard Refinements

This section documents the latest implementation choices added after the initial final-phase completion.

### 17.1 Dashboard score chart is now data-driven

The dashboard chart is no longer a static visual placeholder. It now renders from real user data:

1. `app.py` adds `get_communication_score_history(user_id, limit=20)`
2. `dashboard()` passes `score_history` into `dashboard.html`
3. `dashboard.html` embeds that payload in a JSON script tag (`id="score_history_data"`)
4. `static/js/dashboard_chart.js` parses, normalizes, and draws the chart in `<svg id="score_chart_svg">`

Why this choice:
- Preserves CSCB20 simplicity (plain JS + SVG, no chart libraries)
- Keeps rendering deterministic and easy to explain in a demo
- Uses only already-saved session scores, so no extra backend complexity

### 17.2 All-time view only (filter buttons removed)

The chart now intentionally presents one scope: **All Time**.

- Week/Month/Six Months/Year tabs were removed from `dashboard.html`
- Header now shows a plain "All Time" label

Why this choice:
- Prevents empty/ambiguous filter states in low-data student projects
- Reduces UI complexity while still giving meaningful trend visibility
- Matches current product scope (single simple trend chart)

### 17.3 Numeric coercion fix for chart reliability

In `dashboard_chart.js`, `item.score` is explicitly converted via `Number(item.score)` before finite checks.

Why this was necessary:
- JSON payloads can contain numeric-looking strings
- `Number.isFinite("80")` is `false`, which previously filtered out valid data points
- Explicit coercion ensures real sessions appear correctly on the chart

### 17.4 Hidden empty-state rendering fix

`.chart-empty-text[hidden] { display: none; }` ensures the empty message hides correctly when chart data is available.

Why this was necessary:
- `.chart-empty-text` had explicit `display: flex`
- Without a `[hidden]` override, browser `hidden` behavior could be visually overridden

### 17.5 Light-theme visual polish choices (charcoal accent)

The app now uses a restrained light theme with dark accents:

- Replaced bright blue accents with charcoal (`#1f2329` / `#111418`)
- Kept page backgrounds light (`#f5f5f7`) and cards white (`#ffffff`)
- Unified component styling across dashboard/session/results/auth
- Refined card borders/shadows, spacing rhythm, and heading hierarchy
- Styled read-only session fields to look intentionally non-editable
- Gave cancel action a muted danger-adjacent tone without using harsh red

Constraints respected:
- No route or workflow changes
- No JS ID changes for `microphone.js` integration
- No external CSS frameworks or web fonts
- No flashy animations; only subtle hover/focus transitions
