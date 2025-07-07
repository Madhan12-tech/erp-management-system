from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, os
import uuid

app = Flask(__name__)
app.secret_key = 'secretkey'

# --- DB Connection ---
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- Initialize DB with admin user ---
def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Users Table
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        role TEXT,
        contact TEXT,
        email TEXT UNIQUE,
        password TEXT
    )''')
    cur.execute("INSERT OR IGNORE INTO users (name, role, contact, email, password) VALUES (?, ?, ?, ?, ?)", 
                ("Admin User", "Admin", "9999999999", "admin@ducting.com", "admin123"))

    # Vendors Table
    cur.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        gst TEXT,
        address TEXT,
        bank_name TEXT,
        account_number TEXT,
        ifsc TEXT
    )''')

    # Vendor Contacts Table
    cur.execute('''CREATE TABLE IF NOT EXISTS vendor_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER,
        name TEXT,
        phone TEXT,
        email TEXT,
        FOREIGN KEY(vendor_id) REFERENCES vendors(id)
    )''')

    conn.commit()
    conn.close()

# --- Create Project & Duct Tables ---
def create_project_tables():
    conn = get_db()
    cur = conn.cursor()

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
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS ducts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            type TEXT,
            length REAL,
            width REAL,
            height REAL,
            quantity INTEGER,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')

    conn.commit()
    conn.close()

# ✅ Call table creation and DB initialization at startup
create_project_tables()
init_db()
# --- Login Route ---
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
            flash("Invalid email or password!", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

# --- Logout ---
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# --- Dashboard ---
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

# --- Projects Placeholder ---



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

@app.route('/api/ducts/<int:project_id>')
def api_ducts(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ducts WHERE project_id = ?", (project_id,))
    ducts = [dict(row) for row in cur.fetchall()]
    return ducts

@app.route('/delete_duct/<int:id>', methods=['POST'])
def delete_duct(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM ducts WHERE id = ?", (id,))
    conn.commit()
    return '', 200

@app.route('/submit_sheet/<int:project_id>', methods=['POST'])
def submit_sheet(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET status = 'submitted' WHERE id = ?", (project_id,))
    conn.commit()
    return '', 200

@app.route('/set_status/<int:project_id>/<status>', methods=['POST'])
def set_status(project_id, status):
    allowed_statuses = ['under_review', 'preparation']
    if status not in allowed_statuses:
        return 'Invalid status', 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET status = ? WHERE id = ?", (status, project_id))
    conn.commit()
    return '', 200

@app.route('/approve_project/<int:project_id>', methods=['POST'])
def approve_project(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET status = 'approved' WHERE id = ?", (project_id,))
    conn.commit()
    return '', 200



# --- Employee Registration Placeholder ---
@app.route('/employee_registration')
def employee_registration():
    return "<h2>Employee Registration Coming Soon...</h2>"

# --- Vendor Registration Form ---
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

        # Insert vendor
        cur.execute("INSERT INTO vendors (name, gst, address, bank_name, account_number, ifsc) VALUES (?, ?, ?, ?, ?, ?)",
                    (vendor_name, gst, address, bank_name, account_number, ifsc))
        vendor_id = cur.lastrowid

        # Insert contacts
        for contact in contacts:
            cur.execute("INSERT INTO vendor_contacts (vendor_id, name, phone, email) VALUES (?, ?, ?, ?)",
                        (vendor_id, contact['name'], contact['phone'], contact['email']))

        conn.commit()
        flash("Vendor registered successfully!", "success")
        return redirect(url_for('vendor_registration'))

    return render_template('vendor_registration.html')

# --- Production Placeholder ---
@app.route('/production')
def production():
    return "<h2>Production Module Coming Soon...</h2>"

# --- Summary Placeholder ---
@app.route('/summary')
def summary():
    return "<h2>Summary Coming Soon...</h2>"


@app.route('/add_project', methods=['POST'])
def add_project():
    vendor_id = request.form['vendor_id']
    quotation_ro = request.form['quotation_ro']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    location = request.form['location']
    incharge = request.form['incharge']
    notes = request.form['notes']

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO projects (vendor_id, quotation_ro, start_date, end_date, location, incharge, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (vendor_id, quotation_ro, start_date, end_date, location, incharge, notes))
    conn.commit()
    flash("Project added successfully!", "success")
    return redirect(url_for('projects'))

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
        INSERT INTO projects (vendor_id, quotation_ro, start_date, end_date, location, incharge, notes, file_name, enquiry_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (vendor_id, quotation_ro, start_date, end_date, location, incharge, notes, file_name, enquiry_id))

    conn.commit()
    conn.close()
    flash("✅ Project added successfully!", "success")
    return redirect(url_for('projects'))


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
@app.route('/projects')
def projects():
    # Generate a unique enquiry ID for the Add Project popup
    enquiry_id = str(uuid.uuid4())[:8].upper()  # e.g. "A1B2C3D4"

    # existing code to fetch projects and vendors
    projects = get_all_projects()  
    vendors = get_all_vendors()    

    return render_template('projects.html', projects=projects, vendors=vendors, enquiry_id=enquiry_id)

@app.route('/export_excel/<int:project_id>')
def export_excel(project_id):
    import pandas as pd
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM ducts WHERE project_id = ?", conn, params=(project_id,))
    output_path = f"duct_project_{project_id}.xlsx"
    df.to_excel(output_path, index=False)

    from flask import send_file
    return send_file(output_path, as_attachment=True)

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)
