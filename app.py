from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'vanes_secret_key'

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect('vanes.db')
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')

    # Projects table
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            name TEXT,
            client TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            budget REAL,
            notes TEXT
        )
    ''')

    # Sites table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id TEXT,
            name TEXT,
            location TEXT,
            supervisor TEXT,
            linked_project TEXT,
            status TEXT
        )
    ''')

    # Material Requests table
    c.execute('''
        CREATE TABLE IF NOT EXISTS material_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            item TEXT,
            quantity INTEGER,
            status TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------- CREATE ADMIN USER ----------
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

# ---------- ROUTES ----------
@app.route('/')
def home():
    return redirect(url_for('login'))

# Login route
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

# Dashboard with summary counts
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('vanes.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM projects")
    total_projects = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM sites")
    total_sites = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE role = 'engineer'")
    total_engineers = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM material_requests")
    total_material_requests = c.fetchone()[0]

    conn.close()

    return render_template('dashboard.html',
                           total_projects=total_projects,
                           total_sites=total_sites,
                           total_engineers=total_engineers,
                           total_material_requests=total_material_requests)

# Project ID auto-generator
@app.route('/generate_project_id')
def generate_project_id():
    conn = sqlite3.connect('vanes.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM projects")
    count = c.fetchone()[0] + 1
    conn.close()
    return {"project_id": f"PROJ-2025-{count:03}"}

# Add Project route (form POST)
@app.route('/add_project', methods=['POST'])
def add_project():
    data = request.form
    conn = sqlite3.connect('vanes.db')
    c = conn.cursor()
    c.execute('''INSERT INTO projects (project_id, name, client, start_date, end_date, status, budget, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (data['project_id'], data['project_name'], data['client_name'],
               data['start_date'], data['end_date'], data['status'],
               data['budget'], data['notes']))
    conn.commit()
    conn.close()
    flash("Project added successfully", "success")
    return redirect(url_for('dashboard'))

# Project Sites Page (To use popup)
@app.route('/project_sites')
def project_sites():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('vanes.db')
    c = conn.cursor()
    c.execute("SELECT * FROM projects")
    projects = c.fetchall()
    conn.close()

    return render_template('project_sites.html', projects=projects)

# --------------- Run App ---------------
if __name__ == '__main__':
    app.run(debug=True)
