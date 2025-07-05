from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# -------------------- DATABASE SETUP --------------------

def get_db_connection():
    conn = sqlite3.connect('erp.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    # Vendors table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contact TEXT,
            email TEXT
        )
    ''')

    # Employees table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            email TEXT,
            phone TEXT
        )
    ''')

    # Projects table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            site_location TEXT,
            start_date TEXT,
            end_date TEXT
        )
    ''')

    # Measurement Sheet
    cur.execute('''
        CREATE TABLE IF NOT EXISTS measurement_sheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            entry_date TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS measurement_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER,
            floor TEXT,
            length REAL,
            width REAL,
            height REAL,
            area REAL,
            FOREIGN KEY (sheet_id) REFERENCES measurement_sheet (id)
        )
    ''')

    # Production progress
    cur.execute('''
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            phase TEXT,
            completed_area REAL,
            total_area REAL,
            percent_complete REAL,
            date TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    # Insert dummy admin if not exists
    cur.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                    ('admin', generate_password_hash('admin123')))

    # Insert dummy vendors
    cur.execute("SELECT COUNT(*) FROM vendors")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO vendors (name, contact, email) VALUES ('Alpha Traders', '9876543210', 'alpha@example.com')")
        cur.execute("INSERT INTO vendors (name, contact, email) VALUES ('Beta Supplies', '9123456780', 'beta@example.com')")

    # Insert dummy employees
    cur.execute("SELECT COUNT(*) FROM employees")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO employees (name, role, email, phone) VALUES ('John Doe', 'Designer', 'john@example.com', '9000000000')")
        cur.execute("INSERT INTO employees (name, role, email, phone) VALUES ('Jane Smith', 'Engineer', 'jane@example.com', '9111111111')")

    # Insert dummy project
    cur.execute("SELECT COUNT(*) FROM projects")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO projects (name, site_location, start_date, end_date) VALUES ('HVAC Site A', 'Chennai', '2024-01-01', '2025-12-31')")

    conn.commit()
    conn.close()

init_db()

# -------------------- LOGIN & LOGOUT ROUTES --------------------

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password_input):
            session['user'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

# -------------------- DASHBOARD ROUTE --------------------

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    total_vendors = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
    total_employees = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    conn.close()

    return render_template('dashboard.html',
                           user=session['user'],
                           total_projects=total_projects,
                           total_vendors=total_vendors,
                           total_employees=total_employees)

# -------------------- VENDORS --------------------

@app.route('/vendors', methods=['GET', 'POST'])
def vendors():
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        contact = request.form['contact']
        location = request.form['location']
        conn.execute("INSERT INTO vendors (name, category, contact, location) VALUES (?, ?, ?, ?)",
                     (name, category, contact, location))
        conn.commit()
        flash('Vendor added successfully!', 'success')
        return redirect(url_for('vendors'))

    search = request.args.get('search', '')
    if search:
        vendor_data = conn.execute("SELECT * FROM vendors WHERE name LIKE ?", ('%' + search + '%',)).fetchall()
    else:
        vendor_data = conn.execute("SELECT * FROM vendors").fetchall()

    conn.close()
    return render_template('vendors.html', vendors=vendor_data, search=search)

# -------------------- EXPORT VENDORS TO EXCEL --------------------

@app.route('/export_vendors_excel')
def export_vendors_excel():
    conn = get_db_connection()
    vendors = conn.execute("SELECT * FROM vendors").fetchall()
    conn.close()

    df = pd.DataFrame(vendors, columns=['id', 'name', 'category', 'contact', 'location'])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendors')

    output.seek(0)
    return send_file(output, download_name="vendors.xlsx", as_attachment=True)

# -------------------- EXPORT VENDORS TO PDF --------------------

@app.route('/export_vendors_pdf')
def export_vendors_pdf():
    conn = get_db_connection()
    vendors = conn.execute("SELECT * FROM vendors").fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, y, "Vendor List")
    y -= 30
    c.setFont("Helvetica", 10)
    for vendor in vendors:
        line = f"ID: {vendor[0]}, Name: {vendor[1]}, Category: {vendor[2]}, Contact: {vendor[3]}, Location: {vendor[4]}"
        c.drawString(50, y, line)
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return send_file(buffer, download_name="vendors.pdf", as_attachment=True)

