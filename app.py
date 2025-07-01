from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'vanes_secret'

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect('vanes.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT, name TEXT, client TEXT,
        start TEXT, end TEXT, status TEXT,
        budget REAL, notes TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site_id TEXT, name TEXT, location TEXT,
        linked_project TEXT, supervisor TEXT,
        status TEXT, notes TEXT)''')

    conn.commit()
    conn.close()

init_db()

# ---------- AUTH ----------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user'] = user['name']
            return redirect('/dashboard')
        else:
            flash('Invalid credentials')
            return redirect('/login')

    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    password = generate_password_hash(request.form['password'])

    try:
        conn = get_db()
        conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                     (name, email, password))
        conn.commit()
        conn.close()
        flash('Account created! Please login.')
    except:
        flash('Email already exists.')
    return redirect('/login')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html')

# ---------- PROJECT MANAGEMENT ----------
@app.route('/generate_project_id')
def generate_project_id():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] + 1
    project_id = f"PROJ-2025-{count:04}"
    return jsonify({"project_id": project_id})

@app.route('/add_project', methods=['POST'])
def add_project():
    data = (
        request.form['project_id'],
        request.form['project_name'],
        request.form['client_name'],
        request.form['start_date'],
        request.form['end_date'],
        request.form['status'],
        request.form['budget'],
        request.form['notes']
    )
    conn = get_db()
    conn.execute('''INSERT INTO projects 
        (project_id, name, client, start, end, status, budget, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()
    return redirect('/project_sites')

# ---------- SITE MANAGEMENT ----------
@app.route('/generate_site_id')
def generate_site_id():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0] + 1
    site_id = f"SITE-2025-{count:04}"
    return jsonify({"site_id": site_id})

@app.route('/add_site', methods=['POST'])
def add_site():
    data = (
        request.form['site_id'],
        request.form['site_name'],
        request.form['location'],
        request.form['linked_project'],
        request.form['supervisor'],
        request.form['status'],
        request.form['notes']
    )
    conn = get_db()
    conn.execute('''INSERT INTO sites 
        (site_id, name, location, linked_project, supervisor, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()
    return redirect('/project_sites')

# ---------- COMBINED MODULE ----------
@app.route('/project_sites')
def project_sites():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    sites = conn.execute("SELECT * FROM sites").fetchall()
    conn.close()
    return render_template('project_sites.html', projects=projects, sites=sites)

# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True)
