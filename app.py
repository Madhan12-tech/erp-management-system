from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, os, uuid
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'secretkey'

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# -------------------- DB Initialization --------------------
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')

    # Vendors
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        gst_no TEXT,
        address TEXT,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        bank_name TEXT,
        bank_account TEXT,
        bank_ifsc TEXT
    )''')

    # Employees
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        designation TEXT,
        email TEXT,
        phone TEXT
    )''')

    # Projects
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enquiry_id TEXT UNIQUE,
        client TEXT,
        quotation_ro TEXT,
        start_date TEXT,
        end_date TEXT,
        location TEXT,
        source_drawing TEXT,
        gst_no TEXT,
        address TEXT,
        project_incharge TEXT,
        notes TEXT,
        design_status TEXT DEFAULT 'preparation',
        production_status TEXT DEFAULT NULL
    )''')

# Measurement Sheets
    c.execute('''CREATE TABLE IF NOT EXISTS measurement_sheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        duct_no TEXT,
        duct_type TEXT,
        duct_size TEXT,
        quantity INTEGER,
        remarks TEXT,
        created_at TEXT
    )''')

    # Production Table
    c.execute('''CREATE TABLE IF NOT EXISTS production (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        production_id TEXT UNIQUE,
        task TEXT,
        status TEXT,
        materials TEXT,
        assigned_on TEXT,
        notes TEXT
    )''')

    # Dummy admin login if not exists
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', 'admin123'))

    conn.commit()
    conn.close()

init_db()
# -------------------- Auth Routes --------------------

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (uname, pwd))
        user = c.fetchone()
        conn.close()
        if user:
            session['user'] = uname
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (uname, pwd))
            conn.commit()
            flash("User registered!", "success")
            return redirect(url_for('login'))
        except:
            flash("Username already exists", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html")
    # -------------------- Vendor Management --------------------

@app.route('/vendor_register', methods=['GET', 'POST'])
def vendor_register():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        gst_no = request.form['gst_no']
        address = request.form['address']
        contact_person = request.form['contact_person']
        phone = request.form['phone']
        email = request.form['email']
        bank_name = request.form['bank_name']
        bank_account = request.form['bank_account']
        bank_ifsc = request.form['bank_ifsc']

        c.execute('''INSERT INTO vendors 
            (name, gst_no, address, contact_person, phone, email, bank_name, bank_account, bank_ifsc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (name, gst_no, address, contact_person, phone, email, bank_name, bank_account, bank_ifsc))
        conn.commit()
        flash("Vendor added successfully!", "success")

    c.execute("SELECT * FROM vendors ORDER BY id DESC")
    vendors = c.fetchall()
    conn.close()
    return render_template("vendors.html", vendors=vendors)

@app.route('/vendor_edit/<int:id>', methods=['GET', 'POST'])
def vendor_edit(id):
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        gst_no = request.form['gst_no']
        address = request.form['address']
        contact_person = request.form['contact_person']
        phone = request.form['phone']
        email = request.form['email']
        bank_name = request.form['bank_name']
        bank_account = request.form['bank_account']
        bank_ifsc = request.form['bank_ifsc']

        c.execute('''UPDATE vendors SET 
            name=?, gst_no=?, address=?, contact_person=?, phone=?, email=?, 
            bank_name=?, bank_account=?, bank_ifsc=?
            WHERE id=?''',
            (name, gst_no, address, contact_person, phone, email, 
             bank_name, bank_account, bank_ifsc, id))
        conn.commit()
        flash("Vendor updated!", "success")
        conn.close()
        return redirect(url_for('vendor_register'))

    c.execute("SELECT * FROM vendors WHERE id=?", (id,))
    vendor = c.fetchone()
    c.execute("SELECT * FROM vendors ORDER BY id DESC")
    vendors = c.fetchall()
    conn.close()
    return render_template("vendors.html", vendors=vendors, vendor=vendor, edit=True)

@app.route('/vendor_delete/<int:id>')
def vendor_delete(id):
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("DELETE FROM vendors WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Vendor deleted", "info")
    return redirect(url_for('vendor_register'))
    # -------------------- Employee Management --------------------

@app.route('/employee_register', methods=['GET', 'POST'])
def employee_register():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']

        c.execute("INSERT INTO employees (name, designation, email, phone) VALUES (?, ?, ?, ?)",
                  (name, designation, email, phone))
        conn.commit()
        flash("Employee added successfully!", "success")

    c.execute("SELECT * FROM employees ORDER BY id DESC")
    employees = c.fetchall()
    conn.close()
    return render_template("employees.html", employees=employees)

