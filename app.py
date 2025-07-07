from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import uuid

app = Flask(__name__)
app.secret_key = 'secretkey'

# ---------- DB Connection ----------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------- Initialize DB ----------
def init_db():
    if not os.path.exists("database.db"):
        conn = get_db()
        cur = conn.cursor()

        # USERS TABLE
        cur.execute('''CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            contact TEXT,
            email TEXT UNIQUE,
            password TEXT
        )''')
        cur.execute("INSERT INTO users (name, role, contact, email, password) VALUES (?, ?, ?, ?, ?)",
                    ("Admin User", "Admin", "9999999999", "admin@ducting.com", "admin123"))

        # VENDORS
        cur.execute('''CREATE TABLE vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gst_number TEXT,
            address TEXT,
            account_number TEXT,
            ifsc_code TEXT,
            bank_name TEXT,
            branch TEXT
        )''')

        cur.execute('''CREATE TABLE vendor_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            name TEXT,
            phone TEXT,
            email TEXT,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )''')

        cur.execute('''INSERT INTO vendors (name, gst_number, address, account_number, ifsc_code, bank_name, branch)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    ("CoolAir Pvt Ltd", "GSTIN1234", "Chennai", "1234567890", "IFSC0001", "SBI", "T Nagar"))
        vendor_id = cur.lastrowid
        cur.execute("INSERT INTO vendor_contacts (vendor_id, name, phone, email) VALUES (?, ?, ?, ?)",
                    (vendor_id, "Suresh", "9876543210", "suresh@coolair.com"))

        # PROJECTS
        cur.execute('''CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enquiry_id TEXT,
            vendor TEXT,
            gst TEXT,
            address TEXT,
            quotation TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            incharge TEXT,
            notes TEXT,
            client TEXT,
            site TEXT,
            ducting_area TEXT,
            status TEXT
        )''')

        # DUCTS
        cur.execute('''CREATE TABLE ducts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            type TEXT,
            size TEXT,
            quantity TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )''')

        # PRODUCTION
        cur.execute('''CREATE TABLE production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            sheet_cutting TEXT DEFAULT 'Pending',
            fabrication TEXT DEFAULT 'Pending',
            assembly TEXT DEFAULT 'Pending',
            quality TEXT DEFAULT 'Pending',
            dispatch TEXT DEFAULT 'Pending'
        )''')
        cur.execute("INSERT INTO production (project_name) VALUES (?)", ("Project Alpha",))

        conn.commit()
        conn.close()

init_db()

# ---------- LOGIN ----------
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
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials!", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

# ---------- EMPLOYEE REGISTRATION ----------
@app.route('/employee_registration', methods=['GET', 'POST'])
def employee_registration():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        contact = request.form['contact']
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cur.fetchone():
            flash("Email already exists!", "error")
        else:
            cur.execute("INSERT INTO users (name, role, contact, email, password) VALUES (?, ?, ?, ?, ?)",
                        (name, role, contact, email, password))
            conn.commit()
            flash("Employee registered with login credentials!", "success")

        return redirect(url_for('employee_registration'))

    return render_template('employee_registration.html')

# ---------- VENDOR REGISTRATION ----------
@app.route('/vendor_registration', methods=['GET', 'POST'])
def vendor_registration():
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        gst = request.form['gst_number']
        address = request.form['address']
        acc = request.form['account_number']
        ifsc = request.form['ifsc_code']
        bank = request.form['bank_name']
        branch = request.form['branch']
        names = request.form.getlist('contact_name[]')
        phones = request.form.getlist('contact_phone[]')
        emails = request.form.getlist('contact_email[]')

        cur.execute('''INSERT INTO vendors (name, gst_number, address, account_number, ifsc_code, bank_name, branch)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (name, gst, address, acc, ifsc, bank, branch))
        vendor_id = cur.lastrowid

        for n, p, e in zip(names, phones, emails):
            cur.execute('''INSERT INTO vendor_contacts (vendor_id, name, phone, email)
                           VALUES (?, ?, ?, ?)''',
                        (vendor_id, n, p, e))

        conn.commit()
        flash("Vendor registered successfully!", "success")
        return redirect(url_for('vendor_registration'))

    # View existing vendors
    cur.execute("SELECT * FROM vendors")
    vendors_data = cur.fetchall()
    vendors = []
    for v in vendors_data:
        cur.execute("SELECT name, phone, email FROM vendor_contacts WHERE vendor_id = ?", (v["id"],))
        contacts = cur.fetchall()
        vendors.append({**dict(v), "contacts": contacts})

    conn.close()
    return render_template("vendor_registration.html", vendors=vendors)

