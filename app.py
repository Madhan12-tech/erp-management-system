from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3, os, uuid, csv
from io import BytesIO
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = 'secret123'

# ---------- INIT DB ----------
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, designation TEXT, email TEXT, phone TEXT,
        username TEXT UNIQUE, password TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, gst TEXT, address TEXT, phone TEXT, email TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enquiry_id TEXT, vendor_id INTEGER, quotation_ro TEXT,
        start_date TEXT, end_date TEXT, location TEXT, gst TEXT, address TEXT,
        incharge TEXT, notes TEXT, file TEXT, approval_status TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS measurement_sheet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER, client TEXT, company TEXT,
        location TEXT, engineer TEXT, phone TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS ducts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER, duct_no TEXT, duct_type TEXT,
        duct_size TEXT, quantity INTEGER, remarks TEXT)''')

    # Dummy user
    c.execute("SELECT * FROM employees WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO employees (name, designation, email, phone, username, password) VALUES (?, ?, ?, ?, ?, ?)",
                  ("Admin", "Manager", "admin@example.com", "1234567890", "admin", "admin123"))

    conn.commit()
    conn.close()

init_db()

# ---------- LOGIN ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("SELECT * FROM employees WHERE username=? AND password=?", (uname, pwd))
        user = c.fetchone()
        conn.close()
        if user:
            session['user'] = user[1]
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect('/')

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('erp.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM projects")
    projects = c.fetchall()
    conn.close()
    return render_template("dashboard.html", projects=projects)

# ---------- VENDORS ----------
@app.route('/vendors', methods=['GET', 'POST'])
def vendors():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    if request.method == 'POST':
        c.execute("INSERT INTO vendors (name, gst, address, phone, email) VALUES (?, ?, ?, ?, ?)", (
            request.form['name'], request.form['gst'], request.form['address'],
            request.form['phone'], request.form['email']))
        conn.commit()
        flash('Vendor added', 'success')
        return redirect('/vendors')
    c.execute("SELECT * FROM vendors")
    vendors = c.fetchall()
    conn.close()
    return render_template("vendors.html", vendors=vendors)

# ---------- ADD PROJECT ----------
@app.route('/add_project', methods=['POST'])
def add_project():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    file = request.files['file']
    filename = str(uuid.uuid4()) + "_" + file.filename if file else ""
    if file:
        file.save(os.path.join('uploads', filename))

    c.execute('''INSERT INTO projects (enquiry_id, vendor_id, quotation_ro, start_date, end_date,
        location, gst, address, incharge, notes, file, approval_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (request.form['enquiry_id'], request.form['vendor_id'], request.form['quotation_ro'],
         request.form['start_date'], request.form['end_date'], request.form['location'],
         request.form['gst_number'], request.form['address'], request.form['incharge'],
         request.form['notes'], filename, 'Design Process'))
    conn.commit()
    conn.close()
    flash("Project added", "success")
    return redirect('/dashboard')

# ---------- MEASUREMENT SHEET ----------
@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''INSERT INTO measurement_sheet (project_id, client, company, location, engineer, phone)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (request.form['project_id'], request.form['client_name'], request.form['company_name'],
         request.form['project_location'], request.form['engineer_name'], request.form['phone']))
    conn.commit()
    conn.close()
    return redirect(url_for('measurement_sheet', project_id=request.form['project_id']))

@app.route('/measurement_sheet/<int:project_id>')
def measurement_sheet(project_id):
    conn = sqlite3.connect('erp.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM measurement_sheet WHERE project_id = ?", (project_id,))
    ms = c.fetchone()
    c.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,))
    ducts = c.fetchall()
    conn.close()
    return render_template("measurement_sheet.html", **ms, ducts=ducts, project_id=project_id)

# ---------- DUCT ENTRY ----------
@app.route('/add_duct', methods=['POST'])
def add_duct():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    project_id = request.form['project_id']
    c.execute('''INSERT INTO ducts (project_id, duct_no, duct_type, duct_size, quantity)
        VALUES (?, ?, ?, ?, ?)''',
        (project_id, request.form['duct_no'], request.form['duct_type'],
         request.form['duct_size'], request.form['quantity']))
    conn.commit()
    conn.close()
    return redirect(url_for('measurement_sheet', project_id=project_id))

# ---------- EXPORT ----------
@app.route('/export_csv/<int:project_id>')
def export_csv(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT duct_no, duct_type, duct_size, quantity FROM ducts WHERE project_id = ?", (project_id,))
    data = c.fetchall()
    output = BytesIO()
    writer = csv.writer(output)
    writer.writerow(['Duct No', 'Type', 'Size', 'Quantity'])
    writer.writerows(data)
    output.seek(0)
    return send_file(output, download_name='duct_data.csv', as_attachment=True)

@app.route('/export_excel/<int:project_id>')
def export_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT duct_no, duct_type, duct_size, quantity FROM ducts WHERE project_id = ?", conn, params=(project_id,))
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name='duct_data.xlsx', as_attachment=True)

@app.route('/export_pdf/<int:project_id>')
def export_pdf(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT duct_no, duct_type, duct_size, quantity FROM ducts WHERE project_id = ?", (project_id,))
    data = c.fetchall()
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    y = A4[1] - 50
    p.drawString(50, y, "Duct No | Type | Size | Quantity")
    y -= 20
    for row in data:
        p.drawString(50, y, " | ".join(str(i) for i in row))
        y -= 20
    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name='duct_data.pdf', as_attachment=True)

# ---------- MAIN ----------
if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
