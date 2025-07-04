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
    
@app.route('/export/vendors')
def export_vendors_excel():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, gst, address, phone, email FROM vendors")
    rows = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=["ID", "Name", "GST", "Address", "Phone", "Email"])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendors')

    output.seek(0)
    return send_file(output, download_name="vendors.xlsx", as_attachment=True)
    @app.route('/export/projects')
def export_projects_excel():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.enquiry_id, v.name AS vendor_name, p.quotation_ro, 
               p.start_date, p.end_date, p.location, p.gst, p.address, 
               p.incharge, p.notes, p.approval_status
        FROM projects p
        LEFT JOIN vendors v ON p.vendor_id = v.id
    ''')
    rows = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=["ID", "Enquiry ID", "Vendor Name", "Quotation RO", "Start Date",
                                     "End Date", "Location", "GST", "Address", "Incharge", "Notes", "Status"])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')

    output.seek(0)
    return send_file(output, download_name="projects.xlsx", as_attachment=True)
    @app.route('/export/ducts/<int:project_id>')
def export_ducts_excel(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT duct_no, duct_type, duct_size, quantity, remarks
        FROM ducts WHERE project_id = ?
    ''', (project_id,))
    rows = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=["Duct No", "Type", "Size", "Quantity", "Remarks"])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ducts')

    output.seek(0)
    return send_file(output, download_name=f"ducts_project_{project_id}.xlsx", as_attachment=True)
    @app.route('/export/measurements/<int:project_id>')
def export_measurements_excel(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT client, company, location, engineer, phone, created_at 
        FROM measurement_sheet 
        WHERE project_id = ?
    ''', (project_id,))
    rows = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=["Client", "Company", "Location", "Engineer", "Phone", "Created At"])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Measurement Sheet')

    output.seek(0)
    return send_file(output, download_name=f"measurement_sheet_project_{project_id}.xlsx", as_attachment=True)
    @app.route('/export/employees')
def export_employees_excel():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, designation, email, phone, username FROM employees")
    rows = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=["ID", "Name", "Designation", "Email", "Phone", "Username"])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Employees')

    output.seek(0)
    return send_file(output, download_name="employees.xlsx", as_attachment=True)
    @app.route('/export/production')
def export_production_excel():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, pr.enquiry_id, prod.cutting_done, prod.plasma_done, prod.boxing_done,
               prod.quality_percent, prod.dispatch_percent
        FROM production prod
        JOIN projects pr ON prod.project_id = pr.id
        JOIN projects p ON prod.project_id = p.id
    ''')
    rows = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=[
        "Project ID", "Enquiry ID", "Sheet Cutting (sqm)", "Plasma & Fab (sqm)",
        "Boxing & Assembly (sqm)", "Quality Check (%)", "Dispatch (%)"
    ])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Production Progress')

    output.seek(0)
    return send_file(output, download_name="production_progress.xlsx", as_attachment=True)
    @app.route('/export/production/csv')
def export_production_csv():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, pr.enquiry_id, prod.cutting_done, prod.plasma_done, prod.boxing_done,
               prod.quality_percent, prod.dispatch_percent
        FROM production prod
        JOIN projects pr ON prod.project_id = pr.id
        JOIN projects p ON prod.project_id = p.id
    ''')
    rows = cursor.fetchall()
    conn.close()

    output = BytesIO()
    writer = csv.writer(output)
    writer.writerow(["Project ID", "Enquiry ID", "Sheet Cutting (sqm)", "Plasma & Fab (sqm)",
                     "Boxing & Assembly (sqm)", "Quality Check (%)", "Dispatch (%)"])
    writer.writerows(rows)
    output.seek(0)

    return send_file(output, download_name="production_progress.csv", as_attachment=True, mimetype='text/csv')

# ---------------- START FLASK ----------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
