from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import uuid
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import hashlib

app = Flask(__name__)
app.secret_key = 'secretkey'

# ---------------------- DATABASE SETUP ----------------------

def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # USERS
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # VENDORS
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            company TEXT,
            contact TEXT,
            email TEXT
        )
    ''')

    # PROJECTS
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            location TEXT,
            start_date TEXT,
            end_date TEXT,
            vendor_id INTEGER,
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        )
    ''')

    # EMPLOYEES
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            email TEXT,
            phone TEXT
        )
    ''')

    # MEASUREMENT SHEETS
    c.execute('''
        CREATE TABLE IF NOT EXISTS measurement_sheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            created_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # MEASUREMENT ENTRIES
    c.execute('''
        CREATE TABLE IF NOT EXISTS measurement_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER,
            description TEXT,
            length REAL,
            breadth REAL,
            area REAL,
            FOREIGN KEY (sheet_id) REFERENCES measurement_sheet(id)
        )
    ''')

    # PRODUCTION
    c.execute('''
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            phase TEXT,
            completed_area REAL,
            total_area REAL,
            date TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')
    

    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Insert dummy user
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', 'admin123'))



    conn.commit()
    conn.close()
# ---------------------- DUMMY DATA INSERT ----------------------

def insert_dummy_data():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Insert dummy user if not exists
    hashed_pw = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("SELECT * FROM users WHERE username = ?", ('admin',))
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed_pw))

    # Insert dummy vendors
    vendors = [
        ('ABC Traders', 'ABC Pvt Ltd', '9876543210', 'abc@example.com'),
        ('XYZ Supply', 'XYZ Corp', '9123456780', 'xyz@example.com')
    ]
    for v in vendors:
        c.execute("SELECT * FROM vendors WHERE name = ?", (v[0],))
        if not c.fetchone():
            c.execute("INSERT INTO vendors (name, company, contact, email) VALUES (?, ?, ?, ?)", v)

    conn.commit()
    conn.close()


# ---------------------- LOGIN ----------------------

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


# ---------------------- REGISTER ----------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash('User registered successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'danger')
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')


# ---------------------- DASHBOARD ----------------------

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM projects")
    total_projects = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vendors")
    total_vendors = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM employees")
    total_employees = c.fetchone()[0]
    conn.close()

    return render_template('dashboard.html',
                           user=session['user'],
                           total_projects=total_projects,
                           total_vendors=total_vendors,
                           total_employees=total_employees)

# ---------------------- VENDOR REGISTRATION ----------------------

@app.route('/vendor_registration', methods=['GET', 'POST'])
def vendor_registration():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        company = request.form['company']
        contact = request.form['contact']
        email = request.form['email']

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("INSERT INTO vendors (name, company, contact, email) VALUES (?, ?, ?, ?)",
                  (name, company, contact, email))
        conn.commit()
        conn.close()

        flash("Vendor registered successfully!", "success")
        return redirect(url_for('vendors'))

    return render_template('vendor_registration.html')


# ---------------------- VENDOR LIST ----------------------

@app.route('/vendors')
def vendors():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM vendors")
    vendor_list = c.fetchall()
    conn.close()

    return render_template('vendors.html', vendors=vendor_list)


# ---------------------- EXPORT VENDORS TO EXCEL ----------------------

@app.route('/export/vendors/excel')
def export_vendors_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendors')

    output.seek(0)
    return send_file(output, download_name="vendors.xlsx", as_attachment=True)


# ---------------------- EXPORT VENDORS TO PDF ----------------------

@app.route('/export/vendors/pdf')
def export_vendors_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM vendors")
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y, "Vendor List")
    y -= 30

    p.setFont("Helvetica", 10)
    for row in data:
        row_text = f"ID: {row[0]} | Name: {row[1]} | Company: {row[2]} | Contact: {row[3]} | Email: {row[4]}"
        p.drawString(30, y, row_text)
        y -= 20
        if y < 40:
            p.showPage()
            y = height - 40

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="vendors.pdf", as_attachment=True)

# ---------------------- PROJECT SELECTOR ----------------------

@app.route('/project_selector')
def project_selector():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM projects")
    projects = c.fetchall()
    conn.close()
    return render_template('project_selector.html', projects=projects)


# ---------------------- PROJECTS MANAGEMENT ----------------------

@app.route('/projects', methods=['GET', 'POST'])
def projects():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        client = request.form['client']
        location = request.form['location']
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        c.execute('''INSERT INTO projects (name, client, location, start_date, end_date)
                     VALUES (?, ?, ?, ?, ?)''', (name, client, location, start_date, end_date))
        conn.commit()
        flash("Project added successfully!", "success")
        return redirect(url_for('projects'))

    c.execute("SELECT * FROM projects")
    project_list = c.fetchall()
    conn.close()
    return render_template('projects.html', projects=project_list)


# ---------------------- EXPORT PROJECTS TO EXCEL ----------------------

@app.route('/export/projects/excel')
def export_projects_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')

    output.seek(0)
    return send_file(output, download_name="projects.xlsx", as_attachment=True)


# ---------------------- EXPORT PROJECTS TO PDF ----------------------

@app.route('/export/projects/pdf')
def export_projects_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM projects")
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y, "Project List")
    y -= 30

    p.setFont("Helvetica", 10)
    for row in data:
        row_text = f"ID: {row[0]} | Name: {row[1]} | Client: {row[2]} | Location: {row[3]} | Start: {row[4]} | End: {row[5]}"
        p.drawString(30, y, row_text)
        y -= 20
        if y < 40:
            p.showPage()
            y = height - 40

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="projects.pdf", as_attachment=True)

# ---------------------- EMPLOYEE REGISTRATION & LIST ----------------------

@app.route('/employees', methods=['GET', 'POST'])
def employees():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        c.execute('''INSERT INTO employees (name, role, username, password)
                     VALUES (?, ?, ?, ?)''', (name, role, username, password))
        conn.commit()
        flash("Employee registered successfully!", "success")
        return redirect(url_for('employees'))

    c.execute("SELECT * FROM employees")
    emp_list = c.fetchall()
    conn.close()
    return render_template('employees.html', employees=emp_list)


# ---------------------- EMPLOYEE EDIT ----------------------

@app.route('/employee_edit/<int:emp_id>', methods=['GET', 'POST'])
def employee_edit(emp_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        username = request.form['username']
        password = request.form['password']

        if password:
            hashed_pw = generate_password_hash(password)
            c.execute('''UPDATE employees SET name=?, role=?, username=?, password=? WHERE id=?''',
                      (name, role, username, hashed_pw, emp_id))
        else:
            c.execute('''UPDATE employees SET name=?, role=?, username=? WHERE id=?''',
                      (name, role, username, emp_id))
        conn.commit()
        flash("Employee updated!", "info")
        return redirect(url_for('employees'))

    c.execute("SELECT * FROM employees WHERE id=?", (emp_id,))
    emp = c.fetchone()
    conn.close()
    return render_template('employee_edit.html', employee=emp)


# ---------------------- EXPORT EMPLOYEES TO EXCEL ----------------------

@app.route('/export/employees/excel')
def export_employees_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT id, name, role, username FROM employees", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Employees')

    output.seek(0)
    return send_file(output, download_name="employees.xlsx", as_attachment=True)


# ---------------------- EXPORT EMPLOYEES TO PDF ----------------------

@app.route('/export/employees/pdf')
def export_employees_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT id, name, role, username FROM employees")
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y, "Employee List")
    y -= 30

    p.setFont("Helvetica", 10)
    for row in data:
        row_text = f"ID: {row[0]} | Name: {row[1]} | Role: {row[2]} | Username: {row[3]}"
        p.drawString(30, y, row_text)
        y -= 20
        if y < 40:
            p.showPage()
            y = height - 40

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="employees.pdf", as_attachment=True)

# ---------------------- MEASUREMENT SHEET ----------------------

@app.route('/measurement_sheet', methods=['GET', 'POST'])
def measurement_sheet():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        project_id = request.form['project_id']
        duct_type = request.form['duct_type']
        height = float(request.form['height'])
        width = float(request.form['width'])
        quantity = int(request.form['quantity'])

        area = (height * width * quantity) / 1000000  # in square meters

        c.execute('''INSERT INTO measurement_entries 
                     (project_id, duct_type, height, width, quantity, area)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (project_id, duct_type, height, width, quantity, area))
        conn.commit()
        flash("Measurement entry added!", "success")
        return redirect(url_for('measurement_sheet'))

    c.execute('''SELECT m.id, p.name, m.duct_type, m.height, m.width, m.quantity, m.area 
                 FROM measurement_entries m 
                 JOIN projects p ON m.project_id = p.id''')
    measurements = c.fetchall()

    c.execute("SELECT id, name FROM projects")
    projects = c.fetchall()
    conn.close()
    return render_template('measurement_sheet.html', measurements=measurements, projects=projects)


