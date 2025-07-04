from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import os
import uuid
import csv
import pandas as pd
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret123'

# -------------------- DATABASE INITIALIZATION --------------------
def init_db():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Employees table
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

    # Vendors table
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

    # Projects table
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

    # Measurement Sheet
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

    # Ducts table
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

    # Production Progress Table (5 Phases)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            cutting_done REAL,
            plasma_done REAL,
            boxing_done REAL,
            quality_percent REAL,
            dispatch_percent REAL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # Default admin account
    cursor.execute("SELECT * FROM employees WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Admin User', 'Admin', 'admin@erp.com', '1234567890', 'admin', 'admin123'))

    conn.commit()
    conn.close()

init_db()
# -------------------- AUTH ROUTES --------------------

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user[1]  # name
            session['user_id'] = user[0]  # id
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login to continue.", "warning")
        return redirect(url_for('login'))

    return render_template('dashboard.html', user=session['user'])
    # -------------------- VENDOR MODULE --------------------

@app.route('/vendors')
def vendors():
    if 'user' not in session:
        flash("Please login to continue.", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors")
    vendor_list = cursor.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendor_list)


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


@app.route('/delete_vendor/<int:id>')
def delete_vendor(id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vendors WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Vendor deleted", "info")
    return redirect(url_for('vendors'))


@app.route('/update_vendor/<int:id>', methods=['POST'])
def update_vendor(id):
    name = request.form['name']
    gst = request.form['gst']
    address = request.form['address']
    phone = request.form['phone']
    email = request.form['email']

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE vendors SET name=?, gst=?, address=?, phone=?, email=? WHERE id=?
    ''', (name, gst, address, phone, email, id))
    conn.commit()
    conn.close()
    flash("Vendor updated", "success")
    return redirect(url_for('vendors'))


@app.route('/export_vendors_excel')
def export_vendors_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM vendors', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name="Vendors.xlsx", as_attachment=True)
    # -------------------- PROJECT MODULE --------------------

@app.route('/projects')
def projects():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get all projects with vendor name
    cursor.execute('''
        SELECT p.*, v.name AS vendor_name 
        FROM projects p 
        LEFT JOIN vendors v ON p.vendor_id = v.id
    ''')
    projects = cursor.fetchall()

    # Get all vendors for dropdown
    cursor.execute("SELECT id, name, gst, address FROM vendors")
    vendors = cursor.fetchall()

    conn.close()

    # Dummy Enquiry ID like ENQ123ABC
    enquiry_id = f"ENQ{uuid.uuid4().hex[:6].upper()}"

    return render_template('projects.html',
                           projects=projects,
                           vendors=vendors,
                           enquiry_id=enquiry_id)


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

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO projects (
            enquiry_id, vendor_id, quotation_ro, start_date, end_date,
            location, gst, address, incharge, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (enquiry_id, vendor_id, quotation_ro, start_date, end_date,
          location, gst, address, incharge, notes))
    conn.commit()
    conn.close()

    flash("Project added successfully", "success")
    return redirect(url_for('projects'))


@app.route('/delete_project/<int:id>')
def delete_project(id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Project deleted", "info")
    return redirect(url_for('projects'))


@app.route('/update_project/<int:id>', methods=['POST'])
def update_project(id):
    quotation_ro = request.form['quotation_ro']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    location = request.form['location']
    gst = request.form['gst']
    address = request.form['address']
    incharge = request.form['incharge']
    notes = request.form['notes']

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE projects SET quotation_ro=?, start_date=?, end_date=?,
            location=?, gst=?, address=?, incharge=?, notes=?
        WHERE id=?
    ''', (quotation_ro, start_date, end_date, location, gst, address, incharge, notes, id))
    conn.commit()
    conn.close()
    flash("Project updated", "success")
    return redirect(url_for('projects'))


@app.route('/export_projects_excel')
def export_projects_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('''
        SELECT p.*, v.name as vendor_name FROM projects p
        LEFT JOIN vendors v ON p.vendor_id = v.id
    ''', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name="Projects.xlsx", as_attachment=True)
    # -------------------- MEASUREMENT SHEET --------------------

@app.route('/measurement_sheet/<int:project_id>')
def measurement_sheet(project_id):
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get project info
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()

    # Get measurement sheet
    cursor.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,))
    sheet = cursor.fetchone()

    # Get all ducts
    cursor.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,))
    ducts = cursor.fetchall()

    conn.close()

    return render_template('measurement_sheet.html',
                           project=project,
                           sheet=sheet,
                           ducts=ducts,
                           project_id=project_id)


