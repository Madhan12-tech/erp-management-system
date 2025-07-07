from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'secretkey'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------- DB INITIALIZATION ----------
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Employee Login table
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )''')

    # Vendors
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        gst TEXT,
        address TEXT
    )''')

    # Vendor Contacts
    c.execute('''CREATE TABLE IF NOT EXISTS vendor_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER,
        name TEXT,
        phone TEXT,
        FOREIGN KEY (vendor_id) REFERENCES vendors(id)
    )''')

    # Vendor Bank Details
    c.execute('''CREATE TABLE IF NOT EXISTS vendor_banks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER,
        bank_name TEXT,
        account_no TEXT,
        ifsc_code TEXT,
        FOREIGN KEY (vendor_id) REFERENCES vendors(id)
    )''')

    # Projects Master
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        enquiry_id TEXT,
        quotation_ro TEXT,
        start_date TEXT,
        end_date TEXT,
        location TEXT,
        file_name TEXT,
        gst_number TEXT,
        address TEXT,
        incharge TEXT,
        notes TEXT,
        status TEXT DEFAULT 'Preparation Pending'
    )''')

    # Phase 1 - Preparation
    c.execute('''CREATE TABLE IF NOT EXISTS preparation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        site_engineer TEXT,
        mobile TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )''')

    # Phase Log Tracking Table
    c.execute('''CREATE TABLE IF NOT EXISTS project_status_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        phase TEXT,
        timestamp TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )''')

    # Project File Uploads (drawings)
    c.execute('''CREATE TABLE IF NOT EXISTS project_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        filename TEXT,
        upload_date TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )''')

    # Production Table (Phase 6+)
    c.execute('''CREATE TABLE IF NOT EXISTS production (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        item_name TEXT,
        quantity INTEGER,
        status TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )''')

    # Production Summary (display status)
    c.execute('''CREATE TABLE IF NOT EXISTS production_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        summary TEXT,
        updated_on TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )''')

    # Vendors table
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        gst_number TEXT,
        address TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("SELECT id, name FROM employees WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid login credentials', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


# ---------- REGISTER EMPLOYEE ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO employees (name, email, password, role) VALUES (?, ?, ?, ?)",
                      (name, email, password, role))
            conn.commit()
            flash('Employee registered successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Email already exists.', 'danger')
        conn.close()

        return redirect(url_for('register'))

    return render_template('register.html')


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))


# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# ---------- VENDOR REGISTRATION ----------
@app.route('/vendor_register', methods=['GET', 'POST'])
def vendor_register():
    if request.method == 'POST':
        name = request.form['vendor_name']
        gst = request.form['gst_number']
        address = request.form['address']
        contacts = request.form.getlist('contact_person[]')
        phones = request.form.getlist('contact_phone[]')

        bank_name = request.form.get('bank_name', '')
        account_no = request.form.get('account_number', '')
        ifsc = request.form.get('ifsc', '')

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()

        c.execute("INSERT INTO vendors (name, gst_number, address) VALUES (?, ?, ?)", (name, gst, address))
        vendor_id = c.lastrowid

        for person, phone in zip(contacts, phones):
            c.execute("INSERT INTO vendor_contacts (vendor_id, name, phone) VALUES (?, ?, ?)", (vendor_id, person, phone))

        if bank_name and account_no and ifsc:
            c.execute('''CREATE TABLE IF NOT EXISTS vendor_banks (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            vendor_id INTEGER,
                            bank_name TEXT,
                            account_no TEXT,
                            ifsc_code TEXT,
                            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
                        )''')
            c.execute("INSERT INTO vendor_banks (vendor_id, bank_name, account_no, ifsc_code) VALUES (?, ?, ?, ?)",
                      (vendor_id, bank_name, account_no, ifsc))

        conn.commit()
        conn.close()
        flash("Vendor registered successfully", "success")
        return redirect(url_for('vendor_register'))

    return render_template('vendor_register.html')


# ---------- API: GET VENDOR INFO (FOR AUTO-FILL GST AND ADDRESS) ----------
@app.route('/get_vendor_info/<vendor_name>')
def get_vendor_info(vendor_name):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT gst_number, address FROM vendors WHERE name = ?", (vendor_name,))
    row = c.fetchone()
    conn.close()

    if row:
        return {'gst': row[0], 'address': row[1]}
    return {}
import json

@app.route('/projects_page')
def projects_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Fetch vendors for dropdown
    c.execute("SELECT id, name, gst_number, address FROM vendors")
    vendors = [{'id': row[0], 'name': row[1], 'gst': row[2], 'address': row[3]} for row in c.fetchall()]

    # Fetch employees for project incharge
    c.execute("SELECT name FROM employees")
    employees = [{'name': row[0]} for row in c.fetchall()]

    # Fetch projects for table and phase logic
    c.execute("SELECT * FROM projects")
    rows = c.fetchall()
    columns = [column[0] for column in c.description]
    projects = [dict(zip(columns, row)) for row in rows]

    # For auto-generating enquiry_id
    enquiry_id = "ENQ-" + datetime.now().strftime("%Y%m%d%H%M%S")

    conn.close()

    return render_template("projects.html",
                           vendors=vendors,
                           employees=employees,
                           projects=projects,
                           enquiry_id=enquiry_id,
                           today=datetime.today().strftime('%Y-%m-%d'),
                           vendor_json=json.dumps(vendors))


@app.route('/add_project', methods=['POST'])
def add_project():
    data = request.form

    client = data['client_name']
    enquiry_id = data['enquiry_id']
    quotation_ro = data['quotation_ro']
    start_date = data['start_date']
    end_date = data['end_date']
    location = data['location']
    gst_number = data['gst_number']
    address = data['address']
    incharge = data['incharge']
    notes = data.get('notes', '')

    file = request.files.get('file')
    filename = ''
    if file and file.filename:
        filename = 'uploads/' + file.filename
        file.save(filename)

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''INSERT INTO projects 
        (client_name, enquiry_id, quotation_ro, start_date, end_date, location, gst_number, address, incharge, notes, file, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (client, enquiry_id, quotation_ro, start_date, end_date, location, gst_number, address, incharge, notes, filename, "Preparation Started"))
    conn.commit()
    conn.close()

    flash("Project registered successfully", "success")
    return redirect(url_for('projects_page'))

@app.route('/start_preparation', methods=['POST'])
def start_preparation():
    project_id = request.form.get('project_id')
    site_engineer = request.form.get('site_engineer')
    mobile = request.form.get('mobile')

    if not project_id or not project_id.isdigit():
        flash("Invalid project ID during preparation phase", "error")
        return redirect(url_for('projects_page'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''UPDATE projects SET site_engineer=?, mobile=?, status=? WHERE id=?''',
              (site_engineer, mobile, 'Preparation Completed', int(project_id)))
    conn.commit()
    conn.close()

    flash("Preparation saved. Continue to duct entry.", "success")
    return redirect(url_for('duct_entry', project_id=int(project_id)))


