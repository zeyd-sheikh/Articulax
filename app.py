from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import mysql.connector

load_dotenv()


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


def user_exists(email, username):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT user_id
        FROM users
        WHERE email = %s OR username = %s
    """
    cursor.execute(query, (email, username))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return user is not None


def get_user_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT user_id, username, account_password
        FROM users
        WHERE username = %s
    """
    cursor.execute(query, (username,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return user


def current_user():
    if "user_id" not in session:
        return None

    return {
        "user_id": session["user_id"],
        "username": session["username"]
    }


def get_recent_communication_sessions(user_id, limit=5):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            s.session_id,
            cs.topic,
            s.score,
            s.start_time
        FROM sessions s
        JOIN com_sessions cs
            ON s.session_id = cs.session_id
        WHERE s.user_id = %s
          AND s.mode = 'Communication'
        ORDER BY s.start_time DESC
        LIMIT %s
    """
    cursor.execute(query, (user_id, limit))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    recent_sessions = []
    for row in rows:
        start_time = row["start_time"]
        formatted_date = start_time.strftime("%Y-%m-%d") if start_time else "No date"

        recent_sessions.append({
            "session_id": row["session_id"],
            "topic": row["topic"],
            "score": row["score"] if row["score"] is not None else "--",
            "date": formatted_date
        })

    return recent_sessions


def generate_placeholder_scores(topic, audience, tone, duration):
    duration_value = int(duration)

    vocabulary = min(100, 70 + duration_value * 2)
    relevance = 85
    confidence = 76 if tone == "Casual" else 80
    register = 82 if audience == "Professional" else 78
    clarity = 84
    structure = 81

    overall_score = round(
        (clarity + confidence + structure + relevance + vocabulary) / 5
    )

    feedback = (
        f"You spoke on '{topic}' for a {audience.lower()} audience using a {tone.lower()} tone. "
        "Your response was relevant and reasonably structured. "
        "Try improving confidence, reducing filler words, and making transitions smoother."
    )

    return {
        "overall_score": overall_score,
        "clarity": clarity,
        "confidence": confidence,
        "structure": structure,
        "relevance": relevance,
        "vocabulary": vocabulary,
        "register": register,
        "feedback": feedback
    }


def create_communication_session(user_id, topic, audience, tone, duration):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        generated = generate_placeholder_scores(topic, audience, tone, duration)

        session_insert_query = """
            INSERT INTO sessions (user_id, mode, score)
            VALUES (%s, 'Communication', %s)
        """
        cursor.execute(session_insert_query, (user_id, generated["overall_score"]))
        new_session_id = cursor.lastrowid

        com_session_insert_query = """
            INSERT INTO com_sessions (session_id, topic, audience, tone, duration)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(
            com_session_insert_query,
            (new_session_id, topic, audience, tone, int(duration))
        )

        scores_insert_query = """
            INSERT INTO com_session_scores (
                session_id,
                clarity_score,
                confidence_score,
                structure_score,
                relevance_score,
                vocabulary_score
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            scores_insert_query,
            (
                new_session_id,
                generated["clarity"],
                generated["confidence"],
                generated["structure"],
                generated["relevance"],
                generated["vocabulary"]
            )
        )

        feedback_insert_query = """
            INSERT INTO com_session_feedback (session_id, feedback)
            VALUES (%s, %s)
        """
        cursor.execute(
            feedback_insert_query,
            (new_session_id, generated["feedback"])
        )

        conn.commit()
        return new_session_id

    except mysql.connector.Error:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def get_communication_session_result(session_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            s.session_id,
            s.mode,
            s.score AS overall_score,
            s.start_time,
            cs.topic,
            cs.audience,
            cs.tone,
            cs.duration,
            css.clarity_score,
            css.confidence_score,
            css.structure_score,
            css.relevance_score,
            css.vocabulary_score,
            cf.feedback
        FROM sessions s
        JOIN com_sessions cs
            ON s.session_id = cs.session_id
        LEFT JOIN com_session_scores css
            ON cs.session_id = css.session_id
        LEFT JOIN com_session_feedback cf
            ON cs.session_id = cf.session_id
        WHERE s.session_id = %s
          AND s.user_id = %s
          AND s.mode = 'Communication'
        LIMIT 1
    """
    cursor.execute(query, (session_id, user_id))
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row is None:
        return None

    start_time = row["start_time"]
    formatted_date = start_time.strftime("%Y-%m-%d %H:%M") if start_time else "Latest Session"

    register_score = 82 if row["audience"] == "Professional" else 78

    return {
        "session_id": row["session_id"],
        "topic": row["topic"],
        "date": formatted_date,
        "mode": row["mode"],
        "overall_score": row["overall_score"] if row["overall_score"] is not None else 0,
        "vocabulary": row["vocabulary_score"] if row["vocabulary_score"] is not None else 0,
        "relevance": row["relevance_score"] if row["relevance_score"] is not None else 0,
        "confidence": row["confidence_score"] if row["confidence_score"] is not None else 0,
        "register": register_score,
        "feedback": row["feedback"] if row["feedback"] else "No feedback available yet.",
        "transcript": (
            "Transcript not available yet. "
            "Audio recording and transcript storage will be integrated later."
        )
    }


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

        if not first_name or not last_name or not email or not username or not password or not confirm_password:
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

        insert_query = """
            INSERT INTO users (first_name, last_name, email, username, account_password)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (first_name, last_name, email, username, hashed_password))
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

        return redirect(url_for("dashboard"))

    return render_template("login.html", error=None)


@app.route("/dashboard")
def dashboard():
    user = current_user()

    if user is None:
        return redirect(url_for("login"))

    recent_sessions = get_recent_communication_sessions(user["user_id"], limit=5)

    return render_template(
        "dashboard.html",
        username=user["username"],
        recent_sessions=recent_sessions,
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
        duration=duration
    )


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
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)