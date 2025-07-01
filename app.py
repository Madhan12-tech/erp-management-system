# app.py - Part 1: Setup & DB Initialization
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
import sqlite3, os
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ---------- Database Initialization ----------
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Project Sites
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            site_location TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            budget REAL,
            design_engineer TEXT,
            site_engineer TEXT,
            team_members TEXT
        )
    ''')

    # Accounts & Purchases
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            category TEXT,
            vendor_name TEXT,
            invoice_number TEXT,
            amount REAL,
            tax REAL,
            total REAL,
            date TEXT,
            description TEXT,
            assigned_by TEXT
        )
    ''')

    # Workforce
    c.execute('''
        CREATE TABLE IF NOT EXISTS workforce (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            department TEXT,
            salary REAL,
            present_days INTEGER,
            leave_days INTEGER,
            bonus REAL,
            deductions REAL,
            total_pay REAL,
            join_date TEXT,
            site_assigned TEXT
        )
    ''')

    # Inventory
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT,
            item_name TEXT,
            category TEXT,
            quantity INTEGER,
            unit TEXT,
            location TEXT,
            supplier TEXT,
            cost_price REAL,
            selling_price REAL,
            added_on TEXT
        )
    ''')

    # Transport
    c.execute('''
        CREATE TABLE IF NOT EXISTS transport (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT,
            driver_name TEXT,
            route TEXT,
            material TEXT,
            quantity INTEGER,
            status TEXT,
            assigned_date TEXT
        )
    ''')

    # Production
    c.execute('''
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            process TEXT,
            material_used TEXT,
            output_quantity INTEGER,
            operator TEXT,
            date TEXT
        )
    ''')

    conn.commit()
    conn.close()

# Call DB setup
init_db()
# ---------- Routes: Auth & Dashboard ----------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email=? AND password=?', (email, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user'] = user[1]
            session['role'] = user[4]
            flash('Login successful!', 'success')
            return redirect('/dashboard')
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        try:
            conn = sqlite3.connect('erp.db')
            c = conn.cursor()
            c.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
                      (name, email, password, role))
            conn.commit()
            conn.close()
            flash('Registration successful!', 'success')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('Email already exists.', 'danger')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html', username=session['user'])
    # ---------- Routes: Project & Site Management ----------
@app.route('/project-sites', methods=['GET', 'POST'])
def project_sites():
    if 'user' not in session:
        return redirect('/login')
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        project_name = request.form['project_name']
        site_location = request.form['site_location']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        status = request.form['status']
        budget = request.form['budget']
        design_engineer = request.form['design_engineer']
        site_engineer = request.form['site_engineer']
        team_members = request.form['team_members']

        c.execute('''
            INSERT INTO project_sites (
                project_name, site_location, start_date, end_date,
                status, budget, design_engineer, site_engineer, team_members
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (project_name, site_location, start_date, end_date,
              status, budget, design_engineer, site_engineer, team_members))
        conn.commit()
        flash("Project/Site added successfully!", "success")

    c.execute("SELECT * FROM project_sites ORDER BY start_date DESC")
    projects = c.fetchall()
    conn.close()
    return render_template('project_sites.html', projects=projects)

@app.route('/export/project-sites/excel')
def export_project_sites_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM project_sites", conn)
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='ProjectSites', index=False)
    writer.close()
    output.seek(0)
    conn.close()
    return send_file(output, download_name="project_sites.xlsx", as_attachment=True)

@app.route('/export/project-sites/pdf')
def export_project_sites_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM project_sites")
    data = c.fetchall()
    conn.close()

    output = BytesIO()
    p = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Project Sites Report")
    y -= 30
    p.setFont("Helvetica", 10)
    for row in data:
        text = f"{row[0]} | {row[1]} | {row[2]} | {row[3]} - {row[4]} | ₹{row[6]}"
        p.drawString(50, y, text)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50
    p.save()
    output.seek(0)
    return send_file(output, download_name="project_sites.pdf", as_attachment=True)
    # ---------- Routes: Accounts & Purchase ----------
