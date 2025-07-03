import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'secretkey'
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Initialize Database ---
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')

    # Vendors Table
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

    # Employees Table
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        designation TEXT,
        email TEXT,
        phone TEXT,
        username TEXT,
        password TEXT
    )''')

    # Projects Table
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
        design_status TEXT DEFAULT 'preparation'
    )''')

    # Measurement Sheet Table
    c.execute('''CREATE TABLE IF NOT EXISTS measurement_sheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        duct_no TEXT,
        duct_type TEXT,
        length REAL,
        breadth REAL,
        height REAL,
        quantity INTEGER,
        gauge TEXT,
        area REAL,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )''')

    # Production Status Table
    c.execute('''CREATE TABLE IF NOT EXISTS production (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        sheet_cutting REAL,
        plasma_fabrication REAL,
        boxing_assembly REAL,
        quality_check REAL,
        dispatch REAL,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )''')


    conn.commit()
    conn.close()

init_db()

def create_default_admin():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', 'admin123'))
        conn.commit()
        print("✅ Default admin created!")
    conn.close()

create_default_admin()

# Helper: Generate Unique Enquiry ID
def generate_unique_enquiry_id():
    year = datetime.now().year
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM projects WHERE enquiry_id LIKE ?", (f"VE/TN/{year}/E%",))
    count = c.fetchone()[0] + 1
    conn.close()
    return f"VE/TN/{year}/E{str(count).zfill(3)}"
    # --- Login Route ---
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user'] = username
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password", "danger")
    return render_template('login.html')

# --- Register Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash("User registered successfully!", "success")
            return redirect(url_for('login'))
        except:
            flash("Username already exists", "danger")
        finally:
            conn.close()
    return render_template('register.html')

# --- Logout Route ---
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out", "info")
    return redirect(url_for('login'))

# --- Dashboard Route ---
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')
    # --- Vendor Registration + List ---
@app.route('/vendor_register', methods=['GET', 'POST'])
def vendor_register():
    if 'user' not in session:
        flash("Please login first.", "warning")
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

        c.execute('''INSERT INTO vendors (
            name, gst_no, address, contact_person, phone, email,
            bank_name, bank_account, bank_ifsc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
            name, gst_no, address, contact_person, phone, email,
            bank_name, bank_account, bank_ifsc
        ))
        conn.commit()
        flash("Vendor added successfully!", "success")

    c.execute("SELECT * FROM vendors ORDER BY id DESC")
    vendors = c.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors)

# --- Vendor Edit ---
@app.route('/vendor_edit/<int:id>', methods=['GET', 'POST'])
def vendor_edit(id):
    if 'user' not in session:
        flash("Please login first.", "warning")
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
            WHERE id=?''', (
            name, gst_no, address, contact_person, phone, email,
            bank_name, bank_account, bank_ifsc, id
        ))
        conn.commit()
        flash("Vendor updated successfully!", "success")
        return redirect(url_for('vendor_register'))

    c.execute("SELECT * FROM vendors WHERE id=?", (id,))
    vendor = c.fetchone()
    c.execute("SELECT * FROM vendors ORDER BY id DESC")
    vendors = c.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors, edit=True, vendor=vendor)

# --- Vendor Delete ---
@app.route('/vendor_delete/<int:id>')
def vendor_delete(id):
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("DELETE FROM vendors WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Vendor deleted successfully", "info")
    return redirect(url_for('vendor_register'))
    # --- Employee Registration + List ---
@app.route('/employee_register', methods=['GET', 'POST'])
def employee_register():
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        # Save into employees table
        c.execute('''INSERT INTO employees (
            name, designation, email, phone, username, password
        ) VALUES (?, ?, ?, ?, ?, ?)''', (
            name, designation, email, phone, username, password
        ))

        # Optional: Also insert into users table for login
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        except:
            flash("Username already taken for login.", "danger")

        conn.commit()
        flash("Employee added successfully!", "success")

    c.execute("SELECT * FROM employees ORDER BY id DESC")
    employees = c.fetchall()
    conn.close()
    return render_template('employees.html', employees=employees)

# --- Employee Edit ---
@app.route('/employee_edit/<int:id>', methods=['GET', 'POST'])
def employee_edit(id):
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        c.execute('''UPDATE employees SET
            name=?, designation=?, email=?, phone=?, username=?, password=?
            WHERE id=?''', (
            name, designation, email, phone, username, password, id
        ))
        conn.commit()
        flash("Employee updated successfully!", "success")
        return redirect(url_for('employee_register'))

    c.execute("SELECT * FROM employees WHERE id=?", (id,))
    emp = c.fetchone()
    c.execute("SELECT * FROM employees ORDER BY id DESC")
    employees = c.fetchall()
    conn.close()
    return render_template('employees.html', employees=employees, edit=True, emp=emp)

# --- Employee Delete ---
@app.route('/employee_delete/<int:id>')
def employee_delete(id):
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("DELETE FROM employees WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Employee deleted successfully", "info")
    return redirect(url_for('employee_register'))
    # --- Unique Enquiry ID Generator ---
