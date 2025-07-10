from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from datetime import datetime
from io import BytesIO
import sqlite3
import os
import pandas as pd

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = 'secretkey'

# ✅ Database Connection
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ✅ Initialize DB
def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Projects Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            quotation_ro TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            incharge TEXT,
            notes TEXT,
            file_name TEXT,
            enquiry_id TEXT,
            client_name TEXT,
            site_location TEXT,
            engineer_name TEXT,
            mobile TEXT,
            status TEXT DEFAULT 'new',
            total_sqm REAL DEFAULT 0,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )
    ''')

    # Duct Entries Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS duct_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            duct_no TEXT,
            duct_type TEXT,
            factor TEXT,
            width1 REAL,
            height1 REAL,
            width2 REAL,
            height2 REAL,
            length_or_radius REAL,
            quantity INTEGER,
            degree_or_offset TEXT,
            gauge TEXT,
            area REAL,
            nuts_bolts TEXT,
            cleat TEXT,
            gasket TEXT,
            corner_pieces TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # Vendors Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gst TEXT,
            address TEXT,
            bank_name TEXT,
            account_number TEXT,
            ifsc TEXT
        )
    ''')

    # Vendor Contacts
    cur.execute('''
        CREATE TABLE IF NOT EXISTS vendor_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            name TEXT,
            phone TEXT,
            email TEXT,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )
    ''')

    # Users Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            contact TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    ''')

    # Default admin user
    cur.execute('''
        INSERT OR IGNORE INTO users (email, name, role, contact, password)
        VALUES (?, ?, ?, ?, ?)
    ''', ("admin@ducting.com", "Admin", "Admin", "9999999999", "admin123"))

    # Dummy vendor & contact
    cur.execute('''
        INSERT OR IGNORE INTO vendors (id, name, gst, address, bank_name, account_number, ifsc)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (1, "Dummy Vendor Pvt Ltd", "29ABCDE1234F2Z5", "123 Main Street, City", "Axis Bank", "1234567890", "UTIB0000123"))

    cur.execute('''
        INSERT OR IGNORE INTO vendor_contacts (vendor_id, name, phone, email)
        VALUES (?, ?, ?, ?)
    ''', (1, "Mr. Dummy", "9876543210", "dummy@vendor.com"))

    conn.commit()
    conn.close()


# ✅ Call this once when app starts (or trigger from route)
init_db()
 


# ---------- ✅ Login ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cur.fetchone()

        if user:
            session['user'] = user['name']
            session['role'] = user['role']
            flash("✅ Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("❌ Invalid credentials!", "danger")
            return redirect(url_for('login'))

    return render_template("login.html")


# ---------- ✅ Logout ----------
@app.route('/logout')
def logout():
    session.clear()
    flash("🔒 You have been logged out.", "success")
    return redirect(url_for('login'))


# ---------- ✅ Dashboard ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html", user=session['user'])


# ---------- ✅ Vendor Registration ----------
@app.route('/vendor_registration', methods=['GET', 'POST'])
def vendor_registration():
    if request.method == 'POST':
        vendor_name = request.form['vendor_name']
        gst = request.form['gst']
        address = request.form['address']
        bank_name = request.form['bank_name']
        account_number = request.form['account_number']
        ifsc = request.form['ifsc']

        contacts = []
        for i in range(len(request.form.getlist('contact_name'))):
            contacts.append({
                'name': request.form.getlist('contact_name')[i],
                'phone': request.form.getlist('contact_phone')[i],
                'email': request.form.getlist('contact_email')[i],
            })

        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO vendors (name, gst, address, bank_name, account_number, ifsc) VALUES (?, ?, ?, ?, ?, ?)",
                    (vendor_name, gst, address, bank_name, account_number, ifsc))
        vendor_id = cur.lastrowid

        for contact in contacts:
            cur.execute("INSERT INTO vendor_contacts (vendor_id, name, phone, email) VALUES (?, ?, ?, ?)",
                        (vendor_id, contact['name'], contact['phone'], contact['email']))

        conn.commit()
        flash("✅ Vendor registered successfully!", "success")
        return redirect(url_for('vendor_registration'))

    return render_template('vendor_registration.html')


# ---------- ✅ Vendor Info API (for auto-fill) ----------
@app.route('/api/vendor/<int:vendor_id>')
def get_vendor_info(vendor_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT gst, address FROM vendors WHERE id = ?", (vendor_id,))
    vendor = cur.fetchone()
    if vendor:
        return {'gst': vendor['gst'], 'address': vendor['address']}
    else:
        return {}, 404


# ---------- ✅ Project List Page ----------
@app.route('/projects')
def projects():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM projects ORDER BY id DESC")
    projects = c.fetchall()
    c.execute("SELECT * FROM vendors ORDER BY id DESC")
    vendors = c.fetchall()
    conn.close()

    project = projects[0] if projects else None

    return render_template('projects.html',
                           projects=projects,
                           vendors=vendors,
                           project=project,
                           enquiry_id="ENQ" + str(datetime.now().timestamp()).replace(".", ""))


# ---------- ✅ Create Project (Popup Form) ----------
@app.route('/create_project', methods=['POST'])
def create_project():
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        vendor_id = request.form['vendor_id']
        project_name = request.form['project_name']
        enquiry_no = request.form['enquiry_no']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        incharge = request.form['incharge']
        notes = request.form['notes']
        file = request.files.get('drawing_file')
        file_name = None

        if file and file.filename != '':
            uploads_dir = os.path.join('static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            file_name = file.filename
            file.save(os.path.join(uploads_dir, file_name))

        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO projects (
                vendor_id, quotation_ro, start_date, end_date,
                location, incharge, notes, file_name,
                enquiry_id, client_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vendor_id, '', start_date, end_date,
            '', incharge, notes, file_name,
            enquiry_no, project_name
        ))

        conn.commit()
        conn.close()
        flash("✅ Project added successfully!", "success")
        return redirect(url_for('projects'))

    except Exception as e:
        print("❌ Error while creating project:", e)
        return "Bad Request", 400


# ---------- ✅ Save Measurement Sheet (Popup) ----------
@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    project_id = request.form['project_id']
    client_name = request.form['client_name']
    site_location = request.form['site_location']
    engineer_name = request.form['engineer_name']
    mobile = request.form['mobile']

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        UPDATE projects SET
        client_name = ?, site_location = ?, engineer_name = ?, mobile = ?, status = ?
        WHERE id = ?
    ''', (client_name, site_location, engineer_name, mobile, 'preparation', project_id))
    conn.commit()
    return '', 200


