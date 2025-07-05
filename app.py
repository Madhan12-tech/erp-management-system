from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from io import BytesIO
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = 'ducting_erp_secret_key'

# ------------------ DATABASE INITIALIZATION ------------------

def init_db():
    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()

    # USERS (Login/Employee)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')

    # VENDORS
    cur.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gst_number TEXT,
            address TEXT,
            contact_persons TEXT,
            bank_details TEXT
        )
    ''')

    # PROJECTS
    cur.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enquiry_id TEXT,
            vendor_id INTEGER,
            gst_number TEXT,
            address TEXT,
            quotation_ro TEXT,
            location TEXT,
            incharge TEXT,
            start_date TEXT,
            end_date TEXT,
            notes TEXT,
            drawing_path TEXT,
            status TEXT DEFAULT 'Design Process',
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        )
    ''')

    # MEASUREMENT SHEETS
    cur.execute('''
        CREATE TABLE IF NOT EXISTS measurement_sheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client_name TEXT,
            company_name TEXT,
            project_location TEXT,
            engineer_name TEXT,
            phone TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # DUCT ENTRIES
    cur.execute('''
        CREATE TABLE IF NOT EXISTS measurement_entries (
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

    # PRODUCTION PHASES
    cur.execute('''
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            phase TEXT,
            total_area REAL,
            completed_area REAL,
            percentage REAL,
            updated_on TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    conn.commit()
    conn.close()

# ------------------ DUMMY DATA INSERTION ------------------

def insert_dummy_data():
    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()

    # Insert dummy user
    cur.execute("SELECT * FROM users WHERE email = 'admin@erp.com'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                    ('Admin', 'admin@erp.com', generate_password_hash('admin123'), 'admin'))

    # Insert dummy vendor
    cur.execute("SELECT * FROM vendors WHERE name = 'Alpha HVAC'")
    if not cur.fetchone():
        cur.execute("INSERT INTO vendors (name, gst_number, address, contact_persons, bank_details) VALUES (?, ?, ?, ?, ?)", (
            'Alpha HVAC', 'GSTIN1234XYZ', 'Chennai, TN',
            'John Doe: 9876543210', 'Bank: HDFC, A/C: 123456789, IFSC: HDFC0001'))

    # Insert dummy project
    cur.execute("SELECT * FROM projects WHERE enquiry_id = 'ENQ-1234'")
    if not cur.fetchone():
        cur.execute("INSERT INTO projects (enquiry_id, vendor_id, gst_number, address, quotation_ro, location, incharge, start_date, end_date, notes, drawing_path, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
            'ENQ-1234', 1, 'GSTIN1234XYZ', 'Chennai, TN', 'RO-456', 'Ambattur', 'Mr. Kumar', '2025-07-01', '2025-07-15', 'Urgent HVAC setup', '', 'Design Process'))

    conn.commit()
    conn.close()

# Initialize DB and insert dummy records
init_db()
insert_dummy_data()

# Continue to Part 2...
# ------------------ DATABASE CONNECTION ------------------
def get_db():
    conn = sqlite3.connect('erp.db')
    conn.row_factory = sqlite3.Row
    return conn

# ------------------ AUTH ROUTES ------------------

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password_input = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password_input):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash('Login successful!', 'success')
            return redirect('/dashboard')
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        hashed = generate_password_hash(password)
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                         (name, email, hashed, role))
            conn.commit()
            conn.close()
            flash("Employee registered successfully!", "success")
            return redirect('/login')
        except:
            flash("Email already exists!", "error")
    return render_template('register.html')

# ------------------ DASHBOARD ------------------

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    projects = conn.execute('''
        SELECT p.*, v.name as vendor_name FROM projects p
        LEFT JOIN vendors v ON p.vendor_id = v.id
    ''').fetchall()
    conn.close()
    return render_template('dashboard.html', name=session['user_name'], projects=projects)

# ------------------ VENDOR REGISTRATION ------------------

@app.route('/vendor_registration', methods=['GET', 'POST'])
def vendor_registration():
    if request.method == 'POST':
        name = request.form['name']
        gst_number = request.form['gst_number']
        address = request.form['address']
        contact_names = request.form.getlist('contact_name[]')
        contact_phones = request.form.getlist('contact_phone[]')
        contacts = ', '.join([f"{n}: {p}" for n, p in zip(contact_names, contact_phones)])
        bank_details = request.form['bank_details']
        conn = get_db()
        conn.execute("INSERT INTO vendors (name, gst_number, address, contact_persons, bank_details) VALUES (?, ?, ?, ?, ?)",
                     (name, gst_number, address, contacts, bank_details))
        conn.commit()
        conn.close()
        flash("Vendor registered successfully!", "success")
        return redirect('/vendor_registration')
    return render_template('vendor_register.html')
# ------------------ ADD PROJECT ------------------

@app.route('/add_project', methods=['POST'])
def add_project():
    data = request.form
    conn = get_db()
    conn.execute('''
        INSERT INTO projects (enquiry_id, vendor_id, gst_number, address, quotation_ro, start_date, end_date, location, incharge, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['enquiry_id'], data['vendor_id'], data['gst_number'], data['address'],
        data['quotation_ro'], data['start_date'], data['end_date'],
        data['location'], data['incharge'], data['notes'], 'Design Process'
    ))
    conn.commit()
    conn.close()
    flash('Project added successfully!', 'success')
    return redirect('/dashboard')


# ------------------ MEASUREMENT SHEET ENTRY ------------------

@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    data = request.form
    conn = get_db()
    conn.execute('''
        INSERT INTO measurement_sheet (project_id, client_name, company_name, project_location, engineer_name, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data['project_id'], data['client_name'], data['company_name'],
        data['project_location'], data['engineer_name'], data['phone']
    ))
    conn.commit()
    conn.close()
    flash("Measurement sheet added!", "success")
    return redirect('/dashboard')


# ------------------ DUCT ENTRY ------------------

@app.route('/add_duct', methods=['POST'])
def add_duct():
    data = request.form
    conn = get_db()
    conn.execute('''
        INSERT INTO ducts (project_id, duct_no, duct_type, duct_size, quantity, remarks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data['project_id'], data['duct_no'], data['duct_type'],
        data['duct_size'], data['quantity'], data['remarks']
    ))
    conn.commit()
    conn.close()
    flash('Duct added!', 'success')
    return redirect('/dashboard')


# ------------------ FETCH DUCTS BY PROJECT (API) ------------------

@app.route('/api/ducts/<int:project_id>')
def api_ducts(project_id):
    conn = get_db()
    ducts = conn.execute('SELECT * FROM ducts WHERE project_id = ?', (project_id,)).fetchall()
    conn.close()
    duct_list = [{
        'id': d['id'],
        'duct_no': d['duct_no'],
        'duct_type': d['duct_type'],
        'duct_size': d['duct_size'],
        'quantity': d['quantity'],
        'remarks': d['remarks']
    } for d in ducts]
    return jsonify(duct_list)


# ------------------ EXPORT FUNCTIONS ------------------

@app.route('/export_csv/<int:project_id>')
def export_csv(project_id):
    conn = get_db()
    ducts = conn.execute('SELECT * FROM ducts WHERE project_id = ?', (project_id,)).fetchall()
    conn.close()
    df = pd.DataFrame(ducts)
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='ducts.csv')


@app.route('/export_excel/<int:project_id>')
def export_excel(project_id):
    conn = get_db()
    ducts = conn.execute('SELECT * FROM ducts WHERE project_id = ?', (project_id,)).fetchall()
    conn.close()
    df = pd.DataFrame(ducts)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ducts')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='ducts.xlsx')


# ------------------ SUBMIT MEASUREMENT SHEET ------------------

@app.route('/submit_sheet/<int:project_id>', methods=['POST'])
def submit_sheet(project_id):
    conn = get_db()
    conn.execute("UPDATE projects SET status = 'Submit for Approval' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("Submitted for approval.", "success")
    return redirect('/dashboard')

# ------------------ UPLOAD DRAWING ------------------

@app.route('/upload_drawing/<int:project_id>', methods=['POST'])
def upload_drawing(project_id):
    file = request.files.get('file')
    if file:
        filename = f'drawing_{uuid.uuid4().hex}.pdf'
        file.save(f'static/uploads/{filename}')
        conn = get_db()
        conn.execute('UPDATE projects SET status = ? WHERE id = ?', ('Submit for Approval', project_id))
        conn.commit()
        conn.close()
        flash("Drawing uploaded and submitted for approval!", "success")
    return redirect('/dashboard')


# ------------------ APPROVE PROJECT ------------------

@app.route('/approve_project/<int:project_id>', methods=['POST'])
def approve_project(project_id):
    conn = get_db()
    conn.execute('UPDATE projects SET status = ? WHERE id = ?', ('Approved', project_id))
    conn.commit()
    conn.close()
    flash("Project approved!", "success")
    return redirect('/dashboard')


# ------------------ PUSH TO PRODUCTION ------------------

@app.route('/push_to_production/<int:project_id>')
def push_to_production(project_id):
    conn = get_db()

    area = conn.execute('SELECT SUM(quantity) FROM ducts WHERE project_id = ?', (project_id,)).fetchone()[0]
    area = area if area else 0

    conn.execute('''
        INSERT OR IGNORE INTO production (project_id, area, phase1_done, phase2_done, phase3_done, phase4_percent, phase5_percent)
        VALUES (?, ?, 0, 0, 0, 0, 0)
    ''', (project_id, area))
    conn.commit()
    conn.close()
    flash('Project pushed to production!', 'success')
    return redirect('/production')


# ------------------ PRODUCTION MODULE ------------------

@app.route('/production')
def production_page():
    conn = get_db()
    query = '''
        SELECT p.id, pr.enquiry_id, v.name, pr.location, pr.status, pd.area,
               pd.phase1_done, pd.phase2_done, pd.phase3_done,
               pd.phase4_percent, pd.phase5_percent
        FROM production pd
        JOIN projects pr ON pr.id = pd.project_id
        JOIN vendors v ON v.id = pr.vendor_id
        JOIN projects p ON p.id = pd.project_id
    '''
    data = conn.execute(query).fetchall()
    conn.close()
    return render_template('production.html', productions=data)


# ------------------ UPDATE PROGRESS ------------------

@app.route('/update_progress/<int:project_id>', methods=['POST'])
def update_progress(project_id):
    conn = get_db()
    area = conn.execute("SELECT area FROM production WHERE project_id = ?", (project_id,)).fetchone()[0]
    f = request.form
    phase1 = int(f.get('phase1_done', 0))
    phase2 = int(f.get('phase2_done', 0))
    phase3 = int(f.get('phase3_done', 0))
    phase4 = int(f.get('phase4_percent', 0))
    phase5 = int(f.get('phase5_percent', 0))

    conn.execute('''
        UPDATE production
        SET phase1_done = ?, phase2_done = ?, phase3_done = ?,
            phase4_percent = ?, phase5_percent = ?
        WHERE project_id = ?
    ''', (phase1, phase2, phase3, phase4, phase5, project_id))
    conn.commit()
    conn.close()
    flash('Production updated.', 'success')
    return redirect('/production')


# ------------------ PRODUCTION SUMMARY ------------------

@app.route('/production_summary/<int:project_id>')
def production_summary(project_id):
    conn = get_db()
    prod = conn.execute('''
        SELECT pr.*, v.name AS vendor_name, p.*
        FROM projects pr
        JOIN vendors v ON v.id = pr.vendor_id
        JOIN production p ON p.project_id = pr.id
        WHERE pr.id = ?
    ''', (project_id,)).fetchone()
    conn.close()
    return render_template('production_summary.html', data=prod)

# ------------------ REDIRECT FROM LOGIN TO REGISTER ------------------

@app.route('/register')
def register():
    return redirect('/vendor_registration')


# ------------------ VENDOR REGISTRATION PAGE ------------------

@app.route('/vendor_registration')
def vendor_registration():
    return render_template('vendor_register.html')


# ------------------ SUBMIT VENDOR ------------------

@app.route('/submit_vendor', methods=['POST'])
def submit_vendor():
    f = request.form
    name = f['name']
    gst_number = f['gst_number']
    address = f['address']
    phone = f['phone']
    email = f['email']
    
    conn = get_db()
    cur = conn.cursor()
    
    # Insert main vendor
    cur.execute('INSERT INTO vendors (name, gst_number, address, phone, email) VALUES (?, ?, ?, ?, ?)',
                (name, gst_number, address, phone, email))
    vendor_id = cur.lastrowid

    # Insert communication contacts
    comm_names = request.form.getlist('comm_name[]')
    comm_phones = request.form.getlist('comm_phone[]')
    comm_emails = request.form.getlist('comm_email[]')
    for i in range(len(comm_names)):
        cur.execute('INSERT INTO vendor_contacts (vendor_id, name, phone, email) VALUES (?, ?, ?, ?)',
                    (vendor_id, comm_names[i], comm_phones[i], comm_emails[i]))

    # Insert bank details
    bank_name = f['bank_name']
    acc_no = f['account_number']
    ifsc = f['ifsc_code']
    branch = f['branch_name']
    cur.execute('INSERT INTO vendor_banks (vendor_id, bank_name, account_number, ifsc_code, branch_name) VALUES (?, ?, ?, ?, ?)',
                (vendor_id, bank_name, acc_no, ifsc, branch))

    conn.commit()
    conn.close()
    flash("Vendor registered successfully!", "success")
    return redirect('/vendor_registration')


# ------------------ VIEW REGISTERED VENDORS + CONTACTS ------------------

@app.route('/vendor_list')
def vendor_list():
    conn = get_db()
    vendors = conn.execute('SELECT * FROM vendors').fetchall()
    contacts = conn.execute('SELECT * FROM vendor_contacts').fetchall()
    conn.close()
    return render_template('vendor_list.html', vendors=vendors, contacts=contacts)

# ------------------ EMPLOYEE REGISTRATION PAGE ------------------

@app.route('/employee_register')
def employee_register():
    return render_template('employee_register.html')

# ------------------ EMPLOYEE REGISTRATION SUBMIT ------------------

@app.route('/submit_employee', methods=['POST'])
def submit_employee():
    f = request.form
    name = f['name']
    role = f['role']
    email = f['email']
    password = generate_password_hash(f['password'])

    conn = get_db()
    conn.execute('INSERT INTO employees (name, role, email, password) VALUES (?, ?, ?, ?)',
                 (name, role, email, password))
    conn.commit()
    conn.close()

    flash("Employee registered successfully!", "success")
    return redirect('/employee_register')


# ------------------ LOGIN PAGE ------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        f = request.form
        email = f['email']
        password = f['password']

        conn = get_db()
        user = conn.execute('SELECT * FROM employees WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user[4], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash("Login successful!", "success")
            return redirect('/dashboard')
        else:
            flash("Invalid email or password", "error")
            return redirect('/login')
    return render_template('login.html')


# ------------------ LOGOUT ------------------

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect('/login')


# ------------------ DASHBOARD ------------------

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first", "error")
        return redirect('/login')
    return render_template('dashboard.html', username=session['username'])

# ------------------ ADD MEASUREMENT SHEET ------------------

@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    f = request.form
    project_id = f['project_id']
    client_name = f['client_name']
    company_name = f['company_name']
    project_location = f['project_location']
    engineer_name = f['engineer_name']
    phone = f['phone']

    conn = get_db()
    conn.execute('''
        INSERT INTO measurement_sheet (project_id, client_name, company_name, project_location, engineer_name, phone)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (project_id, client_name, company_name, project_location, engineer_name, phone))
    conn.commit()
    conn.close()

    flash("Measurement sheet saved successfully.", "success")
    return redirect('/projects')


# ------------------ ADD DUCT ENTRY ------------------

@app.route('/add_duct', methods=['POST'])
def add_duct():
    f = request.form
    project_id = f['project_id']
    duct_no = f['duct_no']
    duct_type = f['duct_type']
    duct_size = f['duct_size']
    quantity = f['quantity']
    remarks = f['remarks']

    conn = get_db()
    conn.execute('''
        INSERT INTO measurement_entries (project_id, duct_no, duct_type, duct_size, quantity, remarks)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (project_id, duct_no, duct_type, duct_size, quantity, remarks))
    conn.commit()
    conn.close()

    flash("Duct entry added.", "success")
    return redirect('/projects')


# ------------------ API: GET DUCTS BY PROJECT ------------------

@app.route('/api/ducts/<int:project_id>')
def get_ducts(project_id):
    conn = get_db()
    ducts = conn.execute('SELECT * FROM measurement_entries WHERE project_id = ?', (project_id,)).fetchall()
    conn.close()

    duct_list = []
    for d in ducts:
        duct_list.append({
            'id': d[0],
            'project_id': d[1],
            'duct_no': d[2],
            'duct_type': d[3],
            'duct_size': d[4],
            'quantity': d[5],
            'remarks': d[6]
        })

    return jsonify(duct_list)


# ------------------ EXPORT CSV ------------------

@app.route('/export_csv/<int:project_id>')
def export_csv(project_id):
    conn = get_db()
    data = conn.execute('SELECT * FROM measurement_entries WHERE project_id = ?', (project_id,)).fetchall()
    conn.close()

    output = BytesIO()
    writer = csv.writer(output)
    writer.writerow(['Duct No', 'Type', 'Size', 'Quantity', 'Remarks'])
    for row in data:
        writer.writerow([row[2], row[3], row[4], row[5], row[6]])

    output.seek(0)
    response = make_response(output.read())
    response.headers['Content-Disposition'] = f'attachment; filename=duct_entries_project_{project_id}.csv'
    response.headers["Content-type"] = "text/csv"
    return response


# ------------------ EXPORT EXCEL ------------------

@app.route('/export_excel/<int:project_id>')
def export_excel(project_id):
    conn = get_db()
    data = conn.execute('SELECT * FROM measurement_entries WHERE project_id = ?', (project_id,)).fetchall()
    conn.close()

    df = pd.DataFrame(data, columns=['ID', 'Project ID', 'Duct No', 'Type', 'Size', 'Quantity', 'Remarks'])
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Duct Entries')
    writer.close()
    output.seek(0)

    return send_file(output, download_name=f'duct_entries_{project_id}.xlsx', as_attachment=True)


# ------------------ SUBMIT SHEET ------------------

@app.route('/submit_sheet/<int:project_id>', methods=['POST'])
def submit_sheet(project_id):
    conn = get_db()
    conn.execute('UPDATE projects SET status = ? WHERE id = ?', ('Submit for Approval', project_id))
    conn.commit()
    conn.close()

    flash("Measurement sheet submitted for approval.", "success")
    return redirect('/projects')


# ------------------ DUMMY DATA INSERT ------------------

@app.before_first_request
def insert_dummy_data():
    conn = get_db()
    # Insert dummy vendor
    conn.execute('INSERT OR IGNORE INTO vendors (id, name, gst_number, address) VALUES (1, "ACME Corp", "GSTACME123", "Bangalore")')

    # Insert dummy employee
    dummy_email = "test@ducterp.com"
    if not conn.execute('SELECT * FROM employees WHERE email = ?', (dummy_email,)).fetchone():
        conn.execute('''
            INSERT INTO employees (name, role, email, password)
            VALUES (?, ?, ?, ?)
        ''', ("Test User", "Admin", dummy_email, generate_password_hash("12345")))

    # Dummy project
    if not conn.execute('SELECT * FROM projects WHERE id = 1').fetchone():
        conn.execute('''
            INSERT INTO projects (enquiry_id, vendor_id, quotation_ro, start_date, end_date, location, incharge, notes, file, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('ENQ-ABC123', 1, 'RO123', '2025-07-01', '2025-07-20', 'Bangalore', 'John Doe', 'Test Notes', '', 'Design Process'))

    # Dummy measurement sheet
    if not conn.execute('SELECT * FROM measurement_sheet WHERE project_id = 1').fetchone():
        conn.execute('''
            INSERT INTO measurement_sheet (project_id, client_name, company_name, project_location, engineer_name, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (1, 'XYZ Ltd', 'XYZ Company', 'Bangalore', 'Engineer Raj', '9876543210'))

    # Dummy duct entries
    entries = conn.execute('SELECT * FROM measurement_entries WHERE project_id = 1').fetchall()
    if len(entries) == 0:
        ducts = [
            ('D001', 'Rectangular', '500x300', 10, 'Main Line'),
            ('D002', 'Circular', 'Ø250', 5, 'Secondary Line')
        ]
        for duct in ducts:
            conn.execute('''
                INSERT INTO measurement_entries (project_id, duct_no, duct_type, duct_size, quantity, remarks)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (1, duct[0], duct[1], duct[2], duct[3], duct[4]))

    conn.commit()
    conn.close()
# ------------------ PRODUCTION MODULE DASHBOARD ------------------

@app.route('/production')
def production_dashboard():
    conn = get_db()
    query = '''
        SELECT p.id, p.enquiry_id, p.location, p.status,
               IFNULL(ms.id, 0), IFNULL(SUM(me.quantity), 0),
               IFNULL(SUM(pr.sheet_cutting), 0), IFNULL(SUM(pr.plasma_fab), 0),
               IFNULL(SUM(pr.boxing_assembly), 0), IFNULL(pr.quality_check, 0),
               IFNULL(pr.dispatch, 0)
        FROM projects p
        LEFT JOIN measurement_sheet ms ON p.id = ms.project_id
        LEFT JOIN measurement_entries me ON p.id = me.project_id
        LEFT JOIN production pr ON p.id = pr.project_id
        GROUP BY p.id
    '''
    data = conn.execute(query).fetchall()
    conn.close()
    return render_template('production.html', data=data)


# ------------------ PRODUCTION PROGRESS UPDATE PAGE ------------------

@app.route('/production_update/<int:project_id>')
def production_update(project_id):
    conn = get_db()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    area = conn.execute('SELECT SUM(quantity) FROM measurement_entries WHERE project_id = ?', (project_id,)).fetchone()[0]
    progress = conn.execute('SELECT * FROM production WHERE project_id = ?', (project_id,)).fetchone()
    conn.close()

    if area is None:
        area = 0

    return render_template('production_update.html', project=project, area=area, progress=progress)


# ------------------ UPDATE PROGRESS ------------------

@app.route('/update_progress/<int:project_id>', methods=['POST'])
def update_progress(project_id):
    f = request.form
    sheet_cutting = int(f.get('sheet_cutting', 0))
    plasma_fab = int(f.get('plasma_fab', 0))
    boxing_assembly = int(f.get('boxing_assembly', 0))
    quality_check = int(f.get('quality_check', 0))
    dispatch = int(f.get('dispatch', 0))

    conn = get_db()
    exists = conn.execute('SELECT * FROM production WHERE project_id = ?', (project_id,)).fetchone()

    if exists:
        conn.execute('''
            UPDATE production SET
            sheet_cutting = ?, plasma_fab = ?, boxing_assembly = ?,
            quality_check = ?, dispatch = ?
            WHERE project_id = ?
        ''', (sheet_cutting, plasma_fab, boxing_assembly, quality_check, dispatch, project_id))
    else:
        conn.execute('''
            INSERT INTO production (project_id, sheet_cutting, plasma_fab, boxing_assembly, quality_check, dispatch)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, sheet_cutting, plasma_fab, boxing_assembly, quality_check, dispatch))

    conn.commit()
    conn.close()
    flash("Progress updated successfully.", "success")
    return redirect('/production')


# ------------------ API: PHASE BREAKDOWN ------------------

@app.route('/api/phase_breakdown/<int:project_id>')
def phase_breakdown(project_id):
    conn = get_db()
    data = conn.execute('SELECT * FROM production WHERE project_id = ?', (project_id,)).fetchone()
    conn.close()
    if not data:
        return jsonify({})
    return jsonify({
        "Sheet Cutting": data[1],
        "Plasma & Fabrication": data[2],
        "Boxing & Assembly": data[3],
        "Quality Check": data[4],
        "Dispatch": data[5]
    })


# ------------------ DATABASE TABLE FOR PRODUCTION ------------------

# You must run this on DB init:

'''
CREATE TABLE IF NOT EXISTS production (
    project_id INTEGER PRIMARY KEY,
    sheet_cutting INTEGER DEFAULT 0,
    plasma_fab INTEGER DEFAULT 0,
    boxing_assembly INTEGER DEFAULT 0,
    quality_check INTEGER DEFAULT 0,
    dispatch INTEGER DEFAULT 0
);
'''


# ------------------ DUMMY PRODUCTION DATA ------------------

@app.before_first_request
def insert_dummy_production():
    conn = get_db()
    check = conn.execute('SELECT * FROM production WHERE project_id = 1').fetchone()
    if not check:
        conn.execute('''
            INSERT INTO production (project_id, sheet_cutting, plasma_fab, boxing_assembly, quality_check, dispatch)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (1, 20, 15, 10, 5, 0))
        conn.commit()
    conn.close()
# ------------------ PRODUCTION SUMMARY PAGE ------------------

@app.route('/production_summary')
def production_summary():
    conn = get_db()
    summary = conn.execute('''
        SELECT p.enquiry_id, p.location, p.incharge, p.start_date, p.end_date,
               IFNULL(SUM(me.quantity), 0) as total_area,
               IFNULL(pr.sheet_cutting, 0), IFNULL(pr.plasma_fab, 0),
               IFNULL(pr.boxing_assembly, 0), IFNULL(pr.quality_check, 0),
               IFNULL(pr.dispatch, 0)
        FROM projects p
        LEFT JOIN measurement_entries me ON p.id = me.project_id
        LEFT JOIN production pr ON p.id = pr.project_id
        GROUP BY p.id
    ''').fetchall()
    conn.close()

    results = []
    for row in summary:
        total_area = row[5] if row[5] else 1
        percent_sheet = (row[6] / total_area) * 100 if total_area else 0
        percent_plasma = (row[7] / total_area) * 100 if total_area else 0
        percent_boxing = (row[8] / total_area) * 100 if total_area else 0
        percent_quality = row[9]
        percent_dispatch = row[10]
        overall = (percent_sheet + percent_plasma + percent_boxing + percent_quality + percent_dispatch) / 5
        results.append({
            "enquiry_id": row[0],
            "location": row[1],
            "incharge": row[2],
            "start": row[3],
            "end": row[4],
            "area": row[5],
            "sheet": round(percent_sheet, 2),
            "plasma": round(percent_plasma, 2),
            "boxing": round(percent_boxing, 2),
            "quality": percent_quality,
            "dispatch": percent_dispatch,
            "overall": round(overall, 2)
        })

    return render_template("production_summary.html", results=results)
# ------------------ VENDOR REGISTRATION MODULE ------------------

@app.route('/register_vendor', methods=['GET', 'POST'])
def register_vendor():
    conn = get_db()
    if request.method == 'POST':
        vendor_name = request.form['vendor_name']
        gst_number = request.form['gst_number']
        address = request.form['address']
        bank_name = request.form['bank_name']
        account_number = request.form['account_number']
        ifsc_code = request.form['ifsc_code']
        
        # Insert into vendors table
        conn.execute('INSERT INTO vendors (vendor_name, gst_number, address) VALUES (?, ?, ?)',
                     (vendor_name, gst_number, address))
        vendor_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Insert communication contacts
        contact_names = request.form.getlist('contact_name[]')
        contact_emails = request.form.getlist('contact_email[]')
        contact_phones = request.form.getlist('contact_phone[]')

        for i in range(len(contact_names)):
            if contact_names[i]:
                conn.execute('INSERT INTO vendor_contacts (vendor_id, name, email, phone) VALUES (?, ?, ?, ?)',
                             (vendor_id, contact_names[i], contact_emails[i], contact_phones[i]))

        # Insert bank details
        conn.execute('INSERT INTO vendor_bank_details (vendor_id, bank_name, account_number, ifsc_code) VALUES (?, ?, ?, ?)',
                     (vendor_id, bank_name, account_number, ifsc_code))

        conn.commit()
        flash("Vendor registered successfully!", "success")
        return redirect('/register_vendor')

    # View existing vendors and their contacts
    vendors = conn.execute('SELECT * FROM vendors').fetchall()
    contacts = conn.execute('SELECT * FROM vendor_contacts').fetchall()
    conn.close()
    return render_template('register_vendor.html', vendors=vendors, contacts=contacts)
# ------------------ EXPORT: PROJECTS TO EXCEL ------------------

@app.route('/export_projects_excel')
def export_projects_excel():
    conn = get_db()
    projects = conn.execute('SELECT p.*, v.vendor_name FROM projects p LEFT JOIN vendors v ON p.vendor_id = v.id').fetchall()
    conn.close()

    df = pd.DataFrame(projects, columns=[
        'ID', 'Enquiry ID', 'Vendor ID', 'GST', 'Address', 'Quotation RO', 'Start Date', 'End Date',
        'Location', 'Incharge', 'Notes', 'File', 'Status', 'Vendor Name'
    ])

    output = BytesIO()
    df.to_excel(output, index=False, sheet_name='Projects')
    output.seek(0)

    return send_file(output, download_name="projects_summary.xlsx", as_attachment=True)

# ------------------ EXPORT: MEASUREMENT TO EXCEL ------------------

@app.route('/export_excel/<int:project_id>')
def export_excel(project_id):
    conn = get_db()
    entries = conn.execute('SELECT * FROM measurement_entries WHERE project_id = ?', (project_id,)).fetchall()
    conn.close()

    df = pd.DataFrame(entries, columns=['ID', 'Project ID', 'Duct No', 'Type', 'Size', 'Quantity', 'Remarks'])

    output = BytesIO()
    df.to_excel(output, index=False, sheet_name='Measurement')
    output.seek(0)

    return send_file(output, download_name=f"measurement_project_{project_id}.xlsx", as_attachment=True)

# ------------------ EXPORT: PRODUCTION TO EXCEL ------------------

@app.route('/export_production_excel/<int:project_id>')
def export_production_excel(project_id):
    conn = get_db()
    progress = conn.execute('SELECT * FROM production WHERE project_id = ?', (project_id,)).fetchall()
    conn.close()

    df = pd.DataFrame(progress, columns=[
        'ID', 'Project ID', 'Area SQM', 'Sheet Cutting', 'Plasma Fab',
        'Boxing Assembly', 'QC', 'Dispatch', 'Overall'
    ])

    output = BytesIO()
    df.to_excel(output, index=False, sheet_name='Production')
    output.seek(0)

    return send_file(output, download_name=f"production_project_{project_id}.xlsx", as_attachment=True)
@app.route('/export_project_pdf/<int:project_id>')
def export_project_pdf(project_id):
    conn = get_db()
    project = conn.execute('SELECT p.*, v.vendor_name FROM projects p LEFT JOIN vendors v ON p.vendor_id = v.id WHERE p.id = ?', (project_id,)).fetchone()
    ducts = conn.execute('SELECT * FROM measurement_entries WHERE project_id = ?', (project_id,)).fetchall()
    prod = conn.execute('SELECT * FROM production WHERE project_id = ?', (project_id,)).fetchone()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, y, f"PROJECT SUMMARY REPORT: {project[1]}")
    y -= 30

    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Vendor: {project[-1]} | Location: {project[6]} | Incharge: {project[9]}")
    y -= 20
    c.drawString(50, y, f"Status: {project[12]}")
    y -= 30

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Measurement Entries:")
    y -= 20
    for d in ducts:
        if y < 100: c.showPage(); y = height - 50
        c.drawString(60, y, f"{d[2]} | {d[3]} | {d[4]} | Qty: {d[5]} | Remarks: {d[6]}")
        y -= 15

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Production Progress:")
    y -= 20
    prod_labels = ['Sheet Cutting', 'Plasma Fab', 'Boxing Assembly', 'QC', 'Dispatch', 'Overall']
    for i, label in enumerate(prod_labels, start=3):
        c.drawString(60, y, f"{label}: {prod[i]}%")
        y -= 15

    y -= 40
    c.drawString(50, y, "Project Manager Signature: ____________________")
    y -= 30
    c.drawString(50, y, "Director Signature: ___________________________")

    c.save()
    buffer.seek(0)
    return send_file(buffer, download_name=f"project_{project_id}_summary.pdf", as_attachment=True)
# ------------------ ROOT REDIRECT ------------------

@app.route('/')
def root():
    return redirect(url_for('login'))


# ------------------ LOGIN ------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        user = conn.execute('SELECT * FROM employees WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'error')

    return render_template('login.html')


# ------------------ LOGOUT ------------------

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))


# ------------------ DUMMY DATA INSERT ------------------

def insert_dummy_data():
    conn = get_db()
    cur = conn.cursor()

    # Check and insert dummy employee
    emp_exists = cur.execute("SELECT * FROM employees WHERE username = 'admin'").fetchone()
    if not emp_exists:
        cur.execute("INSERT INTO employees (name, username, password) VALUES (?, ?, ?)", 
                    ('Admin User', 'admin', generate_password_hash('admin123')))

    # Check and insert dummy vendor
    ven_exists = cur.execute("SELECT * FROM vendors WHERE vendor_name = 'Test Vendor'").fetchone()
    if not ven_exists:
        cur.execute("INSERT INTO vendors (vendor_name, gst_number, address) VALUES (?, ?, ?)", 
                    ('Test Vendor', 'GSTIN12345', 'Chennai'))

    # Check and insert dummy project
    proj_exists = cur.execute("SELECT * FROM projects WHERE enquiry_id = 'ENQ-0001'").fetchone()
    if not proj_exists:
        cur.execute("""
            INSERT INTO projects 
            (enquiry_id, vendor_id, gst_number, address, quotation_ro, start_date, end_date,
            location, project_incharge, notes, file, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('ENQ-0001', 1, 'GSTIN12345', 'Chennai', 'QRO-01', '2024-06-01', '2024-08-30',
              'Chennai Site', 'Mr. Kumar', 'Test project', '', 'Design Process'))

    conn.commit()
    conn.close()


# ------------------ SESSION CONFIG + RUN ------------------

if __name__ == '__main__':
    insert_dummy_data()
    app.run(debug=True)
