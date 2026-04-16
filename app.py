"""
This file handles:

- authentication and dashboard rendering
- communication session routes
- transcription, scoring, AI feedback, and persistence
"""

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,            # Return JSON API responses.
)
from werkzeug.security import generate_password_hash, check_password_hash  # Password hashing + verification.
from werkzeug.utils import secure_filename                                 # Sanitize uploaded audio filenames.

from dotenv import load_dotenv                      # Load environment variables from .env file.
from pathlib import Path                            # Safe filesystem path construction.
import os                                           # Environment access and filesystem utilities.
import json                                         # Serialize raw metrics before DB insert.
import uuid                                         # Generate unique audio filenames.
import logging                                      # Log pipeline failures for debugging.
import mysql.connector                              # MySQL database connection/driver.

from services.transcription_service import transcribe_audio_file    # AssemblyAI transcription pipeline.
from services.scoring_service import score_communication_session    # Deterministic rubric scoring.
from services.cohere_service import generate_feedback_json          # Structured coaching feedback generation.

load_dotenv()

# App setup  ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent      # Gets the folder where app.py is located
UPLOAD_DIR = BASE_DIR / "uploads" / "audio"     # Creates the path for uploads/auido and the recorded audio files will be saved here
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)   # Make the uploads/audio folder if it does not already exist

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # Sets the maximum upload size to 50 MB


# Database ---------------------------------------------------------------

def get_db_connection():
    """Create a MySQL connection."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


# Auth helpers -----------------------------------------------------------

def user_exists(email, username):
    """Check if either email or username is already registered."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT user_id FROM users WHERE email = %s OR username = %s",
        (email, username),
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user is not None