# ---------- ✅ Add Duct Entry ----------
@app.route('/add_duct', methods=['POST'])
def add_duct():
    project_id = request.form['project_id']
    duct_no = request.form['duct_no']
    duct_type = request.form['duct_type']
    factor = request.form['factor']
    width1 = request.form['width1']
    height1 = request.form['height1']
    width2 = request.form['width2']
    height2 = request.form['height2']
    length_or_radius = request.form['length_or_radius']
    quantity = request.form['quantity']
    degree_or_offset = request.form['degree_or_offset']
    gauge = request.form.get('gauge', '')  # ✅ This is the missing field

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO duct_entries (
            project_id, duct_no, duct_type, factor,
            width1, height1, width2, height2,
            length_or_radius, quantity, degree_or_offset, gauge
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        project_id, duct_no, duct_type, factor,
        width1, height1, width2, height2,
        length_or_radius, quantity, degree_or_offset, gauge
    ))

    conn.commit()
    conn.close()
    return redirect(url_for('open_project', project_id=project_id))

# ---------- ✅ Live Duct Table API ----------
@app.route('/api/ducts/<int:project_id>')
def api_ducts(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM duct_entries WHERE project_id = ?", (project_id,))
    entries = [dict(row) for row in cur.fetchall()]
    return jsonify(entries)


# ---------- ✅ Delete Duct Entry ----------
@app.route('/delete_duct/<int:id>', methods=['POST'])
def delete_duct(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM duct_entries WHERE id = ?", (id,))
    conn.commit()
    return '', 200

@app.route('/export_pdf/<int:project_id>')
def export_pdf(project_id):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    from io import BytesIO
    from num2words import num2words
    import os

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # ✅ Fetch project info
    c.execute("""
        SELECT client_name, site_location, engineer_name, mobile, start_date, end_date
        FROM projects WHERE id = ?
    """, (project_id,))
    proj = c.fetchone()
    client_name = proj[0] if proj else "Project"
    site_location = proj[1] if proj else ""
    engineer_name = proj[2] if proj else ""
    mobile = proj[3] if proj else ""
    start_date = proj[4] if proj else ""
    end_date = proj[5] if proj else ""

    # ✅ Company Logo
    logo_path = os.path.join("static", "logo.png")
    if os.path.exists(logo_path):
        p.drawImage(logo_path, 50, height - 80, width=80, preserveAspectRatio=True, mask='auto')

    # ✅ Company Details
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, height - 50, "Vanes Engineering Pvt Ltd")

    p.setFont("Helvetica", 10)
    p.drawString(200, height - 65, "No. 23, Industrial Estate, Chennai, Tamil Nadu - 600058")
    p.drawString(200, height - 78, "Email: info@vanesengineering.com | Phone: +91-98765-43210")

    # ✅ Project Header
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 110, f"Client: {client_name}")
    p.drawString(300, height - 110, f"Site: {site_location}")
    p.drawString(50, height - 125, f"Engineer: {engineer_name}")
    p.drawString(300, height - 125, f"Mobile: {mobile}")
    p.drawString(50, height - 140, f"Duration: {start_date} to {end_date}")

    # ✅ Fetch duct entries
    c.execute("""
        SELECT duct_no, duct_type, width1, height1, quantity, area, weight
        FROM duct_entries WHERE project_id = ?
    """, (project_id,))
    entries = c.fetchall()
    conn.close()

    # ✅ Table Data
    data = [["Duct No", "Type", "Width", "Height", "Qty", "Area", "Weight"]]
    total_qty = total_area = total_weight = 0

    for row in entries:
        w = float(row[2]) if row[2] else 0
        h = float(row[3]) if row[3] else 0
        qty = float(row[4]) if row[4] else 0
        area = float(row[5]) if row[5] else 0
        weight = float(row[6]) if row[6] else 0
        data.append([row[0], row[1], w, h, qty, area, weight])
        total_qty += qty
        total_area += area
        total_weight += weight

    # ✅ Add totals row
    data.append(["", "", "", "Total", total_qty, total_area, total_weight])

    # ✅ Draw table
    table = Table(data, colWidths=[60, 55, 50, 50, 50, 60, 60])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER')
    ]))
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 190 - 25 * len(data))

    # ✅ Total area in words
    area_text = num2words(round(total_area, 2), to='decimal').replace(" point", " point ").capitalize()
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, height - 200 - 25 * len(data), f"Total Area in Words: {area_text} square meters")

    # ✅ Signature lines
    p.setFont("Helvetica", 10)
    p.drawString(50, 80, "Engineer Signature: __________________")
    p.drawString(300, 80, "Client Signature: __________________")

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name=f"{client_name}_duct_sheet.pdf",
                     mimetype='application/pdf')



