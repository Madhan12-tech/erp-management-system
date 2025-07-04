from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
import sqlite3
import os
import uuid
from io import BytesIO
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import csv

app = Flask(__name__)
app.secret_key = 'secret123'

# ---------------- DB INIT ----------------
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
            username TEXT,
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
            approval_status TEXT DEFAULT 'Design Process'
        )
    ''')

    # Measurement Sheet Header
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS measurement_sheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client TEXT,
            company TEXT,
            location TEXT,
            engineer TEXT,
            phone TEXT
        )
    ''')

    # Duct Entry Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ducts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            duct_no TEXT,
            duct_type TEXT,
            duct_size TEXT,
            quantity INTEGER,
            remarks TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE username=? AND password=?", (uname, pwd))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user'] = user[1]
            flash('Login Successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Credentials!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# ---------------- REGISTER EMPLOYEE ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        desg = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']
        cursor.execute("INSERT INTO employees (name, designation, email, phone, username, password) VALUES (?, ?, ?, ?, ?, ?)",
                       (name, desg, email, phone, username, password))
        conn.commit()
        flash('Employee registered successfully!', 'success')
        return redirect(url_for('register'))
    
    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    conn.close()
    return render_template('register.html', employees=employees)

@app.route('/employee_edit/<int:id>', methods=['GET', 'POST'])
def employee_edit(id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        desg = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']
        cursor.execute('''
            UPDATE employees SET name=?, designation=?, email=?, phone=?, username=?, password=? WHERE id=?
        ''', (name, desg, email, phone, username, password, id))
        conn.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('register'))

    cursor.execute("SELECT * FROM employees WHERE id=?", (id,))
    row = cursor.fetchone()
    conn.close()
    return render_template('employee_edit.html', row=row)

@app.route('/employee_delete/<int:id>')
def employee_delete(id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employees WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Employee deleted.', 'danger')
    return redirect(url_for('register'))

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects")
    projects = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', projects=projects)
    # ---------------- VENDOR REGISTRATION ----------------
@app.route('/vendors', methods=['GET', 'POST'])
def vendors():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        gst = request.form['gst']
        address = request.form['address']
        phone = request.form['phone']
        email = request.form['email']
        cursor.execute("INSERT INTO vendors (name, gst, address, phone, email) VALUES (?, ?, ?, ?, ?)",
                       (name, gst, address, phone, email))
        conn.commit()
        flash('Vendor registered successfully!', 'success')
        return redirect(url_for('vendors'))

    cursor.execute("SELECT * FROM vendors")
    vendors = cursor.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors)

@app.route('/vendor_delete/<int:id>')
def vendor_delete(id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vendors WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Vendor deleted.', 'danger')
    return redirect(url_for('vendors'))

@app.route('/vendor_edit/<int:id>', methods=['GET', 'POST'])
def vendor_edit(id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        gst = request.form['gst']
        address = request.form['address']
        phone = request.form['phone']
        email = request.form['email']
        cursor.execute('''
            UPDATE vendors SET name=?, gst=?, address=?, phone=?, email=? WHERE id=?
        ''', (name, gst, address, phone, email, id))
        conn.commit()
        flash('Vendor updated successfully!', 'success')
        return redirect(url_for('vendors'))

    cursor.execute("SELECT * FROM vendors WHERE id=?", (id,))
    row = cursor.fetchone()
    conn.close()
    return render_template('vendor_edit.html', row=row)
    # ---------------- PROJECT DASHBOARD + ADD PROJECT ----------------


@app.route('/add_project', methods=['POST'])
def add_project():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    enquiry_id = request.form['enquiry_id']
    vendor_id = request.form['vendor_id']
    quotation_ro = request.form['quotation_ro']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    location = request.form['location']
    gst_number = request.form['gst_number']
    address = request.form['address']
    incharge = request.form['incharge']
    notes = request.form['notes']
    file = request.files['file']
    filename = None

    if file and file.filename:
        filename = str(uuid.uuid4()) + "_" + file.filename
        file.save(os.path.join('uploads', filename))

    cursor.execute('''
        INSERT INTO projects (enquiry_id, vendor_id, quotation_ro, start_date, end_date, location, gst_number, address, incharge, notes, drawing_file, approval_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (enquiry_id, vendor_id, quotation_ro, start_date, end_date, location, gst_number, address, incharge, notes, filename, 'Design Process'))
    conn.commit()
    conn.close()

    flash('Project added successfully!', 'success')
    return redirect(url_for('dashboard'))


# ---------------- MEASUREMENT SHEET POPUP SAVE ----------------
@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    project_id = request.form['project_id']
    client_name = request.form['client_name']
    company_name = request.form['company_name']
    project_location = request.form['project_location']
    engineer_name = request.form['engineer_name']
    phone = request.form['phone']

    cursor.execute('''
        INSERT INTO measurement_sheet (project_id, client_name, company_name, project_location, engineer_name, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, client_name, company_name, project_location, engineer_name, phone))
    conn.commit()

    ms_id = cursor.lastrowid
    conn.close()
    return redirect(url_for('measurement_sheet', project_id=project_id))
    # ---------------- MEASUREMENT SHEET VIEW ----------------
@app.route('/measurement_sheet/<int:project_id>')
def measurement_sheet(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,))
    ms = cursor.fetchone()

    cursor.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,))
    ducts = cursor.fetchall()
    conn.close()

    if not ms:
        flash('Measurement sheet not found.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('measurement_sheet.html',
                           project_id=project_id,
                           enquiry_id=ms[2],
                           client_name=ms[3],
                           project_location=ms[4],
                           engineer_name=ms[5],
                           phone=ms[6],
                           ducts=ducts)


