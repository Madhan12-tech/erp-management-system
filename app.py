from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3, os
from datetime import datetime
from flask import jsonify 

app = Flask(__name__)
app.secret_key = 'secret-key'

# -------- INIT DB --------
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT, password TEXT
    )''')

    # Vendors
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_name TEXT,
        gst TEXT,
        address TEXT
    )''')

    # Projects
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enquiry_id TEXT,
        vendor_id INTEGER,
        quotation_ro TEXT,
        start_date TEXT,
        end_date TEXT,
        location TEXT,
        incharge TEXT,
        notes TEXT,
        drawing_file TEXT,
        design_status TEXT DEFAULT 'In Progress',
        approval_status TEXT DEFAULT 'Not Submitted'
    )''')

    # Measurement Sheets
    c.execute('''CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        client_name TEXT,
        company_name TEXT,
        project_location TEXT,
        engineer_name TEXT,
        phone TEXT
    )''')

    # Duct Entries
    c.execute('''CREATE TABLE IF NOT EXISTS ducts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        duct_no TEXT,
        duct_type TEXT,
        duct_size TEXT,
        quantity INTEGER
    )''')

    # Insert dummy user
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', 'admin123'))

    conn.commit()
    conn.close()

# Initialize database on first run
init_db()
# ---------- LOGIN ----------
@app.route('/', methods=['GET', 'POST'])
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
            session['username'] = uname
            return redirect('/dashboard')
        else:
            flash("Invalid login credentials", "danger")
    return render_template('login.html')


# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (uname, pwd))
        conn.commit()
        conn.close()
        flash("Registration successful", "success")
        return redirect('/')
    return render_template('register.html')


# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    return render_template('dashboard.html')


# ---------- VENDORS PAGE ----------
@app.route('/vendors', methods=['GET', 'POST'])
def vendors():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        vendor_name = request.form['vendor_name']
        gst = request.form['gst']
        address = request.form['address']
        c.execute("INSERT INTO vendors (vendor_name, gst, address) VALUES (?, ?, ?)", (vendor_name, gst, address))
        conn.commit()
        flash("Vendor registered successfully", "success")
        return redirect('/vendors')

    c.execute("SELECT * FROM vendors")
    vendors = c.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors)

@app.route('/vendor_registration')
def vendor_registration():
    return render_template('vendor_registration.html')

@app.route('/add_vendor', methods=['POST'])
def add_vendor():
    vendor_name = request.form['vendor_name']
    gst = request.form['gst']
    address = request.form['address']
    # Optional: Save contacts and bank info here
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("INSERT INTO vendors (vendor_name, gst, address) VALUES (?, ?, ?)",
              (vendor_name, gst, address))
    conn.commit()
    conn.close()
    flash("Vendor registered", "success")
    return redirect('/dashboard')



# ---------- FETCH VENDOR INFO (AJAX for autofill) ----------
@app.route('/vendor_info/<int:vendor_id>')
def vendor_info(vendor_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT gst, address FROM vendors WHERE id=?", (vendor_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return jsonify({'gst': result[0], 'address': result[1]})
    return jsonify({})
# ---------- PROJECTS PAGE ----------
@app.route('/projects')
def projects():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM vendors")
    vendors = c.fetchall()

    c.execute("SELECT * FROM projects")
    projects = c.fetchall()

    c.execute("SELECT DISTINCT incharge FROM projects WHERE incharge IS NOT NULL")
    incharges = [row[0] for row in c.fetchall()]
    conn.close()

    return render_template('projects.html', vendors=vendors, projects=projects, incharges=incharges)


# ---------- ADD PROJECT ----------
@app.route('/add_project', methods=['POST'])
def add_project():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Generate Enquiry ID
    c.execute("SELECT COUNT(*) FROM projects")
    count = c.fetchone()[0] + 1
    enquiry_id = f"VE/TN/2526/E{str(count).zfill(3)}"

    vendor_id = request.form['vendor_id']
    quotation_ro = request.form['quotation_ro']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    location = request.form['location']
    incharge = request.form['incharge']
    notes = request.form['notes']
    file = request.files['drawing_file']

    drawing_filename = ""
    if file and file.filename:
        os.makedirs("uploads", exist_ok=True)
        drawing_filename = f"uploads/{enquiry_id}_{file.filename}"
        file.save(drawing_filename)

    c.execute('''INSERT INTO projects (
        enquiry_id, vendor_id, quotation_ro, start_date, end_date,
        location, incharge, notes, drawing_file
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
        enquiry_id, vendor_id, quotation_ro, start_date, end_date,
        location, incharge, notes, drawing_filename
    ))

    conn.commit()
    conn.close()
    return redirect('/projects')


