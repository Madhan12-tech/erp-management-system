from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import uuid
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'secretkey'

# ---------- DATABASE INITIALIZATION ----------
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
            gst_number TEXT,
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

    # Measurement Sheet
    c.execute('''
        CREATE TABLE IF NOT EXISTS measurement_sheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client_name TEXT,
            company_name TEXT,
            project_location TEXT,
            engineer_name TEXT,
            phone TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # Duct Entries
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

# ---------- INSERT DUMMY DATA ----------
def insert_dummy_data():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Dummy Employee
    hashed_password = generate_password_hash('admin123')
    c.execute("SELECT * FROM employees WHERE email='admin@ducting.com'")
    if not c.fetchone():
        c.execute("INSERT INTO employees (name, email, password, role) VALUES (?, ?, ?, ?)",
                  ('Admin User', 'admin@ducting.com', hashed_password, 'Admin'))

    # Dummy Vendor
    c.execute("SELECT * FROM vendors WHERE name='ABC Fabricators'")
    if not c.fetchone():
        c.execute("INSERT INTO vendors (name, gst_number, address) VALUES (?, ?, ?)",
                  ('ABC Fabricators', '29ABCDE1234F2Z5', 'Bangalore, Karnataka'))

    # Dummy Contacts
    vendor_id = c.execute("SELECT id FROM vendors WHERE name='ABC Fabricators'").fetchone()[0]
    c.execute("SELECT * FROM vendor_contacts WHERE vendor_id=?", (vendor_id,))
    if not c.fetchone():
        c.execute("INSERT INTO vendor_contacts (vendor_id, name, email, phone) VALUES (?, ?, ?, ?)",
                  (vendor_id, 'John Doe', 'john@abc.com', '9876543210'))

    conn.commit()
    conn.close()

# ---------- INITIALIZE DATABASE ----------
init_db()
insert_dummy_data()

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("SELECT * FROM employees WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['email'] = user[2]
            session['name'] = user[1]
            session['role'] = user[4]
            flash("Login successful", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/')
def home():
    return redirect(url_for('login'))  # Or render_template('login.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204  # Return empty 204 No Content to skip errors

@app.route('/projects')
def projects():
    return redirect(url_for('dashboard'))  # or render_template(...) if it's a real page

# ---------- REGISTER EMPLOYEE ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO employees (name, email, password, role) VALUES (?, ?, ?, ?)",
                      (name, email, password, role))
            conn.commit()
            flash("Registration successful", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists", "error")
        finally:
            conn.close()

    return render_template('register.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM projects ORDER BY id DESC")
        projects = c.fetchall()
    except:
        projects = []
    conn.close()

    return render_template('dashboard.html', name=session.get('name', 'User'), projects=projects)
# ---------- VENDOR REGISTRATION ----------

@app.route('/vendor_register', methods=['GET', 'POST'])
def vendor_register():
    if request.method == 'POST':
        name = request.form['vendor_name']
        gst = request.form['gst_number']
        address = request.form['address']
        contacts = request.form.getlist('contact_person[]')
        phones = request.form.getlist('contact_phone[]')

        # ✅ Corrected to match HTML field names
        bank_name = request.form.get('bank_name', '')
        account_no = request.form.get('account_number', '')
        ifsc = request.form.get('ifsc', '')

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()

        c.execute("INSERT INTO vendors (name, gst_number, address) VALUES (?, ?, ?)", (name, gst, address))
        vendor_id = c.lastrowid

        for person, phone in zip(contacts, phones):
            c.execute("INSERT INTO vendor_contacts (vendor_id, name, phone) VALUES (?, ?, ?)", (vendor_id, person, phone))

        if bank_name and account_no and ifsc:
            # Safe: create bank table if not exists
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

    return render_template('vendor_register.html')


# ---------- GET VENDOR LIST FOR DROPDOWN (PROJECTS) ----------
@app.route('/api/vendors')
def get_vendors():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT id, name, gst_number, address FROM vendors")
    data = c.fetchall()
    conn.close()
    return {'vendors': data}

# ---------- ADD PROJECT ----------
@app.route('/add_project', methods=['POST'])
def add_project():
    data = request.form
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("""INSERT INTO projects (
        enquiry_id, vendor_id, gst_number, address, quotation_ro,
        start_date, end_date, location, incharge, notes, file_path, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
        data['enquiry_id'], data['vendor_id'], data['gst_number'], data['address'],
        data['quotation_ro'], data['start_date'], data['end_date'], data['location'],
        data['incharge'], data['notes'], "", "Design Process"
    ))
    conn.commit()
    conn.close()
    flash("Project added successfully", "success")
    return redirect(url_for('dashboard'))


# ---------- ADD MEASUREMENT SHEET ----------
@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    data = request.form
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("""INSERT INTO measurement_sheet (
        project_id, client_name, company_name, project_location,
        engineer_name, phone, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?)""", (
        data['project_id'], data['client_name'], data['company_name'],
        data['project_location'], data['engineer_name'], data['phone'], datetime.now()
    ))
    conn.commit()
    conn.close()
    flash("Measurement sheet added", "success")
    return redirect(url_for('dashboard'))

# ---------- ADD DUCT ENTRY ----------
@app.route('/add_duct', methods=['POST'])
def add_duct():
    data = request.form
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("""INSERT INTO measurement_entries (
        project_id, duct_no, duct_type, duct_size, quantity, remarks
    ) VALUES (?, ?, ?, ?, ?, ?)""", (
        data['project_id'], data['duct_no'], data['duct_type'],
        data['duct_size'], data['quantity'], data['remarks']
    ))
    conn.commit()
    conn.close()
    flash("Duct entry added", "success")
    return redirect(url_for('dashboard'))

# ---------- GET DUCT ENTRIES API ----------
@app.route('/api/ducts/<int:project_id>')
def get_ducts(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("""SELECT id, duct_no, duct_type, duct_size, quantity, remarks
                 FROM measurement_entries WHERE project_id = ?""", (project_id,))
    ducts = c.fetchall()
    conn.close()
    keys = ['id', 'duct_no', 'duct_type', 'duct_size', 'quantity', 'remarks']
    return [dict(zip(keys, row)) for row in ducts]

# ---------- UPLOAD DESIGN DRAWING ----------
@app.route('/upload_drawing/<int:project_id>', methods=['POST'])
def upload_drawing(project_id):
    if 'drawing' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('dashboard'))

    file = request.files['drawing']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('dashboard'))

    filename = secure_filename(file.filename)
    path = os.path.join('uploads', filename)
    file.save(path)

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET file_path = ? WHERE id = ?", (path, project_id))
    conn.commit()
    conn.close()
    flash("Drawing uploaded", "success")
    return redirect(url_for('dashboard'))

# ---------- SUBMIT FOR APPROVAL ----------
@app.route('/submit_for_approval/<int:project_id>')
def submit_for_approval(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Under Review' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("Project submitted for approval", "success")
    return redirect(url_for('dashboard'))

# ---------- APPROVE PROJECT ----------
@app.route('/approve_project/<int:project_id>')
def approve_project(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Approved' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("Project approved and moved to production", "success")
    return redirect(url_for('dashboard'))

# ---------- EXPORT PROJECT SUMMARY PDF ----------
@app.route('/export_project_pdf/<int:project_id>')
def export_project_pdf(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = c.fetchone()
    conn.close()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle("Project Summary")
    pdf.drawString(100, 800, f"Project Summary for ID: {project_id}")
    pdf.drawString(100, 780, f"Vendor ID: {project[2]}")
    pdf.drawString(100, 760, f"GST: {project[3]}")
    pdf.drawString(100, 740, f"Address: {project[4]}")
    pdf.drawString(100, 720, f"Start Date: {project[6]}")
    pdf.drawString(100, 700, f"End Date: {project[7]}")
    pdf.drawString(100, 680, f"Location: {project[8]}")
    pdf.drawString(100, 660, f"Incharge: {project[9]}")
    pdf.drawString(100, 640, f"Status: {project[12]}")
    pdf.drawString(100, 600, "Director Signature: ___________________")
    pdf.drawString(100, 580, "Project Manager Signature: ____________")
    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"project_{project_id}_summary.pdf", mimetype='application/pdf')

# ---------- PRODUCTION DASHBOARD ----------
@app.route('/production')
def production():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM production")
    data = c.fetchall()
    conn.close()
    return render_template('production.html', production=data)

# ---------- UPDATE PRODUCTION PHASE ----------
@app.route('/update_phase/<int:prod_id>', methods=['POST'])
def update_phase(prod_id):
    phase = request.form['phase']
    progress = float(request.form['progress'])

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute(f"UPDATE production SET {phase} = ? WHERE id = ?", (progress, prod_id))
    conn.commit()

    # Recalculate overall progress
    c.execute("SELECT area_sqm, sheet_cutting, plasma_fabrication, boxing_assembly, quality_checking, dispatch FROM production WHERE id = ?", (prod_id,))
    row = c.fetchone()
    area, sc, pf, ba, qc, dp = row

    phase1 = (sc / area) * 100 if area else 0
    phase2 = (pf / area) * 100 if area else 0
    phase3 = (ba / area) * 100 if area else 0
    phase4 = qc  # Already in %
    phase5 = dp  # Already in %

    overall = round((phase1 + phase2 + phase3 + phase4 + phase5) / 5, 2)
    c.execute("UPDATE production SET overall_progress = ? WHERE id = ?", (overall, prod_id))
    conn.commit()
    conn.close()

    flash("Progress updated", "success")
    return redirect(url_for('production'))

# ---------- SHOW PHASE BREAKDOWN ----------
@app.route('/progress_breakdown/<int:prod_id>')
def progress_breakdown(prod_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM production WHERE id = ?", (prod_id,))
    row = c.fetchone()
    conn.close()

    data = {
        'Sheet Cutting': row[3],
        'Plasma & Fabrication': row[4],
        'Boxing & Assembly': row[5],
        'Quality Checking': row[6],
        'Dispatch': row[7],
        'Overall': row[8]
    }
    return render_template('progress_breakdown.html', data=data)

# ---------- PRODUCTION SUMMARY ----------
@app.route('/production_summary')
def production_summary():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("""
        SELECT p.project_id, pj.enquiry_id, pj.location, pr.client_name, pr.company_name,
               pr.engineer_name, pr.phone, pr.project_location, p.area_sqm,
               p.sheet_cutting, p.plasma_fabrication, p.boxing_assembly, 
               p.quality_checking, p.dispatch, p.overall_progress
        FROM production p
        JOIN projects pj ON pj.id = p.project_id
        JOIN measurement_sheet pr ON pr.project_id = p.project_id
    """)
    summary_data = c.fetchall()
    conn.close()
    return render_template('production_summary.html', summary=summary_data)

# ---------- EXPORT PRODUCTION SUMMARY TO EXCEL ----------
@app.route('/export_summary_excel')
def export_summary_excel():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    df = pd.read_sql_query("""
        SELECT pj.enquiry_id AS Enquiry_ID, pj.location AS Location, pr.client_name AS Client,
               pr.company_name AS Company, p.area_sqm AS Area, 
               p.sheet_cutting, p.plasma_fabrication, p.boxing_assembly,
               p.quality_checking, p.dispatch, p.overall_progress
        FROM production p
        JOIN projects pj ON pj.id = p.project_id
        JOIN measurement_sheet pr ON pr.project_id = p.project_id
    """, conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Production Summary')
    writer.close()
    output.seek(0)
    return send_file(output, download_name="Production_Summary.xlsx", as_attachment=True)

# ---------- EXPORT PRODUCTION SUMMARY TO PDF ----------
@app.route('/export_summary_pdf')
def export_summary_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("""
        SELECT pj.enquiry_id, pj.location, pr.client_name, pr.company_name, p.area_sqm,
               p.sheet_cutting, p.plasma_fabrication, p.boxing_assembly, 
               p.quality_checking, p.dispatch, p.overall_progress
        FROM production p
        JOIN projects pj ON pj.id = p.project_id
        JOIN measurement_sheet pr ON pr.project_id = p.project_id
    """)
    data = c.fetchall()
    conn.close()

    output = BytesIO()
    p = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 14)
    p.drawString(180, height - 40, "Production Summary Report")
    y = height - 70
    p.setFont("Helvetica", 10)
    for row in data:
        line = f"ID: {row[0]} | Loc: {row[1]} | Client: {row[2]} | Area: {row[4]} sqm | Progress: {row[-1]}%"
        p.drawString(30, y, line)
        y -= 15
        if y < 100:
            p.showPage()
            y = height - 40

    # Signatures
    p.line(60, 80, 220, 80)
    p.drawString(80, 65, "Director Signature")

    p.line(330, 80, 490, 80)
    p.drawString(350, 65, "Project Manager Signature")

    p.showPage()
    p.save()
    output.seek(0)
    return send_file(output, download_name="Production_Summary.pdf", as_attachment=True)

# ---------- DATABASE INITIALIZATION WITH DUMMY DATA ----------
def seed_dummy_data():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Dummy employees
    c.execute("INSERT OR IGNORE INTO employees (name, email, password) VALUES (?, ?, ?)",
              ("John Doe", "john@example.com", generate_password_hash("1234")))
    
    # Dummy vendors
    c.execute("INSERT OR IGNORE INTO vendors (name, gst, address) VALUES (?, ?, ?)",
              ("ABC Supplies", "27ABCDE1234F2Z5", "Chennai"))

    # Dummy project
    c.execute("INSERT OR IGNORE INTO projects (id, enquiry_id, vendor_id, location) VALUES (?, ?, ?, ?)",
              ("proj001", "ENQ-001", 1, "Bangalore"))

    # Dummy measurement sheet
    c.execute("INSERT OR IGNORE INTO measurement_sheet (project_id, client_name, company_name, engineer_name, phone, project_location) VALUES (?, ?, ?, ?, ?, ?)",
              ("proj001", "Client A", "Company A", "Er. Kumar", "9999999999", "Bangalore Site"))
    # Dummy production entry
    c.execute("INSERT OR IGNORE INTO production (project_id, area_sqm, sheet_cutting, plasma_fabrication, boxing_assembly, quality_checking, dispatch, overall_progress) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              ("proj001", 250, 0, 0, 0, 0, 0, 0))

    conn.commit()
    conn.close()
# ---------- APP STARTUP ----------
if __name__ == '__main__':
    # Ensure database exists
    if not os.path.exists('erp.db'):
        init_db()
        seed_dummy_data()
    else:
        # Optional reseed each time
        seed_dummy_data()
    app.run(debug=True)