@app.route('/employee_edit/<int:id>', methods=['GET', 'POST'])
def employee_edit(id):
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']

        c.execute('''UPDATE employees SET name=?, designation=?, email=?, phone=? WHERE id=?''',
                  (name, designation, email, phone, id))
        conn.commit()
        flash("Employee updated successfully!", "success")
        conn.close()
        return redirect(url_for('employee_register'))

    c.execute("SELECT * FROM employees WHERE id=?", (id,))
    emp = c.fetchone()
    c.execute("SELECT * FROM employees ORDER BY id DESC")
    employees = c.fetchall()
    conn.close()
    return render_template("employees.html", employees=employees, edit=True, emp=emp)

@app.route('/employee_delete/<int:id>')
def employee_delete(id):
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("DELETE FROM employees WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Employee deleted", "info")
    return redirect(url_for('employee_register'))
    # -------------------- Project Management --------------------

# Generate Enquiry ID like VE/TN/2025/E001
def generate_unique_enquiry_id():
    year = datetime.now().year
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM projects WHERE enquiry_id LIKE ?", (f"VE/TN/{year}/E%",))
    count = c.fetchone()[0] + 1
    conn.close()
    return f"VE/TN/{year}/E{str(count).zfill(3)}"

@app.route('/projects')
def projects():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    c.execute("SELECT name, gst_no, address FROM vendors ORDER BY name")
    vendors = [dict(name=row[0], gst=row[1], address=row[2]) for row in c.fetchall()]

    c.execute("SELECT name FROM employees ORDER BY name")
    employees = [row[0] for row in c.fetchall()]

    c.execute("SELECT * FROM projects ORDER BY id DESC")
    projects_raw = c.fetchall()

    projects = []
    for p in projects_raw:
        projects.append({
            'id': p[0],
            'enquiry_id': p[1],
            'client': p[2],
            'quotation_ro': p[3],
            'start_date': p[4],
            'end_date': p[5],
            'location': p[6],
            'source_drawing': p[7],
            'gst_no': p[8],
            'address': p[9],
            'project_incharge': p[10],
            'notes': p[11],
            'design_status': p[12],
            'production_status': p[13]
        })

    conn.close()
    return render_template("projects.html", vendors=vendors, employees=employees, projects=projects)

# -------------------- Measurement Sheet --------------------

