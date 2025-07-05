from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ---------- DB INITIALIZATION ----------
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Vendors table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT,
            email TEXT
        )
    ''')

    # Employees table
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            contact TEXT
        )
    ''')

    # Projects table
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            site TEXT,
            client TEXT,
            start_date TEXT,
            status TEXT
        )
    ''')

    # Ducts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS ducts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            duct_type TEXT,
            length REAL,
            width REAL,
            height REAL,
            quantity INTEGER,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # Measurement Sheet
    c.execute('''
        CREATE TABLE IF NOT EXISTS measurement_sheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            type TEXT,
            total_area REAL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # Measurement Entries
    c.execute('''
        CREATE TABLE IF NOT EXISTS measurement_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER,
            date TEXT,
            completed_area REAL,
            FOREIGN KEY (sheet_id) REFERENCES measurement_sheet(id)
        )
    ''')

    # Production Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            type TEXT,
            phase TEXT,
            area_completed REAL,
            total_area REAL,
            percentage REAL,
            date TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    conn.commit()
    conn.close()

init_db()
# ---------- LOGIN ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')

    return render_template('login.html')


# ---------- REGISTER USER ----------
@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            flash('User registered successfully', 'success')
        except sqlite3.IntegrityError:
            flash('Username already exists', 'error')
        conn.close()

    return render_template('register.html')


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM projects')
    total_projects = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM vendors')
    total_vendors = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM employees')
    total_employees = c.fetchone()[0]

    conn.close()

    return render_template('dashboard.html',
                           user=session['user'],
                           total_projects=total_projects,
                           total_vendors=total_vendors,
                           total_employees=total_employees)

# ---------- VENDORS ----------
@app.route('/vendors', methods=['GET', 'POST'])
def vendors():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    query = "SELECT * FROM vendors"
    keyword = request.args.get('search', '').strip()
    if keyword:
        query += " WHERE name LIKE ? OR contact LIKE ?"
        c.execute(query, (f'%{keyword}%', f'%{keyword}%'))
    else:
        c.execute(query)

    vendors = c.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors, search=keyword)


@app.route('/add_vendor', methods=['POST'])
def add_vendor():
    name = request.form['name']
    contact = request.form['contact']
    email = request.form['email']
    address = request.form['address']

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('INSERT INTO vendors (name, contact, email, address) VALUES (?, ?, ?, ?)',
              (name, contact, email, address))
    conn.commit()
    conn.close()
    flash('Vendor added successfully!', 'success')
    return redirect(url_for('vendors'))


@app.route('/export_vendors_excel')
def export_vendors_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Vendors')
    writer.close()
    output.seek(0)

    return send_file(output, download_name="vendors.xlsx", as_attachment=True)


@app.route('/export_vendors_pdf')
def export_vendors_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM vendors")
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, y, "Vendor List")
    y -= 30
    p.setFont("Helvetica", 10)
    for row in data:
        line = f"ID: {row[0]}, Name: {row[1]}, Contact: {row[2]}, Email: {row[3]}, Address: {row[4]}"
        p.drawString(30, y, line)
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="vendors.pdf", as_attachment=True)

# ---------- PROJECTS ----------
@app.route('/projects', methods=['GET', 'POST'])
def projects():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    query = "SELECT * FROM projects"
    keyword = request.args.get('search', '').strip()
    if keyword:
        query += " WHERE name LIKE ? OR client LIKE ? OR location LIKE ?"
        c.execute(query, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
    else:
        c.execute(query)

    projects = c.fetchall()
    conn.close()
    return render_template('projects.html', projects=projects, search=keyword)


@app.route('/add_project', methods=['POST'])
def add_project():
    name = request.form['name']
    client = request.form['client']
    location = request.form['location']
    start_date = request.form['start_date']

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('INSERT INTO projects (name, client, location, start_date) VALUES (?, ?, ?, ?)',
              (name, client, location, start_date))
    conn.commit()
    conn.close()
    flash('Project added successfully!', 'success')
    return redirect(url_for('projects'))


@app.route('/export_projects_excel')
def export_projects_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Projects')
    writer.close()
    output.seek(0)

    return send_file(output, download_name="projects.xlsx", as_attachment=True)


@app.route('/export_projects_pdf')
def export_projects_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM projects")
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, y, "Project List")
    y -= 30
    p.setFont("Helvetica", 10)
    for row in data:
        line = f"ID: {row[0]}, Name: {row[1]}, Client: {row[2]}, Location: {row[3]}, Start: {row[4]}"
        p.drawString(30, y, line)
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="projects.pdf", as_attachment=True)

