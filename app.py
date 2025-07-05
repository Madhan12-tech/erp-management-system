from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import os
import uuid
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secretkey'

# ------------------ DB INITIALIZATION ------------------ #
def init_db():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # ----------------- USERS ----------------- #
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')

    # ----------------- VENDORS ----------------- #
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT, phone TEXT,
        company TEXT, gst TEXT, address TEXT
    )
    ''')

    # ----------------- EMPLOYEES ----------------- #
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, department TEXT, email TEXT,
        mobile TEXT, username TEXT, password TEXT
    )
    ''')

    # ----------------- PROJECTS ----------------- #
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enquiry_id TEXT, vendor_id INTEGER,
        quotation_ro TEXT, start_date TEXT, end_date TEXT,
        location TEXT, gst TEXT, address TEXT,
        incharge TEXT, notes TEXT, file TEXT,
        FOREIGN KEY (vendor_id) REFERENCES vendors(id)
    )
    ''')

    # ----------------- DUCTS ----------------- #
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ducts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER, type TEXT, area REAL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    # ----------------- MEASUREMENT SHEETS ----------------- #
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS measurement_sheet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        total_area REAL DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS measurement_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sheet_id INTEGER,
        duct_type TEXT,
        completed_area REAL,
        date TEXT,
        FOREIGN KEY (sheet_id) REFERENCES measurement_sheet(id)
    )
    ''')

    # ----------------- PRODUCTION ----------------- #
    cursor.execute('''
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

    # Dummy admin user (if not exists)
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_password = generate_password_hash("admin123")
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed_password))

    # Dummy vendor
    cursor.execute("SELECT * FROM vendors")
    if not cursor.fetchall():
        cursor.execute("INSERT INTO vendors (name, email, phone, company, gst, address) VALUES (?, ?, ?, ?, ?, ?)", 
                       ('Dummy Vendor', 'vendor@example.com', '1234567890', 'Dummy Company', 'GST1234', 'Chennai'))

    conn.commit()
    conn.close()

# Call DB initialization
init_db()

# ------------------ LOGIN ROUTE ------------------ #
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user'] = username
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials. Please try again.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

# ------------------ REGISTER USER ROUTE ------------------ #
@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        department = request.form['department']
        email = request.form['email']
        mobile = request.form['mobile']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO employees (name, department, email, mobile, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, department, email, mobile, username, password))

        # Also create login credentials in `users` table
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))

        conn.commit()
        conn.close()
        flash("Employee registered and login created!", "success")
        return redirect(url_for('register_user'))

    return render_template('register_user.html')

# ------------------ LOGOUT ROUTE ------------------ #
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))
# ------------------ DASHBOARD ROUTE ------------------ #
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
# ------------------ PROJECT MODULE ------------------ #

@app.route('/projects')
def projects():
    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    if search:
        cursor.execute("SELECT * FROM projects WHERE enquiry_id LIKE ? OR location LIKE ? OR incharge LIKE ?", 
                       (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM projects")
    projects = cursor.fetchall()
    conn.close()

    return render_template('projects.html', projects=projects, search=search)

@app.route('/add_project', methods=['POST'])
def add_project():
    enquiry_id = request.form['enquiry_id']
    vendor_id = request.form['vendor_id']
    quotation_ro = request.form['quotation_ro']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    location = request.form['location']
    gst = request.form['gst']
    address = request.form['address']
    incharge = request.form['incharge']
    notes = request.form['notes']
    file = request.files.get('file')

    filename = ''
    if file and file.filename:
        uploads_folder = 'uploads'
        os.makedirs(uploads_folder, exist_ok=True)
        filename = f"{uploads_folder}/{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        file.save(filename)

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO projects (
            enquiry_id, vendor_id, quotation_ro, start_date, end_date,
            location, gst, address, incharge, notes, file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (enquiry_id, vendor_id, quotation_ro, start_date, end_date,
          location, gst, address, incharge, notes, filename))

    conn.commit()
    conn.close()
    flash("Project added successfully", "success")
    return redirect(url_for('projects'))

# -------- EXPORT PROJECTS TO EXCEL -------- #
@app.route('/export_projects_excel')
def export_projects_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')
        writer.save()
    output.seek(0)

    return send_file(output, download_name="projects.xlsx", as_attachment=True)

# -------- EXPORT PROJECTS TO PDF -------- #
@app.route('/export_projects_pdf')
def export_projects_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects")
    projects = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y, "Projects Report")
    y -= 30

    c.setFont("Helvetica", 10)
    for project in projects:
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(30, y, f"Enquiry ID: {project[1]}, Location: {project[5]}, Incharge: {project[8]}")
        y -= 20

    c.save()
    buffer.seek(0)

    return send_file(buffer, download_name="projects.pdf", as_attachment=True)
# ------------------ VENDOR MODULE ------------------ #

@app.route('/vendors')
def vendors():
    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    if search:
        cursor.execute("SELECT * FROM vendors WHERE name LIKE ? OR email LIKE ? OR phone LIKE ?", 
                       (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM vendors")
    vendors = cursor.fetchall()
    conn.close()

    return render_template('vendors.html', vendors=vendors, search=search)

@app.route('/add_vendor', methods=['POST'])
def add_vendor():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    gst = request.form['gst']
    bank = request.form['bank']
    account_no = request.form['account_no']
    ifsc = request.form['ifsc']

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO vendors (name, email, phone, address, gst, bank, account_no, ifsc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, email, phone, address, gst, bank, account_no, ifsc))
    conn.commit()
    conn.close()

    flash("Vendor added successfully", "success")
    return redirect(url_for('vendors'))

# -------- EXPORT VENDORS TO EXCEL -------- #
@app.route('/export_vendors_excel')
def export_vendors_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendors')
        writer.save()
    output.seek(0)

    return send_file(output, download_name="vendors.xlsx", as_attachment=True)

# -------- EXPORT VENDORS TO PDF -------- #
@app.route('/export_vendors_pdf')
def export_vendors_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors")
    vendors = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y, "Vendors Report")
    y -= 30

    c.setFont("Helvetica", 10)
    for v in vendors:
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(30, y, f"Name: {v[1]}, Phone: {v[3]}, Email: {v[2]}")
        y -= 20

    c.save()
    buffer.seek(0)

    return send_file(buffer, download_name="vendors.pdf", as_attachment=True)
# ------------------ EMPLOYEE MODULE ------------------ #

# -------- EXPORT EMPLOYEES TO EXCEL -------- #
@app.route('/export_employees_excel')
def export_employees_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT id, name, role, email FROM employees", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Employees')
        writer.save()
    output.seek(0)

    return send_file(output, download_name="employees.xlsx", as_attachment=True)

# -------- EXPORT EMPLOYEES TO PDF -------- #
@app.route('/export_employees_pdf')
def export_employees_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, role, email FROM employees")
    employees = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y, "Employees Report")
    y -= 30

    c.setFont("Helvetica", 10)
    for emp in employees:
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(30, y, f"Name: {emp[0]}, Role: {emp[1]}, Email: {emp[2]}")
        y -= 20

    c.save()
    buffer.seek(0)

    return send_file(buffer, download_name="employees.pdf", as_attachment=True)
# ------------------ MEASUREMENT SHEET MODULE ------------------ #

@app.route('/measurement/<int:project_id>')
def measurement(project_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    
    if search:
        cursor.execute("""
            SELECT ms.id, ms.sheet_name, ms.total_area, ms.notes, p.name 
            FROM measurement_sheet ms 
            JOIN projects p ON ms.project_id = p.id
            WHERE ms.project_id = ? AND (ms.sheet_name LIKE ? OR ms.notes LIKE ?)
        """, (project_id, f'%{search}%', f'%{search}%'))
    else:
        cursor.execute("""
            SELECT ms.id, ms.sheet_name, ms.total_area, ms.notes, p.name 
            FROM measurement_sheet ms 
            JOIN projects p ON ms.project_id = p.id
            WHERE ms.project_id = ?
        """, (project_id,))
    
    sheets = cursor.fetchall()
    conn.close()
    return render_template("measurement.html", sheets=sheets, project_id=project_id, search=search)


@app.route('/add_measurement_sheet', methods=['POST'])
def add_measurement_sheet():
    if 'user' not in session:
        return redirect(url_for('login'))

    project_id = request.form['project_id']
    sheet_name = request.form['sheet_name']
    total_area = request.form['total_area']
    notes = request.form['notes']

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO measurement_sheet (project_id, sheet_name, total_area, notes)
        VALUES (?, ?, ?, ?)
    ''', (project_id, sheet_name, total_area, notes))
    conn.commit()
    conn.close()
    
    flash("Measurement Sheet Added Successfully", "success")
    return redirect(url_for('measurement', project_id=project_id))
