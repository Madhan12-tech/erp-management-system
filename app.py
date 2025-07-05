from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import letter
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ---------- DATABASE SETUP ----------

def init_db():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Vendors
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT,
            email TEXT
        )
    ''')

    # Projects
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            client TEXT,
            vendor_id INTEGER,
            start_date TEXT,
            end_date TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        )
    ''')

    # Employees
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            email TEXT,
            contact TEXT,
            password TEXT
        )
    ''')

    # Measurement Sheet
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS measurement_sheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            sheet_name TEXT,
            created_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # Measurement Entries
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS measurement_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER,
            area REAL,
            completed_area REAL,
            FOREIGN KEY (sheet_id) REFERENCES measurement_sheet(id)
        )
    ''')

    # Production
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER,
            phase TEXT,
            percentage_complete REAL,
            FOREIGN KEY (sheet_id) REFERENCES measurement_sheet(id)
        )
    ''')

    conn.commit()
    conn.close()


# ---------- DUMMY LOGIN USER ----------

def init_dummy_user():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_password = generate_password_hash("admin123")
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed_password))
        conn.commit()
    conn.close()

# ---------- DUMMY VENDOR DATA ----------

def init_dummy_vendors():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM vendors")
    if cursor.fetchone()[0] == 0:
        vendors = [
            ('Vendor A', '9876543210', 'vendorA@example.com'),
            ('Vendor B', '9123456789', 'vendorB@example.com'),
            ('Vendor C', '9001122334', 'vendorC@example.com')
        ]
        cursor.executemany("INSERT INTO vendors (name, contact, email) VALUES (?, ?, ?)", vendors)
        conn.commit()
    conn.close()

# ---------- RUN INITIALIZATIONS ----------

init_db()
init_dummy_user()
init_dummy_vendors()

# ---------- LOGIN ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM projects")
    total_projects = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM vendors")
    total_vendors = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM employees")
    total_employees = cursor.fetchone()[0]
    conn.close()

    return render_template('dashboard.html',
                           user=session['user'],
                           total_projects=total_projects,
                           total_vendors=total_vendors,
                           total_employees=total_employees)

# ---------- VENDOR REGISTRATION ----------
@app.route('/register_vendor', methods=['GET', 'POST'])
def register_vendor():
    if request.method == 'POST':
        name = request.form['name']
        company = request.form['company']
        contact = request.form['contact']
        email = request.form['email']
        address = request.form['address']
        
        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO vendors (name, company, contact, email, address)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, company, contact, email, address))
        conn.commit()
        conn.close()

        flash('Vendor registered successfully.', 'success')
        return redirect(url_for('vendors'))
    
    return render_template('vendor_register.html')


# ---------- VENDOR LIST ----------
@app.route('/vendors')
def vendors():
    search_query = request.args.get('search', '')

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    if search_query:
        cursor.execute("SELECT * FROM vendors WHERE name LIKE ?", ('%' + search_query + '%',))
    else:
        cursor.execute("SELECT * FROM vendors")
    vendors = cursor.fetchall()
    conn.close()

    return render_template('vendors.html', vendors=vendors, search_query=search_query)


# ---------- EXPORT VENDORS TO EXCEL ----------
@app.route('/vendors/export_excel')
def export_vendors_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Vendors')
    writer.close()
    output.seek(0)

    return send_file(output, download_name="vendors.xlsx", as_attachment=True)


# ---------- EXPORT VENDORS TO PDF ----------
@app.route('/vendors/export_pdf')
def export_vendors_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors")
    vendors = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, y, "Vendor List")
    y -= 30
    p.setFont("Helvetica", 10)
    for v in vendors:
        text = f"{v[1]} | {v[2]} | {v[3]} | {v[4]} | {v[5]}"
        p.drawString(40, y, text)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 40
    p.save()
    buffer.seek(0)

    return send_file(buffer, download_name="vendors.pdf", as_attachment=True)

# ---------- EMPLOYEE REGISTRATION ----------
@app.route('/register_employee', methods=['GET', 'POST'])
def register_employee():
    if request.method == 'POST':
        name = request.form['name']
        department = request.form['department']
        contact = request.form['contact']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO employees (name, department, contact, email, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, department, contact, email, username, hashed_password))
        conn.commit()
        conn.close()

        flash('Employee registered successfully.', 'success')
        return redirect(url_for('employees'))

    return render_template('employee_register.html')


# ---------- EMPLOYEE LIST ----------
@app.route('/employees')
def employees():
    search_query = request.args.get('search', '')

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    if search_query:
        cursor.execute("SELECT * FROM employees WHERE name LIKE ?", ('%' + search_query + '%',))
    else:
        cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    conn.close()

    return render_template('employees.html', employees=employees, search_query=search_query)


# ---------- EXPORT EMPLOYEES TO EXCEL ----------
@app.route('/employees/export_excel')
def export_employees_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM employees", conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Employees')
    writer.close()
    output.seek(0)

    return send_file(output, download_name="employees.xlsx", as_attachment=True)


# ---------- EXPORT EMPLOYEES TO PDF ----------
@app.route('/employees/export_pdf')
def export_employees_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, y, "Employee List")
    y -= 30
    p.setFont("Helvetica", 10)
    for emp in employees:
        text = f"{emp[1]} | {emp[2]} | {emp[3]} | {emp[4]}"
        p.drawString(40, y, text)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 40
    p.save()
    buffer.seek(0)

    return send_file(buffer, download_name="employees.pdf", as_attachment=True)

# ---------- PROJECT MODULE ----------
@app.route('/projects', methods=['GET', 'POST'])
def project_selector():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Dummy vendor dropdown
    cursor.execute("SELECT name FROM vendors")
    vendors = [row[0] for row in cursor.fetchall()]

    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        vendor = request.form['vendor']

        cursor.execute('''
            INSERT INTO projects (name, location, start_date, end_date, vendor)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, location, start_date, end_date, vendor))
        conn.commit()
        flash('Project added successfully!', 'success')
        return redirect(url_for('project_selector'))

    search_query = request.args.get('search', '')
    if search_query:
        cursor.execute("SELECT * FROM projects WHERE name LIKE ?", ('%' + search_query + '%',))
    else:
        cursor.execute("SELECT * FROM projects")
    projects = cursor.fetchall()
    conn.close()

    return render_template('projects.html', projects=projects, vendors=vendors, search_query=search_query)


