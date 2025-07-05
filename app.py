from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import os
import uuid
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secret123'

# ---------- DATABASE INITIALIZATION ----------
def init_db():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Employees Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            designation TEXT,
            email TEXT,
            phone TEXT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    # Vendors Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gst TEXT,
            address TEXT,
            phone TEXT,
            email TEXT
        )
    ''')

    # Dummy Vendors
    cursor.execute("SELECT COUNT(*) FROM vendors")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO vendors (name, gst, address, phone, email)
            VALUES (?, ?, ?, ?, ?)
        ''', [
            ('Vendor A', 'GSTIN1234', 'Address A', '9999911111', 'a@vendor.com'),
            ('Vendor B', 'GSTIN5678', 'Address B', '9999922222', 'b@vendor.com'),
            ('Vendor C', 'GSTIN9101', 'Address C', '9999933333', 'c@vendor.com')
        ])

    # Projects Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enquiry_id TEXT,
            vendor_id INTEGER,
            quotation_ro TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            gst TEXT,
            address TEXT,
            incharge TEXT,
            notes TEXT,
            file TEXT,
            approval_status TEXT DEFAULT 'Design Process',
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        )
    ''')

    # Measurement Sheet Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS measurement_sheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client TEXT,
            company TEXT,
            location TEXT,
            engineer TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # Measurement Entries Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS measurement_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            gauge TEXT,
            duct_type TEXT,
            width REAL,
            height REAL,
            quantity INTEGER,
            area REAL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')

    # Ducts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ducts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            duct_no TEXT,
            duct_type TEXT,
            duct_size TEXT,
            quantity INTEGER,
            remarks TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # Production Progress Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            cutting_done REAL,
            plasma_done REAL,
            boxing_done REAL,
            quality_percent REAL,
            dispatch_percent REAL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')

    # Default admin
    cursor.execute("SELECT * FROM employees WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Admin', 'Administrator', 'admin@erp.com', '1234567890', 'admin',
              generate_password_hash('admin123')))

    conn.commit()
    conn.close()

# Call DB init on startup
init_db()
# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[6], password):
            session['user'] = user[1]
            session['user_id'] = user[0]
            flash("Login successful", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))


# ---------------- EMPLOYEE REGISTRATION ----------------
@app.route('/register_employee', methods=['GET', 'POST'])
def register_employee():
    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO employees (name, designation, email, phone, username, password)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, designation, email, phone, username, hashed_password))
            conn.commit()
            flash("Employee registered successfully", "success")
        except sqlite3.IntegrityError:
            flash("Username already exists", "danger")
        conn.close()
        return redirect(url_for('register_employee'))

    return render_template('register.html')
  # ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login to continue", "warning")
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


# ---------------- VENDOR MODULE ----------------
@app.route('/vendors')
def vendors():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors")
    vendors = cursor.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors)


@app.route('/add_vendor', methods=['POST'])
def add_vendor():
    name = request.form['name']
    gst = request.form['gst']
    address = request.form['address']
    phone = request.form['phone']
    email = request.form['email']

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO vendors (name, gst, address, phone, email)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, gst, address, phone, email))
    conn.commit()
    conn.close()
    flash("Vendor added successfully", "success")
    return redirect(url_for('vendors'))


@app.route('/delete_vendor/<int:vendor_id>')
def delete_vendor(vendor_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vendors WHERE id=?", (vendor_id,))
    conn.commit()
    conn.close()
    flash("Vendor deleted successfully", "info")
    return redirect(url_for('vendors'))


# ---------------- EXPORT VENDORS TO EXCEL ----------------
@app.route('/export_vendors_excel')
def export_vendors_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM vendors', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="Vendors.xlsx", as_attachment=True)
# ---------------- PROJECT MODULE ----------------
@app.route('/projects')
def projects():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT p.*, v.name FROM projects p LEFT JOIN vendors v ON p.vendor_id = v.id")
    projects = cursor.fetchall()

    cursor.execute("SELECT * FROM vendors")
    vendors = cursor.fetchall()

    conn.close()
    return render_template('projects.html', projects=projects, vendors=vendors)


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


# ---------------- EXPORT PROJECTS TO EXCEL ----------------
@app.route('/export_projects_excel')
def export_projects_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM projects', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="Projects.xlsx", as_attachment=True)
# ---------------- MEASUREMENT SHEET MODULE ----------------

@app.route('/measurement/<int:project_id>')
def measurement(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,))
    sheet = cursor.fetchone()

    cursor.execute("SELECT * FROM measurement_entries WHERE project_id = ?", (project_id,))
    entries = cursor.fetchall()

    conn.close()
    return render_template('measurement.html', sheet=sheet, entries=entries, project_id=project_id)


@app.route('/add_measurement_sheet', methods=['POST'])
def add_measurement_sheet():
    project_id = request.form['project_id']
    client = request.form['client']
    company = request.form['company']
    location = request.form['location']
    engineer = request.form['engineer']
    phone = request.form['phone']

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO measurement_sheet (project_id, client, company, location, engineer, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, client, company, location, engineer, phone))
    conn.commit()
    conn.close()
    flash("Measurement sheet saved", "success")
    return redirect(url_for('measurement', project_id=project_id))


@app.route('/add_measurement_entry', methods=['POST'])
def add_measurement_entry():
    project_id = request.form['project_id']
    item = request.form['item']
    length = float(request.form['length'])
    width = float(request.form['width'])
    qty = int(request.form['qty'])

    area = round(length * width * qty / 1000000, 2)  # Sq.m from mm

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO measurement_entries (project_id, item, length, width, qty, area)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, item, length, width, qty, area))
    conn.commit()
    conn.close()
    flash("Entry added", "success")
    return redirect(url_for('measurement', project_id=project_id))


# EXPORT MEASUREMENT ENTRIES TO EXCEL
@app.route('/export_measurements_excel/<int:project_id>')
def export_measurements_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM measurement_entries WHERE project_id=?', conn, params=(project_id,))
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name=f"Measurement_Project_{project_id}.xlsx", as_attachment=True)
# ---------------- DUCT ENTRY MODULE ----------------

@app.route('/duct_entry/<int:project_id>')
def duct_entry(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ducts WHERE project_id=?", (project_id,))
    ducts = cursor.fetchall()
    conn.close()
    return render_template('duct_entry.html', ducts=ducts, project_id=project_id)


@app.route('/add_duct', methods=['POST'])
def add_duct():
    project_id = request.form['project_id']
    duct_no = request.form['duct_no']
    duct_type = request.form['duct_type']
    duct_size = request.form['duct_size']
    quantity = request.form['quantity']
    remarks = request.form['remarks']

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ducts (project_id, duct_no, duct_type, duct_size, quantity, remarks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, duct_no, duct_type, duct_size, quantity, remarks))
    conn.commit()
    conn.close()
    flash("Duct entry added successfully", "success")
    return redirect(url_for('duct_entry', project_id=project_id))


@app.route('/view_ducts/<int:project_id>')
def view_ducts(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ducts WHERE project_id=?", (project_id,))
    ducts = cursor.fetchall()

    cursor.execute("SELECT * FROM projects WHERE id=?", (project_id,))
    project = cursor.fetchone()

    conn.close()
    return render_template('ducts_live_table.html', ducts=ducts, project=project)


@app.route('/export_ducts_excel/<int:project_id>')
def export_ducts_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM ducts WHERE project_id=?', conn, params=(project_id,))
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name=f"Duct_Entries_Project_{project_id}.xlsx", as_attachment=True)
# ---------------- PRODUCTION MODULE ----------------

@app.route('/production/<int:project_id>')
def production(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get total area from measurement_entries (assumes measurement_entries table exists)
    cursor.execute("SELECT SUM(area) FROM measurement_entries WHERE project_id=?", (project_id,))
    total_area = cursor.fetchone()[0] or 0

    # Get current production data (if exists)
    cursor.execute("SELECT * FROM production WHERE project_id=?", (project_id,))
    production_data = cursor.fetchone()

    conn.close()
    return render_template('production.html',
                           project_id=project_id,
                           total_area=total_area,
                           production=production_data)


@app.route('/update_production/<int:project_id>', methods=['POST'])
def update_production(project_id):
    cutting_done = float(request.form.get('cutting_done', 0))
    plasma_done = float(request.form.get('plasma_done', 0))
    boxing_done = float(request.form.get('boxing_done', 0))
    quality_percent = float(request.form.get('quality_percent', 0))
    dispatch_percent = float(request.form.get('dispatch_percent', 0))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM production WHERE project_id=?", (project_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute('''
            UPDATE production SET
                cutting_done=?, plasma_done=?, boxing_done=?,
                quality_percent=?, dispatch_percent=?
            WHERE project_id=?
        ''', (cutting_done, plasma_done, boxing_done,
              quality_percent, dispatch_percent, project_id))
    else:
        cursor.execute('''
            INSERT INTO production (
                project_id, cutting_done, plasma_done,
                boxing_done, quality_percent, dispatch_percent
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, cutting_done, plasma_done,
              boxing_done, quality_percent, dispatch_percent))

    conn.commit()
    conn.close()
    flash("Production updated successfully", "success")
    return redirect(url_for('production', project_id=project_id))
