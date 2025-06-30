from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3, os
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ---------- DB Initialization ----------
def init_db():
    conn = sqlite3.connect('users.db')
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

    # Projects and Sites table (combined)
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            site_location TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            design_engineer TEXT,
            site_engineer TEXT,
            team_name TEXT,
            budget REAL
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------- Authentication ----------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email=? AND password=?', (email, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user'] = user[1]
            session['role'] = user[4]
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
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
                      (name, email, password, role))
            conn.commit()
            conn.close()
            flash('Registration successful!', 'success')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('Email already exists.', 'danger')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect('/login')

# ---------- Dashboard ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html', username=session['user'])

# ---------- Projects & Sites ----------
@app.route('/project-sites', methods=['GET', 'POST'])
def projects_sites():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    if request.method == 'POST':
        project_name = request.form.get('project_name')
        site_location = request.form.get('site_location')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        status = request.form.get('status')
        design_engineer = request.form.get('design_engineer')
        site_engineer = request.form.get('site_engineer')
        team_name = request.form.get('team_name')
        budget = request.form.get('budget')

        c.execute('''
            INSERT INTO project_sites 
            (project_name, site_location, start_date, end_date, status, design_engineer, site_engineer, team_name, budget)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (project_name, site_location, start_date, end_date, status, design_engineer, site_engineer, team_name, budget))
        conn.commit()

    c.execute('SELECT * FROM project_sites')
    data = c.fetchall()
    conn.close()

    return render_template('project_sites.html', data=data)

# ---------- Export to Excel ----------
@app.route('/export_excel')
def export_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM project_sites", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects & Sites')
    output.seek(0)
    return send_file(output, download_name="project_sites.xlsx", as_attachment=True)

# ---------- Export to PDF ----------
@app.route('/export_pdf')
def export_pdf():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM project_sites')
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(100, y, "Projects & Sites Report")
    pdf.setFont("Helvetica", 10)
    y -= 30

    for row in data:
        pdf.drawString(40, y, f"ID:{row[0]}, Project:{row[1]}, Site:{row[2]}, Start:{row[3]}, End:{row[4]}, Status:{row[5]}, Budget:{row[9]}")
        y -= 20
        if y < 50:
            pdf.showPage()
            y = height - 40

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, download_name="project_sites.pdf", as_attachment=True)

# ---------- Run ----------
if __name__ == '__main__':
    app.run(debug=True)
    