def get_user_by_username(username):
    """Fetch login fields for a username; returns None when not found."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT user_id, username, first_name, last_name, account_password "
        "FROM users WHERE username = %s",
        (username,),
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def current_user():
    """Return authenticated user context from session cookie."""
    if "user_id" not in session:
        return None
    return {
        "user_id": session["user_id"],
        "username": session["username"],
        "first_name": session.get("first_name", ""),
        "last_name": session.get("last_name", ""),
    }


# MIME to file extension  -------------------------------------------------------

def extension_for_mime(mime_type: str) -> str:
    '''Return the file extension associated with a MIME type string of a file'''
    mapping = {
        "audio/webm": ".webm",
        "audio/webm;codecs=opus": ".webm",
        "audio/ogg": ".ogg",
        "audio/ogg;codecs=opus": ".ogg",
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "video/webm": ".webm",
    }
    return mapping.get(mime_type, ".webm")


# Session queries -----------------------------------------------------------

def get_recent_communication_sessions(user_id, limit=5):
    """
    Return the latest Communication sessions for dashboard cards.

    Joins 'sessions' with 'com_sessions' to pair each session score/date with
    its communication metadata (topic, audience, tone, duration).
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT s.session_id, cs.topic, s.score, s.start_time
        FROM sessions s
        JOIN com_sessions cs ON s.session_id = cs.session_id
        WHERE s.user_id = %s AND s.mode = 'Communication'
        ORDER BY s.start_time DESC
        LIMIT %s
        """,
        (user_id, limit),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    results = []
    for row in rows:
        start_time = row["start_time"]
        results.append({
            "session_id": row["session_id"],
            "topic": row["topic"],
            "score": row["score"] if row["score"] is not None else "--",
            "date": start_time.strftime("%Y-%m-%d") if start_time else "No date",
        })
    return results


def get_communication_score_history(user_id, limit=20):
    """Return chronological score history for chart rendering."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT s.session_id, s.score, s.start_time
        FROM sessions s
        WHERE s.user_id = %s
          AND s.mode = 'Communication'
          AND s.score IS NOT NULL
        ORDER BY s.start_time ASC
        LIMIT %s
        """,
        (user_id, limit),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    history = []
    for row in rows:
        start_time = row["start_time"]
        history.append({
            "session_id": row["session_id"],
            "score": int(row["score"]),
            "date_label": (
                start_time.strftime("%b %d") if start_time else "Unknown date"
            ),
        })
    return history


def get_communication_session_result(session_id, user_id):
    """
    Return one full result payload for the results page.

    Table relationships used:
    - 'sessions' (owner, mode, overall score, timestamp)
    - 'com_sessions' (topic/audience/tone/duration for that session_id)
    - 'com_session_scores' (dimension-level rubric scores)
    - 'com_session_feedback' (overall + per-dimension narrative feedback)
    - 'session_artifacts' (transcript, audio path, raw metrics blob)
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            s.session_id, s.mode, s.score AS overall_score, s.start_time,
            cs.topic, cs.audience, cs.tone, cs.duration,
            css.clarity_score, css.confidence_score,
            css.structure_score, css.relevance_score, css.vocabulary_score,
            cf.feedback,
            cf.clarity_feedback, cf.confidence_feedback,
            cf.structure_feedback, cf.relevance_feedback, cf.vocabulary_feedback,
            sa.transcript_text, sa.audio_file_path
        FROM sessions s
        JOIN com_sessions cs ON s.session_id = cs.session_id
        LEFT JOIN com_session_scores css ON cs.session_id = css.session_id
        LEFT JOIN com_session_feedback cf ON cs.session_id = cf.session_id
        LEFT JOIN session_artifacts sa ON s.session_id = sa.session_id
        WHERE s.session_id = %s AND s.user_id = %s AND s.mode = 'Communication'
        LIMIT 1
        """,
        (session_id, user_id),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row is None:
        return None

    start_time = row["start_time"]
    formatted_date = (
        start_time.strftime("%Y-%m-%d %H:%M") if start_time else "Latest Session"
    )

    return {
        "session_id": row["session_id"],
        "topic": row["topic"],
        "audience": row["audience"],
        "tone": row["tone"],
        "duration": row["duration"],
        "date": formatted_date,
        "mode": row["mode"],
        "overall_score": row["overall_score"] if row["overall_score"] is not None else 0,
        "clarity": row["clarity_score"] if row["clarity_score"] is not None else 0,
        "confidence": row["confidence_score"] if row["confidence_score"] is not None else 0,
        "structure": row["structure_score"] if row["structure_score"] is not None else 0,
        "relevance": row["relevance_score"] if row["relevance_score"] is not None else 0,
        "vocabulary": row["vocabulary_score"] if row["vocabulary_score"] is not None else 0,
        "feedback": row["feedback"] or "No feedback available yet.",
        "clarity_feedback": row["clarity_feedback"] or "",
        "confidence_feedback": row["confidence_feedback"] or "",
        "structure_feedback": row["structure_feedback"] or "",
        "relevance_feedback": row["relevance_feedback"] or "",
        "vocabulary_feedback": row["vocabulary_feedback"] or "",
        "transcript": row["transcript_text"] or "Transcript not available.",
    }


# DB persistence ---------------------------------------------------------------

def persist_completed_communication_session(
    user_id, topic, audience, tone, duration,
    audio_file_path, transcript_text,
    scores, feedback, raw_metrics,
):
    """
    Persist a completed Communication session across all related tables.

    Uses a single transaction so the session is either fully saved everywhere
    or fully rolled back if any insert fails.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Parent session record used by all communication-specific child tables.
        cursor.execute(
            "INSERT INTO sessions (user_id, mode, score) VALUES (%s, 'Communication', %s)",
            (user_id, scores["overall_score"]),
        )

        session_id = cursor.lastrowid

        # Communication configuration captured when user started this session.
        cursor.execute(
            "INSERT INTO com_sessions (session_id, topic, audience, tone, duration) "
            "VALUES (%s, %s, %s, %s, %s)",
            (session_id, topic, audience, tone, int(duration)),
        )

        # Deterministic rubric breakdown (five scored communication dimensions).
        cursor.execute(
            "INSERT INTO com_session_scores "
            "(session_id, clarity_score, confidence_score, structure_score, "
            "relevance_score, vocabulary_score) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                session_id,
                scores["clarity"],
                scores["confidence"],
                scores["structure"],
                scores["relevance"],
                scores["vocabulary"],
            ),
        )

        # AI-generated narrative feedback, stored separately from numeric scores.
        cursor.execute(
            "INSERT INTO com_session_feedback "
            "(session_id, feedback, clarity_feedback, confidence_feedback, "
            "structure_feedback, relevance_feedback, vocabulary_feedback) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                session_id,
                feedback.get("overall_feedback", ""),
                feedback.get("clarity_feedback", ""),
                feedback.get("confidence_feedback", ""),
                feedback.get("structure_feedback", ""),
                feedback.get("relevance_feedback", ""),
                feedback.get("vocabulary_feedback", ""),
            ),
        )

        # Save session artifacts for results, review, and debugging.
        cursor.execute(
            "INSERT INTO session_artifacts "
            "(session_id, transcript_text, audio_file_path, raw_metrics_json) "
            "VALUES (%s, %s, %s, %s)",
            (session_id, transcript_text, audio_file_path, json.dumps(raw_metrics)),
        )

        conn.commit()
        return session_id

    except mysql.connector.Error:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# Routes -----------------------------------------------------------------------------------

