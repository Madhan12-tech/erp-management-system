# Part 1: Imports, Setup, DB Initialization
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

    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )''')

    # Project & Sites
    c.execute('''CREATE TABLE IF NOT EXISTS project_sites (
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
    )''')

    # Accounts
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
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
    )''')

    # Workforce
    c.execute('''CREATE TABLE IF NOT EXISTS workforce (
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
    )''')

    # HR Subtables
    c.execute('''CREATE TABLE IF NOT EXISTS hr_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, date TEXT, status TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_leave (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, from_date TEXT, to_date TEXT, reason TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, month TEXT, score INTEGER, remarks TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_training (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, topic TEXT, trainer TEXT, date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, doc_type TEXT, uploaded_on TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, department TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_bonus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, bonus REAL, date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hr_deductions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, deduction REAL, reason TEXT, date TEXT
    )''')

    # Inventory Tables
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
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
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_code TEXT,
        action TEXT,
        quantity INTEGER,
        reason TEXT,
        done_by TEXT,
        date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_code TEXT,
        order_type TEXT,
        quantity INTEGER,
        requested_by TEXT,
        approved_by TEXT,
        status TEXT,
        date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_name TEXT,
        contact TEXT,
        email TEXT,
        address TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT UNIQUE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_name TEXT UNIQUE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_damages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_code TEXT,
        quantity INTEGER,
        reason TEXT,
        reported_by TEXT,
        date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_code TEXT,
        quantity INTEGER,
        reason TEXT,
        returned_by TEXT,
        received_by TEXT,
        date TEXT
    )''')

    conn.commit()
    conn.close()

init_db()
# ----------- Authentication & Dashboard -----------
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
    # ----------- Project & Sites Module -----------
@app.route('/project-sites', methods=['GET', 'POST'])
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
            INSERT INTO project_sites (
                project_name, site_location, start_date, end_date, status,
                budget, design_engineer, site_engineer, team_members
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        conn.commit()
        flash("Project added successfully!", "success")
    c.execute('SELECT * FROM project_sites ORDER BY id DESC')
    projects = c.fetchall()
    conn.close()
    return render_template('project_sites.html', projects=projects)

@app.route('/delete-project/<int:id>')
def delete_project(id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM project_sites WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash("Project deleted successfully.", "info")
    return redirect('/project-sites')

@app.route('/export-projects')
def export_projects():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query('SELECT * FROM project_sites', conn)
    conn.close()
    output = BytesIO()
    df.to_excel(output, index=False, sheet_name='Projects')
    output.seek(0)
    return send_file(output, download_name="project_sites.xlsx", as_attachment=True)
    # ----------- Accounts & Purchase Module -----------
@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    if 'user' not in session:
        return redirect('/login')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        type = request.form['type']
        category = request.form['category']
        vendor = request.form['vendor_name']
        invoice = request.form['invoice_number']
        amount = float(request.form['amount'])
        tax = float(request.form['tax'])
        total = amount + tax
        date = request.form['date']
        desc = request.form['description']
        assigned_by = session['user']
        c.execute('''
            INSERT INTO accounts (
                type, category, vendor_name, invoice_number, amount, tax,
                total, date, description, assigned_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (type, category, vendor, invoice, amount, tax, total, date, desc, assigned_by))
        conn.commit()
        flash('Transaction added successfully!', 'success')
    c.execute('SELECT * FROM accounts ORDER BY date DESC')
    accounts_data = c.fetchall()
    conn.close()
    return render_template('accounts.html', accounts=accounts_data)

