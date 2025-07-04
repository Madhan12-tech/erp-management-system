from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import os
import uuid
import csv
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'secret123'

# ---------------- DATABASE INITIALIZATION ----------------
def init_db():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Employee table
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

    # Vendor table
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

    # Project table
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

    # Measurement sheet
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

    # Production progress tracking table
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

    # Insert dummy admin user if not exists
    cursor.execute("SELECT * FROM employees WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Admin User', 'Admin', 'admin@erp.com', '1234567890', 'admin', 'admin123'))

    conn.commit()
    conn.close()

# Call DB initializer
init_db()
# ---------------- AUTH ROUTES ----------------

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = username
            flash("Login successful", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))


# ---------------- DASHBOARD ----------------

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))
    return render_template('dashboard.html')
    # ---------------- VENDOR ROUTES ----------------

@app.route('/vendors')
def vendors():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

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
    # ---------------- PROJECT ROUTES ----------------

@app.route('/projects')
def projects():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.*, v.name AS vendor_name 
        FROM projects p 
        LEFT JOIN vendors v ON p.vendor_id = v.id
    ''')
    projects = cursor.fetchall()

    cursor.execute("SELECT id, name, gst, address FROM vendors")
    vendors = cursor.fetchall()

    conn.close()

    enquiry_id = f"ENQ{uuid.uuid4().hex[:6].upper()}"
    return render_template('projects.html',
                           projects=projects,
                           vendors=vendors,
                           enquiry_id=enquiry_id)


@app.route('/add_project', methods=['POST'])
def add_project():
    data = request.form
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO projects (enquiry_id, vendor_id, quotation_ro, start_date, end_date, location, gst, address, incharge, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['enquiry_id'], data['vendor_id'], data['quotation_ro'], data['start_date'],
        data['end_date'], data['location'], data['gst'], data['address'], data['incharge'], data['notes']
    ))
    conn.commit()
    conn.close()
    flash("Project added successfully", "success")
    return redirect(url_for('projects'))
    @app.route('/measurement_sheet/<int:project_id>')
def measurement_sheet(project_id):
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,))
    sheet = cursor.fetchone()

    cursor.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,))
    ducts = cursor.fetchall()

    conn.close()
    return render_template('measurement_sheet.html', sheet=sheet, ducts=ducts, project_id=project_id)


@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    data = request.form
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO measurement_sheet (project_id, client, company, location, engineer, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data['project_id'], data['client'], data['company'],
        data['location'], data['engineer'], data['phone']
    ))
    conn.commit()
    conn.close()
    flash("Measurement sheet saved", "success")
    return redirect(url_for('measurement_sheet', project_id=data['project_id']))
    # ---------------- DUCT ENTRY ----------------

@app.route('/add_duct', methods=['POST'])
def add_duct():
    project_id = request.form.get('project_id')
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
    flash("Duct added successfully", "success")
    return redirect(url_for('measurement_sheet', project_id=project_id))
    @app.route('/production/<int:project_id>')
def production(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,))
    ducts = cursor.fetchall()

    cursor.execute("SELECT * FROM production WHERE project_id = ?", (project_id,))
    prod_data = cursor.fetchone()

    conn.close()
    return render_template('production.html',
                           ducts=ducts,
                           prod_data=prod_data,
                           project_id=project_id)


@app.route('/update_production/<int:project_id>', methods=['POST'])
def update_production(project_id):
    cutting_done = request.form.get('cutting_done', 0)
    plasma_done = request.form.get('plasma_done', 0)
    boxing_done = request.form.get('boxing_done', 0)
    quality_percent = request.form.get('quality_percent', 0)
    dispatch_percent = request.form.get('dispatch_percent', 0)

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM production WHERE project_id = ?", (project_id,))
    exists = cursor.fetchone()

    if exists:
        cursor.execute('''
            UPDATE production
            SET cutting_done=?, plasma_done=?, boxing_done=?, quality_percent=?, dispatch_percent=?
            WHERE project_id=?
        ''', (cutting_done, plasma_done, boxing_done, quality_percent, dispatch_percent, project_id))
    else:
        cursor.execute('''
            INSERT INTO production (project_id, cutting_done, plasma_done, boxing_done, quality_percent, dispatch_percent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, cutting_done, plasma_done, boxing_done, quality_percent, dispatch_percent))

    conn.commit()
    conn.close()
    flash("Production data updated", "success")
    return redirect(url_for('production', project_id=project_id))
    # ---------------- DASHBOARD ----------------

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM vendors")
    total_vendors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects")
    total_projects = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM measurement_sheet")
    total_measurements = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ducts")
    total_ducts = cursor.fetchone()[0]

    conn.close()

    return render_template('dashboard.html',
                           total_vendors=total_vendors,
                           total_projects=total_projects,
                           total_measurements=total_measurements,
                           total_ducts=total_ducts)

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


@app.route('/export_measurement_excel')
def export_measurement_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM measurement_sheet', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="MeasurementSheet.xlsx", as_attachment=True)


@app.route('/export_ducts_excel')
def export_ducts_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM ducts', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="Ducts.xlsx", as_attachment=True)


@app.route('/export_production_excel')
def export_production_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query('SELECT * FROM production', conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="Production.xlsx", as_attachment=True)
    # ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))


# ---------------- RUN FLASK APP ----------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