# ---------- EXPORT PROJECTS TO EXCEL ----------
@app.route('/projects/export_excel')
def export_projects_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Projects')
    writer.close()
    output.seek(0)

    return send_file(output, download_name="projects.xlsx", as_attachment=True)


# ---------- EXPORT PROJECTS TO PDF ----------
@app.route('/projects/export_pdf')
def export_projects_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects")
    projects = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, y, "Project List")
    y -= 30
    p.setFont("Helvetica", 10)
    for proj in projects:
        text = f"{proj[1]} | {proj[2]} | {proj[3]} to {proj[4]} | Vendor: {proj[5]}"
        p.drawString(40, y, text)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 40
    p.save()
    buffer.seek(0)

    return send_file(buffer, download_name="projects.pdf", as_attachment=True)

# ---------- DUCT ENTRY ----------
@app.route('/duct_entry', methods=['GET', 'POST'])
def duct_entry():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Dummy project & vendor list
    cursor.execute("SELECT name FROM projects")
    project_names = [row[0] for row in cursor.fetchall()]

    if request.method == 'POST':
        project_name = request.form['project_name']
        duct_type = request.form['duct_type']
        material = request.form['material']
        quantity = request.form['quantity']
        area = request.form['area']
        remarks = request.form['remarks']

        cursor.execute('''
            INSERT INTO ducts (project_name, duct_type, material, quantity, area, remarks)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_name, duct_type, material, quantity, area, remarks))
        conn.commit()
        flash('Duct entry added successfully!', 'success')
        return redirect(url_for('duct_entry'))

    search_query = request.args.get('search', '')
    if search_query:
        cursor.execute("SELECT * FROM ducts WHERE project_name LIKE ?", ('%' + search_query + '%',))
    else:
        cursor.execute("SELECT * FROM ducts")
    ducts = cursor.fetchall()
    conn.close()

    return render_template('duct_entry.html', ducts=ducts, project_names=project_names, search_query=search_query)


# ---------- EXPORT DUCTS TO EXCEL ----------
@app.route('/ducts/export_excel')
def export_ducts_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM ducts", conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Duct Entries')
    writer.close()
    output.seek(0)

    return send_file(output, download_name="duct_entries.xlsx", as_attachment=True)


# ---------- EXPORT DUCTS TO PDF ----------
@app.route('/ducts/export_pdf')
def export_ducts_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ducts")
    ducts = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(180, y, "Duct Entry List")
    y -= 30
    p.setFont("Helvetica", 10)
    for duct in ducts:
        text = f"{duct[1]} | {duct[2]} | {duct[3]} | Qty: {duct[4]} | Area: {duct[5]} | {duct[6]}"
        p.drawString(40, y, text)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 40
    p.save()
    buffer.seek(0)

    return send_file(buffer, download_name="duct_entries.pdf", as_attachment=True)

# ---------- MEASUREMENT SHEET POPUP + CALC ----------
@app.route('/measurement_sheet', methods=['GET', 'POST'])
def measurement_sheet():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Dummy project list
    cursor.execute("SELECT id, name FROM projects")
    projects = cursor.fetchall()

    if request.method == 'POST':
        project_id = request.form['project_id']
        entry_type = request.form['entry_type']
        length = float(request.form['length'])
        width = float(request.form['width'])
        area = length * width

        cursor.execute('''
            INSERT INTO measurement_entries (project_id, entry_type, length, width, area)
            VALUES (?, ?, ?, ?, ?)
        ''', (project_id, entry_type, length, width, area))
        conn.commit()
        flash("Measurement entry added", "success")
        return redirect(url_for('measurement_sheet'))

    search_project = request.args.get('project_id')
    if search_project:
        cursor.execute('''
            SELECT me.id, p.name, me.entry_type, me.length, me.width, me.area
            FROM measurement_entries me
            JOIN projects p ON me.project_id = p.id
            WHERE p.id = ?
        ''', (search_project,))
    else:
        cursor.execute('''
            SELECT me.id, p.name, me.entry_type, me.length, me.width, me.area
            FROM measurement_entries me
            JOIN projects p ON me.project_id = p.id
        ''')
    entries = cursor.fetchall()
    conn.close()

    return render_template('measurement_sheet.html', entries=entries, projects=projects, search_project=search_project)


# ---------- EXPORT MEASUREMENT SHEET TO EXCEL ----------
@app.route('/measurement/export_excel')
def export_measurement_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('''
        SELECT p.name as project_name, me.entry_type, me.length, me.width, me.area
        FROM measurement_entries me
        JOIN projects p ON me.project_id = p.id
    ''', conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Measurements')
    writer.close()
    output.seek(0)

    return send_file(output, download_name="measurement_sheet.xlsx", as_attachment=True)


# ---------- EXPORT MEASUREMENT SHEET TO PDF ----------
@app.route('/measurement/export_pdf')
def export_measurement_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.name, me.entry_type, me.length, me.width, me.area
        FROM measurement_entries me
        JOIN projects p ON me.project_id = p.id
    ''')
    data = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    p.setFont("Helvetica-Bold", 14)
    p.drawString(170, y, "Measurement Sheet")
    y -= 30
    p.setFont("Helvetica", 10)

    for row in data:
        p.drawString(40, y, f"Project: {row[0]}, Type: {row[1]}, L: {row[2]}, W: {row[3]}, Area: {row[4]}")
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 40
    p.save()
    buffer.seek(0)

    return send_file(buffer, download_name="measurement_sheet.pdf", as_attachment=True)