@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        type = request.form['type']
        category = request.form['category']
        vendor_name = request.form['vendor_name']
        invoice_number = request.form['invoice_number']
        amount = float(request.form['amount'])
        tax = float(request.form['tax'])
        total = amount + tax
        date = request.form['date']
        description = request.form['description']
        assigned_by = request.form['assigned_by']

        c.execute('''
            INSERT INTO accounts (
                type, category, vendor_name, invoice_number,
                amount, tax, total, date, description, assigned_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (type, category, vendor_name, invoice_number,
              amount, tax, total, date, description, assigned_by))
        conn.commit()
        flash("Account entry added successfully!", "success")

    c.execute("SELECT * FROM accounts ORDER BY date DESC")
    accounts_data = c.fetchall()
    conn.close()
    return render_template('accounts_purchase.html', accounts=accounts_data)

@app.route('/export/accounts/excel')
def export_accounts_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM accounts", conn)
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Accounts', index=False)
    writer.close()
    output.seek(0)
    conn.close()
    return send_file(output, download_name="accounts.xlsx", as_attachment=True)

@app.route('/export/accounts/pdf')
def export_accounts_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM accounts")
    data = c.fetchall()
    conn.close()

    output = BytesIO()
    p = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Accounts Report")
    y -= 30
    p.setFont("Helvetica", 10)
    for row in data:
        text = f"{row[0]} | {row[1]} | {row[2]} | ₹{row[5]} + ₹{row[6]} = ₹{row[7]}"
        p.drawString(50, y, text)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50
    p.save()
    output.seek(0)
    return send_file(output, download_name="accounts.pdf", as_attachment=True)
    # ---------- Routes: Workforce Management ----------
@app.route('/workforce', methods=['GET', 'POST'])
def workforce():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        department = request.form['department']
        salary = float(request.form['salary'])
        present_days = int(request.form['present_days'])
        leave_days = int(request.form['leave_days'])
        bonus = float(request.form['bonus'])
        deductions = float(request.form['deductions'])
        total_pay = (salary / 30 * present_days) + bonus - deductions
        join_date = request.form['join_date']
        site_assigned = request.form['site_assigned']

        c.execute('''
            INSERT INTO workforce (
                name, department, salary, present_days, leave_days,
                bonus, deductions, total_pay, join_date, site_assigned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, department, salary, present_days, leave_days,
              bonus, deductions, total_pay, join_date, site_assigned))
        conn.commit()
        flash("Workforce record added!", "success")

    c.execute("SELECT * FROM workforce ORDER BY join_date DESC")
    workforce_data = c.fetchall()
    conn.close()
    return render_template('workforce.html', workforce=workforce_data)

# ---------- Submodule: Attendance ----------
@app.route('/attendance', methods=['POST'])
def attendance():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    name = request.form['name']
    date = request.form['date']
    status = request.form['status']
    c.execute("INSERT INTO hr_attendance (name, date, status) VALUES (?, ?, ?)", (name, date, status))
    conn.commit()
    conn.close()
    return redirect('/workforce')

# ---------- Submodule: Leave ----------
@app.route('/leave', methods=['POST'])
def leave():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    name = request.form['name']
    from_date = request.form['from_date']
    to_date = request.form['to_date']
    reason = request.form['reason']
    c.execute("INSERT INTO hr_leave (name, from_date, to_date, reason) VALUES (?, ?, ?, ?)",
              (name, from_date, to_date, reason))
    conn.commit()
    conn.close()
    return redirect('/workforce')
    # ---------- Submodule: Performance ----------
@app.route('/performance', methods=['POST'])
def performance():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    name = request.form['name']
    month = request.form['month']
    score = int(request.form['score'])
    remarks = request.form['remarks']
    c.execute("INSERT INTO hr_performance (name, month, score, remarks) VALUES (?, ?, ?, ?)",
              (name, month, score, remarks))
    conn.commit()
    conn.close()
    return redirect('/workforce')

# ---------- Submodule: Training ----------
@app.route('/training', methods=['POST'])
def training():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    name = request.form['name']
    topic = request.form['topic']
    trainer = request.form['trainer']
    date = request.form['date']
    c.execute("INSERT INTO hr_training (name, topic, trainer, date) VALUES (?, ?, ?, ?)",
              (name, topic, trainer, date))
    conn.commit()
    conn.close()
    return redirect('/workforce')

# ---------- Submodule: Documents ----------
@app.route('/documents', methods=['POST'])
def documents():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    name = request.form['name']
    doc_type = request.form['doc_type']
    uploaded_on = request.form['uploaded_on']
    c.execute("INSERT INTO hr_documents (name, doc_type, uploaded_on) VALUES (?, ?, ?)",
              (name, doc_type, uploaded_on))
    conn.commit()
    conn.close()
    return redirect('/workforce')

# ---------- Submodule: Department Assignment ----------
@app.route('/departments', methods=['POST'])
def departments():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    name = request.form['name']
    department = request.form['department']
    c.execute("INSERT INTO hr_departments (name, department) VALUES (?, ?)", (name, department))
    conn.commit()
    conn.close()
    return redirect('/workforce')

# ---------- Submodule: Bonus ----------
@app.route('/bonus', methods=['POST'])
def bonus():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    name = request.form['name']
    bonus = float(request.form['bonus'])
    date = request.form['date']
    c.execute("INSERT INTO hr_bonus (name, bonus, date) VALUES (?, ?, ?)", (name, bonus, date))
    conn.commit()
    conn.close()
    return redirect('/workforce')

