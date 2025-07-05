from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import sqlite3
import pandas as pd
import os
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret123'

# ---------- DATABASE INITIALIZATION ----------
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

    # Insert dummy vendors
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

    # Insert default admin if not exists
    cursor.execute("SELECT * FROM employees WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Admin', 'Administrator', 'admin@erp.com', '1234567890', 'admin', 'admin123'))

    conn.commit()
    conn.close()

# Initialize DB on app start
init_db()
# ---------------- LOGIN ROUTES ----------------
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
            session['user'] = user[1]
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "error")
            return redirect(url_for('login'))
return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- REGISTER EMPLOYEE ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, designation, email, phone, username, password))
        conn.commit()
        conn.close()
        flash("Employee registered successfully", "success")
        return redirect(url_for('dashboard'))

    return render_template('register.html')

# ---------------- DASHBOARD ----------------
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
    return render_template('dashboard.html', user=session['user'], total_projects=total_projects,
                           total_vendors=total_vendors, total_employees=total_employees)
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
    flash("Vendor deleted", "info")
    return redirect(url_for('vendors'))

# ---------------- PROJECT MODULE + POPUP ----------------
@app.route('/projects')
def projects():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Dummy vendor fallback
    cursor.execute("SELECT id, name FROM vendors")
    vendors = cursor.fetchall()
    if not vendors:
        cursor.execute("INSERT INTO vendors (name, gst, address, phone, email) VALUES (?, ?, ?, ?, ?)",
                       ("Dummy Vendor", "GST000", "Dummy Address", "0000000000", "dummy@example.com"))
        conn.commit()
        cursor.execute("SELECT id, name FROM vendors")
        vendors = cursor.fetchall()

    cursor.execute("SELECT p.*, v.name FROM projects p LEFT JOIN vendors v ON p.vendor_id = v.id")
    projects = cursor.fetchall()
    conn.close()
    return render_template('projects.html', vendors=vendors, projects=projects)

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
    file = request.files['file']

    filename = ''
    if file:
        filename = f"uploads/{uuid.uuid4().hex}_{file.filename}"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        file.save(filename)

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO projects (
            enquiry_id, vendor_id, quotation_ro, start_date, end_date, location,
            gst, address, incharge, notes, file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (enquiry_id, vendor_id, quotation_ro, start_date, end_date, location,
          gst, address, incharge, notes, filename))
    conn.commit()
    conn.close()
    flash("Project added successfully", "success")
    return redirect(url_for('projects'))

