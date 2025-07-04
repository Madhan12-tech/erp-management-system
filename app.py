from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
from datetime import datetime
from io import BytesIO
import pandas as pd
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecret'

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # ------------------ Login System ------------------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    # ------------------ Vendor Registration ------------------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_name TEXT,
            gst TEXT,
            address TEXT,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            bank_name TEXT,
            account_number TEXT,
            ifsc TEXT
        )
    ''')

    # ------------------ Employee Registration ------------------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            designation TEXT,
            email TEXT,
            phone TEXT,
            username TEXT,
            password TEXT
        )
    ''')

    # ------------------ Projects Table ------------------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enquiry_id TEXT,
            vendor_name TEXT,
            gst TEXT,
            address TEXT,
            quotation_ro TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            incharge TEXT,
            notes TEXT,
            drawing_file TEXT,
            status TEXT DEFAULT 'Preparation'
        )
    ''')

    # ------------------ Design Stage Status ------------------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS design_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            design_completed INTEGER DEFAULT 0,
            approval_status TEXT DEFAULT 'Not Submitted'
        )
    ''')

    # ------------------ Measurement Sheet Info ------------------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS measurement_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client_name TEXT,
            company_name TEXT,
            project_location TEXT,
            engineer_name TEXT,
            phone TEXT
        )
    ''')

    # ------------------ Duct Entry Table ------------------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS duct_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            duct_no TEXT,
            duct_type TEXT,
            duct_size TEXT,
            quantity INTEGER,
            remarks TEXT
        )
    ''')

    # ------------------ Project Progress Summary ------------------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS production_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            cutting INTEGER DEFAULT 0,
            plasma INTEGER DEFAULT 0,
            boxing INTEGER DEFAULT 0,
            qc INTEGER DEFAULT 0,
            dispatch INTEGER DEFAULT 0
        )
    ''')

    # ------------------ Gauge Sheet Area Summary ------------------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS gauge_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            gauge TEXT,
            sq_meter REAL
        )
    ''')

    # ---------- Create default user ----------
    cur.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', 'admin'))

    conn.commit()
    conn.close()


# Run DB setup on app start
init_db()
# ---------- LOGIN ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']

        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ? AND password = ?", (uname, pwd))
        user = cur.fetchone()
        conn.close()

        if user:
            session['user'] = uname
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')


# ---------- REGISTER VENDOR FORM ----------
@app.route('/register_vendor', methods=['GET'])
def register_vendor():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('vendors.html')