# ---------- PRODUCTION MODULE ----------
@app.route('/production', methods=['GET', 'POST'])
def production():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get all projects
    cursor.execute("SELECT id, name FROM projects")
    projects = cursor.fetchall()

    if request.method == 'POST':
        project_id = request.form['project_id']
        phase = request.form['phase']
        completed_area = float(request.form['completed_area'])

        # Insert or update progress
        cursor.execute('''
            INSERT INTO production (project_id, phase, completed_area)
            VALUES (?, ?, ?)
        ''', (project_id, phase, completed_area))
        conn.commit()
        flash("Production progress updated", "success")
        return redirect(url_for('production'))

    selected_project = request.args.get('project_id')
    if selected_project:
        cursor.execute('''
            SELECT id, project_id, phase, completed_area
            FROM production
            WHERE project_id = ?
        ''', (selected_project,))
    else:
        cursor.execute('SELECT id, project_id, phase, completed_area FROM production')
    progress = cursor.fetchall()

    conn.close()
    return render_template('production.html', projects=projects, progress=progress, selected_project=selected_project)


# ---------- EXPORT PRODUCTION DATA TO EXCEL ----------
@app.route('/production/export_excel')
def export_production_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('''
        SELECT p.name as project_name, pr.phase, pr.completed_area
        FROM production pr
        JOIN projects p ON pr.project_id = p.id
    ''', conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Production')
    writer.close()
    output.seek(0)

    return send_file(output, download_name="production_progress.xlsx", as_attachment=True)


# ---------- EXPORT PRODUCTION DATA TO PDF ----------
@app.route('/production/export_pdf')
def export_production_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.name, pr.phase, pr.completed_area
        FROM production pr
        JOIN projects p ON pr.project_id = p.id
    ''')
    data = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    p.setFont("Helvetica-Bold", 14)
    p.drawString(180, y, "Production Progress")
    y -= 30
    p.setFont("Helvetica", 10)

    for row in data:
        p.drawString(40, y, f"Project: {row[0]}, Phase: {row[1]}, Area Done: {row[2]} sqm")
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 40
    p.save()
    buffer.seek(0)

    return send_file(buffer, download_name="production_progress.pdf", as_attachment=True)

# ---------- DESIGN PROCESS ----------
@app.route('/design_process', methods=['GET', 'POST'])
def design_process():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Fetch projects
    cursor.execute("SELECT id, name FROM projects")
    projects = cursor.fetchall()

    if request.method == 'POST':
        project_id = request.form['project_id']
        drawing_done = request.form.get('drawing_done', 0)
        approval_done = request.form.get('approval_done', 0)
        design_ready = request.form.get('design_ready', 0)

        cursor.execute('''
            INSERT OR REPLACE INTO design_process (project_id, drawing_done, approval_done, design_ready)
            VALUES (?, ?, ?, ?)
        ''', (project_id, drawing_done, approval_done, design_ready))
        conn.commit()
        flash("Design process updated", "success")
        return redirect(url_for('design_process'))

    cursor.execute('''
        SELECT dp.id, p.name, dp.drawing_done, dp.approval_done, dp.design_ready
        FROM design_process dp
        JOIN projects p ON dp.project_id = p.id
    ''')
    design_data = cursor.fetchall()
    conn.close()

    return render_template('design_process.html', projects=projects, design_data=design_data)


# ---------- EXPORT DESIGN PROCESS TO EXCEL ----------
@app.route('/design_process/export_excel')
def export_design_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('''
        SELECT p.name as project_name, dp.drawing_done, dp.approval_done, dp.design_ready
        FROM design_process dp
        JOIN projects p ON dp.project_id = p.id
    ''', conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='DesignProcess')
    writer.close()
    output.seek(0)

    return send_file(output, download_name="design_process.xlsx", as_attachment=True)


# ---------- EXPORT DESIGN PROCESS TO PDF ----------
@app.route('/design_process/export_pdf')
def export_design_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.name, dp.drawing_done, dp.approval_done, dp.design_ready
        FROM design_process dp
        JOIN projects p ON dp.project_id = p.id
    ''')
    data = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    p.setFont("Helvetica-Bold", 14)
    p.drawString(180, y, "Design Process Report")
    y -= 30
    p.setFont("Helvetica", 10)

    for row in data:
        p.drawString(40, y, f"Project: {row[0]}, Drawing: {row[1]}, Approval: {row[2]}, Ready: {row[3]}")
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 40
    p.save()
    buffer.seek(0)

    return send_file(buffer, download_name="design_process.pdf", as_attachment=True)

