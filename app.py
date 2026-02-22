#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import random
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_FILE = "game.db"


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    total_score INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    word TEXT,
                    score INTEGER,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')

    conn.commit()
    conn.close()


# =========================
# RANDOM WORD API
# =========================

def get_random_word(difficulty):
    length_map = {
        "easy": 4,
        "medium": 6,
        "hard": 8
    }

    length = length_map.get(difficulty, 6)

    try:
        response = requests.get(
            f"https://random-word-api.herokuapp.com/word?length={length}",
            timeout=5
        )

        word = response.json()[0].upper()

        if not word.isalpha():
            return get_random_word(difficulty)

        return word

    except:
        fallback = {
            "easy": ["GAME", "PLAY", "WORD"],
            "medium": ["PYTHON", "CODING", "PLAYER"],
            "hard": ["ALGORITHM", "DATABASE", "FUNCTION"]
        }
        return random.choice(fallback[difficulty])


def scramble_word(word):
    letters = list(word)
    random.shuffle(letters)
    return ''.join(letters)


def calculate_score(time_taken, difficulty):
    base = {"easy": 50, "medium": 100, "hard": 150}
    return base.get(difficulty, 100)


# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/create-account", methods=["POST"])
def create_account():
    username = request.form["username"]
    password = request.form["password"]

    conn = get_db()
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                  (username, password))
        conn.commit()
    except:
        return "Username already exists!"

    conn.close()
    return redirect(url_for("home"))


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=? AND password=?",
              (username, password))
    user = c.fetchone()
    conn.close()

    if user:
        session["username"] = username
        return redirect(url_for("dashboard"))
    else:
        return "Invalid credentials"


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("home"))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT total_score, games_played FROM users WHERE username=?",
              (session["username"],))
    user = c.fetchone()
    conn.close()

    return render_template("dashboard.html",
                           score=user["total_score"],
                           games=user["games_played"])


@app.route("/game")
def game():
    if "username" not in session:
        return redirect(url_for("home"))

    difficulty = request.args.get("difficulty", "easy")

    word = get_random_word(difficulty)
    scrambled = scramble_word(word)

    session["current_word"] = word
    session["difficulty"] = difficulty

    return render_template("game.html",
                           scrambled=scrambled,
                           difficulty=difficulty)


@app.route("/submit", methods=["POST"])
def submit():
    if "username" not in session:
        return redirect(url_for("home"))

    answer = request.form["answer"].upper()
    correct_word = session.get("current_word")
    difficulty = session.get("difficulty")

    if not correct_word:
        return redirect(url_for("dashboard"))

    if answer == correct_word:
        score = calculate_score(0, difficulty)
        message = "Correct! 🎉"
    else:
        score = 0
        message = f"Wrong! The word was {correct_word}"

    conn = get_db()
    c = conn.cursor()

    c.execute("UPDATE users SET total_score = total_score + ?, games_played = games_played + 1 WHERE username=?",
              (score, session["username"]))

    c.execute("INSERT INTO games (username, word, score) VALUES (?, ?, ?)",
              (session["username"], correct_word, score))

    conn.commit()
    conn.close()

    return render_template("result.html",
                           message=message,
                           score=score)


@app.route("/daily")
def daily():
    if "username" not in session:
        return redirect(url_for("home"))

    today = datetime.now().strftime("%Y-%m-%d")
    random.seed(today)

    word = get_random_word("medium")
    scrambled = scramble_word(word)

    session["current_word"] = word
    session["difficulty"] = "medium"

    return render_template("daily.html",
                           scrambled=scrambled)


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    init_db()
    app.run()