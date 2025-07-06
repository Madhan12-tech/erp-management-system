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

    # 🆕 Project Enquiry
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_enquiry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            enquiry_id TEXT,
            client_name TEXT,
            company_name TEXT,
            site_engineer TEXT,
            mobile_number TEXT,
            location TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')

    # Project Registration
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_registration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client_name TEXT,
            company_name TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')

    # Measurement Sheet
    c.execute('''
        CREATE TABLE IF NOT EXISTS measurement_sheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client_name TEXT,
            company_name TEXT,
            site_engineer TEXT,
            mobile TEXT,
            location TEXT,
            area_sqm REAL DEFAULT 0
        )
    ''')

    # Measurement Entries
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

    # Production Status
    c.execute('''
        CREATE TABLE IF NOT EXISTS production_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            sheet_cutting_progress REAL,
            plasma_fab_progress REAL,
            boxing_assembly_progress REAL,
            quality_check_progress REAL,
            dispatch_progress REAL,
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

# Run DB initializer on startup
init_db()

# ---------- INSERT DUMMY DATA ----------



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

@app.route("/projects_page")
def projects_page():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''
        SELECT p.*, v.name 
        FROM projects p 
        LEFT JOIN vendors v ON p.vendor_id = v.id
    ''')
    projects = c.fetchall()

    c.execute("SELECT id, name FROM vendors")  # <-- for dropdown
    vendors = c.fetchall()

    conn.close()
    return render_template("projects.html", projects=projects, vendors=vendors)

# ---------- REGISTER EMPLOYEE ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        conn = sqlite3.connect("erp.db")
        c = conn.cursor()
        c.execute("INSERT INTO employees (first_name, last_name, email, username, password, role) VALUES (?, ?, ?, ?, ?, ?)",
                  (first_name, last_name, email, username, password, role))
        conn.commit()
        conn.close()
        flash("Employee registered successfully!", "success")
        return redirect(url_for("login"))
    return render_template("employee_register.html")

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
        c.execute("""
            SELECT p.*, v.name AS vendor_name
            FROM projects p
            LEFT JOIN vendors v ON p.vendor_id = v.id
            ORDER BY p.id DESC
        """)
        projects = c.fetchall()

        c.execute("SELECT id, name, gst, address FROM vendors")
        vendors = c.fetchall()
    except Exception as e:
        print("Dashboard error:", e)
        projects = []
        vendors = []

    conn.close()
    return render_template('dashboard.html', name=session.get('name', 'User'), projects=projects, vendors=vendors)

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
    c.execute("SELECT id, name, gst, address FROM vendors")  # ✅ fixed gst column name
    data = c.fetchall()
    conn.close()
    return {'vendors': data}