# ---------- PROJECTS ----------
@app.route('/projects')
def projects():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects")
    rows = cur.fetchall()
    conn.close()
    return render_template("projects.html", projects=rows)

@app.route('/add_project', methods=['POST'])
def add_project():
    vendor = request.form['vendor']
    gst = request.form['gst']
    address = request.form['address']
    quotation = request.form['quotation']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    location = request.form['location']
    incharge = request.form['incharge']
    notes = request.form['notes']
    enquiry_id = request.form['enquiry_id']

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''INSERT INTO projects 
        (enquiry_id, vendor, gst, address, quotation, start_date, end_date, location, incharge, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (enquiry_id, vendor, gst, address, quotation, start_date, end_date, location, incharge, notes, 'Preparation'))
    conn.commit()
    conn.close()
    flash("Project added successfully", "success")
    return redirect(url_for('projects'))

@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    project_id = request.form['project_id']
    client = request.form['client']
    site = request.form['site']
    ducting_area = request.form['ducting_area']

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''UPDATE projects SET client=?, site=?, ducting_area=?, status=? WHERE id=?''',
                (client, site, ducting_area, "Tag Drawing", project_id))
    conn.commit()
    conn.close()
    flash("Measurement saved!", "success")
    return redirect(url_for('projects'))

@app.route('/add_duct', methods=['POST'])
def add_duct():
    project_id = request.form['project_id']
    type = request.form['type']
    size = request.form['size']
    quantity = request.form['quantity']

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO ducts (project_id, type, size, quantity) VALUES (?, ?, ?, ?)",
                (project_id, type, size, quantity))
    conn.commit()
    conn.close()
    flash("Duct entry added", "success")
    return redirect(url_for('projects'))

@app.route('/api/ducts/<int:project_id>')
def get_ducts(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,))
    rows = cur.fetchall()
    data = [dict(row) for row in rows]
    return {"ducts": data}

# ---------- PRODUCTION ----------
@app.route('/production')
def production():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM production")
    rows = cur.fetchall()
    conn.close()
    return render_template("production.html", productions=rows)

@app.route('/update_stage/<int:project_id>/<string:stage>')
def update_stage(project_id, stage):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE production SET {stage} = 'Completed' WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash(f"{stage.replace('_', ' ').title()} marked completed!", "success")
    return redirect(url_for('production'))

# ---------- SUMMARY ----------
@app.route('/summary')
def summary():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT enquiry_id, vendor, location, status FROM projects")
    project_summary = cur.fetchall()

    cur.execute("""SELECT 
        SUM(sheet_cutting = 'Completed'), 
        SUM(fabrication = 'Completed'),
        SUM(assembly = 'Completed'),
        SUM(quality = 'Completed'),
        SUM(dispatch = 'Completed') 
        FROM production""")
    production_summary = cur.fetchone()

    conn.close()
    return render_template("summary.html", projects=project_summary, production=production_summary)

# ---------- AUTO ID (Optional JS API) ----------
@app.route('/generate_enquiry_id')
def generate_enquiry_id():
    enquiry_id = f"ENQ-{uuid.uuid4().hex[:6].upper()}"
    return {"enquiry_id": enquiry_id}

# ---------- MAIN ----------
if __name__ == '__main__':
    app.run(debug=True)
