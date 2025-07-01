from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3, os
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ---------- Database Initialization ----------
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Project & Sites Table
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

    # Extended Accounts & Purchase Table
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

    # Workforce / HR Table with Auto Payroll
    c.execute('''
        CREATE TABLE IF NOT EXISTS workforce (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            department TEXT,
            site TEXT,
            salary REAL,
            days_present INTEGER,
            leaves INTEGER,
            bonus REAL,
            deductions REAL,
            total_pay REAL,
            joining_date TEXT,
            training_status TEXT,
            performance TEXT,
            documents TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------- Auth ----------
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
            c.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)', (name, email, password, role))
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
def project_sites():
    if 'user' not in session:
        return redirect('/login')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        data = (
            request.form['project_name'],
            request.form['site_location'],
            request.form['start_date'],
            request.form['end_date'],
            request.form['status'],
            float(request.form['budget']),
            request.form['design_engineer'],
            request.form['site_engineer'],
            request.form['team_members']
        )
        c.execute('''
            INSERT INTO project_sites 
            (project_name, site_location, start_date, end_date, status, budget, design_engineer, site_engineer, team_members)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
        conn.commit()
    c.execute('SELECT * FROM project_sites')
    data = c.fetchall()
    generated_id = f"PROJ{1000 + len(data) + 1}"
    conn.close()
    return render_template('project_sites.html', data=data, generated_id=generated_id)

# ---------- Accounts & Purchase ----------
@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    if 'user' not in session:
        return redirect('/login')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        form = request.form
        amount = float(form['amount'])
        tax = float(form.get('tax', 0))
        total = amount + tax
        c.execute('''
            INSERT INTO accounts 
            (type, category, vendor_name, invoice_number, amount, tax, total, date, description, assigned_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (form['type'], form['category'], form['vendor_name'], form['invoice_number'],
             amount, tax, total, form['date'], form['description'], form['assigned_by']))
        conn.commit()
    c.execute('SELECT * FROM accounts ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('accounts_purchase.html', data=data)

# ---------- Workforce / HR Module ----------
@app.route('/workforce', methods=['GET', 'POST'])
def workforce():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Add new workforce entry
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        department = request.form['department']
        site = request.form['site']
        salary = float(request.form['salary'])
        days_present = int(request.form['days_present'])
        leaves = int(request.form['leaves'])
        bonus = float(request.form['bonus'])
        deductions = float(request.form['deductions'])
        joining_date = request.form['joining_date']
        training_status = request.form['training_status']
        performance = request.form['performance']
        documents = request.form['documents']

        total_pay = ((salary / 30) * days_present) + bonus - deductions

        c.execute('''
            INSERT INTO workforce 
            (name, role, department, site, salary, days_present, leaves, bonus, deductions, total_pay, joining_date, training_status, performance, documents)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, role, department, site, salary, days_present, leaves, bonus, deductions, total_pay, joining_date, training_status, performance, documents))
        conn.commit()

    # Filters
    filter_site = request.args.get('site')
    filter_department = request.args.get('department')
    query = "SELECT * FROM workforce WHERE 1=1"
    params = []

    if filter_site:
        query += " AND site = ?"
        params.append(filter_site)
    if filter_department:
        query += " AND department = ?"
        params.append(filter_department)

    c.execute(query, params)
    data = c.fetchall()

    c.execute("SELECT DISTINCT site FROM workforce")
    sites = [row[0] for row in c.fetchall()]
    c.execute("SELECT DISTINCT department FROM workforce")
    departments = [row[0] for row in c.fetchall()]
    conn.close()

    return render_template('workforce.html', data=data, sites=sites, departments=departments)

# ---------- Export Workforce to Excel ----------
@app.route('/export_workforce_excel')
def export_workforce_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM workforce", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Workforce')
    output.seek(0)
    return send_file(output, download_name="workforce.xlsx", as_attachment=True)

# ---------- Export Workforce to PDF ----------
@app.route('/export_workforce_pdf')
def export_workforce_pdf():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM workforce")
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(220, y, "Workforce Report")
    y -= 30
    pdf.setFont("Helvetica", 9)

    for row in data:
        text = f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | ₹{row[10]:.2f}"
        pdf.drawString(30, y, text)
        y -= 20
        if y < 60:
            pdf.showPage()
            y = height - 40

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, download_name="workforce.pdf", as_attachment=True)
# ---------- Run ----------
if __name__ == '__main__':
    app.run(debug=True)
