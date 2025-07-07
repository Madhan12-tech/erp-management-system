from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import uuid
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import random
import string

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# -------------------- DATABASE SETUP --------------------
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Employees
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')

    # Vendors
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gst TEXT,
            address TEXT
        )
    ''')

    # Vendor Contacts
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendor_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            name TEXT,
            phone TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        )
    ''')

    # Projects
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enquiry_id TEXT,
            vendor_id INTEGER,
            gst_number TEXT,
            address TEXT,
            quotation_ro TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            incharge TEXT,
            notes TEXT,
            file TEXT,
            status TEXT DEFAULT 'Design Process',
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        )
    ''')

    # Project Enquiry
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_enquiry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            enquiry_id TEXT,
            client_name TEXT,
            company_name TEXT,
            site_engineer TEXT,
            mobile_number TEXT,
            location TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')

    # Project Registration
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_registration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client_name TEXT,
            company_name TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')

    # Measurement Sheet
    c.execute('''
        CREATE TABLE IF NOT EXISTS measurement_sheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client_name TEXT,
            company_name TEXT,
            site_engineer TEXT,
            mobile TEXT,
            location TEXT,
            area_sqm REAL DEFAULT 0
        )
    ''')

    # Measurement Entries
    c.execute('''
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

    # Production Status
    c.execute('''
        CREATE TABLE IF NOT EXISTS production_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            sheet_cutting_progress REAL,
            plasma_fab_progress REAL,
            boxing_assembly_progress REAL,
            quality_check_progress REAL,
            dispatch_progress REAL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # Production Tracking
    c.execute('''
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            phase TEXT,
            done REAL DEFAULT 0,
            total REAL DEFAULT 0,
            percentage REAL DEFAULT 0,
            date TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    conn.commit()
    conn.close()

# Run DB initializer on startup
init_db()

# -------------------- SEED DUMMY DATA --------------------
def seed_dummy_data():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Dummy Vendors
    vendors = [
        ('ABC Constructions', 'GSTTN1234A1Z5', 'Chennai, Tamil Nadu'),
        ('Skyline Infra', 'GSTMH5678B2X6', 'Mumbai, Maharashtra'),
        ('GreenBuild Ltd', 'GSTKA9012C3Y7', 'Bangalore, Karnataka')
    ]
    for name, gst, address in vendors:
        c.execute("INSERT OR IGNORE INTO vendors (name, gst, address) VALUES (?, ?, ?)", (name, gst, address))

    # Dummy Employees with hashed passwords
    employees = [
        # password: password123
        ('John Doe', 'john.doe@example.com', generate_password_hash('password123'), 'admin'),
        # password: securepass
        ('Priya Sharma', 'priya.sharma@example.com', generate_password_hash('securepass'), 'admin'),
        # password: adminpass
        ('Arun Kumar', 'arun.kumar@example.com', generate_password_hash('adminpass'), 'admin')
    ]
    for name, email, password_hash, role in employees:
        c.execute("INSERT OR IGNORE INTO employees (name, email, password, role) VALUES (?, ?, ?, ?)",
                  (name, email, password_hash, role))

    conn.commit()
    conn.close()

# Optional: Uncomment to run once
# seed_dummy_data()

# -------------------- LOGIN --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        with sqlite3.connect('erp.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id, name, email, password, role FROM employees WHERE email = ?", (email,))
            user = c.fetchone()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['name'] = user[1]
            session['email'] = user[2]
            session['role'] = user[4]
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials. Please try again.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

# -------------------- LOGOUT --------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# -------------------- EMPLOYEE REGISTRATION --------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        name = first_name + " " + last_name
        conn = sqlite3.connect("erp.db")
        c = conn.cursor()
        c.execute("INSERT INTO employees (name, email, password, role) VALUES (?, ?, ?, ?)",
                  (name, email, generate_password_hash(password), role))
        conn.commit()
        conn.close()
        flash("Employee registered successfully!", "success")
        return redirect(url_for("login"))
    return render_template("employee_register.html")

# -------------------- VENDOR REGISTRATION --------------------
@app.route('/vendor_register', methods=['GET', 'POST'])
def vendor_register():
    if request.method == 'POST':
        name = request.form['vendor_name']
        gst = request.form['gst']
        address = request.form['address']
        contacts = request.form.getlist('contact_person[]')
        phones = request.form.getlist('contact_phone[]')

        bank = request.form.get('bank')
        account_no = request.form.get('account_no')
        ifsc = request.form.get('ifsc')

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("INSERT INTO vendors (name, gst, address) VALUES (?, ?, ?)", (name, gst, address))
        vendor_id = c.lastrowid

        for contact, phone in zip(contacts, phones):
            c.execute("INSERT INTO vendor_contacts (vendor_id, name, phone) VALUES (?, ?, ?)",
                      (vendor_id, contact, phone))

        c.execute('''CREATE TABLE IF NOT EXISTS vendor_banks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        vendor_id INTEGER,
                        bank_name TEXT,
                        account_no TEXT,
                        ifsc_code TEXT,
                        FOREIGN KEY (vendor_id) REFERENCES vendors(id)
                    )''')
        c.execute("INSERT INTO vendor_banks (vendor_id, bank_name, account_no, ifsc_code) VALUES (?, ?, ?, ?)",
                  (vendor_id, bank, account_no, ifsc))

        conn.commit()
        conn.close()
        flash("Vendor registered successfully!", "success")
        return redirect(url_for('vendor_register'))

    return render_template("vendor_register.html")

# -------------------- DASHBOARD --------------------
@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html")

@app.route('/')
def home():
    return redirect(url_for('projects_page'))

# -------------------- PROJECT REGISTER (MODAL DATA) --------------------
@app.route('/projects_page')
def projects_page():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Fetch vendors
    c.execute("SELECT id, name, gst, address FROM vendors")
    vendors = [{'id': row[0], 'name': row[1], 'gst': row[2], 'address': row[3]} for row in c.fetchall()]

    # Fetch employees for incharge dropdown
    c.execute("SELECT name FROM employees")
    employees = [{'name': row[0]} for row in c.fetchall()]

    # Fetch project list
    c.execute("SELECT * FROM projects")
    project_rows = c.fetchall()
    projects = [{
        'id': row[0],
        'enquiry_id': row[1],
        'status': row[13],
    } for row in project_rows]

    conn.close()

    # Generate new enquiry_id
    enquiry_id = "ENQ-" + datetime.now().strftime("%Y%m%d%H%M%S")
    today = datetime.today().strftime('%Y-%m-%d')

    return render_template("projects.html", vendors=vendors, employees=employees,
                           enquiry_id=enquiry_id, today=today, projects=projects)



# -------------------- ADD PROJECT --------------------
@app.route('/add_project', methods=['POST'])
def add_project():
    enquiry_id = request.form['enquiry_id']
    client_name = request.form['client_name']
    quotation_ro = request.form['quotation_ro']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    location = request.form['location']
    gst_number = request.form['gst_number']
    address = request.form['address']
    incharge = request.form['incharge']
    notes = request.form['notes']
    file = request.files.get('file')

    filename = None
    if file and file.filename != '':
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        upload_path = os.path.join('static/uploads', filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

    # Get vendor_id from name
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT id FROM vendors WHERE name = ?", (client_name,))
    vendor_row = c.fetchone()
    vendor_id = vendor_row[0] if vendor_row else None

    # Insert into projects
    c.execute('''INSERT INTO projects 
        (enquiry_id, vendor_id, gst_number, address, quotation_ro, start_date, end_date, location, incharge, notes, file) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (enquiry_id, vendor_id, gst_number, address, quotation_ro, start_date, end_date, location, incharge, notes, filename))

    conn.commit()
    conn.close()
    flash("Project added successfully!", "success")
    return redirect(url_for('projects_page'))

# -------------------- START PREPARATION --------------------
@app.route('/start_preparation', methods=['POST'])
def start_preparation():
    project_id = request.form.get('project_id')
    site_engineer = request.form.get('site_engineer')
    mobile = request.form.get('mobile')
    location = request.form.get('location')
    client_name = request.form.get('client_name')

    if not project_id:
        flash("Project ID missing!", "error")
        return redirect(url_for('projects_page'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''INSERT INTO project_enquiry (project_id, enquiry_id, client_name, company_name, site_engineer, mobile_number, location)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (project_id, f"ENQ-{random.randint(1000,9999)}", client_name, client_name, site_engineer, mobile, location))

    c.execute("UPDATE projects SET status = 'Preparation Completed' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    flash("Preparation phase completed!", "success")
    return redirect(url_for('projects_page'))

# -------------------- API: GET GST & ADDRESS --------------------
@app.route('/get_vendor_details/<vendor_name>')
def get_vendor_details(vendor_name):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT gst, address FROM vendors WHERE name = ?", (vendor_name,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'gst': row[0], 'address': row[1]}
    return {'gst': '', 'address': ''}

# -------------------- MARK PHASE COMPLETION --------------------
@app.route('/mark_completion/<int:project_id>', methods=['POST'])
def mark_completion(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Completion Completed' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("Phase 2: Completion marked as done.", "success")
    return redirect(url_for('projects_page'))

# -------------------- SUBMIT FOR APPROVAL --------------------
@app.route('/submit_for_approval/<int:project_id>', methods=['POST'])
def submit_for_approval(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Submitted for Approval' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("Project submitted for approval.", "success")
    return redirect(url_for('projects_page'))

# -------------------- UNDER REVIEW --------------------
@app.route('/under_review/<int:project_id>', methods=['POST'])
def under_review(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Under Review' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("Project is now under review.", "info")
    return redirect(url_for('projects_page'))

# -------------------- APPROVE PROJECT --------------------
@app.route('/approve_project/<int:project_id>', methods=['POST'])
def approve_project(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Approved' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("Project approved ✅", "success")
    return redirect(url_for('projects_page'))

# -------------------- REJECT BACK TO PREPARATION --------------------
@app.route('/reject_to_preparation/<int:project_id>', methods=['POST'])
def reject_to_preparation(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Design Process' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("Project sent back to preparation phase.", "warning")
    return redirect(url_for('projects_page'))

# -------------------- MAIN --------------------
if __name__ == "__main__":
    app.run(debug=True)
