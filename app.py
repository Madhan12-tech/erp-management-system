from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import uuid
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secretkey'

# ----------------------- DATABASE SETUP -----------------------
def init_db():
    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        company TEXT,
        contact TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        position TEXT,
        department TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        location TEXT,
        start_date TEXT,
        end_date TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS measurement_sheet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        type TEXT,
        length REAL,
        breadth REAL,
        height REAL,
        area REAL,
        remarks TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS production (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        sheet_cutting REAL DEFAULT 0,
        plasma_fabrication REAL DEFAULT 0,
        boxing_assembly REAL DEFAULT 0,
        quality_check INTEGER DEFAULT 0,
        dispatch INTEGER DEFAULT 0
    )''')

    # Dummy login user
    cur.execute("SELECT * FROM users WHERE username = ?", ('admin',))
    if not cur.fetchone():
        hashed = generate_password_hash('admin123')
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed))

    # Dummy vendors
    cur.execute("SELECT * FROM vendors")
    if not cur.fetchall():
        cur.execute("INSERT INTO vendors (name, company, contact) VALUES (?, ?, ?)", ('Vendor A', 'ABC Pvt Ltd', '9876543210'))
        cur.execute("INSERT INTO vendors (name, company, contact) VALUES (?, ?, ?)", ('Vendor B', 'XYZ Ltd', '9123456780'))

    conn.commit()
    conn.close()

init_db()

# ----------------------- LOGIN -----------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('erp.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            session['user'] = username
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')


# ----------------------- LOGOUT -----------------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


# ----------------------- REGISTER -----------------------
@app.route('/register', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed = generate_password_hash(password)
        conn = sqlite3.connect('erp.db')
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
            conn.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists', 'error')
            return redirect(url_for('register_user'))
        finally:
            conn.close()
    return render_template('register.html')


# ----------------------- DASHBOARD -----------------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM projects")
    total_projects = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vendors")
    total_vendors = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM employees")
    total_employees = cur.fetchone()[0]
    conn.close()

    return render_template('dashboard.html',
                           user=session['user'],
                           total_projects=total_projects,
                           total_vendors=total_vendors,
                           total_employees=total_employees)

# ----------------------- VENDOR REGISTRATION -----------------------
@app.route('/vendor_registration', methods=['GET', 'POST'])
def vendor_registration():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        email = request.form['email']
        address = request.form['address']
        conn = sqlite3.connect('erp.db')
        cur = conn.cursor()
        cur.execute("INSERT INTO vendors (name, contact, email, address) VALUES (?, ?, ?, ?)",
                    (name, contact, email, address))
        conn.commit()
        conn.close()
        flash('Vendor added successfully!', 'success')
        return redirect(url_for('vendors'))
    return render_template('vendor_registration.html')


# ----------------------- VENDORS LIST -----------------------
@app.route('/vendors')
def vendors():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM vendors")
    vendor_data = cur.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendor_data)

# ----------------------- PROJECT SELECTOR -----------------------
@app.route('/project_selector')
def project_selector():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects")
    project_list = cur.fetchall()
    conn.close()
    return render_template('project_selector.html', projects=project_list)


# ----------------------- PROJECTS MODULE -----------------------
@app.route('/projects', methods=['GET', 'POST'])
def projects():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        client = request.form['client']

        cur.execute("INSERT INTO projects (name, location, start_date, end_date, client) VALUES (?, ?, ?, ?, ?)",
                    (name, location, start_date, end_date, client))
        conn.commit()
        flash('Project added successfully!', 'success')
        return redirect(url_for('projects'))

    cur.execute("SELECT * FROM projects")
    project_data = cur.fetchall()
    conn.close()
    return render_template('projects.html', projects=project_data)

# ----------------------- EMPLOYEE MODULE -----------------------
@app.route('/employees', methods=['GET', 'POST'])
def employees():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        cur.execute("INSERT INTO employees (name, role, email, phone, username, password) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, role, email, phone, username, password))
        conn.commit()
        flash("Employee registered successfully!", "success")
        return redirect(url_for('employees'))

    cur.execute("SELECT * FROM employees")
    employees = cur.fetchall()
    conn.close()
    return render_template("employees.html", employees=employees)


@app.route('/employee/edit/<int:emp_id>', methods=['GET', 'POST'])
def employee_edit(emp_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        email = request.form['email']
        phone = request.form['phone']

        cur.execute("UPDATE employees SET name=?, role=?, email=?, phone=? WHERE id=?",
                    (name, role, email, phone, emp_id))
        conn.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employees'))

    cur.execute("SELECT * FROM employees WHERE id=?", (emp_id,))
    emp = cur.fetchone()
    conn.close()
    return render_template("employee_edit.html", employee=emp)

# ----------------------- VENDOR MODULE -----------------------
@app.route('/vendor_registration', methods=['GET', 'POST'])
def vendor_registration():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        contact = request.form['contact']
        email = request.form['email']
        address = request.form['address']

        conn = sqlite3.connect('erp.db')
        cur = conn.cursor()
        cur.execute("INSERT INTO vendors (name, category, contact, email, address) VALUES (?, ?, ?, ?, ?)",
                    (name, category, contact, email, address))
        conn.commit()
        conn.close()
        flash('Vendor registered successfully!', 'success')
        return redirect(url_for('vendors'))

    return render_template("vendor_registration.html")


@app.route('/vendors')
def vendors():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM vendors")
    vendors_data = cur.fetchall()
    conn.close()
    return render_template("vendors.html", vendors=vendors_data)

# ----------------------- PROJECT MODULE -----------------------
@app.route('/project_selector')
def project_selector():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects")
    projects = cur.fetchall()
    conn.close()
    return render_template("project_selector.html", projects=projects)


@app.route('/projects', methods=['GET', 'POST'])
def projects():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        client = request.form['client']
        location = request.form['location']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        status = request.form['status']

        cur.execute("INSERT INTO projects (name, client, location, start_date, end_date, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, client, location, start_date, end_date, status))
        conn.commit()
        flash('Project added successfully!', 'success')

    cur.execute("SELECT * FROM projects")
    project_data = cur.fetchall()
    conn.close()
    return render_template("projects.html", projects=project_data)

# ----------------------- EMPLOYEE MODULE -----------------------
@app.route('/employee_selector')
def employee_selector():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM employees")
    employees = cur.fetchall()
    conn.close()
    return render_template("employee_selector.html", employees=employees)


@app.route('/employees', methods=['GET', 'POST'])
def employees():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        cur.execute("INSERT INTO employees (name, role, email, phone, username, password) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, role, email, phone, username, password))
        conn.commit()
        flash('Employee added successfully!', 'success')

    cur.execute("SELECT * FROM employees")
    employees = cur.fetchall()
    conn.close()
    return render_template("employees.html", employees=employees)


@app.route('/employee_edit/<int:id>', methods=['GET', 'POST'])
def employee_edit(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        if password:
            password_hash = generate_password_hash(password)
            cur.execute("UPDATE employees SET name=?, role=?, email=?, phone=?, username=?, password=? WHERE id=?",
                        (name, role, email, phone, username, password_hash, id))
        else:
            cur.execute("UPDATE employees SET name=?, role=?, email=?, phone=?, username=? WHERE id=?",
                        (name, role, email, phone, username, id))

        conn.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employees'))

    cur.execute("SELECT * FROM employees WHERE id=?", (id,))
    employee = cur.fetchone()
    conn.close()
    return render_template("employee_edit.html", employee=employee)

# ----------------------- VENDOR MODULE -----------------------
@app.route('/vendor_selector')
def vendor_selector():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM vendors")
    vendors = cur.fetchall()
    conn.close()
    return render_template("vendor_selector.html", vendors=vendors)




# ----------------------- MEASUREMENT MODULE -----------------------
@app.route('/measurement_selector')
def measurement_selector():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects")
    projects = cur.fetchall()
    conn.close()
    return render_template("measurement_selector.html", projects=projects)


@app.route('/measurement_sheet/<int:project_id>')
def measurement_sheet(project_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()
    cur.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
    project_name = cur.fetchone()

    cur.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,))
    measurements = cur.fetchall()
    conn.close()

    return render_template("measurement_sheet.html", project_name=project_name[0], measurements=measurements, project_id=project_id)

# ----------------------- PRODUCTION MODULE -----------------------
@app.route('/production_selector')
def production_selector():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects")
    projects = cur.fetchall()
    conn.close()
    return render_template("production_selector.html", projects=projects)


@app.route('/production/<int:project_id>')
def production(project_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    cur = conn.cursor()
    cur.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
    project_name = cur.fetchone()

    cur.execute("SELECT * FROM production WHERE project_id = ?", (project_id,))
    production_data = cur.fetchall()
    conn.close()

    return render_template("production.html", project_name=project_name[0], production_data=production_data, project_id=project_id)

# ----------------------- LOGOUT + TOAST SETUP -----------------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# ----------------------- TOAST MESSAGE CONTEXT PROCESSOR -----------------------
@app.context_processor
def inject_toast_messages():
    return dict(get_flashed_messages=get_flashed_messages)

# ----------------------- SUMMARY MODULE -----------------------
@app.route('/summary', methods=['GET', 'POST'])
def summary():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    query = "SELECT p.name, p.status, COUNT(d.id), IFNULL(SUM(m.area), 0) FROM projects p LEFT JOIN ducts d ON p.id = d.project_id LEFT JOIN measurement_entries m ON d.id = m.duct_id GROUP BY p.id"
    c.execute(query)
    data = c.fetchall()
    conn.close()

    return render_template('summary.html', data=data)

# ----------------------- EXPORT SUMMARY -----------------------
@app.route('/export_summary_excel')
def export_summary_excel():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("""
        SELECT p.name AS project, p.status, COUNT(d.id) AS total_ducts, IFNULL(SUM(m.area), 0) AS total_area
        FROM projects p
        LEFT JOIN ducts d ON p.id = d.project_id
        LEFT JOIN measurement_entries m ON d.id = m.duct_id
        GROUP BY p.id
    """, conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="summary.xlsx", as_attachment=True)

@app.route('/export_summary_pdf')
def export_summary_pdf():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("""
        SELECT p.name, p.status, COUNT(d.id), IFNULL(SUM(m.area), 0)
        FROM projects p
        LEFT JOIN ducts d ON p.id = d.project_id
        LEFT JOIN measurement_entries m ON d.id = m.duct_id
        GROUP BY p.id
    """)
    data = c.fetchall()
    conn.close()

    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(200, height - 50, "Project Summary Report")
    pdf.setFont("Helvetica", 12)

    y = height - 100
    pdf.drawString(50, y, "Project")
    pdf.drawString(200, y, "Status")
    pdf.drawString(300, y, "Ducts")
    pdf.drawString(400, y, "Total Area")
    y -= 20

    for row in data:
        pdf.drawString(50, y, str(row[0]))
        pdf.drawString(200, y, str(row[1]))
        pdf.drawString(300, y, str(row[2]))
        pdf.drawString(400, y, str(row[3]))
        y -= 20
        if y < 100:
            pdf.showPage()
            y = height - 100

    pdf.save()
    output.seek(0)
    return send_file(output, download_name="summary.pdf", as_attachment=True)

if __name__ == '__main__':
    init_db()  # Ensure DB is initialized
    app.run(debug=True, host='0.0.0.0', port=5000)
