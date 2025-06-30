from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3, os
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ---------- Database Initialization ----------
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

    # Project & Sites table
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            site_location TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            budget REAL,
            design_engineer TEXT,
            site_engineer TEXT,
            team_members TEXT
        )
    ''')

    # Extended Accounts & Purchase table
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            category TEXT,
            vendor_name TEXT,
            invoice_number TEXT,
            amount REAL,
            tax REAL,
            total REAL,
            date TEXT,
            description TEXT,
            assigned_by TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------- Authentication Routes ----------
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
        project_name = request.form['project_name']
        site_location = request.form['site_location']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        status = request.form['status']
        budget = request.form['budget']
        design_engineer = request.form['design_engineer']
        site_engineer = request.form['site_engineer']
        team_members = request.form['team_members']

        c.execute('''
            INSERT INTO project_sites 
            (project_name, site_location, start_date, end_date, status, budget, design_engineer, site_engineer, team_members)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (project_name, site_location, start_date, end_date, status, budget, design_engineer, site_engineer, team_members))
        conn.commit()

    c.execute('SELECT * FROM project_sites')
    data = c.fetchall()
    next_id = len(data) + 1
    generated_id = f"PROJ{1000 + next_id}"
    conn.close()
    return render_template('project_sites.html', data=data, generated_id=generated_id)

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
        pdf.drawString(50, y, f"ID: PROJ{1000+row[0]}, Project: {row[1]}, Location: {row[2]}, Start: {row[3]}, End: {row[4]}, Status: {row[5]}")
        y -= 20
        if y < 50:
            pdf.showPage()
            y = height - 40
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, download_name="project_sites.pdf", as_attachment=True)

# ---------- Accounts ----------
@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    if request.method == 'POST':
        data = (
            request.form['type'],
            request.form.get('category', ''),
            request.form.get('vendor_name', ''),
            request.form.get('invoice_number', ''),
            float(request.form['amount']),
            float(request.form.get('tax', 0)),
            float(request.form['amount']) + float(request.form.get('tax', 0)),
            request.form['date'],
            request.form.get('description', ''),
            request.form.get('assigned_by', '')
        )
        c.execute('''
            INSERT INTO accounts 
            (type, category, vendor_name, invoice_number, amount, tax, total, date, description, assigned_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        conn.commit()

    c.execute('SELECT * FROM accounts ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('accounts.html', data=data)

@app.route('/export_accounts_excel')
def export_accounts_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM accounts", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Accounts & Purchase')
    output.seek(0)
    return send_file(output, download_name="accounts_purchase.xlsx", as_attachment=True)

@app.route('/export_accounts_pdf')
def export_accounts_pdf():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM accounts')
    data = c.fetchall()
    conn.close()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(220, y, "Accounts & Purchase Report")
    y -= 30
    pdf.setFont("Helvetica", 9)
    for row in data:
        pdf.drawString(30, y, f"ID: {row[0]}, Type: {row[1]}, Vendor: {row[3]}, ₹{row[5]} + Tax: {row[6]} = ₹{row[7]}")
        y -= 20
        if y < 60:
            pdf.showPage()
            y = height - 40
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, download_name="accounts_purchase.pdf", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
    