def generate_unique_enquiry_id():
    year = datetime.now().year
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM projects WHERE enquiry_id LIKE ?", (f"VE/TN/{year}/E%",))
    count = c.fetchone()[0] + 1
    conn.close()
    return f"VE/TN/{year}/E{str(count).zfill(3)}"
    # --- Project List + Add Form ---
@app.route('/projects', methods=['GET'])
def projects():
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Get vendors for client dropdown
    c.execute("SELECT name, gst_no, address FROM vendors ORDER BY name")
    vendors = [dict(name=row[0], gst_no=row[1], address=row[2]) for row in c.fetchall()]

    # Get employees for incharge dropdown
    c.execute("SELECT name FROM employees ORDER BY name")
    employees = [row[0] for row in c.fetchall()]

    # Get all projects
    c.execute("SELECT * FROM projects ORDER BY id DESC")
    projects_raw = c.fetchall()
    projects_list = []
    for p in projects_raw:
        projects_list.append({
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
            'design_status': p[12]
        })

    conn.close()
    return render_template('projects.html', vendors=vendors, employees=employees, projects=projects_list)
    # --- Add Project ---
@app.route('/add_project', methods=['POST'])
def add_project():
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

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

    # File upload
    filename = None
    if file and file.filename:
        filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # Auto-generate ID if not present
    if not enquiry_id:
        enquiry_id = generate_unique_enquiry_id()

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE enquiry_id=?", (enquiry_id,))
    if c.fetchone():
        flash("Enquiry ID already exists!", "danger")
        conn.close()
        return redirect(url_for('projects'))

    try:
        c.execute('''
            INSERT INTO projects (
                enquiry_id, client, quotation_ro, start_date, end_date, location,
                source_drawing, gst_no, address, project_incharge, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (enquiry_id, client, quotation_ro, start_date, end_date, location,
             filename, gst_no, address, project_incharge, notes)
        )
        conn.commit()
        flash("Project added successfully!", "success")
    except Exception as e:
        print("Error adding project:", e)
        flash("Error while adding project.", "danger")
    finally:
        conn.close()

    return redirect(url_for('projects'))
    # --- Measurement Sheet Entry Page ---
@app.route('/measurement_sheet/<int:project_id>', methods=['GET', 'POST'])
def measurement_sheet(project_id):
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Get project + client details
    c.execute("SELECT * FROM projects WHERE id=?", (project_id,))
    project = c.fetchone()

    if not project:
        flash("Project not found", "danger")
        return redirect(url_for('projects'))

    # Handle measurement sheet entry POST
    if request.method == 'POST':
        duct_no = request.form['duct_no']
        duct_type = request.form['duct_type']
        length = request.form['length']
        width = request.form['width']
        height = request.form['height']
        gauge = request.form['gauge']
        quantity = request.form['quantity']
        area = float(length) * float(width) * float(quantity) / 1000000  # in sq.meter

        c.execute('''INSERT INTO measurement_sheets (
            project_id, duct_no, duct_type, length, width, height, gauge, quantity, area
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (project_id, duct_no, duct_type, length, width, height, gauge, quantity, area))

        conn.commit()
        flash("Measurement entry added", "success")

    # Fetch all measurements for live table
    c.execute("SELECT * FROM measurement_sheets WHERE project_id=? ORDER BY id DESC", (project_id,))
    sheet_data = c.fetchall()
    conn.close()

    return render_template('measurement_sheet.html', project=project, sheet_data=sheet_data)
    # --- Edit Measurement Entry ---
@app.route('/edit_measurement/<int:id>/<int:project_id>', methods=['GET', 'POST'])
def edit_measurement(id, project_id):
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        duct_no = request.form['duct_no']
        duct_type = request.form['duct_type']
        length = float(request.form['length'])
        width = float(request.form['width'])
        height = float(request.form['height'])
        gauge = request.form['gauge']
        quantity = int(request.form['quantity'])
        area = (length * width * quantity) / 1000000  # convert to sq.meter

        c.execute('''
            UPDATE measurement_sheets SET
            duct_no=?, duct_type=?, length=?, width=?, height=?,
            gauge=?, quantity=?, area=?
            WHERE id=?
        ''', (duct_no, duct_type, length, width, height, gauge, quantity, area, id))

        conn.commit()
        conn.close()
        flash("Measurement entry updated", "success")
        return redirect(url_for('measurement_sheet', project_id=project_id))

    c.execute("SELECT * FROM measurement_sheets WHERE id=?", (id,))
    data = c.fetchone()
    conn.close()
    return render_template('edit_measurement.html', data=data, project_id=project_id)
    # --- Delete Measurement Entry ---
@app.route('/delete_measurement/<int:id>/<int:project_id>')
def delete_measurement(id, project_id):
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("DELETE FROM measurement_sheets WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Entry deleted", "info")
    return redirect(url_for('measurement_sheet', project_id=project_id))
    # --- Final Submit Measurement Sheet (mark as completed design) ---
@app.route('/submit_measurement/<int:project_id>')
def submit_measurement(project_id):
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET design_status='completed' WHERE id=?", (project_id,))
    conn.commit()
    conn.close()
    flash("Design status marked as completed", "success")
    return redirect(url_for('projects'))
    # --- Production View Page ---
@app.route('/production')
def production():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE design_status='completed'")
    projects_raw = c.fetchall()

    project_list = []
    for p in projects_raw:
        c.execute("SELECT * FROM production WHERE project_id=?", (p[0],))
        stage = c.fetchone()

        if stage:
            sheet = stage[2]
            plasma = stage[3]
            boxing = stage[4]
            qc = stage[5]
            dispatch = stage[6]
        else:
            sheet = plasma = boxing = qc = dispatch = 0.0

        total = round((sheet + plasma + boxing + qc + dispatch) / 5, 2)
        project_list.append({
            'id': p[0],
            'enquiry_id': p[1],
            'client': p[2],
            'location': p[6],
            'start_date': p[4],
            'end_date': p[5],
            'project_incharge': p[10],
            'sheet_cutting': sheet,
            'plasma_fabrication': plasma,
            'boxing_assembly': boxing,
            'quality_checking': qc,
            'dispatch': dispatch,
            'total_progress': total
        })

    conn.close()
    return render_template('production.html', projects=project_list)
    # --- Update Production Percentage Stage-by-Stage ---
@app.route('/update_stage/<int:project_id>', methods=['POST'])
def update_stage(project_id):
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    stage_data = {
        'sheet_cutting': float(request.form.get('sheet_cutting', 0)),
        'plasma_fabrication': float(request.form.get('plasma_fabrication', 0)),
        'boxing_assembly': float(request.form.get('boxing_assembly', 0)),
        'quality_checking': float(request.form.get('quality_checking', 0)),
        'dispatch': float(request.form.get('dispatch', 0))
    }

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Check if entry exists
    c.execute("SELECT id FROM production WHERE project_id=?", (project_id,))
    existing = c.fetchone()

    if existing:
        c.execute('''UPDATE production SET
            sheet_cutting=?, plasma_fabrication=?, boxing_assembly=?,
            quality_checking=?, dispatch=?
            WHERE project_id=?''',
            (stage_data['sheet_cutting'], stage_data['plasma_fabrication'],
             stage_data['boxing_assembly'], stage_data['quality_checking'],
             stage_data['dispatch'], project_id))
    else:
        c.execute('''INSERT INTO production (
            project_id, sheet_cutting, plasma_fabrication, boxing_assembly, quality_checking, dispatch
        ) VALUES (?, ?, ?, ?, ?, ?)''',
        (project_id, stage_data['sheet_cutting'], stage_data['plasma_fabrication'],
         stage_data['boxing_assembly'], stage_data['quality_checking'], stage_data['dispatch']))

    conn.commit()
    conn.close()
    flash("Production status updated!", "success")
    return redirect(url_for('production'))
    # --- Summary View ---
@app.route('/summary', methods=['GET', 'POST'])
def summary():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Get project list
    c.execute("SELECT id, enquiry_id FROM projects ORDER BY id DESC")
    projects = c.fetchall()

    selected_project_id = None
    summary_data = {}

    if request.method == 'POST':
        selected_project_id = int(request.form.get('project_id'))

        # --- Project Info ---
        c.execute("SELECT enquiry_id, client, location, start_date, end_date FROM projects WHERE id=?", (selected_project_id,))
        pinfo = c.fetchone()

        # --- Area by Gauge ---
        c.execute('''SELECT gauge, SUM(area) FROM measurement_sheets 
                     WHERE project_id=? GROUP BY gauge''', (selected_project_id,))
        area_by_gauge = c.fetchall()
        gauge_summary = {g[0]: round(g[1], 2) for g in area_by_gauge}

        # --- Production Stages ---
        c.execute("SELECT sheet_cutting, plasma_fabrication, boxing_assembly, quality_checking, dispatch FROM production WHERE project_id=?", (selected_project_id,))
        stages = c.fetchone()
        if stages:
            stage_names = ['Sheet Cutting', 'Plasma Fabrication', 'Boxing & Assembly', 'Quality Checking', 'Dispatch']
            progress_dict = dict(zip(stage_names, stages))
            overall = round(sum(stages)/5, 2)
        else:
            progress_dict = {
                'Sheet Cutting': 0, 'Plasma Fabrication': 0,
                'Boxing & Assembly': 0, 'Quality Checking': 0, 'Dispatch': 0
            }
            overall = 0

        summary_data = {
            'project': {
                'id': pinfo[0], 'client': pinfo[1], 'location': pinfo[2],
                'start_date': pinfo[3], 'end_date': pinfo[4]
            },
            'gauge_summary': gauge_summary,
            'progress': progress_dict,
            'overall_progress': overall
        }

    conn.close()
    return render_template('summary.html', projects=projects, summary=summary_data, selected_project_id=selected_project_id)
if __name__ == '__main__':
    app.run(debug=True)