# ------------------ MEASUREMENT ENTRIES (POPUP) ------------------ #

@app.route('/get_measurement_entries/<int:sheet_id>')
def get_measurement_entries(sheet_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM measurement_entries WHERE sheet_id = ?', (sheet_id,))
    entries = cursor.fetchall()
    conn.close()
    return jsonify(entries)


@app.route('/add_measurement_entry', methods=['POST'])
def add_measurement_entry():
    sheet_id = request.form['sheet_id']
    description = request.form['description']
    length = float(request.form['length'])
    width = float(request.form['width'])

    area = length * width
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO measurement_entries (sheet_id, description, length, width, area)
        VALUES (?, ?, ?, ?, ?)
    ''', (sheet_id, description, length, width, area))

    cursor.execute('''
        UPDATE measurement_sheet SET total_area = total_area + ? WHERE id = ?
    ''', (area, sheet_id))

    conn.commit()
    conn.close()
    flash("Measurement entry added successfully", "success")
    return redirect(request.referrer or '/')

# ------------------ EXPORT MEASUREMENTS ------------------ #

@app.route('/export_measurements_excel/<int:project_id>')
def export_measurements_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("""
        SELECT ms.id, ms.sheet_name, ms.total_area, ms.notes, p.name as project_name
        FROM measurement_sheet ms
        JOIN projects p ON ms.project_id = p.id
        WHERE ms.project_id = ?
    """, conn, params=(project_id,))
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Measurements')

    output.seek(0)
    return send_file(output, download_name="measurement_data.xlsx", as_attachment=True)


@app.route('/export_measurements_pdf/<int:project_id>')
def export_measurements_pdf(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sheet_name, total_area, notes FROM measurement_sheet
        WHERE project_id = ?
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Measurement Sheets")
    y -= 30
    p.setFont("Helvetica", 12)

    for row in rows:
        text = f"Sheet: {row[0]}, Area: {row[1]}, Notes: {row[2]}"
        p.drawString(50, y, text)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="measurement_data.pdf")
# ------------------ PRODUCTION MODULE ------------------ #

@app.route('/production/<int:project_id>')
def production(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute('SELECT name FROM projects WHERE id = ?', (project_id,))
    project = cursor.fetchone()
    if not project:
        flash("Project not found", "error")
        return redirect(url_for('dashboard'))

    cursor.execute('''
        SELECT phase, SUM(completed_area), SUM(total_area)
        FROM production
        WHERE project_id = ?
        GROUP BY phase
    ''', (project_id,))
    phase_data = cursor.fetchall()

    cursor.execute('SELECT * FROM production WHERE project_id = ?', (project_id,))
    all_entries = cursor.fetchall()

    conn.close()
    return render_template('production.html',
                           project_id=project_id,
                           project_name=project[0],
                           phase_data=phase_data,
                           all_entries=all_entries)


@app.route('/add_production_entry', methods=['POST'])
def add_production_entry():
    project_id = request.form['project_id']
    phase = request.form['phase']
    duct_type = request.form['duct_type']
    total_area = float(request.form.get('total_area', 0))
    completed_area = float(request.form.get('completed_area', 0))
    percentage_done = float(request.form.get('percentage_done', 0))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO production (project_id, phase, duct_type, total_area, completed_area, percentage_done)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, phase, duct_type, total_area, completed_area, percentage_done))

    conn.commit()
    conn.close()
    flash("Production entry added", "success")
    return redirect(url_for('production', project_id=project_id))

# ------------------ EXPORT PRODUCTION ------------------ #

@app.route('/export_production_excel/<int:project_id>')
def export_production_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('''
        SELECT phase, duct_type, total_area, completed_area, percentage_done
        FROM production
        WHERE project_id = ?
    ''', conn, params=(project_id,))
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Production')

    output.seek(0)
    return send_file(output, download_name="production_data.xlsx", as_attachment=True)


@app.route('/export_production_pdf/<int:project_id>')
def export_production_pdf(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT phase, duct_type, total_area, completed_area, percentage_done
        FROM production
        WHERE project_id = ?
    ''', (project_id,))
    rows = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Production Report")
    y -= 30
    p.setFont("Helvetica", 12)

    for row in rows:
        text = f"{row[0]} | {row[1]} | {row[2]} sqm | {row[3]} sqm | {row[4]}%"
        p.drawString(50, y, text)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="production_data.pdf")

