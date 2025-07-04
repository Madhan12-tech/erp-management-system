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

# ---------- DB INITIALIZATION ----------
def init_db():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Employee Table
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

    # Vendor Table
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

    # Dummy vendors if empty
    cursor.execute("SELECT COUNT(*) FROM vendors")
    if cursor.fetchone()[0] == 0:
        dummy_vendors = [
            ('Star Fabricators', 'GST1234ABC', 'Chennai, TN', '9876543210', 'star@example.com'),
            ('Delta Ducts', 'GST5678XYZ', 'Coimbatore, TN', '9876543211', 'delta@example.com'),
            ('AirMax Solutions', 'GST1111XYZ', 'Hyderabad, TS', '9876543212', 'airmax@example.com')
        ]
        cursor.executemany('''
            INSERT INTO vendors (name, gst, address, phone, email)
            VALUES (?, ?, ?, ?, ?)
        ''', dummy_vendors)

    # Project Table
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

    # Production Progress Table (5 Phase Tracking)
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

    # Admin Insert if not exists
    cursor.execute("SELECT * FROM employees WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Admin', 'Admin', 'admin@erp.com', '9999999999', 'admin', 'admin123'))

    conn.commit()
    conn.close()

init_db()
# ---------------- LOGIN & LOGOUT ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM employees WHERE username=? AND password=?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = username
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))
    return render_template('dashboard.html')
    # ---------------- VENDOR ROUTES ----------------
@app.route('/vendor_register', methods=['GET', 'POST'])
def vendor_register():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
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
        return redirect(url_for('vendor_register'))

    # Dummy vendors for dropdown prefill test
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vendors')
    vendors = cursor.fetchall()
    conn.close()

    return render_template('vendors.html', vendors=vendors)


@app.route('/delete_vendor/<int:vendor_id>')
def delete_vendor(vendor_id):
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM vendors WHERE id = ?', (vendor_id,))
    conn.commit()
    conn.close()
    flash("Vendor deleted", "info")
    return redirect(url_for('vendor_register'))
    # ---------------- PROJECT ROUTES ----------------
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

    # Generate Enquiry ID like ENQ123ABC
    enquiry_id = f"ENQ{uuid.uuid4().hex[:6].upper()}"

    return render_template('projects.html',
                           projects=projects,
                           vendors=vendors,
                           enquiry_id=enquiry_id)


@app.route('/add_project', methods=['POST'])
def add_project():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

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
    file = request.files['file']

    filename = ''
    if file:
        filename = file.filename
        upload_path = os.path.join('static/uploads', filename)
        file.save(upload_path)

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
    # ---------------- MEASUREMENT SHEET ROUTES ----------------
@app.route('/measurement_sheet/<int:project_id>')
def measurement_sheet(project_id):
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get project info
    cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    project = cursor.fetchone()

    # Get ducts for this project
    cursor.execute('SELECT * FROM ducts WHERE project_id = ?', (project_id,))
    ducts = cursor.fetchall()

    conn.close()

    return render_template('measurement_sheet.html',
                           project=project,
                           ducts=ducts,
                           project_id=project_id)


@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    project_id = request.form['project_id']
    client = request.form['client']
    company = request.form['company']
    location = request.form['location']
    engineer = request.form['engineer']
    phone = request.form['phone']

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO measurement_sheet 
        (project_id, client, company, location, engineer, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, client, company, location, engineer, phone))
    conn.commit()
    conn.close()

    flash("Measurement sheet submitted", "success")
    return redirect(url_for('measurement_sheet', project_id=project_id))


@app.route('/add_duct', methods=['POST'])
def add_duct():
    project_id = request.form['project_id']
    duct_no = request.form['duct_no']
    duct_type = request.form['duct_type']
    duct_size = request.form['duct_size']
    quantity = request.form['quantity']
    remarks = request.form.get('remarks', '')

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ducts (project_id, duct_no, duct_type, duct_size, quantity, remarks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, duct_no, duct_type, duct_size, quantity, remarks))
    conn.commit()
    conn.close()

    return redirect(url_for('measurement_sheet', project_id=project_id))
    # ---------------- PRODUCTION MODULE ROUTES ----------------
@app.route('/production/<int:project_id>')
def production(project_id):
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get total area from measurement ducts
    cursor.execute('SELECT SUM(quantity) FROM ducts WHERE project_id = ?', (project_id,))
    total_area = cursor.fetchone()[0] or 0

    # Get existing production data
    cursor.execute('SELECT * FROM production WHERE project_id = ?', (project_id,))
    data = cursor.fetchone()

    if data:
        cutting = data[2] or 0
        plasma = data[3] or 0
        boxing = data[4] or 0
        quality = data[5] or 0
        dispatch = data[6] or 0
    else:
        cutting = plasma = boxing = quality = dispatch = 0

    conn.close()

    # Calculate percentages only if total_area > 0
    cutting_percent = (cutting / total_area * 100) if total_area else 0
    plasma_percent = (plasma / total_area * 100) if total_area else 0
    boxing_percent = (boxing / total_area * 100) if total_area else 0
    quality_percent = quality
    dispatch_percent = dispatch

    overall = (cutting_percent + plasma_percent + boxing_percent + quality_percent + dispatch_percent) / 5

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
                           quality_percent=quality_percent,
                           dispatch_percent=dispatch_percent,
                           overall=overall,
                           total_area=total_area)


