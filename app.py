from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'vanes_secret_key'

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect('vanes.db')
    c = conn.cursor()

    # Users table (used for login)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------- MANUAL USER CREATION ----------
def insert_admin_user():
    conn = sqlite3.connect('vanes.db')
    c = conn.cursor()
    username = "admin"
    password = "admin123"
    hashed_password = generate_password_hash(password)
    role = "admin"

    try:
        c.execute("INSERT INTO users (name, username, password, role) VALUES (?, ?, ?, ?)",
                  ("Admin", username, hashed_password, role))
        conn.commit()
        print("✔ Admin user created: admin / admin123")
    except:
        print("✔ Admin already exists")
    conn.close()

insert_admin_user()

# ---------- LOGIN ONLY ----------
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']

        conn = sqlite3.connect('vanes.db')
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (uname,))
        row = c.fetchone()
        conn.close()

        if row and check_password_hash(row[0], pwd):
            session['user'] = uname
            flash("Login successful", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)
