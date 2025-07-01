from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'vanes_secret_key'

# -------------------- DATABASE INITIALIZATION --------------------
def init_db():
    conn = sqlite3.connect('vanes.db')
    c = conn.cursor()

    # Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')

    # Projects Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT UNIQUE,
            project_name TEXT,
            client_name TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            budget REAL,
            notes TEXT
        )
    ''')

    # Sites Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id TEXT UNIQUE,
            project_id TEXT,
            site_name TEXT,
            location TEXT,
            supervisor TEXT
        )
    ''')

    # Material Requests Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS material_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id TEXT,
            material_name TEXT,
            quantity INTEGER,
            requested_by TEXT,
            status TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# -------------------- ROUTES --------------------

@app.route('/')
def home():
    return redirect(url_for('login'))

# -------------------- REGISTER --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        raw_password = request.form['password']
        hashed_password = generate_password_hash(raw_password)
        role = request.form['role']

        conn = sqlite3.connect('vanes.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, username, password, role) VALUES (?, ?, ?, ?)",
                      (name, username, hashed_password, role))
            conn.commit()
            flash("User registered successfully.")
        except sqlite3.IntegrityError:
            flash("Username already exists.")
        conn.close()
        return redirect(url_for('register'))

    return render_template('register.html')

# -------------------- LOGIN --------------------
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
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.')
            return redirect(url_for('login'))

    return render_template('login.html')

# -------------------- LOGOUT --------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------------------- DASHBOARD --------------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('vanes.db')
    c = conn.cursor()

    # Counts for dashboard
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

# -------------------- MAIN --------------------
if __name__ == '__main__':
    app.run(debug=True)