@app.route('/update_production/<int:project_id>', methods=['POST'])
def update_production(project_id):
    cutting = float(request.form.get('cutting', 0))
    plasma = float(request.form.get('plasma', 0))
    boxing = float(request.form.get('boxing', 0))
    quality = float(request.form.get('quality', 0))
    dispatch = float(request.form.get('dispatch', 0))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Check if already exists
    cursor.execute('SELECT id FROM production WHERE project_id = ?', (project_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute('''
            UPDATE production SET 
            cutting_done = ?, plasma_done = ?, boxing_done = ?, 
            quality_percent = ?, dispatch_percent = ?
            WHERE project_id = ?
        ''', (cutting, plasma, boxing, quality, dispatch, project_id))
    else:
        cursor.execute('''
            INSERT INTO production 
            (project_id, cutting_done, plasma_done, boxing_done, quality_percent, dispatch_percent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, cutting, plasma, boxing, quality, dispatch))

    conn.commit()
    conn.close()

    flash("Production updated successfully", "success")
    return redirect(url_for('production', project_id=project_id))
    # ---------------- DASHBOARD ROUTE ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    return render_template('dashboard.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))

@app.route('/export_projects_excel')
def export_projects_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('''
        SELECT p.*, v.name as vendor_name
        FROM projects p
        LEFT JOIN vendors v ON p.vendor_id = v.id
    ''', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output,
                     download_name="Projects.xlsx",
                     as_attachment=True)

@app.route('/export_projects_pdf')
def export_projects_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.enquiry_id, v.name, p.location, p.start_date, p.end_date
        FROM projects p
        LEFT JOIN vendors v ON p.vendor_id = v.id
    ''')
    rows = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 40, "Projects Report")

    y = height - 80
    p.setFont("Helvetica", 10)
    for row in rows:
        line = f"Enquiry: {row[0]} | Vendor: {row[1]} | Location: {row[2]} | {row[3]} to {row[4]}"
        p.drawString(50, y, line)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)

    return send_file(buffer,
                     download_name="Projects.pdf",
                     as_attachment=True)
    @app.route('/export_vendors_excel')
def export_vendors_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM vendors', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name="Vendors.xlsx", as_attachment=True)

@app.route('/export_vendors_pdf')
def export_vendors_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, gst, address FROM vendors')
    rows = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 40, "Vendors Report")

    y = height - 80
    p.setFont("Helvetica", 10)
    for row in rows:
        line = f"Vendor: {row[0]} | GST: {row[1]} | Address: {row[2]}"
        p.drawString(50, y, line)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="Vendors.pdf", as_attachment=True)
    
    @app.route('/export_measurements_excel')
def export_measurements_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM measurement_sheet', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name="MeasurementSheet.xlsx", as_attachment=True)

    @app.route('/export_measurements_pdf')
def export_measurements_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('SELECT client, company, location, engineer, phone FROM measurement_sheet')
    rows = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 40, "Measurement Sheet Report")

    y = height - 80
    p.setFont("Helvetica", 10)
    for row in rows:
        line = f"{row[0]} | {row[1]} | {row[2]} | Eng: {row[3]} | {row[4]}"
        p.drawString(50, y, line)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="MeasurementSheet.pdf", as_attachment=True)
    @app.route('/export_production_excel')
def export_production_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM production', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name="ProductionData.xlsx", as_attachment=True)

@app.route('/export_production_pdf')
def export_production_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT project_id, cutting_done, plasma_done, boxing_done,
               quality_percent, dispatch_percent
        FROM production
    ''')
    rows = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 40, "Production Report")

    y = height - 80
    p.setFont("Helvetica", 10)
    for row in rows:
        line = f"Project ID: {row[0]} | Cutting: {row[1]} | Plasma: {row[2]} | Boxing: {row[3]} | QC: {row[4]}% | Dispatch: {row[5]}%"
        p.drawString(50, y, line)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="Production.pdf", as_attachment=True)
    @app.route('/export_ducts_excel')
def export_ducts_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM ducts', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name="DuctEntries.xlsx", as_attachment=True)

@app.route('/export_ducts_pdf')
def export_ducts_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT project_id, duct_no, duct_type, duct_size, quantity, remarks 
        FROM ducts
    ''')
    rows = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 40, "Duct Entries Report")

    y = height - 80
    p.setFont("Helvetica", 10)
    for row in rows:
        line = f"Proj ID: {row[0]} | Duct: {row[1]} | Type: {row[2]} | Size: {row[3]} | Qty: {row[4]} | {row[5]}"
        p.drawString(50, y, line)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="DuctEntries.pdf", as_attachment=True)
    
    @app.route('/export_employees_excel')
def export_employees_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT id, name, designation, email, phone FROM employees', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name="Employees.xlsx", as_attachment=True)

@app.route('/export_employees_pdf')
def export_employees_pdf():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, designation, email, phone FROM employees')
    rows = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 40, "Employees Report")

    y = height - 80
    p.setFont("Helvetica", 10)
    for row in rows:
        line = f"{row[0]} | {row[1]} | {row[2]} | {row[3]}"
        p.drawString(50, y, line)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="Employees.pdf", as_attachment=True)
    

# ---------------- START FLASK ----------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
