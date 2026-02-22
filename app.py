from flask import Flask, render_template, request, redirect, session
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this"

DB = "game.db"

# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # Game history table
    c.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            word TEXT,
            result TEXT,
            score INTEGER,
            date TEXT
        )
    """)

    # Daily challenge table
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT,
            date TEXT UNIQUE
        )
    """)

    # Create today's daily challenge if not exists
    today = str(datetime.now().date())
    words = ["PYTHON", "FLASK", "DATABASE", "FUNCTION", "VARIABLE", "ALGORITHM"]

    c.execute("SELECT * FROM daily WHERE date=?", (today,))
    if not c.fetchone():
        c.execute("INSERT INTO daily(word, date) VALUES (?, ?)",
                  (random.choice(words), today))

    conn.commit()
    conn.close()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def scramble(word):
    letters = list(word)
    random.shuffle(letters)
    scrambled = ''.join(letters)

    while scrambled == word:
        random.shuffle(letters)
        scrambled = ''.join(letters)

    return scrambled


# =========================================================
# ROUTES
# =========================================================

# ---------------- HOME ----------------
@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return render_template("login.html")


# ---------------- REGISTER PAGE ----------------
@app.route("/register")
def register_page():
    return render_template("register.html")


# ---------------- CREATE ACCOUNT ----------------
@app.route("/create-account", methods=["POST"])
def create_account():
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        return "Username and password required"

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users(username, password) VALUES (?, ?)",
                  (username, password))
        conn.commit()
    except:
        conn.close()
        return "User already exists"

    conn.close()

    session["user"] = username
    return redirect("/dashboard")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        return "Username and password required"

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=? AND password=?",
              (username, password))
    user = c.fetchone()
    conn.close()

    if user:
        session["user"] = username
        return redirect("/dashboard")
    else:
        return "Invalid login credentials"


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM games WHERE username=? ORDER BY id DESC",
              (session["user"],))
    history = c.fetchall()

    # Calculate total score
    c.execute("SELECT SUM(score) FROM games WHERE username=?",
              (session["user"],))
    total_score = c.fetchone()[0]
    total_score = total_score if total_score else 0

    conn.close()

    return render_template("dashboard.html",
                           user=session["user"],
                           history=history,
                           total_score=total_score)


# ---------------- PLAY GAME ----------------
@app.route("/game")
def game():
    if "user" not in session:
        return redirect("/")

    words = ["PYTHON", "FLASK", "DATABASE", "FUNCTION", "VARIABLE", "ALGORITHM"]
    word = random.choice(words)

    return render_template("game.html",
                           scrambled=scramble(word),
                           word=word)


# ---------------- SUBMIT GAME ----------------
@app.route("/submit", methods=["POST"])
def submit():
    if "user" not in session:
        return redirect("/")

    answer = request.form.get("answer", "").upper()
    word = request.form.get("word", "").upper()

    result = "Win" if answer == word else "Lose"
    score = 10 if result == "Win" else 0

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        INSERT INTO games(username, word, result, score, date)
        VALUES (?, ?, ?, ?, ?)
    """, (session["user"], word, result, score,
          str(datetime.now().date())))

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# ---------------- DAILY CHALLENGE ----------------
@app.route("/daily")
def daily():
    if "user" not in session:
        return redirect("/")

    today = str(datetime.now().date())

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT word FROM daily WHERE date=?", (today,))
    row = c.fetchone()
    conn.close()

    if not row:
        return "No daily challenge today"

    word = row[0]

    return render_template("daily.html",
                           scrambled=scramble(word),
                           word=word)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    init_db()
    app.run(debug=True)