# ---------- ADD MEASUREMENT SHEET ----------
@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    project_id = request.form['project_id']
    client_name = request.form['client_name']
    company_name = request.form['company_name']
    project_location = request.form['project_location']
    engineer_name = request.form['engineer_name']
    phone = request.form['phone']

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''INSERT INTO measurements (
        project_id, client_name, company_name, project_location, engineer_name, phone
    ) VALUES (?, ?, ?, ?, ?, ?)''', (
        project_id, client_name, company_name, project_location, engineer_name, phone
    ))
    conn.commit()
    conn.close()

    return redirect(f'/measurement_sheet/{project_id}')
# ---------- MEASUREMENT SHEET PAGE ----------
@app.route('/measurement_sheet/<int:project_id>')
def measurement_sheet(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    c.execute("SELECT * FROM measurements WHERE project_id=?", (project_id,))
    measurement = c.fetchone()

    c.execute("SELECT * FROM ducts WHERE project_id=?", (project_id,))
    ducts = c.fetchall()

    c.execute("SELECT * FROM projects WHERE id=?", (project_id,))
    project = c.fetchone()

    conn.close()
    return render_template('measurement_sheet.html',
                           project=project,
                           ducts=ducts,
                           measurement=measurement)


# ---------- ADD DUCT ----------
@app.route('/add_duct', methods=['POST'])
def add_duct():
    project_id = request.form['project_id']
    duct_no = request.form['duct_no']
    duct_type = request.form['duct_type']
    duct_size = request.form['duct_size']
    quantity = request.form['quantity']

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''INSERT INTO ducts (
        project_id, duct_no, duct_type, duct_size, quantity
    ) VALUES (?, ?, ?, ?, ?)''', (
        project_id, duct_no, duct_type, duct_size, quantity
    ))
    conn.commit()
    conn.close()

    return redirect(f'/measurement_sheet/{project_id}')


# ---------- DELETE DUCT ----------
@app.route('/delete_duct/<int:duct_id>')
def delete_duct(duct_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT project_id FROM ducts WHERE id=?", (duct_id,))
    project_id = c.fetchone()[0]
    c.execute("DELETE FROM ducts WHERE id=?", (duct_id,))
    conn.commit()
    conn.close()

    return redirect(f'/measurement_sheet/{project_id}')


# ---------- SUBMIT DESIGN ----------
@app.route('/submit_sheet/<int:project_id>')
def submit_sheet(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET design_status='Completed' WHERE id=?", (project_id,))
    conn.commit()
    conn.close()
    flash("Design submitted successfully", "success")
    return redirect('/dashboard')


# ---------- SUBMIT FOR APPROVAL ----------
@app.route('/submit_for_approval/<int:project_id>')
def submit_for_approval(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET approval_status='Submitted' WHERE id=?", (project_id,))
    conn.commit()
    conn.close()
    flash("Submitted for approval", "info")
    return redirect('/projects')


# ---------- APPROVE PROJECT ----------
@app.route('/approve_project/<int:project_id>')
def approve_project(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET approval_status='Approved' WHERE id=?", (project_id,))
    conn.commit()
    conn.close()
    flash("Project approved", "success")
    return redirect('/projects')


# ---------- RETURN TO PREPARATION ----------
@app.route('/return_to_preparation/<int:project_id>')
def return_to_preparation(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET design_status='In Progress', approval_status='Not Submitted' WHERE id=?", (project_id,))
    conn.commit()
    conn.close()
    flash("Returned to preparation", "warning")
    return redirect('/projects')
from flask import jsonify  # Make sure this is imported at the top if using AJAX

# ---------- EXPORT TO CSV ----------
@app.route('/export_csv/<int:project_id>')
def export_csv(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM ducts WHERE project_id=?", (project_id,))
    data = c.fetchall()
    conn.close()

    output = "Duct No,Duct Type,Duct Size,Quantity\n"
    for row in data:
        output += f"{row[2]},{row[3]},{row[4]},{row[5]}\n"

    return send_file(BytesIO(output.encode()), download_name="measurement_sheet.csv", as_attachment=True)


# ---------- EXPORT TO EXCEL ----------
@app.route('/export_excel/<int:project_id>')
def export_excel(project_id):
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT duct_no, duct_type, duct_size, quantity FROM ducts WHERE project_id=?",
                           conn, params=(project_id,))
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Measurement Sheet')
    output.seek(0)
    return send_file(output, download_name="measurement_sheet.xlsx", as_attachment=True)


# ---------- EXPORT TO PDF ----------
@app.route('/export_pdf/<int:project_id>')
def export_pdf(project_id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    c.execute("SELECT * FROM measurements WHERE project_id=?", (project_id,))
    m = c.fetchone()

    c.execute("SELECT * FROM ducts WHERE project_id=?", (project_id,))
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "Measurement Sheet")
    y -= 20
    p.setFont("Helvetica", 10)

    if m:
        p.drawString(40, y, f"Client: {m[2]} | Company: {m[3]}")
        y -= 15
        p.drawString(40, y, f"Location: {m[4]} | Engineer: {m[5]} | Phone: {m[6]}")
        y -= 25

    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, "Duct No")
    p.drawString(140, y, "Type")
    p.drawString(240, y, "Size")
    p.drawString(340, y, "Qty")
    y -= 15
    p.setFont("Helvetica", 10)

    for row in data:
        p.drawString(40, y, row[2])
        p.drawString(140, y, row[3])
        p.drawString(240, y, row[4])
        p.drawString(340, y, str(row[5]))
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="measurement_sheet.pdf", as_attachment=True)


# ---------- RUN FLASK SERVER ----------
if __name__ == '__main__':
    # For local or Render deployment
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
