from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
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

    # Accounts & Purchase table
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

    # Workforce Payroll
    c.execute('''
        CREATE TABLE IF NOT EXISTS workforce (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            department TEXT,
            salary REAL,
            present_days INTEGER,
            leave_days INTEGER,
            bonus REAL,
            deductions REAL,
            total_pay REAL,
            join_date TEXT,
            site_assigned TEXT
        )
    ''')

    # HR Subtables for popups
    c.execute('''CREATE TABLE IF NOT EXISTS hr_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, date TEXT, status TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_leave (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, from_date TEXT, to_date TEXT, reason TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, month TEXT, score INTEGER, remarks TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_training (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, topic TEXT, trainer TEXT, date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, doc_type TEXT, uploaded_on TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, department TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_bonus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, bonus REAL, date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_deductions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, deduction REAL, reason TEXT, date TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# -------- Authentication Routes --------
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
        data = (
            request.form['project_name'],
            request.form['site_location'],
            request.form['start_date'],
            request.form['end_date'],
            request.form['status'],
            request.form['budget'],
            request.form['design_engineer'],
            request.form['site_engineer'],
            request.form['team_members']
        )
        c.execute('''INSERT INTO project_sites 
            (project_name, site_location, start_date, end_date, status, budget, design_engineer, site_engineer, team_members)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
        conn.commit()

    c.execute('SELECT * FROM project_sites')
    data = c.fetchall()
    next_id = len(data) + 1
    generated_id = f"PROJ{1000 + next_id}"
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
        data = (
            request.form['type'],
            request.form['category'],
            request.form['vendor_name'],
            request.form['invoice_number'],
            float(request.form['amount']),
            float(request.form.get('tax', 0)),
            float(request.form['amount']) + float(request.form.get('tax', 0)),
            request.form['date'],
            request.form['description'],
            request.form['assigned_by']
        )
        c.execute('''INSERT INTO accounts 
            (type, category, vendor_name, invoice_number, amount, tax, total, date, description, assigned_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
        conn.commit()

    c.execute('SELECT * FROM accounts ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('accounts_purchase.html', data=data)

# ---------- Export Functions ----------
@app.route('/export_project_excel')
def export_project_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query('SELECT * FROM project_sites', conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects & Sites')
    output.seek(0)
    return send_file(output, download_name='project_sites.xlsx', as_attachment=True)

@app.route('/export_accounts_excel')
def export_accounts_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query('SELECT * FROM accounts', conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Accounts & Purchase')
    output.seek(0)
    return send_file(output, download_name='accounts_purchase.xlsx', as_attachment=True)
    # ---------- Workforce Main Page ----------
@app.route('/workforce', methods=['GET', 'POST'])
def workforce():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Auto payroll calculation and insert
    if request.method == 'POST':
        name = request.form['name']
        department = request.form['department']
        salary = float(request.form['salary'])
        present_days = int(request.form['present_days'])
        leave_days = int(request.form['leave_days'])
        bonus = float(request.form.get('bonus', 0))
        deductions = float(request.form.get('deductions', 0))
        join_date = request.form['join_date']
        site_assigned = request.form['site_assigned']

        # Payroll calculation (assuming 30-day month)
        per_day_salary = salary / 30
        total_pay = round((per_day_salary * present_days) + bonus - deductions, 2)

        c.execute('''
            INSERT INTO workforce 
            (name, department, salary, present_days, leave_days, bonus, deductions, total_pay, join_date, site_assigned)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, department, salary, present_days, leave_days, bonus, deductions, total_pay, join_date, site_assigned))
        conn.commit()

    # Fetch table
    c.execute('SELECT * FROM workforce')
    data = c.fetchall()
    conn.close()
    return render_template('workforce.html', data=data)

# ---------- HR Feature Routes (10 Popups) ----------
@app.route('/hr/attendance', methods=['POST'])
def hr_attendance():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_attendance (name, date, status) VALUES (?, ?, ?)', 
              (data['name'], data['date'], data['status']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/hr/leave', methods=['POST'])
def hr_leave():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_leave (name, from_date, to_date, reason) VALUES (?, ?, ?, ?)', 
              (data['name'], data['from_date'], data['to_date'], data['reason']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/hr/performance', methods=['POST'])
def hr_performance():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_performance (name, month, score, remarks) VALUES (?, ?, ?, ?)', 
              (data['name'], data['month'], data['score'], data['remarks']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/hr/training', methods=['POST'])
def hr_training():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_training (name, topic, trainer, date) VALUES (?, ?, ?, ?)', 
              (data['name'], data['topic'], data['trainer'], data['date']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/hr/documents', methods=['POST'])
def hr_documents():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_documents (name, doc_type, uploaded_on) VALUES (?, ?, ?)', 
              (data['name'], data['doc_type'], data['uploaded_on']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/hr/departments', methods=['POST'])
def hr_departments():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_departments (name, department) VALUES (?, ?)', 
              (data['name'], data['department']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/hr/bonus', methods=['POST'])
def hr_bonus():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_bonus (name, bonus, date) VALUES (?, ?, ?)', 
              (data['name'], data['bonus'], data['date']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/hr/deductions', methods=['POST'])
def hr_deductions():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_deductions (name, deduction, reason, date) VALUES (?, ?, ?, ?)', 
              (data['name'], data['deduction'], data['reason'], data['date']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})
    # ---------- Workforce Export to Excel ----------
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

# ---------- Workforce Export to PDF ----------
@app.route('/export_workforce_pdf')
def export_workforce_pdf():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM workforce')
    data = c.fetchall()
    conn.close()
    
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(200, y, "Workforce Report")
    y -= 30
    pdf.setFont("Helvetica", 9)

    for row in data:
        pdf.drawString(40, y, f"{row[0]} | {row[1]} | ₹{row[2]} | Days Present: {row[3]} | Pay: ₹{row[8]}")
        y -= 20
        if y < 60:
            pdf.showPage()
            y = height - 40

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, download_name="workforce_report.pdf", as_attachment=True)

# ---------- Run App ----------
if __name__ == '__main__':
    app.run(debug=True)