@app.route('/export_excel/<int:project_id>')
def export_excel(project_id):
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM entries WHERE project_id = ?", conn, params=(project_id,))
    output_path = f"duct_project_{project_id}.xlsx"
    df.to_excel(output_path, index=False)
    return send_file(output_path, as_attachment=True)


# ---------- ✅ Submit Project for Review ----------
@app.route('/submit_for_review/<int:project_id>', methods=['POST'])
def submit_for_review(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET status = 'under_review' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('projects'))


# ---------- ✅ Submit Measurement Sheet for Approval (AJAX) ----------
@app.route('/submit_measurement/<int:project_id>', methods=['POST'])
def submit_measurement(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET status = 'preparation' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return '', 200

# ---------- ✅ Open Project View ----------
@app.route('/project/<int:project_id>')
def open_project(project_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ✅ Fetch selected project
    cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cur.fetchone()

    # ✅ Attach vendor name
    if project:
        cur.execute("SELECT name FROM vendors WHERE id = ?", (project["vendor_id"],))
        vendor = cur.fetchone()
        project = dict(project)
        project["vendor_name"] = vendor["name"] if vendor else ""

    # ✅ All projects for top list
    cur.execute("""
        SELECT projects.*, vendors.name AS vendor_name
        FROM projects
        JOIN vendors ON projects.vendor_id = vendors.id
    """)
    projects = cur.fetchall()

    # ✅ All vendors for dropdown
    cur.execute("SELECT * FROM vendors")
    vendors = cur.fetchall()

    # ✅ Duct entries
    cur.execute("SELECT * FROM duct_entries WHERE project_id = ?", (project_id,))
    entries = cur.fetchall()

    conn.close()

    return render_template(
        "projects.html",
        project=project,
        entries=entries,
        projects=projects,
        vendors=vendors
    )






# ---------- ✅ Approve Project (Final Step) ----------
@app.route('/approve_project/<int:project_id>', methods=['POST'])
def approve_project(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET status = 'approved' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('projects'))



# ---------- ✅ View Production Status ----------
@app.route("/production/<int:project_id>")
def production(project_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ✅ Get project
    cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cur.fetchone()

    # ✅ Calculate total sqm from duct dimensions
    cur.execute("SELECT SUM(length * width * quantity) FROM ducts WHERE project_id = ?", (project_id,))
    total_sqm = cur.fetchone()[0] or 0

    # ✅ Update total_sqm in projects table
    cur.execute("UPDATE projects SET total_sqm = ? WHERE id = ?", (total_sqm, project_id))

    # ✅ Get or create progress record
    cur.execute("SELECT * FROM production_progress WHERE project_id = ?", (project_id,))
    progress = cur.fetchone()
    if not progress:
        cur.execute("INSERT INTO production_progress (project_id) VALUES (?)", (project_id,))
        conn.commit()
        cur.execute("SELECT * FROM production_progress WHERE project_id = ?", (project_id,))
        progress = cur.fetchone()

    conn.commit()
    conn.close()
    return render_template("production.html", project=project, progress=progress)


# ---------- ✅ Update Production Progress ----------
@app.route("/update_production/<int:project_id>", methods=["POST"])
def update_production(project_id):
    sheet_cutting = float(request.form.get("sheet_cutting") or 0)
    plasma_fabrication = float(request.form.get("plasma_fabrication") or 0)
    boxing_assembly = float(request.form.get("boxing_assembly") or 0)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE production_progress
        SET sheet_cutting_sqm = ?, plasma_fabrication_sqm = ?, boxing_assembly_sqm = ?
        WHERE project_id = ?
    """, (sheet_cutting, plasma_fabrication, boxing_assembly, project_id))
    conn.commit()
    conn.close()
    return redirect(url_for('production', project_id=project_id))


# ---------- ✅ View All Projects in Production ----------
@app.route("/production_overview")
def production_overview():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()
    conn.close()
    return render_template("production_overview.html", projects=projects)


# ---------- ✅ Summary Placeholder ----------
@app.route('/summary')
def summary():
    return "<h2>Summary Coming Soon...</h2>"


# ---------- ✅ Submit Full Project and Move to Production ----------
@app.route('/submit_all/<project_id>', methods=['POST'])
def submit_all(project_id):
    conn = get_db()
    cur = conn.cursor()

    # ✅ Mark project as submitted
    cur.execute("UPDATE projects SET status = 'submitted' WHERE id = ?", (project_id,))

    # Optional: Lock duct entries (commented for now)
    # cur.execute("UPDATE duct_entries SET status = 'locked' WHERE project_id = ?", (project_id,))

    conn.commit()
    conn.close()

    flash("✅ Project submitted and moved to production.", "success")
    return redirect(url_for('production', project_id=project_id))


# ---------- ✅ Delete Project ----------
@app.route('/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    conn = get_db()
    cur = conn.cursor()
    
    # Delete related ducts and project
    cur.execute("DELETE FROM duct_entries WHERE project_id = ?", (project_id,))
    cur.execute("DELETE FROM production_progress WHERE project_id = ?", (project_id,))
    cur.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    
    conn.commit()
    conn.close()
    
    flash("🗑️ Project deleted successfully!", "success")
    return redirect(url_for('projects'))



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