# ---------- ADD VENDOR ----------
@app.route('/add_vendor', methods=['POST'])
def add_vendor():
    if 'user' not in session:
        return redirect(url_for('login'))

    data = (
        request.form['vendor_name'],
        request.form['gst'],
        request.form['address'],
        request.form['contact_person'],
        request.form['phone'],
        request.form['email'],
        request.form['bank_name'],
        request.form['account_number'],
        request.form['ifsc']
    )

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO vendors (
            vendor_name, gst, address, contact_person, phone, email, bank_name, account_number, ifsc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()
    conn.close()

    flash('Vendor registered successfully!', 'success')
    return redirect(url_for('register_vendor'))
    # ---------- Project Management ----------

# Ensure upload folder exists
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/projects', methods=['GET', 'POST'])
def projects():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Fetch project data
    c.execute("SELECT * FROM projects")
    projects = c.fetchall()

    # Fetch vendor dropdown
    c.execute("SELECT vendor_name, gst, address FROM vendors")
    vendors = c.fetchall()

    # Fetch employee names for incharge dropdown
    c.execute("SELECT name FROM employees")
    incharges = [row[0] for row in c.fetchall()]

    conn.close()

    return render_template('projects.html',
                           projects=[{
                               'enquiry_id': row[1],
                               'vendor_name': row[2],
                               'location': row[7],
                               'status': row[12]
                           } for row in projects],
                           vendors=[{
                               'vendor_name': v[0],
                               'gst': v[1],
                               'address': v[2]
                           } for v in vendors],
                           incharges=incharges,
                           project_id="",  # empty unless editing
                           design_status="",
                           approval_status=""
                           )

@app.route('/add_project', methods=['POST'])
def add_project():
    enquiry_id = request.form['enquiry_id']
    vendor_name = request.form['vendor_name']
    gst = request.form['gst']
    address = request.form['address']
    quotation_ro = request.form['quotation_ro']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    location = request.form['location']
    incharge = request.form['incharge']
    notes = request.form['notes']
    status = "Preparation"

    # Handle file upload
    file = request.files['drawing_file']
    filename = ""
    if file and file.filename != "":
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # Insert project into DB
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO projects (enquiry_id, vendor_name, gst, address, quotation_ro, start_date, end_date, location, incharge, notes, drawing_file, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (enquiry_id, vendor_name, gst, address, quotation_ro, start_date, end_date, location, incharge, notes, filename, status))
    conn.commit()
    conn.close()

    flash('Project added successfully', 'success')
    return redirect(url_for('projects'))
    # ---------- MEASUREMENT SHEET ENTRY ----------
@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    client = request.form['client_name']
    company = request.form['company_name']
    location = request.form['project_location']
    engineer = request.form['engineer_name']
    phone = request.form['phone']
    project_id = session.get('current_project')

    if not project_id:
        flash('Project ID missing from session', 'danger')
        return redirect('/dashboard')

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE projects SET client_name=?, project_location=?, engineer_name=?, phone=?
        WHERE id=?
    """, (client, location, engineer, phone, project_id))
    conn.commit()
    conn.close()

    return redirect(f'/measurement_sheet/{project_id}')


@app.route('/measurement_sheet/<project_id>')
def measurement_sheet(project_id):
    session['current_project'] = project_id

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get project info
    cursor.execute("SELECT enquiry_id, client_name, project_location, engineer_name, phone FROM projects WHERE id=?", (project_id,))
    project = cursor.fetchone()

    # Get duct entries
    cursor.execute("SELECT * FROM ducts WHERE project_id=?", (project_id,))
    ducts = cursor.fetchall()

    conn.close()

    return render_template('measurement_sheet.html',
                           enquiry_id=project[0],
                           client_name=project[1],
                           project_location=project[2],
                           engineer_name=project[3],
                           phone=project[4],
                           ducts=[{
                               'id': d[0], 'duct_no': d[2], 'duct_type': d[3],
                               'duct_size': d[4], 'quantity': d[5]
                           } for d in ducts])


@app.route('/add_duct', methods=['POST'])
def add_duct():
    project_id = session.get('current_project')
    if not project_id:
        flash('Project ID not found.', 'danger')
        return redirect('/dashboard')

    duct_no = request.form['duct_no']
    duct_type = request.form['duct_type']
    duct_size = request.form['duct_size']
    quantity = request.form['quantity']

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ducts (project_id, duct_no, duct_type, duct_size, quantity)
        VALUES (?, ?, ?, ?, ?)
    """, (project_id, duct_no, duct_type, duct_size, quantity))
    conn.commit()
    conn.close()

    return redirect(f'/measurement_sheet/{project_id}')


@app.route('/delete_duct/<int:duct_id>')
def delete_duct(duct_id):
    project_id = session.get('current_project')
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ducts WHERE id=?", (duct_id,))
    conn.commit()
    conn.close()
    return redirect(f'/measurement_sheet/{project_id}')


