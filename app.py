from flask import Flask, render_template, request, redirect, url_for, make_response, session
from werkzeug.security import generate_password_hash, check_password_hash       # For password bluring
from dotenv import load_dotenv
import os
import mysql.connector

load_dotenv()                                   # Lines 3-16 help load the database settings using the .env file and then connects Python to MySQL
                                                # without havign to hardcode the passwords and information directly into the code using venv 
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

@app.route("/")
def home():
    return render_template('home.html')

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

        return redirect(url_for("home"))

    return render_template("login.html", error=None)

if __name__ == "__main__":
    app.run(debug=True)