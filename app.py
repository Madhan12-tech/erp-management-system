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
            email TEXT,
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
    # Vendor Bank Details
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendor_banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            bank_name TEXT,
            account_no TEXT,
            ifsc_code TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        )
    ''')

    # Design Preparation Phase (Phase 1)
    c.execute('''
        CREATE TABLE IF NOT EXISTS preparation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            site_engineer TEXT,
            mobile TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# Dummy admin if not exists
def create_dummy_admin():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM employees WHERE email = ?", ('admin@erp.com',))
    if not c.fetchone():
        hashed_password = generate_password_hash('admin123')
        c.execute("INSERT INTO employees (name, email, password, role) VALUES (?, ?, ?, ?)",
                  ('Admin', 'admin@erp.com', hashed_password, 'admin'))
        conn.commit()
    conn.close()

create_dummy_admin()

# ---------- AUTH ROUTES ----------

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("SELECT id, name, password FROM employees WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            flash("Login successful", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "error")
            return redirect(url_for('login'))
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO employees (name, email, password, role) VALUES (?, ?, ?, ?)",
                      (name, email, password, 'employee'))
            conn.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already registered", "error")
            return redirect(url_for('register'))
        finally:
            conn.close()
    return render_template("register.html")

# ---------- DASHBOARD ----------

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html")


# ---------- VENDOR REGISTRATION ----------

@app.route('/vendor_register', methods=['GET', 'POST'])
def vendor_register():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['vendor_name']
        gst = request.form['gst']
        address = request.form['address']
        contacts = request.form.getlist('contact_person[]')
        phones = request.form.getlist('contact_phone[]')
        bank_name = request.form.get('bank')
        account_no = request.form.get('account_no')
        ifsc = request.form.get('ifsc')

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()

        # Insert vendor
        c.execute("INSERT INTO vendors (name, gst, address) VALUES (?, ?, ?)", (name, gst, address))
        vendor_id = c.lastrowid

        # Insert contacts
        for person, phone in zip(contacts, phones):
            c.execute("INSERT INTO vendor_contacts (vendor_id, name, phone) VALUES (?, ?, ?)",
                      (vendor_id, person, phone))

        # Insert bank
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

    return render_template("vendor_register.html")


# ---------- API: Get Vendor Details (AJAX Support) ----------

@app.route('/get_vendor_details', methods=['POST'])
def get_vendor_details():
    vendor_name = request.form['vendor_name']
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT gst, address FROM vendors WHERE name = ?", (vendor_name,))
    result = c.fetchone()
    conn.close()
    if result:
        return jsonify({'gst': result[0], 'address': result[1]})
    else:
        return jsonify({'gst': '', 'address': ''})

from datetime import datetime

# ---------- PROJECTS PAGE + REGISTRATION ----------

@app.route('/projects_page')
def projects_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Fetch vendors
    c.execute("SELECT id, name, gst, address FROM vendors")
    vendors = [{'id': row[0], 'name': row[1], 'gst': row[2], 'address': row[3]} for row in c.fetchall()]

    # Fetch employees
    c.execute("SELECT name FROM employees")
    employees = [{'name': row[0]} for row in c.fetchall()]

    # Fetch projects
    c.execute("SELECT * FROM projects")
    project_rows = c.fetchall()
    projects = [{'id': row[0], 'client_name': row[1], 'location': row[5], 'status': row[9]} for row in project_rows]

    # Generate Enquiry ID
    enquiry_id = f"ENQ-{uuid.uuid4().hex[:6].upper()}"

    conn.close()

    return render_template('projects.html',
                           vendors=vendors,
                           employees=employees,
                           enquiry_id=enquiry_id,
                           today=datetime.today().strftime('%Y-%m-%d'),
                           projects=projects)


@app.route('/add_project', methods=['POST'])
def add_project():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    data = request.form
    file = request.files.get('file')
    filename = file.filename if file else None

    enquiry_id = data['enquiry_id']
    client_name = data['client_name']
    quotation_ro = data['quotation_ro']
    start_date = data['start_date']
    end_date = data['end_date']
    location = data['location']
    gst_number = data.get('gst_number', '')
    address = data.get('address', '')
    incharge = data['incharge']
    notes = data.get('notes', '')

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enquiry_id TEXT,
                    client_name TEXT,
                    quotation_ro TEXT,
                    start_date TEXT,
                    location TEXT,
                    end_date TEXT,
                    drawing TEXT,
                    incharge TEXT,
                    status TEXT,
                    notes TEXT,
                    gst TEXT,
                    address TEXT
                )''')

    c.execute('''INSERT INTO projects (
                    enquiry_id, client_name, quotation_ro, start_date, location, end_date,
                    drawing, incharge, status, notes, gst, address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (enquiry_id, client_name, quotation_ro, start_date, location, end_date,
               filename, incharge, 'Preparation Started', notes, gst_number, address))

    conn.commit()
    conn.close()

    if file:
        file.save(f"uploads/{filename}")

    flash("Project registered successfully", "success")
    return redirect(url_for('projects_page'))

# ---------- DESIGN PROCESS PHASES ----------

@app.route('/start_preparation', methods=['POST'])
def start_preparation():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    project_id = request.form.get('project_id')
    site_engineer = request.form.get('site_engineer')
    mobile = request.form.get('mobile')

    if not project_id:
        flash("Project ID missing in preparation form", "error")
        return redirect(url_for('projects_page'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Create table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS preparation_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    site_engineer TEXT,
                    mobile TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )''')

    c.execute("INSERT INTO preparation_details (project_id, site_engineer, mobile) VALUES (?, ?, ?)",
              (project_id, site_engineer, mobile))

    c.execute("UPDATE projects SET status = 'Preparation Completed' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    flash("Preparation completed", "success")
    return redirect(url_for('projects_page'))


@app.route('/mark_completion/<int:project_id>', methods=['POST'])
def mark_completion(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Completion Completed' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    flash("Project marked as completed", "success")
    return redirect(url_for('projects_page'))


@app.route('/submit_for_approval/<int:project_id>', methods=['POST'])
def submit_for_approval(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Submitted for Approval' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    flash("Project submitted for approval", "success")
    return redirect(url_for('projects_page'))


@app.route('/under_review/<int:project_id>', methods=['POST'])
def under_review(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Under Review' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    flash("Project status updated to 'Under Review'", "success")
    return redirect(url_for('projects_page'))


@app.route('/approve_project/<int:project_id>', methods=['POST'])
def approve_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Approved' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    flash("Project approved", "success")
    return redirect(url_for('projects_page'))


@app.route('/reject_to_preparation/<int:project_id>', methods=['POST'])
def reject_to_preparation(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Preparation Started' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    flash("Project sent back to preparation", "warning")
    return redirect(url_for('projects_page'))

---------- MAIN ----------
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=10000)
