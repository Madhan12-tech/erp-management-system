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

# --- DB Init ---
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
        design_status TEXT DEFAULT 'preparation'
    )''')
    conn.commit()
    conn.close()

init_db()

# --- Helper Functions ---
def generate_unique_enquiry_id():
    year = datetime.now().year
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM projects WHERE enquiry_id LIKE ?", (f"VE/TN/{year}/E%",))
    count = c.fetchone()[0] + 1
    conn.close()
    return f"VE/TN/{year}/E{str(count).zfill(3)}"

# --- Routes ---

# Login
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

# Register new user (optional for admin)
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

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out", "info")
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# Vendor CRUD
@app.route('/vendor_register', methods=['GET', 'POST'])
def vendor_register():
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    if request.method == 'POST':
        # Get form data
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
            (name, gst_no, address, contact_person, phone, email, bank_name, bank_account, bank_ifsc)
        )
        conn.commit()
        flash("Vendor added successfully", "success")
    c.execute("SELECT * FROM vendors ORDER BY id DESC")
    vendors = c.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors)

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
            name=?, gst_no=?, address=?, contact_person=?, phone=?, email=?, bank_name=?, bank_account=?, bank_ifsc=?
            WHERE id=?''',
            (name, gst_no, address, contact_person, phone, email, bank_name, bank_account, bank_ifsc, id)
        )
        conn.commit()
        flash("Vendor updated successfully", "success")
        conn.close()
        return redirect(url_for('vendor_register'))
    c.execute("SELECT * FROM vendors WHERE id=?", (id,))
    vendor = c.fetchone()
    conn.close()
    return render_template('vendors.html', vendor=vendor, edit=True)

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

# Employee CRUD
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
        c.execute("INSERT INTO employees (name, designation, email, phone) VALUES (?, ?, ?, ?)",
                  (name, designation, email, phone))
        conn.commit()
        flash("Employee added successfully", "success")
    c.execute("SELECT * FROM employees ORDER BY id DESC")
    employees = c.fetchall()
    conn.close()
    return render_template('employees.html', employees=employees)

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
        c.execute('''UPDATE employees SET name=?, designation=?, email=?, phone=? WHERE id=?''',
                  (name, designation, email, phone, id))
        conn.commit()
        conn.close()
        flash("Employee updated successfully", "success")
        return redirect(url_for('employee_register'))
    c.execute("SELECT * FROM employees WHERE id=?", (id,))
    emp = c.fetchone()
    c.execute("SELECT * FROM employees ORDER BY id DESC")
    employees = c.fetchall()
    conn.close()
    return render_template('employees.html', employees=employees, edit=True, emp=emp)

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

# Projects
@app.route('/projects', methods=['GET'])
def projects():
    if 'user' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT name, gst_no, address FROM vendors ORDER BY name")
    vendors = [dict(name=row[0], gst_no=row[1], address=row[2]) for row in c.fetchall()]
    c.execute("SELECT name FROM employees ORDER BY name")
    employees = [dict(name=row[0]) for row in c.fetchall()]
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
            'design_status': p[12],
        })
    conn.close()
    return render_template('projects.html', vendors=vendors, employees=employees, projects=projects_list)

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
        flash("Enquiry ID already exists!", "danger")
        conn.close()
        return redirect(url_for('projects'))
    try:
        c.execute('''
            INSERT INTO projects (enquiry_id, client, quotation_ro, start_date, end_date, location,
                source_drawing, gst_no, address, project_incharge, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (enquiry_id, client, quotation_ro, start_date, end_date, location,
             filename, gst_no, address, project_incharge, notes)
        )
        conn.commit()
        flash("Project added successfully!", "success")
    except Exception as e:
        print("Error adding project:", e)
        flash("Error adding project.", "danger")
    finally:
        conn.close()
    return redirect(url_for('projects'))

if __name__ == '__main__':
    app.run(debug=True)