@app.route('/delete-account/<int:id>')
def delete_account(id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM accounts WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Transaction deleted.', 'info')
    return redirect('/accounts')

@app.route('/export-accounts')
def export_accounts():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query('SELECT * FROM accounts', conn)
    conn.close()
    output = BytesIO()
    df.to_excel(output, index=False, sheet_name='Accounts')
    output.seek(0)
    return send_file(output, download_name="accounts_data.xlsx", as_attachment=True)
    # ----------- Workforce / HR Module -----------
@app.route('/workforce', methods=['GET', 'POST'])
def workforce():
    if 'user' not in session:
        return redirect('/login')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        department = request.form['department']
        salary = float(request.form['salary'])
        present = int(request.form['present_days'])
        leave = int(request.form['leave_days'])
        bonus = float(request.form['bonus'])
        deductions = float(request.form['deductions'])
        total = salary + bonus - deductions
        join_date = request.form['join_date']
        site = request.form['site_assigned']
        c.execute('''
            INSERT INTO workforce (
                name, department, salary, present_days, leave_days,
                bonus, deductions, total_pay, join_date, site_assigned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, department, salary, present, leave, bonus, deductions, total, join_date, site))
        conn.commit()
        flash('Employee added successfully!', 'success')
    c.execute('SELECT * FROM workforce ORDER BY join_date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('workforce.html', data=data)

@app.route('/delete-workforce/<int:id>')
def delete_workforce(id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM workforce WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Employee removed.', 'info')
    return redirect('/workforce')

@app.route('/export-workforce')
def export_workforce():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query('SELECT * FROM workforce', conn)
    conn.close()
    output = BytesIO()
    df.to_excel(output, index=False, sheet_name='Workforce')
    output.seek(0)
    return send_file(output, download_name="workforce_data.xlsx", as_attachment=True)
    # ---------- HR Attendance ----------
@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        date = request.form['date']
        status = request.form['status']
        c.execute('INSERT INTO hr_attendance (name, date, status) VALUES (?, ?, ?)', (name, date, status))
        conn.commit()
    c.execute('SELECT * FROM hr_attendance ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('attendance.html', data=data)

# ---------- HR Leave ----------
@app.route('/leave', methods=['GET', 'POST'])
def leave():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        from_date = request.form['from_date']
        to_date = request.form['to_date']
        reason = request.form['reason']
        c.execute('INSERT INTO hr_leave (name, from_date, to_date, reason) VALUES (?, ?, ?, ?)',
                  (name, from_date, to_date, reason))
        conn.commit()
    c.execute('SELECT * FROM hr_leave ORDER BY from_date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('leave.html', data=data)

# ---------- HR Performance ----------
@app.route('/performance', methods=['GET', 'POST'])
def performance():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        month = request.form['month']
        score = request.form['score']
        remarks = request.form['remarks']
        c.execute('INSERT INTO hr_performance (name, month, score, remarks) VALUES (?, ?, ?, ?)',
                  (name, month, score, remarks))
        conn.commit()
    c.execute('SELECT * FROM hr_performance ORDER BY month DESC')
    data = c.fetchall()
    conn.close()
    return render_template('performance.html', data=data)

# ---------- HR Training ----------
@app.route('/training', methods=['GET', 'POST'])
def training():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        topic = request.form['topic']
        trainer = request.form['trainer']
        date = request.form['date']
        c.execute('INSERT INTO hr_training (name, topic, trainer, date) VALUES (?, ?, ?, ?)',
                  (name, topic, trainer, date))
        conn.commit()
    c.execute('SELECT * FROM hr_training ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('training.html', data=data)

# ---------- HR Documents ----------
@app.route('/documents', methods=['GET', 'POST'])
def documents():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        doc_type = request.form['doc_type']
        uploaded_on = request.form['uploaded_on']
        c.execute('INSERT INTO hr_documents (name, doc_type, uploaded_on) VALUES (?, ?, ?)',
                  (name, doc_type, uploaded_on))
        conn.commit()
    c.execute('SELECT * FROM hr_documents ORDER BY uploaded_on DESC')
    data = c.fetchall()
    conn.close()
    return render_template('documents.html', data=data)
    # ---------- HR Departments ----------
@app.route('/departments', methods=['GET', 'POST'])
def departments():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        department = request.form['department']
        c.execute('INSERT INTO hr_departments (name, department) VALUES (?, ?)', (name, department))
        conn.commit()
    c.execute('SELECT * FROM hr_departments ORDER BY name ASC')
    data = c.fetchall()
    conn.close()
    return render_template('departments.html', data=data)

# ---------- HR Bonus ----------
@app.route('/bonus', methods=['GET', 'POST'])
def bonus():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        bonus = request.form['bonus']
        date = request.form['date']
        c.execute('INSERT INTO hr_bonus (name, bonus, date) VALUES (?, ?, ?)', (name, bonus, date))
        conn.commit()
    c.execute('SELECT * FROM hr_bonus ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('bonus.html', data=data)

# ---------- HR Deductions ----------
@app.route('/deductions', methods=['GET', 'POST'])
def deductions():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        deduction = request.form['deduction']
        reason = request.form['reason']
        date = request.form['date']
        c.execute('INSERT INTO hr_deductions (name, deduction, reason, date) VALUES (?, ?, ?, ?)',
                  (name, deduction, reason, date))
        conn.commit()
    c.execute('SELECT * FROM hr_deductions ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('deductions.html', data=data)

# ---------- Custom 404 Handler ----------
@app.errorhandler(404)
def page_not_found(e):
    # ---------- Inventory Routes ----------
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        item_code = request.form['item_code']
        item_name = request.form['item_name']
        category = request.form['category']
        quantity = request.form['quantity']
        unit = request.form['unit']
        location = request.form['location']
        supplier = request.form['supplier']
        cost_price = request.form['cost_price']
        selling_price = request.form['selling_price']
        added_on = datetime.now().strftime("%Y-%m-%d")
        c.execute('''
            INSERT INTO inventory (item_code, item_name, category, quantity, unit, location, supplier, cost_price, selling_price, added_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (item_code, item_name, category, quantity, unit, location, supplier, cost_price, selling_price, added_on))
        conn.commit()
    c.execute('SELECT * FROM inventory ORDER BY added_on DESC')
    data = c.fetchall()
    conn.close()
    return render_template('inventory.html', data=data)

@app.route('/inventory/logs', methods=['GET', 'POST'])
def inventory_logs():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        item_code = request.form['item_code']
        action = request.form['action']
        quantity = request.form['quantity']
        reason = request.form['reason']
        done_by = session.get('user', 'Unknown')
        date = datetime.now().strftime("%Y-%m-%d")
        c.execute('''
            INSERT INTO inventory_logs (item_code, action, quantity, reason, done_by, date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (item_code, action, quantity, reason, done_by, date))
        conn.commit()
    c.execute('SELECT * FROM inventory_logs ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('inventory_logs.html', data=data)

@app.route('/inventory/orders', methods=['GET', 'POST'])
def inventory_orders():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        item_code = request.form['item_code']
        order_type = request.form['order_type']
        quantity = request.form['quantity']
        requested_by = session.get('user', 'Unknown')
        approved_by = request.form['approved_by']
        status = request.form['status']
        date = datetime.now().strftime("%Y-%m-%d")
        c.execute('''
            INSERT INTO inventory_orders (item_code, order_type, quantity, requested_by, approved_by, status, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (item_code, order_type, quantity, requested_by, approved_by, status, date))
        conn.commit()
    c.execute('SELECT * FROM inventory_orders ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('inventory_orders.html', data=data)
    
    return "<h1>404 - Page not found</h1><p>The page you are looking for does not exist.</p>", 404
    @app.route('/inventory/suppliers', methods=['GET', 'POST'])
def inventory_suppliers():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        supplier_name = request.form['supplier_name']
        contact = request.form['contact']
        email = request.form['email']
        address = request.form['address']
        c.execute('''
            INSERT INTO inventory_suppliers (supplier_name, contact, email, address)
            VALUES (?, ?, ?, ?)
        ''', (supplier_name, contact, email, address))
        conn.commit()
    c.execute('SELECT * FROM inventory_suppliers')
    data = c.fetchall()
    conn.close()
    return render_template('inventory_suppliers.html', data=data)

@app.route('/inventory/damages', methods=['GET', 'POST'])
def inventory_damages():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        item_code = request.form['item_code']
        quantity = request.form['quantity']
        reason = request.form['reason']
        reported_by = session.get('user', 'Unknown')
        date = datetime.now().strftime("%Y-%m-%d")
        c.execute('''
            INSERT INTO inventory_damages (item_code, quantity, reason, reported_by, date)
            VALUES (?, ?, ?, ?, ?)
        ''', (item_code, quantity, reason, reported_by, date))
        conn.commit()
    c.execute('SELECT * FROM inventory_damages ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('inventory_damages.html', data=data)

@app.route('/inventory/returns', methods=['GET', 'POST'])
def inventory_returns():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        item_code = request.form['item_code']
        quantity = request.form['quantity']
        reason = request.form['reason']
        returned_by = session.get('user', 'Unknown')
        received_by = request.form['received_by']
        date = datetime.now().strftime("%Y-%m-%d")
        c.execute('''
            INSERT INTO inventory_returns (item_code, quantity, reason, returned_by, received_by, date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (item_code, quantity, reason, returned_by, received_by, date))
        conn.commit()
    c.execute('SELECT * FROM inventory_returns ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('inventory_returns.html', data=data)

@app.route('/inventory/setup', methods=['GET', 'POST'])
def inventory_setup():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        category = request.form.get('category')
        location = request.form.get('location')
        if category:
            c.execute('INSERT OR IGNORE INTO inventory_categories (category_name) VALUES (?)', (category,))
        if location:
            c.execute('INSERT OR IGNORE INTO inventory_locations (location_name) VALUES (?)', (location,))
        conn.commit()
    c.execute('SELECT * FROM inventory_categories')
    categories = c.fetchall()
    c.execute('SELECT * FROM inventory_locations')
    locations = c.fetchall()
    conn.close()
    return render_template('inventory_setup.html', categories=categories, locations=locations)
    # ------------ Export: Inventory to Excel ------------
@app.route('/export/inventory/excel')
def export_inventory_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    output.seek(0)
    return send_file(output, download_name="Inventory_Report.xlsx", as_attachment=True)

# ------------ Export: Workforce to Excel ------------
@app.route('/export/workforce/excel')
def export_workforce_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM workforce", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Workforce')
    output.seek(0)
    return send_file(output, download_name="Workforce_Report.xlsx", as_attachment=True)

# ------------ Export: Accounts to Excel ------------
@app.route('/export/accounts/excel')
def export_accounts_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM accounts", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Accounts')
    output.seek(0)
    return send_file(output, download_name="Accounts_Report.xlsx", as_attachment=True)

# ------------ Export: Inventory to PDF ------------
@app.route('/export/inventory/pdf')
def export_inventory_pdf():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM inventory')
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    pdf.setFont("Helvetica", 12)
    y = height - 40
    pdf.drawString(30, y, "Inventory Report")
    y -= 30
    for row in data:
        pdf.drawString(30, y, str(row))
        y -= 20
        if y < 50:
            pdf.showPage()
            y = height - 40
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, download_name='Inventory_Report.pdf', as_attachment=True)
    # ---------- Run the App ----------
if __name__ == '__main__':
    app.run(debug=True)