@app.route('/edit_duct/<int:duct_id>', methods=['GET', 'POST'])
def edit_duct(duct_id):
    project_id = session.get('current_project')
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        duct_no = request.form['duct_no']
        duct_type = request.form['duct_type']
        duct_size = request.form['duct_size']
        quantity = request.form['quantity']
        remarks = request.form['remarks']

        cursor.execute("""
            UPDATE ducts SET duct_no=?, duct_type=?, duct_size=?, quantity=?, remarks=?
            WHERE id=?
        """, (duct_no, duct_type, duct_size, quantity, remarks, duct_id))
        conn.commit()
        conn.close()
        return redirect(f'/measurement_sheet/{project_id}')

    cursor.execute("SELECT * FROM ducts WHERE id=?", (duct_id,))
    row = cursor.fetchone()
    conn.close()

    return render_template("edit_measurement.html", row=row, project_id=project_id)


@app.route('/submit_sheet')
def submit_sheet():
    project_id = session.get('current_project')
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET design_status='completed' WHERE id=?", (project_id,))
    conn.commit()
    conn.close()
    flash("Measurement Sheet Submitted Successfully", "success")
    return redirect('/dashboard')
    # ---------- PROJECT SUMMARY VIEW ----------
@app.route('/project_summary')
def project_summary():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, enquiry_id FROM projects")
    projects = [{'id': row[0], 'enquiry_id': row[1]} for row in cursor.fetchall()]
    conn.close()
    return render_template('project_summary.html', projects=projects)