@app.route('/measurement/<int:project_id>', methods=['GET', 'POST'])
def measurement_sheet(project_id):
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Get project & client info
    c.execute("SELECT enquiry_id, client, location, start_date, end_date FROM projects WHERE id=?", (project_id,))
    project = c.fetchone()
    if not project:
        flash("Project not found", "danger")
        return redirect(url_for('projects'))

    project_info = {
        'enquiry_id': project[0],
        'client': project[1],
        'location': project[2],
        'start_date': project[3],
        'end_date': project[4]
    }

    # Handle form POST (insert measurement row)
    if request.method == 'POST':
        duct_no = request.form.get('duct_no')
        duct_type = request.form.get('duct_type')
        duct_size = request.form.get('duct_size')
        quantity = request.form.get('quantity')
        remarks = request.form.get('remarks')
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute('''INSERT INTO measurement_sheets (project_id, duct_no, duct_type, duct_size, quantity, remarks, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (project_id, duct_no, duct_type, duct_size, quantity, remarks, created_at))
        conn.commit()
        flash("Entry added to measurement sheet", "success")

    # Get existing sheet entries
    c.execute("SELECT id, duct_no, duct_type, duct_size, quantity, remarks FROM measurement_sheets WHERE project_id=? ORDER BY id DESC", (project_id,))
    sheet_rows = c.fetchall()
    conn.close()

    return render_template('measurement.html', project=project_info, sheet=sheet_rows, project_id=project_id)

@app.route('/measurement_edit/<int:id>/<int:project_id>', methods=['GET', 'POST'])
def measurement_edit(id, project_id):
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        duct_no = request.form.get('duct_no')
        duct_type = request.form.get('duct_type')
        duct_size = request.form.get('duct_size')
        quantity = request.form.get('quantity')
        remarks = request.form.get('remarks')

        c.execute('''UPDATE measurement_sheets SET 
                     duct_no=?, duct_type=?, duct_size=?, quantity=?, remarks=? 
                     WHERE id=?''',
                  (duct_no, duct_type, duct_size, quantity, remarks, id))
        conn.commit()
        conn.close()
        flash("Measurement entry updated", "success")
        return redirect(url_for('measurement_sheet', project_id=project_id))

    # GET request: fetch row
    c.execute("SELECT * FROM measurement_sheets WHERE id=?", (id,))
    row = c.fetchone()
    conn.close()
    return render_template('measurement_edit.html', row=row, project_id=project_id)

@app.route('/measurement_delete/<int:id>/<int:project_id>')
def measurement_delete(id, project_id):
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("DELETE FROM measurement_sheets WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Measurement entry deleted", "info")
    return redirect(url_for('measurement_sheet', project_id=project_id))
@app.route('/add_project', methods=['POST'])
def add_project():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login.'))

    enquiry_id = request.form.get('enquiry_id')
    client = request.form.get('client')
    quotation_ro = request.form.get('quotation_ro')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    location = request.form.get('location')
    gst_no = request.form.get('gst_no')
    address = request.form.get('address')
    project_incharge = request.form.get('project_incharge')
    notes = request.form.get('notes')

    file = request.files.get('source_drawing')
    filename = None
    if file and file.filename != '':
        filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    if not enquiry_id:
        enquiry_id = generate_unique_enquiry_id()

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    c.execute("SELECT * FROM projects WHERE enquiry_id=?", (enquiry_id,))
    if c.fetchone():
        flash("Enquiry ID already exists", "danger")
        conn.close()
        return redirect(url_for('projects'))

    try:
        c.execute('''
            INSERT INTO projects (enquiry_id, client, quotation_ro, start_date, end_date,
                location, source_drawing, gst_no, address, project_incharge, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (enquiry_id, client, quotation_ro, start_date, end_date, location,
              filename, gst_no, address, project_incharge, notes))
        conn.commit()
        flash("Project added successfully", "success")
    except Exception as e:
        print("Error:", e)
        flash("Failed to add project", "danger")
    finally:
        conn.close()

    return redirect(url_for('projects'))
    # -------------------- Design Status Progress --------------------

@app.route('/update_design_status/<int:project_id>/<string:new_status>')
def update_design_status(project_id, new_status):
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login.html'))

    valid_statuses = ['preparation', 'completed', 'submitted', 'under_review', 'approved']
    if new_status not in valid_statuses:
        flash("Invalid status!", "danger")
        return redirect(url_for('projects'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET design_status=? WHERE id=?", (new_status, project_id))
    conn.commit()

    # If approved, initialize production status
    if new_status == 'approved':
        c.execute("UPDATE projects SET production_status = 'pending' WHERE id=?", (project_id,))
        flash("Design approved and sent to production!", "success")
    else:
        flash(f"Design status updated to {new_status.replace('_', ' ').title()}", "info")

    conn.commit()
    conn.close()
    return redirect(url_for('projects'))
    # -------------------- Production Module --------------------

@app.route('/production')
def production():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE design_status='approved'")
    data = c.fetchall()
    conn.close()

    projects = []
    for p in data:
        projects.append({
            'id': p[0],
            'enquiry_id': p[1],
            'client': p[2],
            'location': p[6],
            'start_date': p[4],
            'end_date': p[5],
            'project_incharge': p[10],
            'production_status': p[13] or 'pending'
        })
    return render_template("production.html", projects=projects)

@app.route('/update_production/<int:id>/<string:status>')
def update_production(id, status):
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login.html'))

    valid = ['started', 'completed']
    if status not in valid:
        flash("Invalid production status", "danger")
        return redirect(url_for('production'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET production_status=? WHERE id=?", (status, id))
    conn.commit()
    conn.close()
    flash(f"Production marked as {status}", "success")
    return redirect(url_for('production'))
    # -------------------- Summary Module --------------------

@app.route('/summary')
def summary():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM vendors")
    total_vendors = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM employees")
    total_employees = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM projects")
    total_projects = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM projects WHERE design_status='approved'")
    approved_projects = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM projects WHERE production_status='completed'")
    completed_productions = c.fetchone()[0]

    conn.close()

    return render_template("summary.html", 
        total_vendors=total_vendors,
        total_employees=total_employees,
        total_projects=total_projects,
        approved_projects=approved_projects,
        completed_productions=completed_productions
    )


# -------------------- Final Server Run --------------------
if __name__ == '__main__':
    app.run(debug=True)
