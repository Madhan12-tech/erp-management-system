from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
import sqlite3, os
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ---------- Database Initialization ----------
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Inventory tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT,
            item_name TEXT,
            quantity INTEGER,
            unit TEXT,
            category TEXT,
            location TEXT,
            reorder_level INTEGER,
            status TEXT,
            added_on TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT,
            action TEXT,
            quantity INTEGER,
            date TEXT,
            handled_by TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT,
            quantity INTEGER,
            vendor TEXT,
            order_date TEXT,
            delivery_date TEXT,
            status TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_damages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT,
            quantity INTEGER,
            reason TEXT,
            reported_on TEXT,
            action_taken TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT,
            quantity INTEGER,
            return_to TEXT,
            reason TEXT,
            returned_on TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT,
            quantity INTEGER,
            from_location TEXT,
            to_location TEXT,
            transferred_on TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT,
            quantity INTEGER,
            checked_in_by TEXT,
            date TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_checkouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT,
            quantity INTEGER,
            checked_out_by TEXT,
            date TEXT
        )
    ''')

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# -------- Authentication Routes --------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
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
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        try:
            conn = sqlite3.connect('users.db')
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
    # ---------- Inventory Main Page ----------
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'user' not in session:
        return redirect('/login')
    conn = sqlite3.connect('users.db')
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
            INSERT INTO inventory (item_code, item_name, category, quantity, unit, location, supplier, cost_price, selling_price, added_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        conn.commit()

    c.execute('SELECT * FROM inventory ORDER BY added_on DESC')
    items = c.fetchall()
    conn.close()
    return render_template('inventory.html', items=items)

# ---------- Inventory Popup Endpoints ----------
@app.route('/inventory/logs', methods=['POST'])
def inventory_logs():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO inventory_logs (item_code, action, quantity, reason, done_by, date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['item_code'], data['action'], data['quantity'], data['reason'], data['done_by'], data['date']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/inventory/orders', methods=['POST'])
def inventory_orders():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO inventory_orders (item_code, order_type, quantity, requested_by, approved_by, status, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (data['item_code'], data['order_type'], data['quantity'], data['requested_by'], data['approved_by'], data['status'], data['date']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/inventory/suppliers', methods=['POST'])
def inventory_suppliers():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO inventory_suppliers (supplier_name, contact, email, address)
        VALUES (?, ?, ?, ?)
    ''', (data['supplier_name'], data['contact'], data['email'], data['address']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/inventory/categories', methods=['POST'])
def inventory_categories():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO inventory_categories (category_name) VALUES (?)', (data['category_name'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/inventory/locations', methods=['POST'])
def inventory_locations():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO inventory_locations (location_name) VALUES (?)', (data['location_name'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/inventory/damages', methods=['POST'])
def inventory_damages():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO inventory_damages (item_code, quantity, reason, reported_by, date)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['item_code'], data['quantity'], data['reason'], data['reported_by'], data['date']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/inventory/returns', methods=['POST'])
def inventory_returns():
    data = request.form
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO inventory_returns (item_code, quantity, reason, returned_by, received_by, date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['item_code'], data['quantity'], data['reason'], data['returned_by'], data['received_by'], data['date']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ---------- Inventory Export ----------
@app.route('/export_inventory_excel')
def export_inventory_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query('SELECT * FROM inventory', conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    output.seek(0)
    return send_file(output, download_name='inventory.xlsx', as_attachment=True)
    # ---------- Project & Sites ----------
@app.route('/project_sites', methods=['GET', 'POST'])
def project_sites():
    if 'user' not in session:
        return redirect('/login')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        data = (
            request.form['project_name'],
            request.form['site_location'],
            request.form['start_date'],
            request.form['end_date'],
            request.form['status'],
            request.form['budget'],
            request.form['design_engineer'],
            request.form['site_engineer'],
            request.form['team_members']
        )
        c.execute('''
            INSERT INTO project_sites (project_name, site_location, start_date, end_date, status, budget, design_engineer, site_engineer, team_members)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        conn.commit()
    c.execute('SELECT * FROM project_sites')
    projects = c.fetchall()
    conn.close()
    return render_template('project_sites.html', projects=projects)

@app.route('/export_projects')
def export_projects():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query('SELECT * FROM project_sites', conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')
    output.seek(0)
    return send_file(output, download_name='projects.xlsx', as_attachment=True)

# ---------- Accounts & Purchase ----------
@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    if 'user' not in session:
        return redirect('/login')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        data = (
            request.form['type'],
            request.form['category'],
            request.form['vendor_name'],
            request.form['invoice_number'],
            request.form['amount'],
            request.form['tax'],
            request.form['total'],
            request.form['date'],
            request.form['description'],
            request.form['assigned_by']
        )
        c.execute('''
            INSERT INTO accounts (type, category, vendor_name, invoice_number, amount, tax, total, date, description, assigned_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        conn.commit()
    c.execute('SELECT * FROM accounts ORDER BY date DESC')
    entries = c.fetchall()
    conn.close()
    return render_template('accounts.html', entries=entries)

@app.route('/export_accounts')
def export_accounts():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query('SELECT * FROM accounts', conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Accounts')
    output.seek(0)
    return send_file(output, download_name='accounts.xlsx', as_attachment=True)

# ---------- Workforce (HR) ----------
@app.route('/workforce', methods=['GET', 'POST'])
def workforce():
    if 'user' not in session:
        return redirect('/login')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        data = (
            request.form['name'],
            request.form['department'],
            float(request.form['salary']),
            int(request.form['present_days']),
            int(request.form['leave_days']),
            float(request.form['bonus']),
            float(request.form['deductions']),
            float(request.form['salary']) + float(request.form['bonus']) - float(request.form['deductions']),
            request.form['join_date'],
            request.form['site_assigned']
        )
        c.execute('''
            INSERT INTO workforce (name, department, salary, present_days, leave_days, bonus, deductions, total_pay, join_date, site_assigned)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        conn.commit()
    c.execute('SELECT * FROM workforce ORDER BY join_date DESC')
    employees = c.fetchall()
    conn.close()
    return render_template('workforce.html', employees=employees)

@app.route('/export_workforce')
def export_workforce():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query('SELECT * FROM workforce', conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Workforce')
    output.seek(0)
    return send_file(output, download_name='workforce.xlsx', as_attachment=True)
    # ----------- HR POPUPS -------------
@app.route('/hr_attendance', methods=['POST'])
def hr_attendance():
    name = request.form['name']
    date = request.form['date']
    status = request.form['status']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_attendance (name, date, status) VALUES (?, ?, ?)', (name, date, status))
    conn.commit()
    conn.close()
    return redirect('/workforce')

@app.route('/hr_leave', methods=['POST'])
def hr_leave():
    name = request.form['name']
    from_date = request.form['from_date']
    to_date = request.form['to_date']
    reason = request.form['reason']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_leave (name, from_date, to_date, reason) VALUES (?, ?, ?, ?)', (name, from_date, to_date, reason))
    conn.commit()
    conn.close()
    return redirect('/workforce')

@app.route('/hr_performance', methods=['POST'])
def hr_performance():
    name = request.form['name']
    month = request.form['month']
    score = request.form['score']
    remarks = request.form['remarks']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_performance (name, month, score, remarks) VALUES (?, ?, ?, ?)', (name, month, score, remarks))
    conn.commit()
    conn.close()
    return redirect('/workforce')

@app.route('/hr_training', methods=['POST'])
def hr_training():
    name = request.form['name']
    topic = request.form['topic']
    trainer = request.form['trainer']
    date = request.form['date']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_training (name, topic, trainer, date) VALUES (?, ?, ?, ?)', (name, topic, trainer, date))
    conn.commit()
    conn.close()
    return redirect('/workforce')

@app.route('/hr_documents', methods=['POST'])
def hr_documents():
    name = request.form['name']
    doc_type = request.form['doc_type']
    uploaded_on = request.form['uploaded_on']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_documents (name, doc_type, uploaded_on) VALUES (?, ?, ?)', (name, doc_type, uploaded_on))
    conn.commit()
    conn.close()
    return redirect('/workforce')

@app.route('/hr_departments', methods=['POST'])
def hr_departments():
    name = request.form['name']
    department = request.form['department']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_departments (name, department) VALUES (?, ?)', (name, department))
    conn.commit()
    conn.close()
    return redirect('/workforce')

@app.route('/hr_bonus', methods=['POST'])
def hr_bonus():
    name = request.form['name']
    bonus = request.form['bonus']
    date = request.form['date']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_bonus (name, bonus, date) VALUES (?, ?, ?)', (name, bonus, date))
    conn.commit()
    conn.close()
    return redirect('/workforce')

@app.route('/hr_deductions', methods=['POST'])
def hr_deductions():
    name = request.form['name']
    deduction = request.form['deduction']
    reason = request.form['reason']
    date = request.form['date']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO hr_deductions (name, deduction, reason, date) VALUES (?, ?, ?, ?)', (name, deduction, reason, date))
    conn.commit()
    conn.close()
    return redirect('/workforce')

# ---------- Run Server ----------
if __name__ == '__main__':
    app.run(debug=True)