# -------------------- PROJECTS --------------------

@app.route('/projects', methods=['GET', 'POST'])
def projects():
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        client = request.form['client']
        location = request.form['location']
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        conn.execute("INSERT INTO projects (name, client, location, start_date, end_date) VALUES (?, ?, ?, ?, ?)",
                     (name, client, location, start_date, end_date))
        conn.commit()
        flash('Project added successfully!', 'success')
        return redirect(url_for('projects'))

    search = request.args.get('search', '')
    if search:
        project_data = conn.execute("SELECT * FROM projects WHERE name LIKE ?", ('%' + search + '%',)).fetchall()
    else:
        project_data = conn.execute("SELECT * FROM projects").fetchall()

    conn.close()
    return render_template('projects.html', projects=project_data, search=search)

@app.route('/project_selector')
def project_selector():
    if 'user' not in session:
        return redirect(url_for('login'))

    next_page = request.args.get('next')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM projects")
    projects = c.fetchall()
    conn.close()

    return render_template('project_selector.html', projects=projects, next_page=next_page)

# -------------------- EXPORT PROJECTS TO EXCEL --------------------

@app.route('/export_projects_excel')
def export_projects_excel():
    conn = get_db_connection()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()

    df = pd.DataFrame(projects, columns=['id', 'name', 'client', 'location', 'start_date', 'end_date'])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')

    output.seek(0)
    return send_file(output, download_name="projects.xlsx", as_attachment=True)

# -------------------- EXPORT PROJECTS TO PDF --------------------

@app.route('/export_projects_pdf')
def export_projects_pdf():
    conn = get_db_connection()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, y, "Project List")
    y -= 30
    c.setFont("Helvetica", 10)
    for p in projects:
        line = f"ID: {p[0]}, Name: {p[1]}, Client: {p[2]}, Location: {p[3]}, Start: {p[4]}, End: {p[5]}"
        c.drawString(50, y, line)
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return send_file(buffer, download_name="projects.pdf", as_attachment=True)

# -------------------- MEASUREMENT SHEET --------------------

@app.route('/measurement_sheet/<int:project_id>', methods=['GET', 'POST'])
def measurement_sheet(project_id):
    conn = get_db_connection()

    if request.method == 'POST':
        item = request.form['item']
        length = float(request.form['length'])
        breadth = float(request.form['breadth'])
        height = float(request.form['height'])
        area = round(length * breadth, 2)

        conn.execute("INSERT INTO measurement_sheet (project_id, item, length, breadth, height, area) VALUES (?, ?, ?, ?, ?, ?)",
                     (project_id, item, length, breadth, height, area))
        conn.commit()
        flash('Measurement entry added!', 'success')
        return redirect(url_for('measurement_sheet', project_id=project_id))

    search = request.args.get('search', '')
    if search:
        entries = conn.execute("SELECT * FROM measurement_sheet WHERE project_id = ? AND item LIKE ?",
                               (project_id, '%' + search + '%')).fetchall()
    else:
        entries = conn.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,)).fetchall()

    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return render_template('measurement_sheet.html', entries=entries, project=project, search=search)

# -------------------- EXPORT MEASUREMENT TO EXCEL --------------------

@app.route('/export_measurements_excel/<int:project_id>')
def export_measurements_excel(project_id):
    conn = get_db_connection()
    entries = conn.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()

    df = pd.DataFrame(entries, columns=['id', 'project_id', 'item', 'length', 'breadth', 'height', 'area'])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Measurements')

    output.seek(0)
    return send_file(output, download_name=f"measurement_sheet_{project_id}.xlsx", as_attachment=True)

# -------------------- EXPORT MEASUREMENT TO PDF --------------------

@app.route('/export_measurements_pdf/<int:project_id>')
def export_measurements_pdf(project_id):
    conn = get_db_connection()
    entries = conn.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(160, y, f"Measurement Sheet - Project {project_id}")
    y -= 30
    c.setFont("Helvetica", 9)

    for row in entries:
        line = f"Item: {row[2]}, L: {row[3]}, B: {row[4]}, H: {row[5]}, Area: {row[6]}"
        c.drawString(50, y, line)
        y -= 18
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return send_file(buffer, download_name=f"measurement_sheet_{project_id}.pdf", as_attachment=True)

