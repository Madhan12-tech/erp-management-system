from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

DB_NAME = 'erp_system.db'

# ---------- Database Initialization ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()


    # Users (employees) table
    c.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        designation TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')

    # Vendors table
    c.execute('''
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        company TEXT,
        email TEXT UNIQUE,
        phone TEXT
    )
    ''')

    # Projects table
    c.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enquiry_id TEXT UNIQUE NOT NULL,
        client_name TEXT,
        project_location TEXT,
        start_date TEXT,
        end_date TEXT,
        source_drawing TEXT,
        incharge TEXT,
        approval_status TEXT DEFAULT 'Pending',
        remarks TEXT
    )
    ''')

    # Ducts table (measurement entries)
    c.execute('''
    CREATE TABLE IF NOT EXISTS ducts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        duct_no TEXT,
        duct_type TEXT,
        duct_size TEXT,
        quantity INTEGER,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    # Production progress table
    c.execute('''
    CREATE TABLE IF NOT EXISTS production (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        sheet_cutting_done REAL DEFAULT 0,
        plasma_fabrication_done REAL DEFAULT 0,
        boxing_assembly_done REAL DEFAULT 0,
        quality_checking_done REAL DEFAULT 0,
        dispatch_done REAL DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    # Design process table
    c.execute('''
    CREATE TABLE IF NOT EXISTS design_process (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        status TEXT DEFAULT 'Not Started',
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    conn.commit()
    conn.close()

dummy_users = {
    "admin": "admin123",
    "user1": "pass123",
    "vendor1": "vendorpass"
}

# ---------- Dummy Data Insertion ----------
def insert_dummy_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Insert dummy employees with hashed passwords
    employees = [
        ('Madhan Kumar', 'Project Manager', 'madhan@example.com', '9876543210', 'madhan', generate_password_hash('password123')),
        ('Anita Sharma', 'Engineer', 'anita@example.com', '9123456780', 'anita', generate_password_hash('pass456')),
    ]
    for e in employees:
        try:
            c.execute('INSERT INTO employees (name, designation, email, phone, username, password) VALUES (?, ?, ?, ?, ?, ?)', e)
        except:
            pass  # ignore if already exists

    # Insert dummy vendors
    vendors = [
        ('Vendor A', 'Company A', 'vendorA@example.com', '9123456789'),
        ('Vendor B', 'Company B', 'vendorB@example.com', '9876543211'),
    ]
    for v in vendors:
        try:
            c.execute('INSERT INTO vendors (name, company, email, phone) VALUES (?, ?, ?, ?)', v)
        except:
            pass

    # Insert dummy projects
    projects = [
        ('ENQ001', 'ABC Corp', 'Mumbai', '2025-01-01', '2025-03-01', 'drawing1.pdf', 'Madhan Kumar', 'Pending', None),
        ('ENQ002', 'XYZ Ltd', 'Delhi', '2025-02-01', '2025-04-01', None, 'Anita Sharma', 'Approved', 'Looks good.'),
    ]
    for p in projects:
        try:
            c.execute('INSERT INTO projects (enquiry_id, client_name, project_location, start_date, end_date, source_drawing, incharge, approval_status, remarks) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', p)
        except:
            pass

    # Insert dummy ducts
    ducts = [
        (1, 'D001', 'Rectangular', '100x50', 10),
        (1, 'D002', 'Circular', '50mm', 20),
        (2, 'D001', 'Rectangular', '150x75', 15),
    ]
    for d in ducts:
        try:
            c.execute('INSERT INTO ducts (project_id, duct_no, duct_type, duct_size, quantity) VALUES (?, ?, ?, ?, ?)', d)
        except:
            pass

    # Insert dummy production progress
    production = [
        (1, 50, 30, 20, 10, 0),
        (2, 100, 90, 80, 75, 50),
    ]
    for p in production:
        try:
            c.execute('INSERT INTO production (project_id, sheet_cutting_done, plasma_fabrication_done, boxing_assembly_done, quality_checking_done, dispatch_done) VALUES (?, ?, ?, ?, ?, ?)', p)
        except:
            pass

    # Insert dummy design process statuses
    design_processes = [
        (1, 'In Progress'),
        (2, 'Completed'),
    ]
    for d in design_processes:
        try:
            c.execute('INSERT INTO design_process (project_id, status) VALUES (?, ?)', d)
        except:
            pass

    conn.commit()
    conn.close()

# Initialize DB and insert dummy data at start
if not os.path.exists(DB_NAME):
    init_db()
    insert_dummy_data()

# ---------- Authentication Routes ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check dummy credentials
        if username in dummy_users and dummy_users[username] == password:
            session['user'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')

    return render_template('login.html')
@app.route('/register_vendor', methods=['GET', 'POST'])
def register_vendor():
    if request.method == 'POST':
        # handle form submission
        pass
    return render_template('register_vendor.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# ---------- Dashboard Route ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Pass user info if needed
    username = session['user']

    return render_template('dashboard.html', username=username)

# ---------- Home redirect to login ----------
@app.route('/')
def home():
    return redirect(url_for('login'))

# ---------- Vendor Routes ----------

@app.route('/vendors')
def vendors():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM vendors")
    vendor_rows = c.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendor_rows)

@app.route('/vendor/add', methods=['GET', 'POST'])
def add_vendor():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        company = request.form['company']
        email = request.form['email']
        phone = request.form['phone']

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO vendors (name, company, email, phone) VALUES (?, ?, ?, ?)", (name, company, email, phone))
            conn.commit()
            flash('Vendor added successfully!', 'success')
            return redirect(url_for('vendors'))
        except sqlite3.IntegrityError:
            flash('Error: Email must be unique!', 'danger')
        finally:
            conn.close()

    return render_template('vendor_form.html', action='Add')

@app.route('/vendor/edit/<int:vendor_id>', methods=['GET', 'POST'])
def edit_vendor(vendor_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        company = request.form['company']
        email = request.form['email']
        phone = request.form['phone']

        try:
            c.execute("UPDATE vendors SET name=?, company=?, email=?, phone=? WHERE id=?", (name, company, email, phone, vendor_id))
            conn.commit()
            flash('Vendor updated successfully!', 'success')
            return redirect(url_for('vendors'))
        except sqlite3.IntegrityError:
            flash('Error: Email must be unique!', 'danger')

    c.execute("SELECT * FROM vendors WHERE id=?", (vendor_id,))
    vendor = c.fetchone()
    conn.close()
    if not vendor:
        flash('Vendor not found.', 'warning')
        return redirect(url_for('vendors'))

    return render_template('vendor_form.html', vendor=vendor, action='Edit')

@app.route('/vendor/delete/<int:vendor_id>', methods=['POST'])
def delete_vendor(vendor_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM vendors WHERE id=?", (vendor_id,))
    conn.commit()
    conn.close()
    flash('Vendor deleted successfully!', 'success')
    return redirect(url_for('vendors'))

# ---------- Vendor Export Excel ----------
@app.route('/vendors/export/excel')
def export_vendors_excel():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT id, name, company, email, phone FROM vendors", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        vendors_df.to_excel(writer, index=False, sheet_name='Vendors')

    output.seek(0)
    return send_file(output, download_name="vendors.xlsx", as_attachment=True)

# ---------- Vendor Export PDF ----------
@app.route('/vendors/export/pdf')
def export_vendors_pdf():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, company, email, phone FROM vendors")
    vendors = c.fetchall()
    conn.close()

    output = BytesIO()
    p = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 50, "Vendor List")

    p.setFont("Helvetica", 10)
    y = height - 80
    headers = ["ID", "Name", "Company", "Email", "Phone"]
    col_widths = [30, 120, 120, 150, 100]

    x = 50
    for i, header in enumerate(headers):
        p.drawString(x, y, header)
        x += col_widths[i]
    y -= 20

    for row in vendors:
        x = 50
        for i, val in enumerate(row):
            p.drawString(x, y, str(val))
            x += col_widths[i]
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    output.seek(0)
    return send_file(output, download_name="vendors.pdf", as_attachment=True)

# ------------------ Employee Module ------------------

@app.route('/employees')
def employees():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    employees = conn.execute('SELECT * FROM employees').fetchall()
    conn.close()
    return render_template('employees.html', employees=employees)

@app.route('/employee/add', methods=['GET', 'POST'])
def add_employee():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        conn.execute(
            '''INSERT INTO employees (name, designation, email, phone, username, password)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (name, designation, email, phone, username, password)
        )
        conn.commit()
        conn.close()
        flash('Employee added successfully.', 'success')
        return redirect(url_for('employees'))
    return render_template('employee_add.html')

@app.route('/employee/edit/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    employee = conn.execute('SELECT * FROM employees WHERE id = ?', (id,)).fetchone()
    if not employee:
        flash('Employee not found.', 'danger')
        conn.close()
        return redirect(url_for('employees'))

    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password_raw = request.form['password']
        if password_raw.strip():
            password = generate_password_hash(password_raw)
            conn.execute(
                '''UPDATE employees SET name=?, designation=?, email=?, phone=?, username=?, password=? WHERE id=?''',
                (name, designation, email, phone, username, password, id)
            )
        else:
            conn.execute(
                '''UPDATE employees SET name=?, designation=?, email=?, phone=?, username=? WHERE id=?''',
                (name, designation, email, phone, username, id)
            )
        conn.commit()
        conn.close()
        flash('Employee updated successfully.', 'success')
        return redirect(url_for('employees'))

    conn.close()
    return render_template('employee_edit.html', row=employee)

@app.route('/employee/delete/<int:id>')
def delete_employee(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM employees WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Employee deleted successfully.', 'success')
    return redirect(url_for('employees'))

# Export employees to Excel
@app.route('/employees/export/excel')
def export_employees_excel():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    employees = conn.execute('SELECT id, name, designation, email, phone, username FROM employees').fetchall()
    conn.close()
    df = pd.DataFrame(employees, columns=['ID', 'Name', 'Designation', 'Email', 'Phone', 'Username'])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Employees')
    output.seek(0)
    return send_file(output, download_name="employees.xlsx", as_attachment=True)

# Export employees to PDF
@app.route('/employees/export/pdf')
def export_employees_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    employees = conn.execute('SELECT id, name, designation, email, phone, username FROM employees').fetchall()
    conn.close()
    output = BytesIO()
    p = SimpleDocTemplate(output, pagesize=letter)
    data = [['ID', 'Name', 'Designation', 'Email', 'Phone', 'Username']]
    for emp in employees:
        data.append(list(emp))
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#007bff')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME', (0,0),(-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0),(-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    elems = [table]
    p.build(elems)
    output.seek(0)
    return send_file(output, download_name="employees.pdf", as_attachment=True)

# Submit button simulation for employees module
@app.route('/employees/submit', methods=['POST'])
def submit_employees():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Implement submit logic here if needed
    flash('Employees data submitted successfully.', 'success')
    return redirect(url_for('employees'))


# ------------------ Projects Module ------------------

@app.route('/projects')
def projects():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM projects').fetchall()
    conn.close()
    return render_template('projects.html', projects=projects)

@app.route('/project/add', methods=['GET', 'POST'])
def add_project():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        enquiry_id = request.form['enquiry_id']
        client_name = request.form['client_name']
        location = request.form['location']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        incharge = request.form['incharge']
        status = request.form['status']
        source_drawing = None  # For simplicity, no file upload now

        conn = get_db_connection()
        conn.execute(
            '''INSERT INTO projects (enquiry_id, client_name, location, start_date, end_date, incharge, status, source_drawing)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (enquiry_id, client_name, location, start_date, end_date, incharge, status, source_drawing)
        )
        conn.commit()
        conn.close()
        flash('Project added successfully.', 'success')
        return redirect(url_for('projects'))
    return render_template('project_add.html')

@app.route('/project/edit/<int:id>', methods=['GET', 'POST'])
def edit_project(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (id,)).fetchone()
    if not project:
        flash('Project not found.', 'danger')
        conn.close()
        return redirect(url_for('projects'))

    if request.method == 'POST':
        enquiry_id = request.form['enquiry_id']
        client_name = request.form['client_name']
        location = request.form['location']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        incharge = request.form['incharge']
        status = request.form['status']
        # Source drawing edit skipped for now

        conn.execute(
            '''UPDATE projects SET enquiry_id=?, client_name=?, location=?, start_date=?, end_date=?, incharge=?, status=? WHERE id=?''',
            (enquiry_id, client_name, location, start_date, end_date, incharge, status, id)
        )
        conn.commit()
        conn.close()
        flash('Project updated successfully.', 'success')
        return redirect(url_for('projects'))

    conn.close()
    return render_template('project_edit.html', row=project)

@app.route('/project/delete/<int:id>')
def delete_project(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM projects WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Project deleted successfully.', 'success')
    return redirect(url_for('projects'))

# Export projects Excel
@app.route('/projects/export/excel')
def export_projects_excel():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    projects = conn.execute('SELECT id, enquiry_id, client_name, location, start_date, end_date, incharge, status FROM projects').fetchall()
    conn.close()
    df = pd.DataFrame(projects, columns=['ID', 'Enquiry ID', 'Client', 'Location', 'Start Date', 'End Date', 'Incharge', 'Status'])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')
    output.seek(0)
    return send_file(output, download_name="projects.xlsx", as_attachment=True)

# Export projects PDF
@app.route('/projects/export/pdf')
def export_projects_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    projects = conn.execute('SELECT id, enquiry_id, client_name, location, start_date, end_date, incharge, status FROM projects').fetchall()
    conn.close()
    output = BytesIO()
    p = SimpleDocTemplate(output, pagesize=letter)
    data = [['ID', 'Enquiry ID', 'Client', 'Location', 'Start Date', 'End Date', 'Incharge', 'Status']]
    for pr in projects:
        data.append(list(pr))
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#007bff')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME', (0,0),(-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0),(-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    p.build([table])
    output.seek(0)
    return send_file(output, download_name="projects.pdf", as_attachment=True)

# Submit projects (dummy)
@app.route('/projects/submit', methods=['POST'])
def submit_projects():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flash('Projects data submitted successfully.', 'success')
    return redirect(url_for('projects'))

@app.route('/review')
def review():
    # Example: Fetch project from DB or define dummy
    project = (1, 'Project ABC', 'Location XYZ')  # Replace with actual DB query
    return render_template('review.html', project=project)


if 'username' not in session:
    return redirect(url_for('login'))


# ------------------ Measurement Sheet Module ------------------

@app.route('/measurement_sheets')
def measurement_sheets():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    sheets = conn.execute('SELECT * FROM measurement_sheets').fetchall()
    conn.close()
    return render_template('measurement_sheets.html', sheets=sheets)

@app.route('/measurement_sheet/add', methods=['GET', 'POST'])
def add_measurement_sheet():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        project_id = request.form['project_id']
        gauge = request.form['gauge']
        sheet_area = request.form['sheet_area']
        conn = get_db_connection()
        conn.execute('INSERT INTO measurement_sheets (project_id, gauge, sheet_area) VALUES (?, ?, ?)',
                     (project_id, gauge, sheet_area))
        conn.commit()
        conn.close()
        flash('Measurement sheet added successfully.', 'success')
        return redirect(url_for('measurement_sheets'))
    conn = get_db_connection()
    projects = conn.execute('SELECT id, enquiry_id FROM projects').fetchall()
    conn.close()
    return render_template('measurement_sheet_add.html', projects=projects)

@app.route('/measurement_sheet/edit/<int:id>', methods=['GET', 'POST'])
def edit_measurement_sheet(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    sheet = conn.execute('SELECT * FROM measurement_sheets WHERE id = ?', (id,)).fetchone()
    projects = conn.execute('SELECT id, enquiry_id FROM projects').fetchall()
    if not sheet:
        flash('Measurement sheet not found.', 'danger')
        conn.close()
        return redirect(url_for('measurement_sheets'))

    if request.method == 'POST':
        project_id = request.form['project_id']
        gauge = request.form['gauge']
        sheet_area = request.form['sheet_area']
        conn.execute('UPDATE measurement_sheets SET project_id=?, gauge=?, sheet_area=? WHERE id=?',
                     (project_id, gauge, sheet_area, id))
        conn.commit()
        conn.close()
        flash('Measurement sheet updated successfully.', 'success')
        return redirect(url_for('measurement_sheets'))

    conn.close()
    return render_template('measurement_sheet_edit.html', row=sheet, projects=projects)

@app.route('/measurement_sheet/delete/<int:id>')
def delete_measurement_sheet(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM measurement_sheets WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Measurement sheet deleted successfully.', 'success')
    return redirect(url_for('measurement_sheets'))

# Export measurement sheets Excel
@app.route('/measurement_sheets/export/excel')
def export_measurement_sheets_excel():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    sheets = conn.execute('''
        SELECT ms.id, p.enquiry_id, ms.gauge, ms.sheet_area 
        FROM measurement_sheets ms
        JOIN projects p ON ms.project_id = p.id
    ''').fetchall()
    conn.close()
    df = pd.DataFrame(sheets, columns=['ID', 'Project Enquiry ID', 'Gauge', 'Sheet Area'])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='MeasurementSheets')
    output.seek(0)
    return send_file(output, download_name="measurement_sheets.xlsx", as_attachment=True)

# Export measurement sheets PDF
@app.route('/measurement_sheets/export/pdf')
def export_measurement_sheets_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    sheets = conn.execute('''
        SELECT ms.id, p.enquiry_id, ms.gauge, ms.sheet_area 
        FROM measurement_sheets ms
        JOIN projects p ON ms.project_id = p.id
    ''').fetchall()
    conn.close()
    output = BytesIO()
    p = SimpleDocTemplate(output, pagesize=letter)
    data = [['ID', 'Project Enquiry ID', 'Gauge', 'Sheet Area']]
    for row in sheets:
        data.append(list(row))
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#007bff')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME', (0,0),(-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0),(-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    p.build([table])
    output.seek(0)
    return send_file(output, download_name="measurement_sheets.pdf", as_attachment=True)

# Submit measurement sheets (dummy)
@app.route('/measurement_sheets/submit', methods=['POST'])
def submit_measurement_sheets():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flash('Measurement sheets data submitted successfully.', 'success')
    return redirect(url_for('measurement_sheets'))

# ------------------ Production Module ------------------

@app.route('/production')
def production():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    production_rows = conn.execute('SELECT * FROM production').fetchall()
    conn.close()
    return render_template('production.html', productions=production_rows)

@app.route('/production/add', methods=['GET', 'POST'])
def add_production():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    projects = conn.execute('SELECT id, enquiry_id FROM projects').fetchall()
    conn.close()

    if request.method == 'POST':
        project_id = request.form['project_id']
        phase = request.form['phase']
        completed_area = float(request.form['completed_area'])
        total_area = float(request.form['total_area'])
        percent_complete = round((completed_area / total_area) * 100, 2) if total_area > 0 else 0

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO production (project_id, phase, completed_area, total_area, percent_complete)
            VALUES (?, ?, ?, ?, ?)
        ''', (project_id, phase, completed_area, total_area, percent_complete))
        conn.commit()
        conn.close()
        flash('Production record added successfully.', 'success')
        return redirect(url_for('production'))

    return render_template('production_add.html', projects=projects)

@app.route('/production/edit/<int:id>', methods=['GET', 'POST'])
def edit_production(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    production_row = conn.execute('SELECT * FROM production WHERE id = ?', (id,)).fetchone()
    projects = conn.execute('SELECT id, enquiry_id FROM projects').fetchall()
    if not production_row:
        flash('Production record not found.', 'danger')
        conn.close()
        return redirect(url_for('production'))

    if request.method == 'POST':
        project_id = request.form['project_id']
        phase = request.form['phase']
        completed_area = float(request.form['completed_area'])
        total_area = float(request.form['total_area'])
        percent_complete = round((completed_area / total_area) * 100, 2) if total_area > 0 else 0

        conn.execute('''
            UPDATE production SET project_id=?, phase=?, completed_area=?, total_area=?, percent_complete=?
            WHERE id=?
        ''', (project_id, phase, completed_area, total_area, percent_complete, id))
        conn.commit()
        conn.close()
        flash('Production record updated successfully.', 'success')
        return redirect(url_for('production'))

    conn.close()
    return render_template('production_edit.html', row=production_row, projects=projects)

@app.route('/production/delete/<int:id>')
def delete_production(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM production WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Production record deleted successfully.', 'success')
    return redirect(url_for('production'))

# Export Production Excel
@app.route('/production/export/excel')
def export_production_excel():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    records = conn.execute('''
        SELECT p.id, pr.enquiry_id, p.phase, p.completed_area, p.total_area, p.percent_complete
        FROM production p
        JOIN projects pr ON p.project_id = pr.id
    ''').fetchall()
    conn.close()
    df = pd.DataFrame(records, columns=['ID', 'Project Enquiry ID', 'Phase', 'Completed Area', 'Total Area', 'Percent Complete'])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Production')
    output.seek(0)
    return send_file(output, download_name="production.xlsx", as_attachment=True)

# Export Production PDF
@app.route('/production/export/pdf')
def export_production_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    records = conn.execute('''
        SELECT p.id, pr.enquiry_id, p.phase, p.completed_area, p.total_area, p.percent_complete
        FROM production p
        JOIN projects pr ON p.project_id = pr.id
    ''').fetchall()
    conn.close()
    output = BytesIO()
    p = SimpleDocTemplate(output, pagesize=letter)
    data = [['ID', 'Project Enquiry ID', 'Phase', 'Completed Area', 'Total Area', 'Percent Complete']]
    for row in records:
        data.append(list(row))
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#007bff')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME', (0,0),(-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0),(-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    p.build([table])
    output.seek(0)
    return send_file(output, download_name="production.pdf", as_attachment=True)

# Submit production (dummy)
@app.route('/production/submit', methods=['POST'])
def submit_production():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flash('Production data submitted successfully.', 'success')
    return redirect(url_for('production'))

# ------------------ Summary Module ------------------

@app.route('/summary')
def summary():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    projects = conn.execute('SELECT id, enquiry_id FROM projects').fetchall()
    conn.close()
    return render_template('summary.html', projects=projects)

@app.route('/get_summary_data/<int:project_id>')
def get_summary_data(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Project info
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        conn.close()
        return jsonify({})

    # Dummy client and incharge names for example
    client = "ABC Client"
    project_incharge = project['incharge']

    # Dummy source drawing filename
    source_drawing = project['source_drawing'] if 'source_drawing' in project.keys() else None

    # Gauge summary dummy data (simulate actual calculation)
    gauge_summary = {
        '16 Gauge': 120.5,
        '18 Gauge': 95.0,
        '20 Gauge': 75.3
    }

    # Production stage percentages dummy data
    stages = {
        'cutting': 70,
        'plasma': 60,
        'boxing': 50,
        'qc': 40,
        'dispatch': 30
    }

    conn.close()

    return jsonify({
        'client': client,
        'project_incharge': project_incharge,
        'start_date': project['start_date'],
        'end_date': project['end_date'],
        'source_drawing': source_drawing,
        'gauge_summary': gauge_summary,
        'stages': stages
    })

# Export summary as Excel
@app.route('/summary/export/excel/<int:project_id>')
def export_summary_excel(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Dummy data for export
    data = {
        'Gauge': ['16 Gauge', '18 Gauge', '20 Gauge'],
        'Total Sq.m': [120.5, 95.0, 75.3]
    }
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Gauge Summary')
    output.seek(0)
    return send_file(output, download_name=f"summary_project_{project_id}.xlsx", as_attachment=True)

# Export summary as PDF
@app.route('/summary/export/pdf/<int:project_id>')
def export_summary_pdf(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    output = BytesIO()
    p = SimpleDocTemplate(output, pagesize=letter)
    data = [['Gauge', 'Total Sq.m'],
            ['16 Gauge', 120.5],
            ['18 Gauge', 95.0],
            ['20 Gauge', 75.3]]
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#007bff')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME', (0,0),(-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0),(-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    p.build([table])
    output.seek(0)
    return send_file(output, download_name=f"summary_project_{project_id}.pdf", as_attachment=True)

# Submit summary (dummy)
@app.route('/summary/submit', methods=['POST'])
def submit_summary():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flash('Summary submitted successfully.', 'success')
    return redirect(url_for('summary'))

@app.route('/review')
def review():
    return render_template('review.html')

@app.route('/routes')
def show_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(str(rule))
    return "<br>".join(routes)

if __name__ == '__main__':
    # Insert dummy data on first run

    conn = get_db_connection()

    # Dummy user (admin)
    try:
        conn.execute("INSERT INTO employees (name, designation, email, phone, username, password) VALUES (?, ?, ?, ?, ?, ?)",
                     ("Admin User", "Administrator", "admin@example.com", "1234567890", "admin", "admin123"))
    except sqlite3.IntegrityError:
        pass  # Already exists

    # Dummy vendor
    try:
        conn.execute("INSERT INTO vendors (name, contact_person, email, phone, address) VALUES (?, ?, ?, ?, ?)",
                     ("Best Supplies", "John Vendor", "vendor@example.com", "0987654321", "123 Vendor St"))
    except sqlite3.IntegrityError:
        pass

    # Dummy projects
    try:
        conn.execute("""
        INSERT INTO projects (enquiry_id, client_name, location, start_date, end_date, status, incharge, phone, source_drawing, approval_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("ENQ001", "Client A", "Location A", "2025-01-01", "2025-12-31", "Open", "Engineer A", "9999999999", "drawing1.pdf", "Pending"))
    except sqlite3.IntegrityError:
        pass

    # Dummy ducts
    try:
        conn.execute("""
        INSERT INTO ducts (project_id, duct_no, duct_type, duct_size, quantity)
        VALUES (?, ?, ?, ?, ?)
        """, (1, "D001", "Rectangular", "500x300", 10))
    except sqlite3.IntegrityError:
        pass

    # Dummy production progress
    try:
        conn.execute("""
        INSERT INTO production (project_id, sheet_cutting_done, plasma_done, boxing_done, qc_done, dispatch_done)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (1, 50.0, 40.0, 30.0, 20.0, 10.0))
    except sqlite3.IntegrityError:
        pass

    # Dummy measurement sheet
    try:
        conn.execute("""
        INSERT INTO measurement_sheet (project_id, created_at)
        VALUES (?, ?)
        """, (1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    except sqlite3.IntegrityError:
        pass

    conn.commit()
    conn.close()

    print("Starting ERP Flask app on http://127.0.0.1:5000")
    app.run(debug=True)

