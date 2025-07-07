from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, os

app = Flask(__name__)
app.secret_key = 'secretkey'

# --- DB Connection ---
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- Initialize DB with admin user ---
def init_db():
    if not os.path.exists("database.db"):
        conn = get_db()
        cur = conn.cursor()

        # Users Table
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

        # Vendors Table
        cur.execute('''CREATE TABLE vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gst TEXT,
            address TEXT,
            bank_name TEXT,
            account_number TEXT,
            ifsc TEXT
        )''')

        # Vendor Contacts Table
        cur.execute('''CREATE TABLE vendor_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            name TEXT,
            phone TEXT,
            email TEXT,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )''')

        # --------- Project + Duct Tables ----------

    # Projects Table
    cur.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enquiry_id TEXT,
        vendor_name TEXT,
        location TEXT,
        status TEXT,
        client_name TEXT,
        site_location TEXT,
        engineer_name TEXT,
        mobile TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Duct Table
    cur.execute('''CREATE TABLE IF NOT EXISTS ducts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        type TEXT,
        length REAL,
        width REAL,
        height REAL,
        quantity INTEGER,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )''')



# Call this once on app start
create_project_tables()

        conn.commit()
        conn.close()

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
@app.route('/projects')
def projects():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects ORDER BY id DESC")
    projects = cur.fetchall()
    return render_template('projects.html', projects=projects)


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

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)
