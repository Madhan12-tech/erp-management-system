from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
import sqlite3
import pandas as pd
from io import BytesIO
import os

app = Flask(__name__)
app.secret_key = 'secretkey123'

DATABASE = 'ducting_erp.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ----------- DATABASE SETUP (ALL TABLES) --------------
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Employees table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        designation TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT NOT NULL,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    ''')

    # Vendors table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        gst_number TEXT NOT NULL,
        address TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        alt_contact TEXT,
        acc_holder_name TEXT NOT NULL,
        bank_name TEXT NOT NULL,
        branch TEXT NOT NULL,
        account_no TEXT NOT NULL,
        ifsc_code TEXT NOT NULL
    )
    ''')

    # Projects table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enquiry_id TEXT NOT NULL UNIQUE,
        client_name TEXT NOT NULL,
        location TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        engineer_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        tagged_drawing TEXT,
        status TEXT DEFAULT 'Pending',
        incharge TEXT,
        approval_status TEXT DEFAULT 'Pending',
        remarks TEXT
    )
    ''')

    # Measurement Sheet table (duct entries)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS measurement_sheet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        duct_no TEXT NOT NULL,
        duct_type TEXT NOT NULL,
        duct_size TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        remarks TEXT,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )
    ''')

    # Production Progress table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS production_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        stage TEXT NOT NULL,
        progress INTEGER NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )
    ''')

    conn.commit()
    conn.close()

# -------------- DUMMY DATA SETUP ----------------
def insert_dummy_data():
    conn = get_db_connection()
    cur = conn.cursor()

    # Insert dummy employee if none exists
    cur.execute('SELECT COUNT(*) FROM employees')
    if cur.fetchone()[0] == 0:
        employees = [
            ('Madhan', 'Project Manager', 'madhan@example.com', '9876543210', 'madhan', 'password123'),
            ('Alice', 'Engineer', 'alice@example.com', '9123456780', 'alice', 'password123'),
        ]
        cur.executemany('INSERT INTO employees (name, designation, email, phone, username, password) VALUES (?, ?, ?, ?, ?, ?)', employees)

    # Insert dummy vendor if none exists
    cur.execute('SELECT COUNT(*) FROM vendors')
    if cur.fetchone()[0] == 0:
        vendors = [
            ('ABC Ducts Pvt Ltd', 'GST1234567', '123 Industrial Area', 'abc@ducts.com', '9876500000', '9876500001', 'ABC Ducts', 'State Bank', 'Main Branch', '1234567890', 'SBIN0001234'),
        ]
        cur.executemany('''
        INSERT INTO vendors (company_name, gst_number, address, email, phone, alt_contact, acc_holder_name, bank_name, branch, account_no, ifsc_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', vendors)

    # Insert dummy projects if none exists
    cur.execute('SELECT COUNT(*) FROM projects')
    if cur.fetchone()[0] == 0:
        projects = [
            ('ENQ1001', 'Client A', 'Location A', '2025-07-01', '2025-07-31', 'Madhan', '9876543210', None, 'In Progress', 'Madhan', 'Pending', None),
            ('ENQ1002', 'Client B', 'Location B', '2025-07-05', '2025-08-05', 'Alice', '9123456780', None, 'Pending', 'Alice', 'Pending', None),
        ]
        cur.executemany('''
        INSERT INTO projects (enquiry_id, client_name, location, start_date, end_date, engineer_name, phone, tagged_drawing, status, incharge, approval_status, remarks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', projects)

    # Insert dummy measurement entries
    cur.execute('SELECT COUNT(*) FROM measurement_sheet')
    if cur.fetchone()[0] == 0:
        measurements = [
            (1, 'D001', 'Rectangular', '100x50', 10, 'No remarks'),
            (1, 'D002', 'Circular', '50 dia', 5, ''),
            (2, 'D003', 'Rectangular', '80x40', 7, 'Urgent'),
        ]
        cur.executemany('''
        INSERT INTO measurement_sheet (project_id, duct_no, duct_type, duct_size, quantity, remarks)
        VALUES (?, ?, ?, ?, ?, ?)''', measurements)

    # Insert dummy production progress
    cur.execute('SELECT COUNT(*) FROM production_progress')
    if cur.fetchone()[0] == 0:
        stages = ['cutting', 'plasma', 'boxing', 'qc', 'dispatch']
        progress_data = []
        for project_id in [1, 2]:
            for stage in stages:
                progress_data.append((project_id, stage, 0))
        cur.executemany('''
        INSERT INTO production_progress (project_id, stage, progress)
        VALUES (?, ?, ?)''', progress_data)

    conn.commit()
    conn.close()

# -------------------- EXPORT FUNCTIONS -------------------

def export_excel(dataframe, filename):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Sheet1')
        writer.save()
    output.seek(0)
    return send_file(output, attachment_filename=filename, as_attachment=True)

def export_pdf(dataframe, filename):
    # Since we cannot use canvas, we convert dataframe to HTML and then PDF via wkhtmltopdf or similar
    # Here, we'll just send the HTML as PDF for simplicity (can be improved)
    html = dataframe.to_html(index=False)
    pdf_output = BytesIO()
    pdf_output.write(html.encode('utf-8'))
    pdf_output.seek(0)
    return send_file(pdf_output, attachment_filename=filename, as_attachment=True, mimetype='application/pdf')

# -------------- ROUTES --------------------

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM employees WHERE username=? AND password=?', (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('login'))

# DASHBOARD route (show project summary etc)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM projects').fetchall()
    conn.close()
    return render_template('dashboard.html', projects=projects, username=session.get('username'))

# VENDOR REGISTRATION
@app.route('/register_vendor', methods=['GET', 'POST'])
def register_vendor():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.form
        conn.execute('''
        INSERT INTO vendors (company_name, gst_number, address, email, phone, alt_contact, acc_holder_name, bank_name, branch, account_no, ifsc_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['company_name'], data['gst_number'], data['address'], data['email'], data['phone'], data.get('alt_contact'),
              data['acc_holder_name'], data['bank_name'], data['branch'], data['account_no'], data['ifsc_code']))
        conn.commit()
        conn.close()
        flash('Vendor registered successfully', 'success')
        return redirect(url_for('dashboard'))
    conn.close()
    return render_template('vendor_registration.html')

# EMPLOYEE REGISTRATION
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.form
        try:
            conn.execute('''
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (data['name'], data['designation'], data['email'], data['phone'], data['username'], data['password']))
            conn.commit()
            flash('Employee registered successfully', 'success')
        except sqlite3.IntegrityError:
            flash('Username or Email already exists', 'danger')
        return redirect(url_for('register'))
    employees = conn.execute('SELECT * FROM employees').fetchall()
    conn.close()
    return render_template('register.html', employees=employees)

# Employee edit and delete routes can come in next parts

# MEASUREMENT SHEET LIST
@app.route('/measurement_sheet/<int:project_id>', methods=['GET'])
def measurement_sheet(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
    ducts = conn.execute('SELECT * FROM measurement_sheet WHERE project_id=?', (project_id,)).fetchall()
    conn.close()
    return render_template('measurement_sheet.html',
                           enquiry_id=project['enquiry_id'],
                           client_name=project['client_name'],
                           project_location=project['location'],
                           engineer_name=project['engineer_name'],
                           phone=project['phone'],
                           ducts=ducts)

# ADD DUCT ENTRY
@app.route('/add_duct', methods=['POST'])
def add_duct():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    project_id = request.args.get('project_id', type=int)
    if not project_id:
        flash('Project ID missing', 'danger')
        return redirect(url_for('dashboard'))
    data = request.form
    conn = get_db_connection()
    conn.execute('''
    INSERT INTO measurement_sheet (project_id, duct_no, duct_type, duct_size, quantity, remarks)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, data['duct_no'], data['duct_type'], data['duct_size'], data['quantity'], data.get('remarks', '')))
    conn.commit()
    conn.close()
    flash('Duct entry added', 'success')
    return redirect(url_for('measurement_sheet', project_id=project_id))