# ---------------- MEASUREMENT ENTRIES (Area Tracking) ----------------

@app.route('/measurement_entries/<int:project_id>')
def measurement_entries(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM measurement_entries WHERE project_id=?', (project_id,))
    entries = cursor.fetchall()
    conn.close()
    return render_template('measurement_entries.html', entries=entries, project_id=project_id)


@app.route('/add_measurement_entry', methods=['POST'])
def add_measurement_entry():
    project_id = request.form['project_id']
    floor = request.form['floor']
    duct_no = request.form['duct_no']
    length = float(request.form['length'])
    breadth = float(request.form['breadth'])
    quantity = int(request.form['quantity'])

    area = round(length * breadth * quantity / 1000000, 2)  # sqm from mm

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO measurement_entries (
            project_id, floor, duct_no, length, breadth, quantity, area
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (project_id, floor, duct_no, length, breadth, quantity, area))

    conn.commit()
    conn.close()
    flash("Measurement entry added", "success")
    return redirect(url_for('measurement_entries', project_id=project_id))
@app.route('/export_vendors_excel')
def export_vendors_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM vendors', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="Vendors.xlsx", as_attachment=True)


@app.route('/export_projects_excel')
def export_projects_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM projects', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="Projects.xlsx", as_attachment=True)


@app.route('/export_employees_excel')
def export_employees_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM employees', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="Employees.xlsx", as_attachment=True)


@app.route('/export_ducts_excel/<int:project_id>')
def export_ducts_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM ducts WHERE project_id=?', conn, params=(project_id,))
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name=f"Duct_Entries_Project_{project_id}.xlsx", as_attachment=True)