@app.route("/")
def home():

    return render_template("home.html")


@app.route("/about")
def about():

    return render_template("about.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        error = None
        if not all([first_name, last_name, email, username, password, confirm_password]):
            error = "All fields are required."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif user_exists(email, username):
            error = "Email or username already exists."

        if error:
            return render_template("register.html", error=error)

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (first_name, last_name, email, username, account_password) "
            "VALUES (%s, %s, %s, %s, %s)",
            (first_name, last_name, email, username, hashed_password),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html", error=None)


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        error = None
        if not username or not password:
            error = "Username and password are required."
        else:
            user = get_user_by_username(username)
            if user is None:
                error = "Invalid username or password."
            elif not check_password_hash(user["account_password"], password):
                error = "Invalid username or password."

        if error:
            return render_template("login.html", error=error)

        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        session["first_name"] = user["first_name"]
        session["last_name"] = user["last_name"]
        return redirect(url_for("dashboard"))

    return render_template("login.html", error=None)


@app.route("/dashboard")
def dashboard():

    user = current_user()
    if user is None:
        return redirect(url_for("login"))

    recent_sessions = get_recent_communication_sessions(user["user_id"], limit=5)
    score_history = get_communication_score_history(user["user_id"], limit=20)
    fn = (user.get("first_name") or "").strip()
    ln = (user.get("last_name") or "").strip()
    if not fn and not ln:
        dash_first, dash_last = user["username"], ""
    else:
        dash_first, dash_last = fn, ln
    return render_template(
        "dashboard.html",
        first_name=dash_first,
        last_name=dash_last,
        recent_sessions=recent_sessions,
        score_history=score_history,
    )


@app.route("/session", methods=["GET"])
def session_start():

    user = current_user()
    if user is None:
        return redirect(url_for("login"))

    topic = request.args.get("topic", "").strip()
    audience = request.args.get("audience", "").strip()
    tone = request.args.get("tone", "").strip()
    duration = request.args.get("duration", "").strip()

    valid_audiences = {"Kids", "General", "Professional"}
    valid_tones = {"Formal", "Persuasive", "Casual"}

    if not topic:
        return redirect(url_for("dashboard"))
    if audience not in valid_audiences:
        return redirect(url_for("dashboard"))
    if tone not in valid_tones:
        return redirect(url_for("dashboard"))
    if not duration.isdigit() or int(duration) <= 0:
        return redirect(url_for("dashboard"))

    return render_template(
        "session.html",
        username=user["username"],
        topic=topic,
        audience=audience,
        tone=tone,
        duration=duration,
    )


# API processing -----------------------------------------------------------------

@app.route("/complete-session", methods=["POST"])
def complete_session():
    """
    Complete a communication session from uploaded recording.

    Inputs: multipart form ('audio', 'topic', 'audience', 'tone', 'duration').
    Returns: JSON success payload with 'session_id', or JSON error payload.
    """
    user = current_user()
    if user is None:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    # 1) Validate input payload and guardrails before expensive processing.
    topic = request.form.get("topic", "").strip()
    audience = request.form.get("audience", "").strip()
    tone = request.form.get("tone", "").strip()
    duration = request.form.get("duration", "").strip()
    audio = request.files.get("audio")

    valid_audiences = {"Kids", "General", "Professional"}
    valid_tones = {"Formal", "Persuasive", "Casual"}

    if not topic or len(topic) > 150:
        return jsonify({"success": False, "error": "Invalid topic."}), 400
    
    if audience not in valid_audiences:
        return jsonify({"success": False, "error": "Invalid audience."}), 400
    
    if tone not in valid_tones:
        return jsonify({"success": False, "error": "Invalid tone."}), 400
    
    if not duration.isdigit() or int(duration) <= 0:
        return jsonify({"success": False, "error": "Invalid duration."}), 400
    
    if audio is None or audio.filename == "":
        return jsonify({"success": False, "error": "No audio file received."}), 400

    duration_int = int(duration)

    # 2) Save the uploaded audio to disk; extension depends on browser MIME type.
    mime = audio.content_type or "audio/webm"
    ext = extension_for_mime(mime)
    filename = f"{user['user_id']}_{uuid.uuid4().hex}{ext}"
    safe_name = secure_filename(filename)
    file_path = str(UPLOAD_DIR / safe_name)

    try:
        audio.save(file_path)
    except Exception:
        logging.exception("Failed to save audio file")
        return jsonify({"success": False, "error": "Failed to save audio file."}), 500

    if os.path.getsize(file_path) == 0:
        os.remove(file_path)
        return jsonify({"success": False, "error": "Audio file is empty."}), 400

    # 3) Transcribe with AssemblyAI; returns normalized text + word-level timing.
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    try:
        transcript_payload = transcribe_audio_file(file_path, api_key)
    except Exception:
        logging.exception("Transcription failed")
        return jsonify({
            "success": False,
            "error": "We could not process your recording. Please try again.",
        }), 502

    transcript_text = transcript_payload.get("text", "").strip()
    if not transcript_text or len(transcript_text) < 5:
        return jsonify({
            "success": False,
            "error": "No speech was detected clearly enough to score this session.",
        }), 422

    # 4) Compute deterministic rubric scores from transcript metrics.
    try:
        scores = score_communication_session(
            topic, audience, tone, duration_int, transcript_payload,
        )
    except Exception:
        logging.exception("Scoring failed")
        return jsonify({
            "success": False,
            "error": "Scoring failed. Please try again.",
        }), 500

    # 5) Generate structured coaching feedback with Cohere.
    feedback = generate_feedback_json(
        topic, audience, tone, duration_int, transcript_text,
        scores, scores["raw_metrics"], scores["low_sample_flags"],
    )

    # 6) Persist everything in MySQL: session row + config + scores + feedback + transcript artifacts
    try:
        session_id = persist_completed_communication_session(
            user_id=user["user_id"],
            topic=topic,
            audience=audience,
            tone=tone,
            duration=duration_int,
            audio_file_path=file_path,
            transcript_text=transcript_text,
            scores=scores,
            feedback=feedback,
            raw_metrics=scores["raw_metrics"],
        )
    except Exception:
        logging.exception("Failed to save session to database")
        return jsonify({
            "success": False,
            "error": "Failed to save session results.",
        }), 500

    return jsonify({"success": True, "session_id": session_id})


@app.route("/results")
def results():

    user = current_user()
    if user is None:
        return redirect(url_for("login"))

    session_id = request.args.get("session_id", "").strip()
    if not session_id.isdigit():
        return redirect(url_for("dashboard"))

    result = get_communication_session_result(int(session_id), user["user_id"])
    if result is None:
        return redirect(url_for("dashboard"))

    return render_template("results.html", result=result)


@app.route("/logout", methods=["POST"])
def logout():
    """Clear login session. Inputs: none. Returns: redirect to login."""
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