@app.route('/duct_entry/<int:project_id>')
def duct_entry(project_id):
    # This will be filled later — placeholder page
    return f"Duct entry page for project {project_id} (coming soon)"


@app.route('/mark_completion/<int:project_id>', methods=['POST'])
def mark_completion(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status=? WHERE id=?", ('Completion Completed', project_id))
    conn.commit()
    conn.close()
    flash("Marked as completed", "info")
    return redirect(url_for('projects_page'))


@app.route('/submit_for_approval/<int:project_id>', methods=['POST'])
def submit_for_approval(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status=? WHERE id=?", ('Submitted for Approval', project_id))
    conn.commit()
    conn.close()
    flash("Submitted for approval", "info")
    return redirect(url_for('projects_page'))


@app.route('/under_review/<int:project_id>', methods=['POST'])
def under_review(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status=? WHERE id=?", ('Under Review', project_id))
    conn.commit()
    conn.close()
    flash("Now under review", "info")
    return redirect(url_for('projects_page'))


@app.route('/approve_project/<int:project_id>', methods=['POST'])
def approve_project(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status=? WHERE id=?", ('Approved ✅', project_id))
    conn.commit()
    conn.close()
    flash("Project Approved", "success")
    return redirect(url_for('projects_page'))


@app.route('/reject_to_preparation/<int:project_id>', methods=['POST'])
def reject_to_preparation(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status=? WHERE id=?", ('Preparation Started', project_id))
    conn.commit()
    conn.close()
    flash("Sent back to Preparation phase", "warning")
    return redirect(url_for('projects_page'))
@app.route('/production')
def production():
    return "Production module under construction."


@app.route('/production_summary')
def production_summary():
    return "Production summary view is coming soon."


# ---------- DB SETUP ----------
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    # Vendors table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gst TEXT,
            address TEXT
        )
    ''')

    # Employees table
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            designation TEXT
        )
    ''')

    # Projects table
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            enquiry_id TEXT,
            quotation_ro TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            file TEXT,
            gst_number TEXT,
            address TEXT,
            incharge TEXT,
            notes TEXT,
            status TEXT DEFAULT 'Preparation Started',
            site_engineer TEXT,
            mobile TEXT
        )
    ''')

    # Insert dummy user if not exists
    c.execute("SELECT * FROM users WHERE username=?", ('admin',))
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', 'admin123'))

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    app.run(debug=True)