@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    project_id = request.form['project_id']
    client = request.form['client']
    company = request.form['company']
    location = request.form['location']
    engineer = request.form['engineer']
    phone = request.form['phone']

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute('''
            UPDATE measurement_sheet
            SET client=?, company=?, location=?, engineer=?, phone=?
            WHERE project_id=?
        ''', (client, company, location, engineer, phone, project_id))
    else:
        cursor.execute('''
            INSERT INTO measurement_sheet (
                project_id, client, company, location, engineer, phone
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, client, company, location, engineer, phone))

    conn.commit()
    conn.close()
    flash("Measurement sheet saved", "success")
    return redirect(url_for('measurement_sheet', project_id=project_id))


# -------------------- DUCT ENTRY --------------------

@app.route('/add_duct', methods=['POST'])
def add_duct():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    project_id = request.form['project_id']
    duct_no = request.form['duct_no']
    duct_type = request.form['duct_type']
    duct_size = request.form['duct_size']
    quantity = request.form['quantity']
    remarks = request.form.get('remarks', '')

    cursor.execute('''
        INSERT INTO ducts (project_id, duct_no, duct_type, duct_size, quantity, remarks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, duct_no, duct_type, duct_size, quantity, remarks))

    conn.commit()
    conn.close()
    flash("Duct added", "success")
    return redirect(url_for('measurement_sheet', project_id=project_id))


# -------------------- DESIGN PROCESS APPROVAL --------------------

@app.route('/update_design_process/<int:project_id>')
def update_design_process(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET approval_status='Approved' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("Design Process Approved", "success")
    return redirect(url_for('measurement_sheet', project_id=project_id))


# -------------------- EXPORT MEASUREMENT --------------------

@app.route('/export_measurements_excel')
def export_measurements_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM measurement_sheet', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name="Measurements.xlsx", as_attachment=True)
    # -------------------- PRODUCTION MODULE --------------------

@app.route('/production/<int:project_id>')
def production(project_id):
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get measurement sheet total area (dummy sum of quantity for now)
    cursor.execute('SELECT SUM(quantity) FROM ducts WHERE project_id = ?', (project_id,))
    total_area = cursor.fetchone()[0] or 0

    # Get production entry
    cursor.execute("SELECT * FROM production WHERE project_id = ?", (project_id,))
    row = cursor.fetchone()

    if row:
        cutting = row[2] or 0
        plasma = row[3] or 0
        boxing = row[4] or 0
        quality = row[5] or 0
        dispatch = row[6] or 0
    else:
        cutting = plasma = boxing = quality = dispatch = 0

    # Percentages for area-based
    cutting_percent = round((cutting / total_area) * 100, 2) if total_area else 0
    plasma_percent = round((plasma / total_area) * 100, 2) if total_area else 0
    boxing_percent = round((boxing / total_area) * 100, 2) if total_area else 0

    # Overall progress
    overall_progress = round((cutting_percent + plasma_percent + boxing_percent + quality + dispatch) / 5, 2)

    conn.close()

    return render_template('production.html',
                           project_id=project_id,
                           cutting=cutting,
                           plasma=plasma,
                           boxing=boxing,
                           quality=quality,
                           dispatch=dispatch,
                           cutting_percent=cutting_percent,
                           plasma_percent=plasma_percent,
                           boxing_percent=boxing_percent,
                           quality_percent=quality,
                           dispatch_percent=dispatch,
                           overall=overall_progress,
                           total_area=total_area)


@app.route('/update_production/<int:project_id>', methods=['POST'])
def update_production(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cutting_done = float(request.form.get('cutting_done', 0))
    plasma_done = float(request.form.get('plasma_done', 0))
    boxing_done = float(request.form.get('boxing_done', 0))
    quality_percent = float(request.form.get('quality_percent', 0))
    dispatch_percent = float(request.form.get('dispatch_percent', 0))

    cursor.execute("SELECT * FROM production WHERE project_id = ?", (project_id,))
    exists = cursor.fetchone()

    if exists:
        cursor.execute('''
            UPDATE production
            SET cutting_done = ?, plasma_done = ?, boxing_done = ?, quality_percent = ?, dispatch_percent = ?
            WHERE project_id = ?
        ''', (cutting_done, plasma_done, boxing_done, quality_percent, dispatch_percent, project_id))
    else:
        cursor.execute('''
            INSERT INTO production (project_id, cutting_done, plasma_done, boxing_done, quality_percent, dispatch_percent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, cutting_done, plasma_done, boxing_done, quality_percent, dispatch_percent))

    conn.commit()
    conn.close()
    flash("Production updated", "success")
    return redirect(url_for('production', project_id=project_id))


# -------------------- EXPORT PRODUCTION --------------------

@app.route('/export_production_excel')
def export_production_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM production', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name="Production.xlsx", as_attachment=True)
    # ------------------ MAIN SERVER ------------------

if __name__ == '__main__':
    init_db()  # Ensure DB is initialized on first run
    app.run(debug=True)