@app.route('/export_measurements_excel/<int:project_id>')
def export_measurements_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM measurement_entries WHERE project_id=?', conn, params=(project_id,))
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name=f"Measurement_Project_{project_id}.xlsx", as_attachment=True)
@app.route('/project_summary/<int:project_id>')
def project_summary(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get project info
    cursor.execute('SELECT * FROM projects WHERE id=?', (project_id,))
    project = cursor.fetchone()

    # Total measured area
    cursor.execute('SELECT SUM(area) FROM measurement_entries WHERE project_id=?', (project_id,))
    total_area = cursor.fetchone()[0] or 0

    # Production progress
    cursor.execute('SELECT * FROM production WHERE project_id=?', (project_id,))
    prod = cursor.fetchone()
    conn.close()

    cutting = prod[2] if prod else 0
    plasma = prod[3] if prod else 0
    boxing = prod[4] if prod else 0
    quality = prod[5] if prod else 0
    dispatch = prod[6] if prod else 0

    def calc_percent(done): return (done / total_area) * 100 if total_area else 0

    percent_data = {
        'Cutting': calc_percent(cutting),
        'Fabrication': calc_percent(plasma),
        'Boxing': calc_percent(boxing),
        'Quality Check': quality,
        'Dispatch': dispatch
    }
    overall_percent = round(sum(percent_data.values()) / len(percent_data), 2)

    return render_template('summary.html',
                           project=project,
                           total_area=total_area,
                           done_data={'Cutting': cutting, 'Fabrication': plasma, 'Boxing': boxing},
                           percent_data=percent_data,
                           overall_percent=overall_percent)


@app.route('/project_summary_pdf/<int:project_id>')
def project_summary_pdf(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM projects WHERE id=?', (project_id,))
    project = cursor.fetchone()

    cursor.execute('SELECT SUM(area) FROM measurement_entries WHERE project_id=?', (project_id,))
    total_area = cursor.fetchone()[0] or 0

    cursor.execute('SELECT * FROM production WHERE project_id=?', (project_id,))
    prod = cursor.fetchone()
    conn.close()

    cutting = prod[2] if prod else 0
    plasma = prod[3] if prod else 0
    boxing = prod[4] if prod else 0
    quality = prod[5] if prod else 0
    dispatch = prod[6] if prod else 0

    def calc_percent(x): return (x / total_area) * 100 if total_area else 0
    percent_data = {
        'Cutting': calc_percent(cutting),
        'Fabrication': calc_percent(plasma),
        'Boxing': calc_percent(boxing),
        'Quality Check': quality,
        'Dispatch': dispatch
    }

    overall = round(sum(percent_data.values()) / len(percent_data), 2)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 50, "Project Summary Report")

    c.setFont("Helvetica", 12)
    y = height - 100
    c.drawString(40, y, f"Project ID: {project[0]}")
    c.drawString(40, y - 20, f"Location: {project[6]}")
    c.drawString(40, y - 40, f"Total Measured Area: {total_area} sqm")

    y -= 80
    c.drawString(40, y, "Progress Summary:")
    for phase, percent in percent_data.items():
        y -= 20
        c.drawString(60, y, f"{phase}: {round(percent, 2)}%")

    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, f"Overall Completion: {overall}%")

    c.showPage()
    c.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f"Project_{project_id}_Summary.pdf",
                     mimetype='application/pdf')
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
