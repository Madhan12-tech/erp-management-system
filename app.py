from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'vanes_secret_key'

DB_NAME = 'erp_users.db'

# ---------- DB Initialization ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# ---------- Routes ----------
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT name, role FROM users WHERE email=? AND password=?', (email, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['name'] = user[0]
            session['role'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
                      (name, email, password, role))
            conn.commit()
            conn.close()
            flash("Registered successfully! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists", "warning")
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'name' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')


@app.route('/add-project-site', methods=['POST'])
def add_project_site():
    if 'name' not in session:
        return redirect('/login')

    project_name = request.form['project_name']
    site_location = request.form['site_location']
    client = request.form['client']
    status = request.form['status']
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects_sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            site_location TEXT,
            client TEXT,
            status TEXT
        )
    ''')
    c.execute('INSERT INTO projects_sites (project_name, site_location, client, status) VALUES (?, ?, ?, ?)',
              (project_name, site_location, client, status))
    conn.commit()
    conn.close()

    flash("Project site added successfully!", "success")
    return redirect('/projects-sites')

@app.route('/projects-sites')
def projects_sites():
    if 'name' not in session:
        return redirect('/login')

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS projects_sites (id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT, site_location TEXT, client TEXT, status TEXT)')
    c.execute('SELECT * FROM projects_sites')
    projects = c.fetchall()
    conn.close()

    return render_template('project_sites.html', projects=projects, user=session['name'])


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

# ---------- Main ----------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