# ---------------- MEASUREMENT SHEET ----------------
@app.route('/measurement/<int:project_id>')
def measurement(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,))
    measurement = cursor.fetchone()
    conn.close()
    return render_template('measurement.html', measurement=measurement, project_id=project_id)

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
    cursor.execute('''
        INSERT INTO measurement_sheet (project_id, client, company, location, engineer, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, client, company, location, engineer, phone))
    conn.commit()
    conn.close()
    flash("Measurement added", "success")
    return redirect(url_for('projects'))
    # ---------------- DUCT ENTRY ----------------
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
    flash("Duct entry added", "success")
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
    @app.route('/update_design_status/<int:project_id>', methods=['POST'])
def update_design_status(project_id):
    new_status = request.form['new_status']
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET approval_status=? WHERE id=?", (new_status, project_id))
    conn.commit()
    conn.close()
    flash("Design status updated", "info")
    return redirect(url_for('projects'))
    # ---------------- PRODUCTION MODULE ----------------

# View Production for a Project
@app.route('/production/<int:project_id>')
def production(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get total area from measurement_entries
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
    cutting_done = request.form.get('cutting_done', 0)
    plasma_done = request.form.get('plasma_done', 0)
    boxing_done = request.form.get('boxing_done', 0)
    quality_percent = request.form.get('quality_percent', 0)
    dispatch_percent = request.form.get('dispatch_percent', 0)

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Check if entry exists
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
    # example logic inside production.html (Jinja)
{% set cutting_percent = (production.cutting_done / total_area * 100) if total_area else 0 %}
{% set plasma_percent = (production.plasma_done / total_area * 100) if total_area else 0 %}
{% set boxing_percent = (production.boxing_done / total_area * 100) if total_area else 0 %}
{% set overall = ((cutting_percent + plasma_percent + boxing_percent + quality + dispatch) / 5) %}
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

    # Project info
    cursor.execute('SELECT * FROM projects WHERE id=?', (project_id,))
    project = cursor.fetchone()

    # Measurement sheet total area
    cursor.execute('SELECT SUM(area) FROM measurement_entries WHERE project_id=?', (project_id,))
    total_area = cursor.fetchone()[0] or 0

    # Production data
    cursor.execute('SELECT * FROM production WHERE project_id=?', (project_id,))
    prod = cursor.fetchone()

    conn.close()

    # Progress calculations
    cutting_done = prod[2] if prod else 0
    plasma_done = prod[3] if prod else 0
    boxing_done = prod[4] if prod else 0
    quality_percent = prod[5] if prod else 0
    dispatch_percent = prod[6] if prod else 0

    def calc_percent(done):
        return (done / total_area) * 100 if total_area else 0

    percent_data = {
        'Cutting': calc_percent(cutting_done),
        'Fabrication': calc_percent(plasma_done),
        'Boxing': calc_percent(boxing_done),
        'Quality Check': quality_percent,
        'Dispatch': dispatch_percent
    }

    overall_percent = sum(percent_data.values()) / len(percent_data)

    return render_template('summary.html',
                           project=project,
                           total_area=total_area,
                           done_data={
                               'Cutting': cutting_done,
                               'Fabrication': plasma_done,
                               'Boxing': boxing_done
                           },
                           percent_data=percent_data,
                           overall_percent=overall_percent)
    @app.route('/register_employee', methods=['GET', 'POST'])
def register_employee():
    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO employees (name, designation, email, phone, username, password)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, designation, email, phone, username, password))
            conn.commit()
            flash("Employee registered successfully", "success")
        except sqlite3.IntegrityError:
            flash("Username already exists", "danger")
        conn.close()
        return redirect(url_for('register_employee'))

    return render_template('register_employee.html')
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
            session['user'] = user[1]
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')
    @app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))
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
    flash('Duct entry added successfully!', 'success')
    return redirect(url_for('project_detail', project_id=project_id))
    @app.route('/project_detail/<int:project_id>')
def project_detail(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    project = cursor.fetchone()

    cursor.execute('SELECT * FROM ducts WHERE project_id = ?', (project_id,))
    ducts = cursor.fetchall()

    conn.close()
    return render_template('project_detail.html', project=project, ducts=ducts)
    # ---------------- PRODUCTION MODULE ----------------

@app.route('/production/<int:project_id>', methods=['GET', 'POST'])
def production(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        cutting_done = request.form.get('cutting_done', 0)
        plasma_done = request.form.get('plasma_done', 0)
        boxing_done = request.form.get('boxing_done', 0)
        quality_percent = request.form.get('quality_percent', 0)
        dispatch_percent = request.form.get('dispatch_percent', 0)

        cursor.execute('''
            INSERT OR REPLACE INTO production (
                id, project_id, cutting_done, plasma_done, boxing_done, 
                quality_percent, dispatch_percent
            )
            VALUES (
                COALESCE((SELECT id FROM production WHERE project_id = ?), NULL), 
                ?, ?, ?, ?, ?, ?
            )
        ''', (
            project_id, project_id, cutting_done, plasma_done,
            boxing_done, quality_percent, dispatch_percent
        ))
        conn.commit()
        flash("Production updated successfully!", "success")
        return redirect(url_for('production', project_id=project_id))

    # Fetch current project production data
    cursor.execute('SELECT * FROM production WHERE project_id = ?', (project_id,))
    production_data = cursor.fetchone()

    # Fetch total area from ducts for this project
    cursor.execute('''
        SELECT SUM(quantity) FROM ducts WHERE project_id = ?
    ''', (project_id,))
    total_quantity = cursor.fetchone()[0] or 0

    conn.close()
    return render_template('production.html', project_id=project_id, production=production_data, total_quantity=total_quantity)
    # ---------------- SUMMARY PAGE ----------------

@app.route('/summary/<int:project_id>')
def summary(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM production WHERE project_id = ?', (project_id,))
    production = cursor.fetchone()

    cursor.execute('SELECT * FROM ducts WHERE project_id = ?', (project_id,))
    ducts = cursor.fetchall()

    conn.close()
    return render_template('summary.html', project_id=project_id, production=production, ducts=ducts)


# ---------------- EXPORT FUNCTIONS ----------------

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


@app.route('/export_production_excel/<int:project_id>')
def export_production_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM production WHERE project_id = ?', conn, params=(project_id,))
    conn.close()
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name=f"Production_Project_{project_id}.xlsx", as_attachment=True)
    # ------------------- MAIN ----------------------

if __name__ == '__main__':
    if not os.path.exists('erp.db'):
        init_db()
    app.run(debug=True)