# ---------- MEASUREMENT SHEETS ----------
@app.route('/measurement/<int:project_id>', methods=['GET', 'POST'])
def measurement(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    keyword = request.args.get('search', '').strip()
    if keyword:
        c.execute('''
            SELECT * FROM measurement_sheet 
            WHERE project_id = ? AND sheet_name LIKE ? 
        ''', (project_id, f'%{keyword}%'))
    else:
        c.execute('SELECT * FROM measurement_sheet WHERE project_id = ?', (project_id,))
    
    sheets = c.fetchall()
    c.execute('SELECT name FROM projects WHERE id = ?', (project_id,))
    project_name = c.fetchone()[0]
    conn.close()
    return render_template('measurement_sheet.html', sheets=sheets, project_id=project_id, project_name=project_name, search=keyword)


@app.route('/add_measurement/<int:project_id>', methods=['POST'])
def add_measurement(project_id):
    sheet_name = request.form['sheet_name']
    total_area = request.form['total_area']

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('INSERT INTO measurement_sheet (project_id, sheet_name, total_area) VALUES (?, ?, ?)',
              (project_id, sheet_name, total_area))
    conn.commit()
    conn.close()
    flash('Measurement sheet added successfully!', 'success')
    return redirect(url_for('measurement', project_id=project_id))


@app.route('/measurement_popup/<int:sheet_id>')
def measurement_popup(sheet_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('SELECT * FROM measurement_entries WHERE sheet_id = ?', (sheet_id,))
    entries = c.fetchall()

    c.execute('SELECT sheet_name FROM measurement_sheet WHERE id = ?', (sheet_id,))
    sheet_name = c.fetchone()[0]
    conn.close()
    return render_template('measurement_popup.html', entries=entries, sheet_id=sheet_id, sheet_name=sheet_name)


@app.route('/add_measurement_entry/<int:sheet_id>', methods=['POST'])
def add_measurement_entry(sheet_id):
    description = request.form['description']
    area = request.form['area']

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('INSERT INTO measurement_entries (sheet_id, description, area) VALUES (?, ?, ?)',
              (sheet_id, description, area))
    conn.commit()
    conn.close()
    flash('Measurement entry added successfully!', 'success')
    return redirect(url_for('measurement_popup', sheet_id=sheet_id))


@app.route('/export_measurement_excel/<int:project_id>')
def export_measurement_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query(f'''
        SELECT sheet_name, total_area FROM measurement_sheet 
        WHERE project_id = {project_id}
    ''', conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Measurement Sheets')
    writer.close()
    output.seek(0)

    return send_file(output, download_name="measurement_sheets.xlsx", as_attachment=True)


@app.route('/export_measurement_pdf/<int:project_id>')
def export_measurement_pdf(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('SELECT sheet_name, total_area FROM measurement_sheet WHERE project_id = ?', (project_id,))
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(150, y, "Measurement Sheet List")
    y -= 30
    p.setFont("Helvetica", 10)

    for row in data:
        p.drawString(30, y, f"Sheet: {row[0]}, Total Area: {row[1]}")
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="measurement_sheets.pdf", as_attachment=True)

# ---------- PRODUCTION MODULE ----------
@app.route('/production/<int:project_id>')
def production(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Get all measurement sheets for the project
    c.execute('SELECT id, sheet_name, total_area FROM measurement_sheet WHERE project_id = ?', (project_id,))
    sheets = c.fetchall()

    production_data = []

    for sheet_id, sheet_name, total_area in sheets:
        sheet_progress = {'sheet_id': sheet_id, 'sheet_name': sheet_name, 'total_area': total_area}
        total_done_area = 0

        # Loop through first 3 phases (area-based)
        for phase in ['Sheet Cutting', 'Plasma and Fabrication', 'Boxing and Assembly']:
            c.execute('''
                SELECT done_area FROM production 
                WHERE sheet_id = ? AND phase = ?
            ''', (sheet_id, phase))
            result = c.fetchone()
            done = result[0] if result else 0
            total_done_area += done
            percent = (done / total_area * 100) if total_area else 0
            sheet_progress[phase] = f"{percent:.2f}%"

        # Next 2 phases (percentage-only)
        for phase in ['Quality Checking', 'Dispatch']:
            c.execute('''
                SELECT percentage FROM production 
                WHERE sheet_id = ? AND phase = ?
            ''', (sheet_id, phase))
            result = c.fetchone()
            percent = result[0] if result else 0
            sheet_progress[phase] = f"{percent:.2f}%"

        # Overall completion
        overall = total_done_area / total_area * 100 if total_area else 0
        sheet_progress['overall'] = f"{overall:.2f}%"
        production_data.append(sheet_progress)

    conn.close()
    return render_template('production.html', production_data=production_data, project_id=project_id)


@app.route('/production_update/<int:sheet_id>/<phase>', methods=['GET', 'POST'])
def production_update(sheet_id, phase):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        if phase in ['Sheet Cutting', 'Plasma and Fabrication', 'Boxing and Assembly']:
            done_area = float(request.form['done_area'])
            c.execute('''
                INSERT INTO production (sheet_id, phase, done_area, percentage)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(sheet_id, phase) DO UPDATE SET done_area=excluded.done_area
            ''', (sheet_id, phase, done_area))
        else:
            percentage = float(request.form['percentage'])
            c.execute('''
                INSERT INTO production (sheet_id, phase, done_area, percentage)
                VALUES (?, ?, 0, ?)
                ON CONFLICT(sheet_id, phase) DO UPDATE SET percentage=excluded.percentage
            ''', (sheet_id, phase, percentage))

        conn.commit()
        conn.close()
        flash(f"{phase} updated successfully!", "success")
        return redirect(url_for('production', project_id=request.form['project_id']))
    
    # GET: show current value
    if phase in ['Sheet Cutting', 'Plasma and Fabrication', 'Boxing and Assembly']:
        c.execute('SELECT done_area FROM production WHERE sheet_id = ? AND phase = ?', (sheet_id, phase))
        value = c.fetchone()
        done_area = value[0] if value else 0
        conn.close()
        return render_template('production_phase_popup.html', sheet_id=sheet_id, phase=phase, value=done_area, type='area')
    else:
        c.execute('SELECT percentage FROM production WHERE sheet_id = ? AND phase = ?', (sheet_id, phase))
        value = c.fetchone()
        percentage = value[0] if value else 0
        conn.close()
        return render_template('production_phase_popup.html', sheet_id=sheet_id, phase=phase, value=percentage, type='percentage')


@app.route('/export_production_excel/<int:project_id>')
def export_production_excel(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('SELECT id, sheet_name, total_area FROM measurement_sheet WHERE project_id = ?', (project_id,))
    sheets = c.fetchall()

    data = []
    for sheet_id, sheet_name, total_area in sheets:
        row = {'Sheet Name': sheet_name, 'Total Area': total_area}
        for phase in ['Sheet Cutting', 'Plasma and Fabrication', 'Boxing and Assembly']:
            c.execute('SELECT done_area FROM production WHERE sheet_id = ? AND phase = ?', (sheet_id, phase))
            result = c.fetchone()
            area = result[0] if result else 0
            row[phase] = f"{area:.2f}"

        for phase in ['Quality Checking', 'Dispatch']:
            c.execute('SELECT percentage FROM production WHERE sheet_id = ? AND phase = ?', (sheet_id, phase))
            result = c.fetchone()
            percent = result[0] if result else 0
            row[phase] = f"{percent:.2f}%"

        data.append(row)
    conn.close()

    df = pd.DataFrame(data)
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Production')
    writer.close()
    output.seek(0)
    return send_file(output, download_name="production_report.xlsx", as_attachment=True)


@app.route('/export_production_pdf/<int:project_id>')
def export_production_pdf(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('SELECT id, sheet_name FROM measurement_sheet WHERE project_id = ?', (project_id,))
    sheets = c.fetchall()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(150, y, "Production Report")
    y -= 30
    p.setFont("Helvetica", 9)

    for sheet_id, sheet_name in sheets:
        p.drawString(30, y, f"Sheet: {sheet_name}")
        y -= 15
        for phase in ['Sheet Cutting', 'Plasma and Fabrication', 'Boxing and Assembly']:
            c.execute('SELECT done_area FROM production WHERE sheet_id = ? AND phase = ?', (sheet_id, phase))
            result = c.fetchone()
            val = result[0] if result else 0
            p.drawString(50, y, f"{phase}: {val} sqm")
            y -= 15
        for phase in ['Quality Checking', 'Dispatch']:
            c.execute('SELECT percentage FROM production WHERE sheet_id = ? AND phase = ?', (sheet_id, phase))
            result = c.fetchone()
            val = result[0] if result else 0
            p.drawString(50, y, f"{phase}: {val}%")
            y -= 15

        y -= 10
        if y < 50:
            p.showPage()
            y = height - 50

    conn.close()
    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="production_report.pdf", as_attachment=True)

# ---------- SUMMARY MODULE ----------
@app.route('/summary/<int:project_id>')
def summary(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Get project name
    c.execute('SELECT name FROM projects WHERE id = ?', (project_id,))
    project = c.fetchone()
    project_name = project[0] if project else "Unknown"

    # Count vendors
    c.execute('SELECT COUNT(*) FROM vendors WHERE project_id = ?', (project_id,))
    vendor_count = c.fetchone()[0]

    # Count measurement sheets
    c.execute('SELECT COUNT(*) FROM measurement_sheet WHERE project_id = ?', (project_id,))
    sheet_count = c.fetchone()[0]

    # Count employees
    c.execute('SELECT COUNT(*) FROM employees')
    employee_count = c.fetchone()[0]

    # Total area across all sheets
    c.execute('SELECT SUM(total_area) FROM measurement_sheet WHERE project_id = ?', (project_id,))
    total_area = c.fetchone()[0] or 0

    # Overall progress
    c.execute('SELECT id, total_area FROM measurement_sheet WHERE project_id = ?', (project_id,))
    sheets = c.fetchall()
    overall_progress = 0
    for sheet_id, area in sheets:
        if not area:
            continue
        done_area = 0
        for phase in ['Sheet Cutting', 'Plasma and Fabrication', 'Boxing and Assembly']:
            c.execute('SELECT done_area FROM production WHERE sheet_id = ? AND phase = ?', (sheet_id, phase))
            result = c.fetchone()
            done_area += result[0] if result else 0
        overall_progress += (done_area / area) * 100

    overall_progress = (overall_progress / len(sheets)) if sheets else 0
    conn.close()

    return render_template("summary.html",
                           project_name=project_name,
                           vendor_count=vendor_count,
                           sheet_count=sheet_count,
                           employee_count=employee_count,
                           total_area=total_area,
                           overall_progress=round(overall_progress, 2))


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))


# ---------- APP RUN ----------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