@app.route('/get_summary_data/<int:project_id>')
def get_summary_data(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Project Basic Info
    cursor.execute("""
        SELECT client_name, project_incharge, start_date, end_date, drawing_file
        FROM projects WHERE id=?
    """, (project_id,))
    row = cursor.fetchone()
    project_info = {
        'client': row[0],
        'project_incharge': row[1],
        'start_date': row[2],
        'end_date': row[3],
        'source_drawing': row[4]
    }

    # Gauge Summary Calculation (dummy logic: duct_size includes gauge number like '100G', etc.)
    cursor.execute("SELECT duct_size, quantity FROM ducts WHERE project_id=?", (project_id,))
    entries = cursor.fetchall()
    gauge_summary = {}
    for size, qty in entries:
        # Assuming gauge is extracted from duct_size, e.g., '18G'
        if 'G' in size:
            parts = size.upper().split('G')
            gauge = parts[0].strip() + 'G' if parts[0].strip().isdigit() else 'Unknown'
        else:
            gauge = 'Unknown'
        gauge_summary[gauge] = gauge_summary.get(gauge, 0) + qty

    # Stage Progress (dummy values or can be calculated from another table)
    stages = {
        'cutting': 50,
        'plasma': 40,
        'boxing': 30,
        'qc': 20,
        'dispatch': 10
    }

    conn.close()
    return jsonify({
        **project_info,
        'gauge_summary': gauge_summary,
        'stages': stages
    })
    # ---------- EMPLOYEE REGISTRATION ----------
@app.route('/employee_register', methods=['GET', 'POST'])
def employee_register():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        cursor.execute("""
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, designation, email, phone, username, password))
        conn.commit()
        flash("Employee Registered Successfully", "success")
        return redirect(url_for('employee_register'))

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    conn.close()
    return render_template("employee_register.html", employees=employees)


@app.route('/employee_edit/<int:id>', methods=['GET', 'POST'])
def employee_edit(id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        cursor.execute("""
            UPDATE employees
            SET name=?, designation=?, email=?, phone=?, username=?, password=?
            WHERE id=?
        """, (name, designation, email, phone, username, password, id))
        conn.commit()
        flash("Employee Updated", "info")
        return redirect(url_for('employee_register'))

    cursor.execute("SELECT * FROM employees WHERE id=?", (id,))
    emp = cursor.fetchone()
    conn.close()
    return render_template("employee_edit.html", emp=emp)


@app.route('/employee_delete/<int:id>')
def employee_delete(id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employees WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Employee Deleted", "danger")
    return redirect(url_for('employee_register'))
    # ---------- MEASUREMENT SHEET ----------
@app.route('/measurement_sheet/<int:project_id>')
def measurement_sheet(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get project basic info
    cursor.execute("SELECT enquiry_id, client_name, project_location, engineer_name, phone FROM measurement_sheets WHERE project_id=?", (project_id,))
    project = cursor.fetchone()

    # Get all duct entries
    cursor.execute("SELECT * FROM duct_entries WHERE project_id=?", (project_id,))
    ducts = cursor.fetchall()

    conn.close()
    return render_template("measurement_sheet.html", 
                           project_id=project_id,
                           enquiry_id=project[0],
                           client_name=project[1],
                           project_location=project[2],
                           engineer_name=project[3],
                           phone=project[4],
                           ducts=ducts)


@app.route('/submit_sheet/<int:project_id>')
def submit_sheet(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET status='Under Review' WHERE id=?", (project_id,))
    conn.commit()
    conn.close()
    flash("Measurement Sheet Submitted", "success")
    return redirect(url_for('dashboard'))
    # ---------- PROJECT SUMMARY ----------
@app.route('/project_summary')
def project_summary():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, enquiry_id FROM projects")
    projects = [{'id': row[0], 'enquiry_id': row[1]} for row in cursor.fetchall()]
    conn.close()
    return render_template('project_summary.html', projects=projects)


@app.route('/get_summary_data/<int:project_id>')
def get_summary_data(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Project details
    cursor.execute("""
        SELECT p.enquiry_id, m.client_name, p.project_incharge, p.start_date, p.end_date, p.source_drawing
        FROM projects p
        LEFT JOIN measurement_sheets m ON p.id = m.project_id
        WHERE p.id=?
    """, (project_id,))
    result = cursor.fetchone()
    if not result:
        return {}

    enquiry_id, client_name, incharge, start, end, drawing = result

    # Gauge summary from duct_entries
    cursor.execute("""
        SELECT duct_size, SUM(quantity) FROM duct_entries WHERE project_id=?
        GROUP BY duct_size
    """, (project_id,))
    gauge_summary = {row[0]: row[1] for row in cursor.fetchall()}

    # Dummy logic for progress stages (real logic should come from production tracking)
    # For demonstration: fetch random or fixed % (here, fixed demo values)
    stages = {
        'cutting': 60,
        'plasma': 45,
        'boxing': 30,
        'qc': 20,
        'dispatch': 10
    }

    conn.close()
    return {
        'enquiry_id': enquiry_id,
        'client': client_name,
        'project_incharge': incharge,
        'start_date': start,
        'end_date': end,
        'source_drawing': drawing,
        'gauge_summary': gauge_summary,
        'stages': stages
    }
    # ---------- APPROVAL FLOW ----------

@app.route('/submit_for_approval/<int:project_id>', methods=['POST'])
def submit_for_approval(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Update project status to "Under Review"
    cursor.execute("UPDATE projects SET approval_status = ? WHERE id = ?", ('Under Review', project_id))
    conn.commit()
    conn.close()

    flash('Project submitted for approval.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/approval_review/<int:project_id>')
def approval_review(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT enquiry_id, approval_status FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    conn.close()

    if not project:
        flash('Project not found.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('approval_review.html', project_id=project_id, enquiry_id=project[0], status=project[1])


@app.route('/approve_project/<int:project_id>', methods=['POST'])
def approve_project(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Set approval status to Approved
    cursor.execute("UPDATE projects SET approval_status = ? WHERE id = ?", ('Approved', project_id))

    # TODO: Push data to Production module (not implemented here)
    # For example: Insert into production table or trigger production workflows

    conn.commit()
    conn.close()

    flash('Project approved and pushed to production.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/send_back_project/<int:project_id>', methods=['POST'])
def send_back_project(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Set approval status back to "Design Process"
    cursor.execute("UPDATE projects SET approval_status = ? WHERE id = ?", ('Design Process', project_id))
    conn.commit()
    conn.close()

    flash('Project sent back to Design Process.', 'warning')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
