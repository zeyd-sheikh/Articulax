from flask import Flask, render_template, request, redirect, url_for, make_response, session

from dotenv import load_dotenv
import os
import mysql.connector

load_dotenv()                                   # Lines 3-16 help load the database settings using the .env file and then connects Python to MySQL
                                                # without havign to hardcode the passwords and information directly into the code
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

if __name__ == "__main__":
    app.run(debug=True)