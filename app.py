from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ---------- DB Initialization ----------
def init_db():
    conn = sqlite3.connect('erp_users.db')
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Projects & Sites table
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects_sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            site_location TEXT,
            client TEXT,
            status TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------- Routes ----------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('erp_users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email=? AND password=?', (email, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user'] = user[1]
            flash('Login successful!', 'success')
            return redirect('/dashboard')
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        try:
            conn = sqlite3.connect('erp_users.db')
            c = conn.cursor()
            c.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
                      (name, email, password, role))
            conn.commit()
            conn.close()
            flash('Registration successful!', 'success')
            return redirect('/login')
        except:
            flash('Email already exists.', 'danger')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template("dashboard.html", user=session['user'])

@app.route('/projects_sites')
def projects_sites():
    if 'user' not in session:
        return redirect('/login')
    conn = sqlite3.connect('erp_users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM projects_sites')
    data = c.fetchall()
    conn.close()
    return render_template('project_sites.html', projects=data)

# ---------- Run ----------
if __name__ == '__main__':
    app.run(debug=True)