# ------------------ PRODUCTION SUMMARY & PROGRESS ------------------ #

@app.route('/production_summary/<int:project_id>')
def production_summary(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Overall Phase Summary
    cursor.execute('''
        SELECT phase,
               SUM(total_area) as total_area,
               SUM(completed_area) as completed_area
        FROM production
        WHERE project_id = ?
        GROUP BY phase
    ''', (project_id,))
    summary = cursor.fetchall()

    # Phase breakdown by duct type
    cursor.execute('''
        SELECT phase, duct_type, total_area, completed_area, percentage_done
        FROM production
        WHERE project_id = ?
        ORDER BY phase
    ''', (project_id,))
    breakdown = cursor.fetchall()

    conn.close()

    # Calculate overall progress
    total_area = sum([row[1] for row in summary])
    completed_area = sum([row[2] for row in summary])
    overall_progress = round((completed_area / total_area) * 100, 2) if total_area > 0 else 0

    return render_template('production_summary.html',
                           project_id=project_id,
                           summary=summary,
                           breakdown=breakdown,
                           total_area=total_area,
                           completed_area=completed_area,
                           overall_progress=overall_progress)

# ------------------ MEASUREMENT SHEET VIEW ------------------ #

@app.route('/measurement/<int:project_id>')
def measurement(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM measurement_sheet WHERE project_id = ?', (project_id,))
    sheets = cursor.fetchall()

    # Get total measurement entries
    cursor.execute('SELECT * FROM measurement_entries WHERE project_id = ?', (project_id,))
    entries = cursor.fetchall()

    conn.close()

    return render_template('measurement_sheet.html', project_id=project_id, sheets=sheets, entries=entries)


# ------------------ ADD MEASUREMENT SHEET ENTRY ------------------ #

@app.route('/add_measurement_entry', methods=['POST'])
def add_measurement_entry():
    project_id = request.form['project_id']
    sheet_id = request.form['sheet_id']
    duct_type = request.form['duct_type']
    height = float(request.form['height'])
    width = float(request.form['width'])
    quantity = int(request.form['quantity'])
    remarks = request.form['remarks']

    area = round((height * width * quantity) / 1000000, 2)

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO measurement_entries (
            project_id, sheet_id, duct_type, height, width, quantity, area, remarks
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (project_id, sheet_id, duct_type, height, width, quantity, area, remarks))

    # Also update total_area in measurement_sheet
    cursor.execute('UPDATE measurement_sheet SET total_area = total_area + ? WHERE id = ?', (area, sheet_id))

    conn.commit()
    conn.close()
    flash('Entry added successfully', 'success')
    return redirect(url_for('measurement', project_id=project_id))


# ------------------ EXPORT MEASUREMENT ENTRIES (EXCEL) ------------------ #

@app.route('/export_measurement_excel/<int:project_id>')
def export_measurement_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('''
        SELECT * FROM measurement_entries WHERE project_id = ?
    ''', conn, params=(project_id,))
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name='measurement_entries.xlsx', as_attachment=True)


# ------------------ EXPORT MEASUREMENT ENTRIES (PDF) ------------------ #

@app.route('/export_measurement_pdf/<int:project_id>')
def export_measurement_pdf(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM measurement_entries WHERE project_id = ?', (project_id,))
    entries = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.drawString(100, height - 50, f"Measurement Entries for Project ID: {project_id}")
    y = height - 80
    pdf.setFont("Helvetica", 9)

    for entry in entries:
        line = f"Sheet ID: {entry[2]}, Type: {entry[3]}, {entry[4]}x{entry[5]}, Qty: {entry[6]}, Area: {entry[7]} m²"
        pdf.drawString(50, y, line)
        y -= 15
        if y < 50:
            pdf.showPage()
            y = height - 50

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, download_name='measurement_entries.pdf', as_attachment=True)

# ------------------ QUALITY CHECK PHASE (PHASE 4) ------------------ #

@app.route('/quality_check/<int:project_id>', methods=['GET', 'POST'])
def quality_check(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        percent = float(request.form['percent'])
        updated_on = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
            INSERT INTO production (project_id, phase, percent_completed, updated_on)
            VALUES (?, ?, ?, ?)
        ''', (project_id, 'Quality Check', percent, updated_on))

        conn.commit()
        flash('Quality Check progress updated.', 'success')
        return redirect(url_for('quality_check', project_id=project_id))

    cursor.execute('''
        SELECT * FROM production
        WHERE project_id = ? AND phase = 'Quality Check'
        ORDER BY updated_on DESC
    ''', (project_id,))
    records = cursor.fetchall()
    conn.close()

    return render_template('quality_check.html', project_id=project_id, records=records)


# ------------------ DISPATCH PHASE (PHASE 5) ------------------ #

@app.route('/dispatch/<int:project_id>', methods=['GET', 'POST'])
def dispatch(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        percent = float(request.form['percent'])
        updated_on = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
            INSERT INTO production (project_id, phase, percent_completed, updated_on)
            VALUES (?, ?, ?, ?)
        ''', (project_id, 'Dispatch', percent, updated_on))

        conn.commit()
        flash('Dispatch progress updated.', 'success')
        return redirect(url_for('dispatch', project_id=project_id))

    cursor.execute('''
        SELECT * FROM production
        WHERE project_id = ? AND phase = 'Dispatch'
        ORDER BY updated_on DESC
    ''', (project_id,))
    records = cursor.fetchall()
    conn.close()

    return render_template('dispatch.html', project_id=project_id, records=records)

# ------------------ OVERALL PROGRESS SUMMARY PER PROJECT ------------------ #

@app.route('/summary/<int:project_id>')
def summary(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get project info
    cursor.execute('SELECT name FROM projects WHERE id = ?', (project_id,))
    project = cursor.fetchone()

    # Total area for project
    cursor.execute('SELECT SUM(area) FROM measurement_sheet WHERE project_id = ?', (project_id,))
    total_area = cursor.fetchone()[0] or 0

    # Calculate area-based progress (Phases 1-3)
    phases = ['Sheet Cutting', 'Plasma and Fabrication', 'Boxing and Assembly']
    phase_progress = {}
    for phase in phases:
        cursor.execute('''
            SELECT SUM(area_done) FROM production
            WHERE project_id = ? AND phase = ?
        ''', (project_id, phase))
        done = cursor.fetchone()[0] or 0
        phase_progress[phase] = {
            'done': done,
            'total': total_area,
            'percent': round((done / total_area) * 100, 2) if total_area else 0
        }

    # Percentage-only progress (Phases 4-5)
    cursor.execute('''
        SELECT phase, percent_completed, updated_on
        FROM production
        WHERE project_id = ? AND phase IN ('Quality Check', 'Dispatch')
        ORDER BY updated_on DESC
    ''', (project_id,))
    rows = cursor.fetchall()
    latest_percent = {}
    for row in rows:
        phase, percent, _ = row
        if phase not in latest_percent:
            latest_percent[phase] = percent  # take latest only

    # Calculate overall progress (weighted average)
    total_phases = 5
    total_percent = 0

    for phase in phases:
        total_percent += phase_progress[phase]['percent']

    for phase in ['Quality Check', 'Dispatch']:
        total_percent += latest_percent.get(phase, 0)

    overall_percent = round(total_percent / total_phases, 2)

    conn.close()

    return render_template('summary.html', project=project, overall=overall_percent,
                           phase_progress=phase_progress, extra_phases=latest_percent)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