# ---------- MEASUREMENT SHEET ENTRY ----------
@app.route('/measurement_sheet', methods=['GET', 'POST'])
def measurement_sheet():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Fetch project list for dropdown
    cursor.execute("SELECT id, name FROM projects")
    projects = cursor.fetchall()

    if request.method == 'POST':
        project_id = request.form['project_id']
        date = request.form['date']
        remarks = request.form['remarks']
        cursor.execute('''
            INSERT INTO measurement_sheet (project_id, date, remarks)
            VALUES (?, ?, ?)
        ''', (project_id, date, remarks))
        conn.commit()
        flash("Measurement sheet created.", "success")
        return redirect(url_for('measurement_sheet'))

    # List all measurement sheets with project name
    cursor.execute('''
        SELECT m.id, p.name, m.date, m.remarks
        FROM measurement_sheet m
        JOIN projects p ON m.project_id = p.id
        ORDER BY m.id DESC
    ''')
    sheets = cursor.fetchall()
    conn.close()
    return render_template('measurement_sheet.html', projects=projects, sheets=sheets)


# ---------- ADD ENTRY TO A MEASUREMENT SHEET ----------
@app.route('/measurement_entry/<int:sheet_id>', methods=['GET', 'POST'])
def measurement_entry(sheet_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        location = request.form['location']
        length = float(request.form['length'])
        width = float(request.form['width'])
        height = float(request.form['height'])
        area = round(length * width, 2)

        cursor.execute('''
            INSERT INTO measurement_entries (sheet_id, location, length, width, height, area)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (sheet_id, location, length, width, height, area))
        conn.commit()
        flash("Measurement entry added.", "success")
        return redirect(url_for('measurement_entry', sheet_id=sheet_id))

    # Get all entries of this sheet
    cursor.execute('''
        SELECT location, length, width, height, area
        FROM measurement_entries
        WHERE sheet_id = ?
    ''', (sheet_id,))
    entries = cursor.fetchall()
    conn.close()
    return render_template('measurement_entry.html', sheet_id=sheet_id, entries=entries)

# ---------- EXPORT MEASUREMENT SHEET TO EXCEL ----------
@app.route('/export_measurement_excel')
def export_measurement_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('''
        SELECT m.id AS SheetID, p.name AS ProjectName, m.date, m.remarks,
               e.location, e.length, e.width, e.height, e.area
        FROM measurement_sheet m
        JOIN projects p ON m.project_id = p.id
        LEFT JOIN measurement_entries e ON m.id = e.sheet_id
    ''', conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='MeasurementSheet')
    writer.close()
    output.seek(0)
    return send_file(output, download_name="Measurement_Sheet.xlsx", as_attachment=True)


# ---------- EXPORT MEASUREMENT SHEET TO PDF ----------
@app.route('/export_measurement_pdf')
def export_measurement_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.id, p.name, m.date, m.remarks, e.location, e.length, e.width, e.height, e.area
        FROM measurement_sheet m
        JOIN projects p ON m.project_id = p.id
        LEFT JOIN measurement_entries e ON m.id = e.sheet_id
    ''')
    records = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica", 10)

    c.drawString(50, y, "Measurement Sheet Report")
    y -= 20

    for row in records:
        line = f"SheetID: {row[0]}, Project: {row[1]}, Date: {row[2]}, Remarks: {row[3]}, " \
               f"Location: {row[4]}, L:{row[5]}, W:{row[6]}, H:{row[7]}, Area:{row[8]}"
        c.drawString(30, y, line)
        y -= 15
        if y < 40:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 50

    c.save()
    buffer.seek(0)
    return send_file(buffer, download_name='MeasurementSheet.pdf', as_attachment=True)


# ---------- PRODUCTION MODULE ----------
@app.route('/production')
def production():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.id, p.name,
               IFNULL(SUM(CASE WHEN ph.phase = 'Sheet Cutting' THEN ph.completed_area ELSE 0 END), 0) as cutting_done,
               IFNULL(SUM(CASE WHEN ph.phase = 'Plasma and Fabrication' THEN ph.completed_area ELSE 0 END), 0) as fabrication_done,
               IFNULL(SUM(CASE WHEN ph.phase = 'Boxing and Assembly' THEN ph.completed_area ELSE 0 END), 0) as assembly_done,
               IFNULL(SUM(CASE WHEN ph.phase = 'Quality Checking' THEN ph.percentage ELSE 0 END), 0) as qc_percent,
               IFNULL(SUM(CASE WHEN ph.phase = 'Dispatch' THEN ph.percentage ELSE 0 END), 0) as dispatch_percent,
               IFNULL(SUM(ms.area), 0) as total_area
        FROM projects p
        LEFT JOIN measurement_sheet ms ON p.id = ms.project_id
        LEFT JOIN production ph ON ms.id = ph.sheet_id
        GROUP BY p.id
    ''')
    data = cursor.fetchall()
    conn.close()
    return render_template('production.html', data=data)


@app.route('/update_production', methods=['POST'])
def update_production():
    sheet_id = request.form['sheet_id']
    phase = request.form['phase']
    area = request.form.get('completed_area', None)
    percent = request.form.get('percentage', None)

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Check if the entry already exists
    cursor.execute('SELECT id FROM production WHERE sheet_id = ? AND phase = ?', (sheet_id, phase))
    existing = cursor.fetchone()

    if existing:
        if phase in ['Quality Checking', 'Dispatch']:
            cursor.execute('UPDATE production SET percentage = ? WHERE id = ?', (percent, existing[0]))
        else:
            cursor.execute('UPDATE production SET completed_area = ? WHERE id = ?', (area, existing[0]))
    else:
        if phase in ['Quality Checking', 'Dispatch']:
            cursor.execute('INSERT INTO production (sheet_id, phase, percentage) VALUES (?, ?, ?)', (sheet_id, phase, percent))
        else:
            cursor.execute('INSERT INTO production (sheet_id, phase, completed_area) VALUES (?, ?, ?)', (sheet_id, phase, area))

    conn.commit()
    conn.close()
    flash('Production updated successfully.')
    return redirect(url_for('production'))

# ---------- PRODUCTION EXPORT ----------
@app.route('/production/export/excel')
def export_production_excel():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.name AS project,
               ms.sheet_number,
               pr.phase,
               pr.completed_area,
               pr.percentage
        FROM production pr
        JOIN measurement_sheet ms ON pr.sheet_id = ms.id
        JOIN projects p ON ms.project_id = p.id
    ''')
    rows = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=['Project', 'Sheet Number', 'Phase', 'Completed Area', 'Percentage'])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Production')

    output.seek(0)
    return send_file(output, download_name="production.xlsx", as_attachment=True)


