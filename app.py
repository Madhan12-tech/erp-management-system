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
# ---------- Authentication ----------
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
            flash("Login successful!", "success")
            return redirect('/dashboard')
        else:
            flash("Invalid credentials", "danger")
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
            flash("Registration successful!", "success")
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect('/login')

# ---------- Dashboard ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html', username=session['user'])
    # ---------- Project & Sites Module ----------
@app.route('/projects', methods=['GET', 'POST'])
def projects():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('users.db')
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
                project_name, site_location, start_date, end_date, status,
                budget, design_engineer, site_engineer, team_members
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (project_name, site_location, start_date, end_date, status,
             budget, design_engineer, site_engineer, team_members))
        conn.commit()

    c.execute('SELECT * FROM project_sites ORDER BY start_date DESC')
    projects = c.fetchall()
    conn.close()
    return render_template('projects.html', projects=projects)

@app.route('/delete_project/<int:id>')
def delete_project(id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM project_sites WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash("Project deleted successfully.", "info")
    return redirect('/projects')

@app.route('/export_projects_excel')
def export_projects_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM project_sites", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')
    output.seek(0)

    return send_file(output, download_name="projects.xlsx", as_attachment=True)

@app.route('/export_projects_pdf')
def export_projects_pdf():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM project_sites")
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Projects Report")
    p.setFont("Helvetica", 10)
    y -= 30

    for row in data:
        text = f"{row[1]} | {row[2]} | {row[3]} to {row[4]} | {row[5]} | Budget: {row[6]}"
        p.drawString(50, y, text)
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50
    p.save()
    buffer.seek(0)

    return send_file(buffer, download_name="projects.pdf", as_attachment=True)
    # ---------- Accounts & Purchase Module ----------
@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    if request.method == 'POST':
        type_ = request.form['type']
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
                type, category, vendor_name, invoice_number, amount,
                tax, total, date, description, assigned_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (type_, category, vendor_name, invoice_number, amount,
             tax, total, date, description, assigned_by))
        conn.commit()

    c.execute('SELECT * FROM accounts ORDER BY date DESC')
    accounts = c.fetchall()
    conn.close()
    return render_template('accounts.html', accounts=accounts)