# -------------------- MEASUREMENT SUMMARY --------------------

@app.route('/measurement_summary/<int:project_id>')
def measurement_summary(project_id):
    conn = get_db_connection()
    result = conn.execute("""
        SELECT item, SUM(area) as total_area
        FROM measurement_sheet
        WHERE project_id = ?
        GROUP BY item
    """, (project_id,)).fetchall()

    conn.close()
    return render_template('measurement_summary.html', project_id=project_id, summary=result)


# -------------------- DUCT ENTRY --------------------

@app.route('/duct_entry/<int:project_id>', methods=['GET', 'POST'])
def duct_entry(project_id):
    conn = get_db_connection()

    if request.method == 'POST':
        item_type = request.form['item_type']
        length = float(request.form['length'])
        breadth = float(request.form['breadth'])
        height = float(request.form['height'])
        quantity = int(request.form['quantity'])
        area = round(length * breadth * quantity, 2)

        conn.execute("INSERT INTO ducts (project_id, item_type, length, breadth, height, quantity, area) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (project_id, item_type, length, breadth, height, quantity, area))
        conn.commit()
        flash("Duct added successfully", "success")
        return redirect(url_for('duct_entry', project_id=project_id))

    search = request.args.get('search', '')
    if search:
        ducts = conn.execute("SELECT * FROM ducts WHERE project_id = ? AND item_type LIKE ?",
                             (project_id, f'%{search}%')).fetchall()
    else:
        ducts = conn.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,)).fetchall()

    conn.close()
    return render_template('duct_entry.html', ducts=ducts, project_id=project_id, search=search)


# -------------------- EXPORT DUCTS --------------------

@app.route('/export_ducts_excel/<int:project_id>')
def export_ducts_excel(project_id):
    conn = get_db_connection()
    ducts = conn.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()

    df = pd.DataFrame(ducts, columns=['id', 'project_id', 'item_type', 'length', 'breadth', 'height', 'quantity', 'area'])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ducts')

    output.seek(0)
    return send_file(output, download_name=f"ducts_{project_id}.xlsx", as_attachment=True)


@app.route('/export_ducts_pdf/<int:project_id>')
def export_ducts_pdf(project_id):
    conn = get_db_connection()
    ducts = conn.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(160, y, f"Duct Entry - Project {project_id}")
    y -= 30
    c.setFont("Helvetica", 9)

    for d in ducts:
        line = f"{d[2]} - L:{d[3]} B:{d[4]} H:{d[5]} Qty:{d[6]} Area:{d[7]}"
        c.drawString(50, y, line)
        y -= 18
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return send_file(buffer, download_name=f"ducts_{project_id}.pdf", as_attachment=True)

# -------------------- PRODUCTION SELECTOR --------------------

@app.route('/production_selector')
def production_selector():
    conn = get_db_connection()
    projects = conn.execute("SELECT id, name FROM projects").fetchall()
    conn.close()
    return render_template('production_selector.html', projects=projects)


# -------------------- PRODUCTION MODULE --------------------