# ---------------- DUCT ENTRY ----------------
@app.route('/add_duct', methods=['POST'])
def add_duct():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    project_id = request.args.get('project_id') or request.form.get('project_id')
    duct_no = request.form['duct_no']
    duct_type = request.form['duct_type']
    duct_size = request.form['duct_size']
    quantity = request.form['quantity']

    cursor.execute('''
        INSERT INTO ducts (project_id, duct_no, duct_type, duct_size, quantity)
        VALUES (?, ?, ?, ?, ?)
    ''', (project_id, duct_no, duct_type, duct_size, quantity))

    conn.commit()
    conn.close()
    return redirect(url_for('measurement_sheet', project_id=project_id))
    # ---------------- EDIT DUCT ENTRY ----------------
@app.route('/edit_duct/<int:duct_id>', methods=['GET', 'POST'])
def edit_duct(duct_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        duct_no = request.form['duct_no']
        duct_type = request.form['duct_type']
        duct_size = request.form['duct_size']
        quantity = request.form['quantity']
        remarks = request.form['remarks']

        cursor.execute('''
            UPDATE ducts SET duct_no = ?, duct_type = ?, duct_size = ?, quantity = ?, remarks = ?
            WHERE id = ?
        ''', (duct_no, duct_type, duct_size, quantity, remarks, duct_id))

        conn.commit()
        cursor.execute("SELECT project_id FROM ducts WHERE id = ?", (duct_id,))
        project_id = cursor.fetchone()[0]
        conn.close()

        flash('Duct entry updated successfully!', 'success')
        return redirect(url_for('measurement_sheet', project_id=project_id))
    else:
        cursor.execute("SELECT * FROM ducts WHERE id = ?", (duct_id,))
        row = cursor.fetchone()

        if not row:
            flash("Entry not found", "danger")
            return redirect(url_for('dashboard'))

        project_id = row[1]
        conn.close()
        return render_template('edit_measurement.html', row=row, project_id=project_id)


# ---------------- DELETE DUCT ENTRY ----------------
@app.route('/delete_duct/<int:duct_id>')
def delete_duct(duct_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT project_id FROM ducts WHERE id = ?", (duct_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        flash('Duct entry not found.', 'danger')
        return redirect(url_for('dashboard'))

    project_id = row[0]

    cursor.execute("DELETE FROM ducts WHERE id = ?", (duct_id,))
    conn.commit()
    conn.close()

    flash("Duct entry deleted successfully!", "warning")
    return redirect(url_for('measurement_sheet', project_id=project_id))


# ---------------- SUBMIT MEASUREMENT SHEET ----------------
@app.route('/submit_sheet/<int:project_id>', methods=['POST'])
def submit_sheet(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Change status to "Submitted"
    cursor.execute("UPDATE projects SET approval_status = ? WHERE id = ?", ("Submit for Approval", project_id))
    conn.commit()
    conn.close()

    flash("Measurement Sheet Submitted!", "success")
    return redirect(url_for('dashboard'))
    

# ---------------- EXPORT DUCT DATA AS CSV ----------------
@app.route('/export_csv/<int:project_id>')
def export_csv(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT duct_no, duct_type, duct_size, quantity FROM ducts WHERE project_id = ?", (project_id,))
    data = cursor.fetchall()
    conn.close()

    output = BytesIO()
    writer = csv.writer(output)
    writer.writerow(['Duct No', 'Type', 'Size', 'Quantity'])
    writer.writerows(data)
    output.seek(0)

    return send_file(output, mimetype='text/csv', download_name='duct_data.csv', as_attachment=True)


# ---------------- EXPORT DUCT DATA AS EXCEL ----------------
@app.route('/export_excel/<int:project_id>')
def export_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT duct_no, duct_type, duct_size, quantity FROM ducts WHERE project_id = ?", conn, params=(project_id,))
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name='duct_data.xlsx', as_attachment=True)


# ---------------- EXPORT DUCT DATA AS PDF ----------------
@app.route('/export_pdf/<int:project_id>')
def export_pdf(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT duct_no, duct_type, duct_size, quantity FROM ducts WHERE project_id = ?", (project_id,))
    data = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Duct Measurement Sheet")
    y -= 30

    p.setFont("Helvetica", 12)
    p.drawString(50, y, "Duct No | Type | Size | Quantity")
    y -= 20
    for row in data:
        line = " | ".join(str(val) for val in row)
        p.drawString(50, y, line)
        y -= 18
        if y < 40:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', download_name='duct_data.pdf', as_attachment=True)
    # ---------------- PROJECT SUMMARY PAGE ----------------
@app.route('/project_summary')
def project_summary():
    conn = sqlite3.connect('erp.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, enquiry_id FROM projects")
    projects = cursor.fetchall()
    conn.close()
    return render_template("project_summary.html", projects=projects)


# ---------------- GET SUMMARY DATA FOR SELECTED PROJECT ----------------
@app.route('/get_summary_data/<int:project_id>')
def get_summary_data(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Fetch Project Info
    cursor.execute("SELECT client_name, project_incharge, start_date, end_date, drawing_file FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    if not row:
        return {}

    # Gauge Summary (sum sheet area grouped by gauge)
    cursor.execute("SELECT gauge, SUM(sheet_area) FROM ducts WHERE project_id = ? GROUP BY gauge", (project_id,))
    gauge_data = cursor.fetchall()
    gauge_summary = {g[0]: g[1] for g in gauge_data}

    # Stages (Dummy values - can be updated based on actual workflow or production logs)
    stages = {
        "cutting": 40,
        "plasma": 60,
        "boxing": 30,
        "qc": 50,
        "dispatch": 20
    }

    conn.close()

    return {
        "client": row[0],
        "project_incharge": row[1],
        "start_date": row[2],
        "end_date": row[3],
        "source_drawing": row[4],
        "gauge_summary": gauge_summary,
        "stages": stages
    }
    # ---------------- EMPLOYEE REGISTRATION ----------------
@app.route('/register_employee', methods=['GET', 'POST'])
def register_employee():
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
        flash('Employee registered successfully!', 'success')
        return redirect('/register_employee')

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    conn.close()
    return render_template('employee_register.html', employees=employees)


# ---------------- EMPLOYEE DELETE ----------------
@app.route('/employee_delete/<int:id>')
def employee_delete(id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employees WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Employee deleted.', 'danger')
    return redirect('/register_employee')


# ---------------- EMPLOYEE EDIT ----------------
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
        flash('Employee updated successfully!', 'success')
        return redirect('/register_employee')

    cursor.execute("SELECT * FROM employees WHERE id = ?", (id,))
    employee = cursor.fetchone()
    conn.close()
    return render_template('edit_employee.html', employee=employee)
    # ---------- APPROVAL FLOW ----------

@app.route('/submit_for_approval/<int:project_id>', methods=['POST'])
def submit_for_approval(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
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
    cursor.execute("UPDATE projects SET approval_status = ? WHERE id = ?", ('Approved', project_id))

    # ✅ TODO: Push to production (future implementation placeholder)
    conn.commit()
    conn.close()
    flash('Project approved and pushed to production.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/send_back_project/<int:project_id>', methods=['POST'])
def send_back_project(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET approval_status = ? WHERE id = ?", ('Design Process', project_id))
    conn.commit()
    conn.close()
    flash('Project sent back to Design Process.', 'warning')
    return redirect(url_for('dashboard'))
    # ---------- PROJECT SUMMARY ----------

@app.route('/project_summary')
def project_summary():
    conn = sqlite3.connect('erp.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, enquiry_id FROM projects")
    projects = cursor.fetchall()
    conn.close()

    return render_template("project_summary.html", projects=projects)


@app.route('/get_summary_data/<int:project_id>')
def get_summary_data(project_id):
    conn = sqlite3.connect('erp.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get project details
    cursor.execute("""
        SELECT p.enquiry_id, p.client_name, p.project_incharge, p.start_date, p.end_date, p.drawing_file
        FROM projects p WHERE p.id = ?
    """, (project_id,))
    project = cursor.fetchone()

    # Get gauge summary
    cursor.execute("""
        SELECT gauge, SUM(sheet_area) AS total_area
        FROM measurement_sheet
        WHERE project_id = ?
        GROUP BY gauge
    """, (project_id,))
    gauges = cursor.fetchall()
    gauge_summary = {g['gauge']: round(g['total_area'], 2) for g in gauges}

    # Simulated production progress (can be updated to use real values later)
    stages = {
        "cutting": 40,
        "plasma": 30,
        "boxing": 20,
        "qc": 10,
        "dispatch": 5
    }

    conn.close()

    return jsonify({
        "client": project["client_name"],
        "project_incharge": project["project_incharge"],
        "start_date": project["start_date"],
        "end_date": project["end_date"],
        "source_drawing": project["drawing_file"],
        "gauge_summary": gauge_summary,
        "stages": stages
    })
    # ---------- MAIN SERVER ----------

if __name__ == '__main__':
    init_db()  # Initializes DB with required tables if not present
    app.run(debug=True)
