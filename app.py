from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from io import BytesIO
import pandas as pd
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from flask import send_file

app = Flask(__name__)
app.secret_key = 'secret123'

# ---------------- DB INIT ----------------
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

    # Production Table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS production (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        duct_no TEXT,
        duct_type TEXT,
        duct_size TEXT,
        quantity INTEGER,
        remarks TEXT
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

    conn.commit()

    # Insert dummy admin user if not exists
    cursor.execute("SELECT * FROM employees WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Admin User', 'Manager', 'admin@erp.com', '1234567890', 'admin', 'admin123'))

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
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    return render_template('login.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


# ---------------- EMPLOYEE REGISTRATION ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        cursor.execute('''
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, designation, email, phone, username, password))
        conn.commit()
        flash('Employee registered successfully!', 'success')
        return redirect(url_for('register'))

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    conn.close()

    return render_template('register.html', employees=employees)


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))
    return render_template('dashboard.html')
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

        cursor.execute('''
            INSERT INTO vendors (name, gst, address, phone, email)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, gst, address, phone, email))
        conn.commit()
        flash('Vendor registered successfully!', 'success')
        return redirect(url_for('vendors'))

    cursor.execute("SELECT * FROM vendors")
    vendors = cursor.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors)


# ---------------- VENDOR DELETE ----------------
@app.route('/vendor_delete/<int:id>')
def vendor_delete(id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vendors WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Vendor deleted.', 'danger')
    return redirect(url_for('vendors'))


# ---------------- VENDOR EDIT ----------------
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
            UPDATE vendors SET name = ?, gst = ?, address = ?, phone = ?, email = ?
            WHERE id = ?
        ''', (name, gst, address, phone, email, id))
        conn.commit()
        flash('Vendor updated successfully!', 'success')
        return redirect(url_for('vendors'))

    cursor.execute("SELECT * FROM vendors WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    return render_template('vendor_edit.html', row=row)
    # ---------------- PROJECT DASHBOARD ----------------
@app.route('/projects')
def projects():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get projects with vendor names and incharge names
    cursor.execute('''
        SELECT p.*, v.name as vendor_name 
        FROM projects p 
        LEFT JOIN vendors v ON p.vendor_id = v.id
    ''')
    projects = cursor.fetchall()

    # Get all vendors for the dropdown
    cursor.execute("SELECT id, name, gst, address FROM vendors")
    vendors = cursor.fetchall()

    conn.close()
    return render_template('projects.html', projects=projects, vendors=vendors)


# ---------------- ADD PROJECT ----------------
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
    
    drawing_file = ''
    if file and file.filename:
        drawing_file = f"{uuid.uuid4().hex}_{file.filename}"
        file.save(os.path.join('uploads', drawing_file))

    cursor.execute('''
        INSERT INTO projects (
            enquiry_id, vendor_id, quotation_ro, start_date, end_date,
            location, gst, address, incharge, notes, file, approval_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        enquiry_id, vendor_id, quotation_ro, start_date, end_date,
        location, gst_number, address, incharge, notes, drawing_file, 'Design Process'
    ))

    conn.commit()
    conn.close()
    flash("Project added successfully!", "success")
    return redirect(url_for('projects'))
    # ---------------- ADD MEASUREMENT SHEET ----------------
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
        INSERT INTO measurement_sheet (
            project_id, client, company, location, engineer, phone
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        project_id, client_name, company_name, project_location, engineer_name, phone
    ))
    conn.commit()
    conn.close()

    return redirect(url_for('measurement_sheet', project_id=project_id))
    # ---------------- MEASUREMENT SHEET VIEW ----------------
@app.route('/measurement_sheet/<int:project_id>')
def measurement_sheet(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Get sheet header
    cursor.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,))
    ms = cursor.fetchone()

    # Get all duct entries
    cursor.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,))
    ducts = cursor.fetchall()

    conn.close()

    if not ms:
        flash("Measurement sheet not found.", "danger")
        return redirect(url_for('dashboard'))

    return render_template("measurement_sheet.html",
        project_id=project_id,
        client_name=ms[2],
        company=ms[3],
        location=ms[4],
        engineer=ms[5],
        phone=ms[6],
        ducts=ducts
                          )
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

    return redirect(url_for('measurement_sheet', project_id=project_id))
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
            UPDATE ducts
            SET duct_no = ?, duct_type = ?, duct_size = ?, quantity = ?, remarks = ?
            WHERE id = ?
        ''', (duct_no, duct_type, duct_size, quantity, remarks, duct_id))

        conn.commit()

        cursor.execute("SELECT project_id FROM ducts WHERE id = ?", (duct_id,))
        project_id = cursor.fetchone()[0]
        conn.close()

        flash("Duct entry updated!", "success")
        return redirect(url_for('measurement_sheet', project_id=project_id))

    else:
        cursor.execute("SELECT * FROM ducts WHERE id = ?", (duct_id,))
        row = cursor.fetchone()
        conn.close()
        return render_template('edit_measurement.html', row=row)
        @app.route('/delete_duct/<int:duct_id>')
def delete_duct(duct_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute("SELECT project_id FROM ducts WHERE id = ?", (duct_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        flash("Duct not found!", "danger")
        return redirect(url_for('dashboard'))

    project_id = row[0]

    cursor.execute("DELETE FROM ducts WHERE id = ?", (duct_id,))
    conn.commit()
    conn.close()

    flash("Duct deleted!", "warning")
    return redirect(url_for('measurement_sheet', project_id=project_id))
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
    @app.route('/export_excel/<int:project_id>')
def export_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT duct_no, duct_type, duct_size, quantity FROM ducts WHERE project_id = ?", conn, params=(project_id,))
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     download_name='duct_data.xlsx', as_attachment=True)
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
        p.drawString(50, y, " | ".join(str(val) for val in row))
        y -= 18
        if y < 40:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', download_name='duct_data.pdf', as_attachment=True)
    @app.route('/submit_sheet/<int:project_id>', methods=['POST'])
def submit_sheet(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET approval_status = ? WHERE id = ?", ("Submit for Approval", project_id))
    conn.commit()
    conn.close()

    flash("Submitted for approval!", "success")
    return redirect(url_for('dashboard'))
    @app.route('/review/<int:project_id>', methods=['GET', 'POST'])
def review(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form['action']
        if action == 'approve':
            new_status = 'Approved'
        else:
            new_status = 'Design Process'

        cursor.execute("UPDATE projects SET approval_status = ? WHERE id = ?", (new_status, project_id))
        conn.commit()
        conn.close()

        flash(f'Project {action.capitalize()}d Successfully!', 'success')
        return redirect(url_for('dashboard'))

    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    conn.close()

    if not project:
        flash('Project not found!', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('review.html', project=project)
    
    @app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects")
    projects = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', projects=projects)
    @app.route('/push_to_production/<int:project_id>')
def push_to_production(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Only proceed if project is approved
    cursor.execute("SELECT approval_status FROM projects WHERE id = ?", (project_id,))
    status = cursor.fetchone()
    if not status or status[0] != "Approved":
        flash("Project is not approved yet.", "danger")
        conn.close()
        return redirect(url_for('dashboard'))

    # Copy duct entries to production
    cursor.execute("SELECT duct_no, duct_type, duct_size, quantity, remarks FROM ducts WHERE project_id = ?", (project_id,))
    duct_rows = cursor.fetchall()

    for duct in duct_rows:
        cursor.execute('''
            INSERT INTO production (project_id, duct_no, duct_type, duct_size, quantity, remarks)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, *duct))

    conn.commit()
    flash("Project pushed to production!", "success")
    conn.close()
    return redirect(url_for('production_dashboard'))
    @app.route('/production')
def production_dashboard():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT project_id, duct_no, duct_type, duct_size, quantity, remarks
        FROM production
    ''')
    rows = cursor.fetchall()
    conn.close()
    return render_template('production.html', rows=rows)
    # ---------------- RUN FLASK SERVER ----------------
if __name__ == '__main__':
    app.run(debug=True)
    
