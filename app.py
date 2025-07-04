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

    # Production progress tracking
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
    # ✅ MAIN production progress table
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

# ✅ LOG of daily updates (renamed from conflicting "production")
cursor.execute('''
    CREATE TABLE IF NOT EXISTS production_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        duct_no TEXT,
        duct_type TEXT,
        duct_size TEXT,
        quantity INTEGER,
        remarks TEXT,
        pushed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        pushed_by TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
''')

# Duct entry
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

    # Insert admin login if not exists
    cursor.execute("SELECT * FROM employees WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Admin User', 'Admin', 'admin@erp.com', '1234567890', 'admin', 'admin123'))

    conn.commit()
    conn.close()

# Call this to initialize DB when app starts
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
        try:
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
        except Exception as e:
            flash(f'Error: {e}', 'danger')
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

    # If vendors table is empty, insert dummy vendors for testing
    if not vendors:
        dummy_vendors = [
            (1, 'ABC Ducting Ltd.', 'GST123ABC', 'Chennai'),
            (2, 'XYZ Fabrication', 'GST456XYZ', 'Bangalore'),
            (3, 'CoolAir Systems', 'GST789CA', 'Mumbai')
        ]
        cursor.executemany("INSERT INTO vendors (id, name, gst, address) VALUES (?, ?, ?, ?)", dummy_vendors)
        conn.commit()
        vendors = dummy_vendors

    conn.close()

    # Generate Enquiry ID like ENQ123ABC
    enquiry_id = f"ENQ{uuid.uuid4().hex[:6].upper()}"

    return render_template('projects.html',
                           projects=projects,
                           vendors=vendors,
                           enquiry_id=enquiry_id)
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

    # Handle drawing file upload
    drawing_file = ''
    if file and file.filename:
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        drawing_file = filename
        os.makedirs('uploads', exist_ok=True)
        file.save(os.path.join('uploads', filename))

    # Insert into DB
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

    cursor.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,))
    ms = cursor.fetchone()

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


# ---------------- ADD DUCT ENTRY ----------------
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


# ---------------- DELETE DUCT ----------------
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


# ---------------- EXPORT TO CSV ----------------
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


# ---------------- EXPORT TO EXCEL ----------------
@app.route('/export_excel/<int:project_id>')
def export_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query(
        "SELECT duct_no, duct_type, duct_size, quantity FROM ducts WHERE project_id = ?",
        conn,
        params=(project_id,)
    )
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        download_name='duct_data.xlsx',
        as_attachment=True)


# ---------------- SUBMIT FOR APPROVAL ----------------
@app.route('/submit_sheet/<int:project_id>', methods=['POST'])
def submit_sheet(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET approval_status = ? WHERE id = ?", ("Submit for Approval", project_id))
    conn.commit()
    conn.close()

    flash("Submitted for approval!", "success")
    return redirect(url_for('dashboard'))
    # ---------------- REVIEW PROJECT ----------------
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


# ---------------- PUSH TO PRODUCTION ----------------
@app.route('/push_to_production/<int:project_id>')
def push_to_production(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Ensure project is approved
    cursor.execute("SELECT approval_status FROM projects WHERE id = ?", (project_id,))
    status = cursor.fetchone()
    if not status or status[0] != "Approved":
        flash("Project is not approved yet.", "danger")
        conn.close()
        return redirect(url_for('dashboard'))

    # Prevent duplicate pushes
    cursor.execute("SELECT * FROM production WHERE project_id = ?", (project_id,))
    if cursor.fetchone():
        flash("Project already pushed to production.", "info")
        conn.close()
        return redirect(url_for('dashboard'))

    # Get ducts from measurement sheet
    cursor.execute("SELECT duct_no, duct_type, duct_size, quantity, remarks FROM ducts WHERE project_id = ?", (project_id,))
    ducts = cursor.fetchall()

    # Insert ducts into production
    for duct in ducts:
        cursor.execute('''
            INSERT INTO production (project_id, duct_no, duct_type, duct_size, quantity, remarks)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, *duct))

    conn.commit()
    conn.close()

    flash("Project pushed to production!", "success")
    return redirect(url_for('production_dashboard'))


# ---------------- PRODUCTION DASHBOARD ----------------
@app.route('/production')
def production_dashboard():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT d.project_id, pr.enquiry_id, d.duct_no, d.duct_type, d.duct_size, d.quantity, d.remarks
        FROM production d
        LEFT JOIN projects pr ON d.project_id = pr.id
        GROUP BY d.id
    ''')
    rows = cursor.fetchall()
    conn.close()

    return render_template('production.html', rows=rows)


@app.route('/production/<int:project_id>', methods=['GET', 'POST'])
def production(project_id):
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Handle form submission
    if request.method == 'POST':
        cutting = float(request.form.get('cutting', 0))
        plasma = float(request.form.get('plasma', 0))
        boxing = float(request.form.get('boxing', 0))
        quality = float(request.form.get('quality', 0))
        dispatch = float(request.form.get('dispatch', 0))

        # Check if record exists
        cursor.execute("SELECT id FROM production WHERE project_id = ?", (project_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute('''
                UPDATE production 
                SET cutting_done=?, plasma_done=?, boxing_done=?, quality_percent=?, dispatch_percent=?
                WHERE project_id=?
            ''', (cutting, plasma, boxing, quality, dispatch, project_id))
        else:
            cursor.execute('''
                INSERT INTO production (project_id, cutting_done, plasma_done, boxing_done, quality_percent, dispatch_percent)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (project_id, cutting, plasma, boxing, quality, dispatch))

        conn.commit()
        flash("Production data updated", "success")
        return redirect(url_for('production', project_id=project_id))

    # Fetch current values
    cursor.execute("SELECT * FROM production WHERE project_id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()

    # Dummy total area for now (replace with actual measurement sheet total later)
    total_area = 100  

    return render_template("production.html",
                           project_id=project_id,
                           total_area=total_area,
                           data=row)
# ---------------- RUN FLASK SERVER ----------------
if __name__ == '__main__':
    # Create uploads directory if it doesn't exist
    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    # Initialize the database
    init_db()

    # Run the Flask app
    app.run(debug=True)
    
