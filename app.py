from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
import sqlite3, os
import uuid
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = 'secretkey'

# ---------- ✅ Database Connection ----------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # ✅ USERS Table (Admin + Dummy)
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        role TEXT,
        contact TEXT,
        email TEXT UNIQUE,
        password TEXT
    )''')
    cur.execute("INSERT OR IGNORE INTO users (email, name, role, contact, password) VALUES (?, ?, ?, ?, ?)", 
                ("admin@ducting.com", "Admin", "Admin", "9999999999", "admin123"))

    # ✅ VENDORS Table
    cur.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        gst TEXT,
        address TEXT,
        bank_name TEXT,
        account_number TEXT,
        ifsc TEXT
    )''')

    # ✅ VENDOR CONTACTS
    cur.execute('''CREATE TABLE IF NOT EXISTS vendor_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER,
        name TEXT,
        phone TEXT,
        email TEXT,
        FOREIGN KEY(vendor_id) REFERENCES vendors(id)
    )''')

    # ✅ PROJECTS TABLE
    cur.execute('''CREATE TABLE IF NOT EXISTS projects (
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
    )''')

    # ✅ DUCTS TABLE
    cur.execute('''CREATE TABLE IF NOT EXISTS ducts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        type TEXT,
        w1 REAL,
        h1 REAL,
        w2 REAL,
        h2 REAL,
        length_radius REAL,
        quantity INTEGER,
        offset_degree TEXT,
        gauge TEXT,
        area REAL,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )''')

    # ✅ PRODUCTION PROGRESS
    cur.execute('''CREATE TABLE IF NOT EXISTS production_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER UNIQUE,
        sheet_cutting_sqm REAL DEFAULT 0,
        plasma_fabrication_sqm REAL DEFAULT 0,
        boxing_assembly_sqm REAL DEFAULT 0,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )''')

    conn.commit()
    conn.close()

# Call on startup
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


# ---------- ✅ Vendor API (Auto-fill GST & Address) ----------
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

# ---------- ✅ Add Project (First Popup) ----------
@app.route('/create_project', methods=['POST'])
def create_project():
    if 'user' not in session:
        return redirect(url_for('login'))

    vendor_id = request.form['vendor_id']
    quotation_ro = request.form['quotation_ro']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    location = request.form['location']
    incharge = request.form['incharge']
    notes = request.form['notes']
    enquiry_id = request.form['enquiry_id']

    file = request.files['file']
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
            location, incharge, notes, file_name, enquiry_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (vendor_id, quotation_ro, start_date, end_date, location, incharge, notes, file_name, enquiry_id))

    conn.commit()
    conn.close()
    flash("✅ Project added successfully!", "success")
    return redirect(url_for('projects'))

# ---------- ✅ Save Measurement Sheet Popup Data ----------
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
    type_ = request.form['type']
    length = request.form['length']
    width = request.form['width']
    height = request.form['height']
    quantity = request.form['quantity']

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO ducts (project_id, type, length, width, height, quantity)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, type_, length, width, height, quantity))
    conn.commit()
    return '', 200

# ---------- ✅ Submit for Review ----------
@app.route('/submit_for_review/<int:project_id>', methods=['POST'])
def submit_for_review(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET status = 'under_review' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('projects'))

# ---------- ✅ Submit Measurement Sheet for Approval ----------
@app.route('/submit_measurement/<int:project_id>', methods=['POST'])
def submit_measurement(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET status = 'submitted for approval' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('projects'))

# ---------- ✅ Approve Project (Final Step) ----------
@app.route('/approve_project/<int:project_id>', methods=['POST'])
def approve_project(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET status = 'approved' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('projects'))

# ---------- ✅ API: Get Duct Entries for Project (Live Table) ----------
@app.route('/api/ducts/<int:project_id>')
def api_ducts(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,))
    ducts = [dict(row) for row in cur.fetchall()]
    return ducts

# ---------- ✅ Delete Duct Entry ----------
@app.route('/delete_duct/<int:id>', methods=['POST'])
def delete_duct(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM ducts WHERE id = ?", (id,))
    conn.commit()
    return '', 200

# ---------- ✅ Export Duct Table to Excel ----------
@app.route('/export_excel/<int:project_id>')
def export_excel(project_id):
    import pandas as pd
    from flask import send_file

    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM ducts WHERE project_id = ?", conn, params=(project_id,))
    output_path = f"duct_project_{project_id}.xlsx"
    df.to_excel(output_path, index=False)
    return send_file(output_path, as_attachment=True)

# ---------- ✅ Open Measurement Entry Page ----------
@app.route('/measurement/<int:project_id>')
def measurement_entry(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cur.fetchone()
    conn.close()
    return render_template('measurement.html', project=project)
@app.route("/production/<int:project_id>")
def production(project_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get project
    cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cur.fetchone()

    # Calculate total sqm from ducts
    cur.execute("SELECT SUM(length * width * quantity) FROM ducts WHERE project_id = ?", (project_id,))
    total_sqm = cur.fetchone()[0] or 0

    # Update total_sqm in projects table
    cur.execute("UPDATE projects SET total_sqm = ? WHERE id = ?", (total_sqm, project_id))

    # Get or create production progress record
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

@app.route("/production_overview")
def production_overview():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()
    return render_template("production_overview.html", projects=projects)

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

@app.route('/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM ducts WHERE project_id = ?", (project_id,))
    cur.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("Project deleted successfully!", "success")
    return redirect(url_for('projects'))



@app.route('/summary')
def summary():
    return "<h2>Summary Coming Soon...</h2>"

def get_all_projects():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT p.*, v.name as vendor_name
        FROM projects p
        LEFT JOIN vendors v ON p.vendor_id = v.id
        ORDER BY p.id DESC
    ''')
    projects = [dict(row) for row in cur.fetchall()]
    conn.close()
    return projects

def get_all_vendors():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM vendors ORDER BY name')
    vendors = [dict(row) for row in cur.fetchall()]
    conn.close()
    return vendors

if __name__ == '__main__':
    app.run(debug=True)