# DELETE DUCT ENTRY
@app.route('/delete_duct/<int:duct_id>')
def delete_duct(duct_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    # get project id for redirect
    duct = conn.execute('SELECT project_id FROM measurement_sheet WHERE id=?', (duct_id,)).fetchone()
    if duct:
        conn.execute('DELETE FROM measurement_sheet WHERE id=?', (duct_id,))
        conn.commit()
        flash('Duct entry deleted', 'success')
        project_id = duct['project_id']
    else:
        flash('Duct entry not found', 'danger')
        project_id = None
    conn.close()
    if project_id:
        return redirect(url_for('measurement_sheet', project_id=project_id))
    else:
        return redirect(url_for('dashboard'))

# EXPORT measurement sheet to Excel
@app.route('/export_measurement_excel/<int:project_id>')
def export_measurement_excel(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    data = conn.execute('SELECT duct_no, duct_type, duct_size, quantity, remarks FROM measurement_sheet WHERE project_id=?', (project_id,)).fetchall()
    conn.close()
    df = pd.DataFrame(data, columns=['Duct No', 'Type', 'Size', 'Quantity', 'Remarks'])
    return export_excel(df, f'measurement_sheet_{project_id}.xlsx')

# EXPORT measurement sheet to PDF (via HTML)
@app.route('/export_measurement_pdf/<int:project_id>')
def export_measurement_pdf(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    data = conn.execute('SELECT duct_no, duct_type, duct_size, quantity, remarks FROM measurement_sheet WHERE project_id=?', (project_id,)).fetchall()
    conn.close()
    df = pd.DataFrame(data, columns=['Duct No', 'Type', 'Size', 'Quantity', 'Remarks'])
    return export_pdf(df, f'measurement_sheet_{project_id}.pdf')

# SUBMIT measurement sheet (dummy)
@app.route('/submit_measurement/<int:project_id>', methods=['POST'])
def submit_measurement(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Here you could update project status or similar
    flash('Measurement Sheet submitted successfully', 'success')
    return redirect(url_for('measurement_sheet', project_id=project_id))

# Run once on app start
with app.app_context():
    init_db()
    insert_dummy_data()

if __name__ == '__main__':
    app.run(debug=True)