# ---------- ADD PROJECT ----------
@app.route('/add_project', methods=['POST'])
def add_project():
    try:
        data = {
            'vendor_id': request.form.get('vendor_id'),
            'gst': request.form.get('gst'),
            'address': request.form.get('address'),
            'quotation_ro': request.form.get('quotation_ro'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'location': request.form.get('location'),
            'incharge': request.form.get('incharge'),
            'notes': request.form.get('notes')
        }

        drawing = request.files.get('drawing')
        drawing_path = ''
        if drawing and drawing.filename:
            filename = secure_filename(drawing.filename)
            drawing_path = os.path.join('static/uploads', filename)
            drawing.save(drawing_path)

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("""
            INSERT INTO projects (
              vendor_id, gst_number, address, quotation_ro,
              start_date, end_date, location, incharge, notes, file_path, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['vendor_id'], data['gst'], data['address'], data['quotation_ro'],
            data['start_date'], data['end_date'], data['location'],
            data['incharge'], data['notes'], drawing_path, 'Design Process'
        ))
        conn.commit()
        conn.close()
        flash("Project added successfully!", "success")
    except Exception as e:
        print("Error in /add_project:", e)
        flash("Failed to add project.", "error")
    return redirect(url_for('projects_page'))

@app.route("/start_preparation", methods=["POST"])
def start_preparation():
    project_id = request.form["project_id"]
    client_name = request.form["client_name"]
    location = request.form["location"]
    site_engineer = request.form["site_engineer"]
    mobile = request.form["mobile"]

    # Save to measurement_sheet
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("""
        INSERT INTO measurement_sheet (project_id, client_name, location, site_engineer, mobile)
        VALUES (?, ?, ?, ?, ?)
    """, (project_id, client_name, location, site_engineer, mobile))
    conn.commit()
    conn.close()

    flash("Preparation phase saved! Proceed with duct entry.", "success")
    return redirect(url_for('duct_entry', project_id=project_id))


@app.route('/duct_entry/<int:project_id>')
def duct_entry(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Fetch measurement sheet details
    c.execute("SELECT client_name, location, site_engineer, mobile FROM measurement_sheet WHERE project_id = ?", (project_id,))
    project_details = c.fetchone()

    # Fetch existing duct entries
    c.execute("SELECT * FROM measurement_entries WHERE project_id = ?", (project_id,))
    duct_entries = c.fetchall()

    conn.close()

    return render_template('duct_entry.html', project_id=project_id, project_details=project_details, duct_entries=duct_entries)

@app.route('/add_duct_entry', methods=['POST'])
def add_duct_entry():
    project_id = request.form['project_id']
    duct_no = request.form['duct_no']
    duct_type = request.form['duct_type']
    duct_size = request.form['duct_size']
    quantity = request.form['quantity']
    remarks = request.form['remarks']

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("""
        INSERT INTO measurement_entries (project_id, duct_no, duct_type, duct_size, quantity, remarks)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (project_id, duct_no, duct_type, duct_size, quantity, remarks))
    conn.commit()
    conn.close()

    flash("Duct entry added successfully.", "success")
    return redirect(url_for('duct_entry', project_id=project_id))

@app.route('/delete_duct/<int:entry_id>/<int:project_id>')
def delete_duct(entry_id, project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("DELETE FROM measurement_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

    flash("Duct entry deleted.", "info")
    return redirect(url_for('duct_entry', project_id=project_id))

@app.route('/submit_duct/<int:project_id>')
def submit_duct(project_id):
    flash("Duct entry submitted successfully! Proceed to Completion phase.", "success")
    return redirect(url_for('projects_page'))

@app.route('/mark_completion/<int:project_id>', methods=['POST'])
def mark_completion(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Completion Done' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    flash("✅ Phase 2: Design marked as completed.", "success")
    return redirect(url_for('projects_page'))


@app.route('/submit_for_approval/<int:project_id>', methods=['POST'])
def submit_for_approval_final(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Submitted for Approval' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    flash("📤 Phase 3: Design submitted for approval.", "info")
    return redirect(url_for('projects_page'))




@app.route('/under_review/<int:project_id>', methods=['POST'])
def under_review(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Under Review' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("🔍 Phase 4: Design moved to Under Review.", "info")
    return redirect(url_for('projects_page'))

@app.route('/approve_project/<int:project_id>', methods=['POST'])
def approve_project(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Get area from measurement sheet to pass to production_status
    c.execute("SELECT area_sqm FROM measurement_sheet WHERE project_id = ?", (project_id,))
    area = c.fetchone()
    total_area = area[0] if area else 0

    # Insert into production_status
    c.execute('''
        INSERT OR IGNORE INTO production_status (project_id, sheet_cutting_progress, plasma_fab_progress, 
        boxing_assembly_progress, quality_check_progress, dispatch_progress)
        VALUES (?, 0, 0, 0, 0, 0)
    ''', (project_id,))
    
    c.execute("UPDATE projects SET status = 'Approved' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("✅ Phase 5: Project approved and sent to Production.", "success")
    return redirect(url_for('projects_page'))

@app.route('/reject_to_preparation/<int:project_id>', methods=['POST'])
def reject_to_preparation(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status = 'Preparation' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("⚠️ Review failed. Sent back to Preparation phase.", "warning")
    return redirect(url_for('projects_page'))

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


# ---------- APPROVE PROJECT ----------


# ---------- EXPORT PROJECT SUMMARY PDF ----------
@app.route("/export_pdf/<int:project_id>")
def export_pdf(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("""
        SELECT ms.client_name, ms.company_name, ms.site_engineer, ms.location,
               ms.area_sqm, pr.sheet_cutting, pr.plasma_fabrication, pr.boxing_assembly,
               pr.quality_checking, pr.dispatch
        FROM measurement_sheet ms
        JOIN production pr ON pr.project_id = ms.project_id
        WHERE ms.project_id = ?
    """, (project_id,))
    
    row = c.fetchone()
    conn.close()

    if row:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.drawString(50, 800, f"Project ID: {project_id}")
        pdf.drawString(50, 780, f"Client: {row[0]}, Company: {row[1]}")
        pdf.drawString(50, 760, f"Site Engineer: {row[2]}, Location: {row[3]}")
        pdf.drawString(50, 740, f"Area: {row[4]} sqm")
        pdf.drawString(50, 700, f"Sheet Cutting: {row[5]}%")
        pdf.drawString(50, 680, f"Plasma & Fabrication: {row[6]}%")
        pdf.drawString(50, 660, f"Boxing & Assembly: {row[7]}%")
        pdf.drawString(50, 640, f"Quality Checking: {row[8]}%")
        pdf.drawString(50, 620, f"Dispatch: {row[9]}%")
        pdf.showPage()
        pdf.save()
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"production_{project_id}.pdf", mimetype='application/pdf')
    else:
        flash("No data found.")
        return redirect(url_for('production'))
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

@app.route('/update_production/<int:project_id>', methods=['POST'])
def update_production(project_id):
    sheet_cutting = request.form.get('sheet_cutting', type=float)
    plasma_fabrication = request.form.get('plasma_fabrication', type=float)
    boxing_assembly = request.form.get('boxing_assembly', type=float)
    quality_checking = request.form.get('quality_checking', type=float)
    dispatch = request.form.get('dispatch', type=float)

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("""
        UPDATE production SET
            sheet_cutting = ?, plasma_fabrication = ?, boxing_assembly = ?,
            quality_checking = ?, dispatch = ?
        WHERE project_id = ?
    """, (sheet_cutting, plasma_fabrication, boxing_assembly, quality_checking, dispatch, project_id))
    conn.commit()
    conn.close()
    
    flash("Production updated successfully!", "success")
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

    # Corrected query: removed pr.enquiry_id and used valid columns
    c.execute("""
        SELECT 
            p.id AS project_id,
            pr.project_id,
            pr.location,
            pr.client_name,
            pr.company_name,
            m.area_sqm,
            s.sheet_cutting_progress,
            s.plasma_fab_progress,
            s.boxing_assembly_progress,
            s.quality_check_progress,
            s.dispatch_progress
        FROM projects p
        JOIN project_enquiry pr ON pr.project_id = p.id
        JOIN measurement_sheet m ON m.project_id = p.id
        JOIN production_status s ON s.project_id = p.id
    """)

    rows = c.fetchall()
    conn.close()

    summary_data = []
    for row in rows:
        project = {
            'project_id': row[0],
            'enquiry_id': row[1],  # this now holds pr.project_id
            'location': row[2],
            'client_name': row[3],
            'company_name': row[4],
            'area_sqm': row[5],
            'sheet_cutting': row[6],
            'plasma_fab': row[7],
            'boxing_assembly': row[8],
            'quality_check': row[9],
            'dispatch': row[10],
            'overall': round((row[6] + row[7] + row[8] + row[9] + row[10]) / 5, 2)
        }
        summary_data.append(project)

    return render_template('production_summary.html', summary_data=summary_data)
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

    # Insert dummy vendors
    vendors = [
        ('ABC Constructions', 'GSTTN1234A1Z5', 'Chennai, Tamil Nadu'),
        ('Skyline Infra', 'GSTMH5678B2X6', 'Mumbai, Maharashtra'),
        ('GreenBuild Ltd', 'GSTKA9012C3Y7', 'Bangalore, Karnataka')
    ]
    for name, gst, address in vendors:
        c.execute("INSERT OR IGNORE INTO vendors (name, gst_number, address) VALUES (?, ?, ?)", (name, gst, address))

    # Insert dummy employees
    employees = [
        ('John Doe', 'john.doe@example.com', 'password123'),
        ('Priya Sharma', 'priya.sharma@example.com', 'securepass'),
        ('Arun Kumar', 'arun.kumar@example.com', 'adminpass')
    ]
    for name, email, password in employees:
        c.execute("INSERT OR IGNORE INTO employees (name, email, password) VALUES (?, ?, ?)", (name, email, password))

    # Optional: Insert a dummy project to test dropdowns/project_id pattern
    c.execute("INSERT OR IGNORE INTO projects (project_id, client_name, vendor_name, quotation_ro, start_date, end_date, location, source_drawing, gst_number, address, project_incharge, notes, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
        ("VE/TN/2526/E001", "ABC Constructions", "ABC Constructions", "RO1234", "2025-07-05", "2025-07-31", "Chennai Site", "", "GSTTN1234A1Z5", "Chennai, Tamil Nadu", "John Doe", "Test notes", "Preparation"))


    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    seed_dummy_data()
    app.run(debug=True)
