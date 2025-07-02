from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
from datetime import datetime
import pandas as pd
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# ---------- DATABASE INIT ----------
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Users
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    # Projects
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enquiry_id TEXT,
            client_name TEXT,
            gst_number TEXT,
            address TEXT,
            quotation_ro TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            drawing_file TEXT,
            project_incharge TEXT,
            notes TEXT,
            status TEXT DEFAULT 'preparation'
        )
    ''')

    # Vendors (for client dropdown)
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gst TEXT,
            address TEXT
        )
    ''')

    # Employees (for incharge dropdown)
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    ''')

    conn.commit()
    conn.close()

# Call it once
init_db()

# ---------- HOME REDIRECT ----------
@app.route('/')
def home():
    return redirect(url_for('login'))
    # ---------- LOGIN ----------
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
            flash('Login successful!', 'success')
            return redirect('/dashboard')
        else:
            flash('Invalid username or password.', 'error')
            return redirect('/login')

    return render_template('login.html')

# ---------- REGISTER ----------
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
            flash('Registration successful! Please login.', 'success')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'error')
            return redirect('/register')
        finally:
            conn.close()

    return render_template('register.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect('/login')

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login first.", "error")
        return redirect('/login')
    return render_template('dashboard.html')
    # ---------- PROJECTS PAGE ----------
@app.route('/projects')
def projects():
    if 'user' not in session:
        flash("Please login first.", "error")
        return redirect('/login')

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Get all projects
    c.execute("SELECT * FROM projects")
    projects = [dict(zip([column[0] for column in c.description], row)) for row in c.fetchall()]

    # Get all vendors
    c.execute("SELECT name, gst, address FROM vendors")
    vendors = [dict(name=row[0], gst=row[1], address=row[2]) for row in c.fetchall()]

    # Get all employees
    c.execute("SELECT name FROM employees")
    employees = [dict(name=row[0]) for row in c.fetchall()]

    conn.close()

    today = datetime.today().strftime('%Y-%m-%d')

    return render_template("projects.html", projects=projects, vendors=vendors, employees=employees, today=today)
    # ---------- ADD PROJECT ----------
@app.route('/add_project', methods=['POST'])
def add_project():
    if 'user' not in session:
        flash("Please login first.", "error")
        return redirect('/login')

    client_name = request.form['client_name']
    gst_number = request.form['gst_number']
    address = request.form['address']
    quotation_ro = request.form['quotation_ro']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    location = request.form['location']
    project_incharge = request.form['project_incharge']
    notes = request.form['notes']

    # Upload file
    drawing_file = request.files['drawing_file']
    filename = ""
    if drawing_file and drawing_file.filename != '':
        filename = f"uploads/{drawing_file.filename}"
        os.makedirs("uploads", exist_ok=True)
        drawing_file.save(filename)

    # Generate Enquiry ID like VE/TN/2526/E001
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM projects")
    count = c.fetchone()[0] + 1
    enquiry_id = f"VE/TN/2526/E{str(count).zfill(3)}"

    # Save project
    c.execute('''
        INSERT INTO projects (
            enquiry_id, client_name, gst_number, address,
            quotation_ro, start_date, end_date,
            location, drawing_file, project_incharge, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        enquiry_id, client_name, gst_number, address,
        quotation_ro, start_date, end_date,
        location, filename, project_incharge, notes
    ))

    conn.commit()
    conn.close()

    flash("Project added successfully!", "success")
    return redirect('/projects')
    # ---------- EDIT PROJECT ----------
@app.route('/edit_project/<int:id>', methods=['GET', 'POST'])
def edit_project(id):
    if 'user' not in session:
        flash("Please login first.", "error")
        return redirect('/login')

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    if request.method == 'POST':
        client_name = request.form['client_name']
        gst_number = request.form['gst_number']
        address = request.form['address']
        quotation_ro = request.form['quotation_ro']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        location = request.form['location']
        project_incharge = request.form['project_incharge']
        notes = request.form['notes']

        drawing_file = request.files['drawing_file']
        if drawing_file and drawing_file.filename != '':
            filename = f"uploads/{drawing_file.filename}"
            os.makedirs("uploads", exist_ok=True)
            drawing_file.save(filename)
            c.execute('''
                UPDATE projects SET client_name=?, gst_number=?, address=?, quotation_ro=?, 
                start_date=?, end_date=?, location=?, drawing_file=?, project_incharge=?, notes=? 
                WHERE id=?
            ''', (client_name, gst_number, address, quotation_ro, start_date, end_date,
                  location, filename, project_incharge, notes, id))
        else:
            c.execute('''
                UPDATE projects SET client_name=?, gst_number=?, address=?, quotation_ro=?, 
                start_date=?, end_date=?, location=?, project_incharge=?, notes=? 
                WHERE id=?
            ''', (client_name, gst_number, address, quotation_ro, start_date, end_date,
                  location, project_incharge, notes, id))

        conn.commit()
        conn.close()
        flash("Project updated successfully!", "success")
        return redirect('/projects')

    c.execute("SELECT * FROM projects WHERE id=?", (id,))
    project = c.fetchone()
    conn.close()

    return render_template("edit_project.html", project=project)


# ---------- DELETE PROJECT ----------
@app.route('/delete_project/<int:id>')
def delete_project(id):
    if 'user' not in session:
        flash("Please login first.", "error")
        return redirect('/login')

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("DELETE FROM projects WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Project deleted successfully!", "info")
    return redirect('/projects')
    # ---------- MARK AS COMPLETED ----------
@app.route('/mark_completed/<int:id>')
def mark_completed(id):
    if 'user' not in session:
        flash("Please login first.", "error")
        return redirect('/login')

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status='completed' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Project marked as completed.", "info")
    return redirect('/projects')


# ---------- SUBMIT FOR APPROVAL ----------
@app.route('/submit_for_approval/<int:id>')
def submit_for_approval(id):
    if 'user' not in session:
        flash("Please login first.", "error")
        return redirect('/login')

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status='submitted' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Project submitted for approval.", "info")
    return redirect('/projects')


# ---------- MARK UNDER REVIEW ----------
@app.route('/mark_review/<int:id>')
def mark_review(id):
    if 'user' not in session:
        flash("Please login first.", "error")
        return redirect('/login')

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status='under_review' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Project moved to review stage.", "info")
    return redirect('/projects')


# ---------- APPROVE PROJECT ----------
@app.route('/approve_project/<int:id>')
def approve_project(id):
    if 'user' not in session:
        flash("Please login first.", "error")
        return redirect('/login')

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("UPDATE projects SET status='approved' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Project approved successfully.", "success")
    return redirect(f"/measurement_sheet/{id}")
    # ---------- EXPORT PROJECTS: CSV ----------
@app.route('/export_projects_csv')
def export_projects_csv():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()

    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='projects.csv')


# ---------- EXPORT PROJECTS: EXCEL ----------
@app.route('/export_projects_excel')
def export_projects_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')
    output.seek(0)

    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='projects.xlsx')


# ---------- EXPORT PROJECTS: PDF ----------
@app.route('/export_projects_pdf')
def export_projects_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT enquiry_id, client_name, quotation_ro, start_date, end_date FROM projects")
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Projects List")
    y -= 30

    p.setFont("Helvetica", 10)
    for row in data:
        p.drawString(50, y, f"Enquiry ID: {row[0]}, Client: {row[1]}, Quotation: {row[2]}, Start: {row[3]}, End: {row[4]}")
        y -= 20
        if y < 60:
            p.showPage()
            y = height - 40

    p.save()
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='projects.pdf')
    if __name__ == '__main__':
    app.run(debug=True)