@app.route('/production/export/pdf')
def export_production_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.name AS project,
               ms.sheet_number,
               pr.phase,
               pr.completed_area,
               pr.percentage
        FROM production pr
        JOIN measurement_sheet ms ON pr.sheet_id = ms.id
        JOIN projects p ON ms.project_id = p.id
    ''')
    rows = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, height - 30, "Production Report")

    y = height - 60
    p.setFont("Helvetica", 10)
    headers = ['Project', 'Sheet', 'Phase', 'Area', 'Percent']
    for i, header in enumerate(headers):
        p.drawString(30 + i*100, y, header)
    y -= 20

    for row in rows:
        for i, item in enumerate(row):
            p.drawString(30 + i*100, y, str(item))
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 60

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="production.pdf", as_attachment=True)

# ---------- PRODUCTION SEARCH FILTER ----------
@app.route('/production/search', methods=['GET', 'POST'])
def search_production():
    if request.method == 'POST':
        keyword = request.form['search']
        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pr.id, p.name, ms.sheet_number, pr.phase, pr.completed_area, pr.percentage
            FROM production pr
            JOIN measurement_sheet ms ON pr.sheet_id = ms.id
            JOIN projects p ON ms.project_id = p.id
            WHERE p.name LIKE ? OR pr.phase LIKE ?
        ''', (f'%{keyword}%', f'%{keyword}%'))
        results = cursor.fetchall()
        conn.close()
        return render_template('production.html', production_data=results, search=keyword)
    return redirect(url_for('production_selector'))


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ---------- INITIATE DATABASE ----------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