@app.route('/delete_account/<int:id>')
def delete_account(id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM accounts WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash("Record deleted from Accounts.", "info")
    return redirect('/accounts')

@app.route('/export_accounts_excel')
def export_accounts_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM accounts", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Accounts')
    output.seek(0)

    return send_file(output, download_name="accounts.xlsx", as_attachment=True)

@app.route('/export_accounts_pdf')
def export_accounts_pdf():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM accounts")
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Accounts & Purchase Report")
    p.setFont("Helvetica", 10)
    y -= 30

    for row in data:
        text = f"{row[1]} | {row[2]} | {row[3]} | ₹{row[6]} | {row[7]}"
        p.drawString(50, y, text)
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50
    p.save()
    buffer.seek(0)

    return send_file(buffer, download_name="accounts.pdf", as_attachment=True)
    # ---------- Workforce Module ----------
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
        present_days = int(request.form['present_days'])
        leave_days = int(request.form['leave_days'])
        bonus = float(request.form['bonus'])
        deductions = float(request.form['deductions'])
        join_date = request.form['join_date']
        site_assigned = request.form['site_assigned']
        total_pay = ((salary / 30) * present_days) + bonus - deductions

        c.execute('''INSERT INTO workforce 
                     (name, department, salary, present_days, leave_days, bonus, deductions, total_pay, join_date, site_assigned)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (name, department, salary, present_days, leave_days,
                   bonus, deductions, total_pay, join_date, site_assigned))
        conn.commit()

    c.execute('SELECT * FROM workforce ORDER BY join_date DESC')
    workforce = c.fetchall()
    conn.close()
    return render_template('workforce.html', workforce=workforce)

@app.route('/delete_workforce/<int:id>')
def delete_workforce(id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM workforce WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash("Workforce record deleted.", "info")
    return redirect('/workforce')

@app.route('/export_workforce_excel')
def export_workforce_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM workforce", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Workforce')
    output.seek(0)

    return send_file(output, download_name="workforce.xlsx", as_attachment=True)

@app.route('/export_workforce_pdf')
def export_workforce_pdf():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM workforce")
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Workforce Payroll Report")
    p.setFont("Helvetica", 10)
    y -= 30

    for row in data:
        text = f"{row[1]} | Dept: {row[2]} | ₹{row[8]} | Join: {row[9]}"
        p.drawString(50, y, text)
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50
    p.save()
    buffer.seek(0)

    return send_file(buffer, download_name="workforce.pdf", as_attachment=True)
    # ---------- Inventory Management ----------
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'user' not in session:
        return redirect('/login')
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
        added_on = request.form['added_on']
        c.execute('''INSERT INTO inventory 
            (item_code, item_name, category, quantity, unit, location, supplier, cost_price, selling_price, added_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (item_code, item_name, category, quantity, unit, location, supplier, cost_price, selling_price, added_on))
        conn.commit()

    c.execute("SELECT * FROM inventory ORDER BY added_on DESC")
    items = c.fetchall()
    conn.close()
    return render_template("inventory.html", items=items)

@app.route('/delete_inventory/<int:id>')
def delete_inventory(id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM inventory WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash("Inventory item deleted.", "info")
    return redirect('/inventory')

@app.route('/export_inventory_excel')
def export_inventory_excel():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    output.seek(0)
    return send_file(output, download_name="inventory.xlsx", as_attachment=True)

@app.route('/export_inventory_pdf')
def export_inventory_pdf():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM inventory")
    items = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Inventory Items Report")
    p.setFont("Helvetica", 10)
    y -= 30

    for item in items:
        text = f"{item[1]} | {item[2]} | Qty: {item[4]} | {item[6]}"
        p.drawString(50, y, text)
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50
    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="inventory.pdf", as_attachment=True)
    # ---------- Inventory Logs ----------
@app.route('/inventory_logs', methods=['GET', 'POST'])
def inventory_logs():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        item_code = request.form['item_code']
        action = request.form['action']
        quantity = request.form['quantity']
        reason = request.form['reason']
        done_by = request.form['done_by']
        date = request.form['date']
        c.execute('''INSERT INTO inventory_logs (item_code, action, quantity, reason, done_by, date)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (item_code, action, quantity, reason, done_by, date))
        conn.commit()
    c.execute("SELECT * FROM inventory_logs ORDER BY date DESC")
    logs = c.fetchall()
    conn.close()
    return render_template('inventory_logs.html', logs=logs)


# ---------- Inventory Orders ----------
@app.route('/inventory_orders', methods=['GET', 'POST'])
def inventory_orders():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        item_code = request.form['item_code']
        order_type = request.form['order_type']
        quantity = request.form['quantity']
        requested_by = request.form['requested_by']
        approved_by = request.form['approved_by']
        status = request.form['status']
        date = request.form['date']
        c.execute('''INSERT INTO inventory_orders (item_code, order_type, quantity, requested_by, approved_by, status, date)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (item_code, order_type, quantity, requested_by, approved_by, status, date))
        conn.commit()
    c.execute("SELECT * FROM inventory_orders ORDER BY date DESC")
    orders = c.fetchall()
    conn.close()
    return render_template('inventory_orders.html', orders=orders)


# ---------- Inventory Damages ----------
@app.route('/inventory_damages', methods=['GET', 'POST'])
def inventory_damages():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        item_code = request.form['item_code']
        quantity = request.form['quantity']
        reason = request.form['reason']
        reported_by = request.form['reported_by']
        date = request.form['date']
        c.execute('''INSERT INTO inventory_damages (item_code, quantity, reason, reported_by, date)
                     VALUES (?, ?, ?, ?, ?)''',
                  (item_code, quantity, reason, reported_by, date))
        conn.commit()
    c.execute("SELECT * FROM inventory_damages ORDER BY date DESC")
    damages = c.fetchall()
    conn.close()
    return render_template('inventory_damages.html', damages=damages)


# ---------- Inventory Returns ----------
@app.route('/inventory_returns', methods=['GET', 'POST'])
def inventory_returns():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        item_code = request.form['item_code']
        quantity = request.form['quantity']
        reason = request.form['reason']
        returned_by = request.form['returned_by']
        received_by = request.form['received_by']
        date = request.form['date']
        c.execute('''INSERT INTO inventory_returns (item_code, quantity, reason, returned_by, received_by, date)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (item_code, quantity, reason, returned_by, received_by, date))
        conn.commit()
    c.execute("SELECT * FROM inventory_returns ORDER BY date DESC")
    returns = c.fetchall()
    conn.close()
    return render_template('inventory_returns.html', returns=returns)
    # ---------- Inventory Categories ----------
@app.route('/inventory_categories', methods=['GET', 'POST'])
def inventory_categories():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        category_name = request.form['category_name']
        c.execute('INSERT OR IGNORE INTO inventory_categories (category_name) VALUES (?)',
                  (category_name,))
        conn.commit()
    c.execute('SELECT * FROM inventory_categories ORDER BY id DESC')
    categories = c.fetchall()
    conn.close()
    return render_template('inventory_categories.html', categories=categories)


# ---------- Inventory Suppliers ----------
@app.route('/inventory_suppliers', methods=['GET', 'POST'])
def inventory_suppliers():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        supplier_name = request.form['supplier_name']
        contact = request.form['contact']
        email = request.form['email']
        address = request.form['address']
        c.execute('''INSERT INTO inventory_suppliers (supplier_name, contact, email, address)
                     VALUES (?, ?, ?, ?)''',
                  (supplier_name, contact, email, address))
        conn.commit()
    c.execute('SELECT * FROM inventory_suppliers ORDER BY id DESC')
    suppliers = c.fetchall()
    conn.close()
    return render_template('inventory_suppliers.html', suppliers=suppliers)


# ---------- 404 Error Page ----------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# ---------- Run the Flask App ----------
if __name__ == '__main__':
    app.run(debug=True)