# ---------------------- MEASUREMENT EDIT ----------------------

@app.route('/measurement_edit/<int:entry_id>', methods=['GET', 'POST'])
def measurement_edit(entry_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        duct_type = request.form['duct_type']
        height = float(request.form['height'])
        width = float(request.form['width'])
        quantity = int(request.form['quantity'])
        area = (height * width * quantity) / 1000000

        c.execute('''UPDATE measurement_entries 
                     SET duct_type=?, height=?, width=?, quantity=?, area=? 
                     WHERE id=?''',
                  (duct_type, height, width, quantity, area, entry_id))
        conn.commit()
        flash("Measurement entry updated.", "info")
        return redirect(url_for('measurement_sheet'))

    c.execute("SELECT * FROM measurement_entries WHERE id=?", (entry_id,))
    entry = c.fetchone()
    conn.close()
    return render_template('measurement_edit.html', entry=entry)


# ---------------------- EXPORT MEASUREMENTS TO EXCEL ----------------------

@app.route('/export/measurements/excel')
def export_measurements_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('''SELECT m.id, p.name as project, m.duct_type, m.height, m.width, m.quantity, m.area 
                              FROM measurement_entries m 
                              JOIN projects p ON m.project_id = p.id''', conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Measurements')

    output.seek(0)
    return send_file(output, download_name="measurements.xlsx", as_attachment=True)


# ---------------------- EXPORT MEASUREMENTS TO PDF ----------------------

@app.route('/export/measurements/pdf')
def export_measurements_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''SELECT m.id, p.name, m.duct_type, m.height, m.width, m.quantity, m.area 
                 FROM measurement_entries m 
                 JOIN projects p ON m.project_id = p.id''')
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y, "Measurement Sheet")
    y -= 30

    p.setFont("Helvetica", 9)
    for row in data:
        text = f"ID:{row[0]} | Project:{row[1]} | Duct:{row[2]} | H:{row[3]} | W:{row[4]} | Qty:{row[5]} | Area:{round(row[6],2)} m²"
        p.drawString(30, y, text)
        y -= 18
        if y < 40:
            p.showPage()
            y = height - 40

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="measurements.pdf", as_attachment=True)

# ---------------------- PRODUCTION MODULE ----------------------

@app.route('/production_selector', methods=['GET', 'POST'])
def production_selector():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Insert progress
    if request.method == 'POST':
        project_id = request.form['project_id']
        duct_type = request.form['duct_type']
        phase = request.form['phase']
        completed_area = float(request.form['completed_area'])

        c.execute('''SELECT total_area FROM measurement_summary 
                     WHERE project_id=? AND duct_type=?''', (project_id, duct_type))
        result = c.fetchone()
        if result:
            total_area = result[0]
        else:
            total_area = 1  # prevent division by zero if missing

        percentage = round((completed_area / total_area) * 100, 2)

        c.execute('''INSERT INTO production 
                     (project_id, duct_type, phase, completed_area, percentage) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (project_id, duct_type, phase, completed_area, percentage))
        conn.commit()
        flash("Production updated.", "success")
        return redirect(url_for('production_selector'))

    c.execute('''SELECT p.id, p.name FROM projects p''')
    projects = c.fetchall()

    c.execute('''SELECT pr.id, pj.name, pr.duct_type, pr.phase, pr.completed_area, pr.percentage 
                 FROM production pr
                 JOIN projects pj ON pr.project_id = pj.id''')
    records = c.fetchall()
    conn.close()

    return render_template('production.html', projects=projects, records=records)


# ---------------------- EXPORT PRODUCTION TO EXCEL ----------------------

@app.route('/export/production/excel')
def export_production_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('''SELECT pj.name AS project, pr.duct_type, pr.phase, 
                                     pr.completed_area, pr.percentage
                              FROM production pr
                              JOIN projects pj ON pr.project_id = pj.id''', conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Production Status')

    output.seek(0)
    return send_file(output, download_name="production.xlsx", as_attachment=True)


# ---------------------- EXPORT PRODUCTION TO PDF ----------------------

@app.route('/export/production/pdf')
def export_production_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''SELECT pj.name, pr.duct_type, pr.phase, pr.completed_area, pr.percentage 
                 FROM production pr
                 JOIN projects pj ON pr.project_id = pj.id''')
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y, "Production Progress")
    y -= 30

    p.setFont("Helvetica", 9)
    for row in data:
        line = f"Project: {row[0]} | Duct: {row[1]} | Phase: {row[2]} | Done: {row[3]} m² | {row[4]}%"
        p.drawString(30, y, line)
        y -= 18
        if y < 40:
            p.showPage()
            y = height - 40

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="production.pdf", as_attachment=True)


# ---------------------- REVIEW MODULE ----------------------

@app.route('/review')
def review():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    c.execute('''SELECT p.id, p.name FROM projects p''')
    projects = c.fetchall()

    c.execute('''SELECT m.project_id, p.name, m.duct_type, m.total_area 
                 FROM measurement_summary m
                 JOIN projects p ON m.project_id = p.id''')
    measurements = c.fetchall()

    c.execute('''SELECT project_id, duct_type, phase, completed_area, percentage 
                 FROM production''')
    productions = c.fetchall()

    conn.close()

    return render_template('review.html', projects=projects,
                           measurements=measurements,
                           productions=productions)


# ---------------------- SUMMARY MODULE ----------------------

@app.route('/summary')
def summary():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    c.execute('''SELECT pj.name, ms.duct_type, 
                        COALESCE(SUM(pr.percentage), 0) / COUNT(DISTINCT pr.phase) AS avg_progress
                 FROM measurement_summary ms
                 JOIN projects pj ON ms.project_id = pj.id
                 LEFT JOIN production pr ON ms.project_id = pr.project_id AND ms.duct_type = pr.duct_type
                 GROUP BY ms.project_id, ms.duct_type''')
    summary = c.fetchall()
    conn.close()

    return render_template('summary.html', summary=summary)


# ---------------------- EXPORT SUMMARY TO EXCEL ----------------------

@app.route('/export/summary/excel')
def export_summary_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('''SELECT pj.name AS project, ms.duct_type, 
                                     COALESCE(SUM(pr.percentage), 0) / COUNT(DISTINCT pr.phase) AS avg_progress
                              FROM measurement_summary ms
                              JOIN projects pj ON ms.project_id = pj.id
                              LEFT JOIN production pr ON ms.project_id = pr.project_id AND ms.duct_type = pr.duct_type
                              GROUP BY ms.project_id, ms.duct_type''', conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Summary')

    output.seek(0)
    return send_file(output, download_name="summary.xlsx", as_attachment=True)


# ---------------------- EXPORT SUMMARY TO PDF ----------------------

@app.route('/export/summary/pdf')
def export_summary_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''SELECT pj.name, ms.duct_type, 
                        COALESCE(SUM(pr.percentage), 0) / COUNT(DISTINCT pr.phase) AS avg_progress
                 FROM measurement_summary ms
                 JOIN projects pj ON ms.project_id = pj.id
                 LEFT JOIN production pr ON ms.project_id = pr.project_id AND ms.duct_type = pr.duct_type
                 GROUP BY ms.project_id, ms.duct_type''')
    rows = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y, "Project Summary Overview")
    y -= 30

    p.setFont("Helvetica", 9)
    for row in rows:
        line = f"Project: {row[0]} | Duct: {row[1]} | Avg Progress: {round(row[2], 2)}%"
        p.drawString(30, y, line)
        y -= 18
        if y < 40:
            p.showPage()
            y = height - 40

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="summary.pdf", as_attachment=True)

if __name__ == '__main__':
    init_db()
    insert_dummy_data()
    app.run(debug=True)