@app.route('/production/<int:project_id>', methods=['GET', 'POST'])
def production(project_id):
    conn = get_db_connection()

    # Initialize default phases if not already
    phases = ['Sheet Cutting', 'Plasma and Fabrication', 'Boxing and Assembly', 'Quality Checking', 'Dispatch']
    for phase in phases:
        exists = conn.execute("SELECT id FROM production WHERE project_id = ? AND phase = ?", (project_id, phase)).fetchone()
        if not exists:
            conn.execute("INSERT INTO production (project_id, phase, completed_area, total_area, percent_complete) VALUES (?, ?, 0, 0, 0)", (project_id, phase))
            conn.commit()

    if request.method == 'POST':
        for phase in phases:
            done_area = request.form.get(f'done_{phase}', '')
            if done_area:
                done_area = float(done_area)
                total_area = conn.execute("SELECT total_area FROM production WHERE project_id = ? AND phase = ?", (project_id, phase)).fetchone()[0]
                percent = round((done_area / total_area) * 100, 2) if total_area else 0
                conn.execute("UPDATE production SET completed_area = ?, percent_complete = ? WHERE project_id = ? AND phase = ?",
                             (done_area, percent, project_id, phase))
        conn.commit()
        flash("Production updated successfully", "success")
        return redirect(url_for('production', project_id=project_id))

    prod_data = conn.execute("SELECT * FROM production WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()
    return render_template("production.html", data=prod_data, project_id=project_id)


# -------------------- EXPORT PRODUCTION --------------------

@app.route('/export_production_excel/<int:project_id>')
def export_production_excel(project_id):
    conn = get_db_connection()
    data = conn.execute("SELECT * FROM production WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()

    df = pd.DataFrame(data, columns=['id', 'project_id', 'phase', 'completed_area', 'total_area', 'percent_complete'])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Production')
    output.seek(0)
    return send_file(output, download_name=f"production_{project_id}.xlsx", as_attachment=True)


@app.route('/export_production_pdf/<int:project_id>')
def export_production_pdf(project_id):
    conn = get_db_connection()
    data = conn.execute("SELECT * FROM production WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(160, y, f"Production Report - Project {project_id}")
    y -= 30
    c.setFont("Helvetica", 9)

    for row in data:
        line = f"{row[2]} - Done: {row[3]} / {row[4]} sqm ({row[5]}%)"
        c.drawString(50, y, line)
        y -= 18
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return send_file(buffer, download_name=f"production_{project_id}.pdf", as_attachment=True)


# -------------------- QUALITY CHECKING & DISPATCH (only percentage) --------------------

@app.route('/update_phase_progress/<int:project_id>', methods=['POST'])
def update_phase_progress(project_id):
    conn = get_db_connection()
    phases = ['Quality Checking', 'Dispatch']

    for phase in phases:
        percent = request.form.get(f'percent_{phase}')
        if percent:
            conn.execute("UPDATE production SET percent_complete = ?, completed_area = 0, total_area = 0 WHERE project_id = ? AND phase = ?",
                         (percent, project_id, phase))
    conn.commit()
    conn.close()
    flash("Phase progress updated.", "success")
    return redirect(url_for('summary', project_id=project_id))


# -------------------- SUMMARY MODULE --------------------

@app.route('/summary/<int:project_id>')
def summary(project_id):
    conn = get_db_connection()
    project = conn.execute("SELECT name FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for('dashboard'))

    production_data = conn.execute("SELECT phase, completed_area, total_area, percent_complete FROM production WHERE project_id = ?", (project_id,)).fetchall()

    # Calculate overall progress
    total_percent = 0
    for row in production_data:
        total_percent += row['percent_complete']
    overall_progress = round(total_percent / len(production_data), 2) if production_data else 0

    conn.close()
    return render_template("summary.html", project=project['name'], data=production_data, progress=overall_progress, project_id=project_id)


# -------------------- EXPORT SUMMARY --------------------

@app.route('/export_summary_excel/<int:project_id>')
def export_summary_excel(project_id):
    conn = get_db_connection()
    project_name = conn.execute("SELECT name FROM projects WHERE id = ?", (project_id,)).fetchone()['name']
    data = conn.execute("SELECT * FROM production WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()

    df = pd.DataFrame(data, columns=['id', 'project_id', 'phase', 'completed_area', 'total_area', 'percent_complete'])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Summary')
    output.seek(0)
    return send_file(output, download_name=f"summary_{project_name}.xlsx", as_attachment=True)


@app.route('/export_summary_pdf/<int:project_id>')
def export_summary_pdf(project_id):
    conn = get_db_connection()
    project_name = conn.execute("SELECT name FROM projects WHERE id = ?", (project_id,)).fetchone()['name']
    data = conn.execute("SELECT * FROM production WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(150, y, f"Summary Report - {project_name}")
    y -= 30
    c.setFont("Helvetica", 9)

    for row in data:
        line = f"{row[2]} - Done: {row[3]} / {row[4]} sqm ({row[5]}%)"
        c.drawString(50, y, line)
        y -= 18
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return send_file(buffer, download_name=f"summary_{project_name}.pdf", as_attachment=True)


# -------------------- MAIN --------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