# ---------- Submodule: Deductions ----------
@app.route('/deductions', methods=['POST'])
def deductions():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    name = request.form['name']
    deduction = float(request.form['deduction'])
    reason = request.form['reason']
    date = request.form['date']
    c.execute("INSERT INTO hr_deductions (name, deduction, reason, date) VALUES (?, ?, ?, ?)",
              (name, deduction, reason, date))
    conn.commit()
    conn.close()
    return redirect('/workforce')
    # ---------- Inventory: Main ----------
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    if request.method == 'POST':
        data = (
            request.form['item_code'],
            request.form['item_name'],
            request.form['category'],
            request.form['quantity'],
            request.form['unit'],
            request.form['location'],
            request.form['supplier'],
            request.form['cost_price'],
            request.form['selling_price'],
            request.form['added_on']
        )
        c.execute('''
            INSERT INTO inventory 
            (item_code, item_name, category, quantity, unit, location, supplier, cost_price, selling_price, added_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
        conn.commit()
    c.execute("SELECT * FROM inventory ORDER BY added_on DESC")
    inventory_data = c.fetchall()
    conn.close()
    return render_template("inventory.html", inventory_data=inventory_data)

# ---------- Inventory: Logs ----------
@app.route('/inventory/logs', methods=['POST'])
def inventory_logs():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    data = (
        request.form['item_code'],
        request.form['action'],
        request.form['quantity'],
        request.form['reason'],
        request.form['done_by'],
        request.form['date']
    )
    c.execute('''
        INSERT INTO inventory_logs (item_code, action, quantity, reason, done_by, date)
        VALUES (?, ?, ?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()
    return redirect('/inventory')

# ---------- Inventory: Orders ----------
@app.route('/inventory/orders', methods=['POST'])
def inventory_orders():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    data = (
        request.form['item_code'],
        request.form['order_type'],
        request.form['quantity'],
        request.form['requested_by'],
        request.form['approved_by'],
        request.form['status'],
        request.form['date']
    )
    c.execute('''
        INSERT INTO inventory_orders 
        (item_code, order_type, quantity, requested_by, approved_by, status, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()
    return redirect('/inventory')

# ---------- Inventory: Damages ----------
@app.route('/inventory/damages', methods=['POST'])
def inventory_damages():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    data = (
        request.form['item_code'],
        request.form['quantity'],
        request.form['reason'],
        request.form['reported_by'],
        request.form['date']
    )
    c.execute('''
        INSERT INTO inventory_damages (item_code, quantity, reason, reported_by, date)
        VALUES (?, ?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()
    return redirect('/inventory')

# ---------- Inventory: Returns ----------
@app.route('/inventory/returns', methods=['POST'])
def inventory_returns():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    data = (
        request.form['item_code'],
        request.form['quantity'],
        request.form['reason'],
        request.form['returned_by'],
        request.form['received_by'],
        request.form['date']
    )
    c.execute('''
        INSERT INTO inventory_returns (item_code, quantity, reason, returned_by, received_by, date)
        VALUES (?, ?, ?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()
    return redirect('/inventory')

# ---------- Inventory: Add Supplier ----------
@app.route('/inventory/suppliers', methods=['POST'])
def inventory_suppliers():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    data = (
        request.form['supplier_name'],
        request.form['contact'],
        request.form['email'],
        request.form['address']
    )
    c.execute('''
        INSERT INTO inventory_suppliers (supplier_name, contact, email, address)
        VALUES (?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()
    return redirect('/inventory')

# ---------- Inventory: Add Category & Location ----------
@app.route('/inventory/meta', methods=['POST'])
def inventory_meta():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    if request.form.get("meta_type") == "category":
        category = request.form['category_name']
        c.execute("INSERT OR IGNORE INTO inventory_categories (category_name) VALUES (?)", (category,))
    elif request.form.get("meta_type") == "location":
        location = request.form['location_name']
        c.execute("INSERT OR IGNORE INTO inventory_locations (location_name) VALUES (?)", (location,))
    conn.commit()
    conn.close()
    return redirect('/inventory')
    # ---------- EXPORT: Inventory to Excel ----------
@app.route('/export/inventory/excel')
def export_inventory_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Inventory')
    writer.close()
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="inventory_data.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ---------- EXPORT: Inventory to PDF ----------
@app.route('/export/inventory/pdf')
def export_inventory_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM inventory")
    rows = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, y, "Inventory Report")
    y -= 30

    p.setFont("Helvetica", 10)
    headers = ["ID", "Item Code", "Name", "Category", "Qty", "Unit", "Location", "Supplier", "Cost", "Selling", "Added On"]
    col_widths = [30, 60, 80, 60, 30, 30, 60, 70, 50, 50, 60]
    
    for i, header in enumerate(headers):
        p.drawString(sum(col_widths[:i]) + 20, y, header)
    y -= 20

    for row in rows:
        for i, value in enumerate(row):
            p.drawString(sum(col_widths[:i]) + 20, y, str(value))
        y -= 15
        if y < 40:
            p.showPage()
            y = height - 40

    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="inventory_report.pdf", mimetype='application/pdf')


# ---------- FINAL APP RUN ----------
if __name__ == '__main__':
    app.run(debug=True)
