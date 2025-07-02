from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import os
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# --- Initialize DB ---
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')

    # Vendors table
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id TEXT NOT NULL,
        name TEXT NOT NULL,
        company TEXT,
        email TEXT,
        phone TEXT,
        address TEXT,
        gst TEXT,
        pan TEXT,
        bank TEXT,
        acc_no TEXT,
        ifsc TEXT,
        created_at TEXT
    )''')

    conn.commit()
    conn.close()

# Ensure DB initialized
init_db()
# ----------- Routes: Login/Register -----------

@app.route('/', methods=['GET'])
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password_input = request.form['password']

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password_input):
            session['user'] = user[1]  # name
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            conn.commit()
            flash('Registration successful! You can now login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists. Try logging in.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])
    # ----------- Vendor Table Setup -----------

def create_vendor_table():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id TEXT UNIQUE,
        name TEXT,
        email TEXT,
        phone TEXT,
        company TEXT,
        gst TEXT,
        address TEXT,
        services TEXT,
        rating INTEGER,
        joined_on TEXT
    )''')
    conn.commit()
    conn.close()

create_vendor_table()

# ----------- Helper: Generate Vendor ID -----------

def generate_vendor_id():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM vendors")
    count = c.fetchone()[0] + 1
    conn.close()
    return f"VND-{1000 + count}"

# ----------- Routes: Vendor Management -----------

@app.route('/vendors')
def vendors():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM vendors")
    vendors = c.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors)

@app.route('/add_vendor', methods=['POST'])
def add_vendor():
    try:
        name = request.form['name']
        company = request.form['company']
        email = request.form['email']
        phone = request.form['phone']
        gst = request.form['gst']
        address = request.form['address']
        category = request.form['category']
        rating = request.form['rating']
        status = request.form['status']

        # Generate unique vendor ID
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vendors")
        count = cursor.fetchone()[0]
        vendor_id = f"VEND{count + 1:04d}"

        cursor.execute('''INSERT INTO vendors 
            (vendor_id, name, company, email, phone, gst, address, category, rating, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (vendor_id, name, company, email, phone, gst, address, category, rating, status))

        conn.commit()
        conn.close()
        flash('Vendor added successfully!', 'success')
    except Exception as e:
        print("Error adding vendor:", e)
        flash('Failed to add vendor', 'danger')

    return redirect('/vendors')

@app.route('/edit_vendor/<int:id>', methods=['POST'])
def edit_vendor(id):
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    company = request.form['company']
    gst = request.form['gst']
    address = request.form['address']
    services = request.form['services']
    rating = request.form['rating']

    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute('''UPDATE vendors SET 
        name=?, email=?, phone=?, company=?, gst=?, address=?, services=?, rating=?
        WHERE id=?''',
        (name, email, phone, company, gst, address, services, rating, id))
    conn.commit()
    conn.close()
    flash("Vendor updated successfully!", "info")
    return redirect(url_for('vendors'))

@app.route('/delete_vendor/<int:id>')
def delete_vendor(id):
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("DELETE FROM vendors WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Vendor deleted!", "danger")
    return redirect(url_for('vendors'))
    # ------------------ EXPORT VENDORS ------------------

@app.route('/export_vendor_csv')
def export_vendor_csv():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()
    csv_data = df.to_csv(index=False)
    return send_file(BytesIO(csv_data.encode()), download_name="vendors.csv", as_attachment=True, mimetype='text/csv')

@app.route('/export_vendor_excel')
def export_vendor_excel():
    conn = sqlite3.connect('erp.db')
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendors')
    output.seek(0)
    return send_file(output, download_name="vendors.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/export_vendor_pdf')
def export_vendor_pdf():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM vendors")
    vendors = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, y, "Vendor Report")
    y -= 40
    p.setFont("Helvetica", 10)

    headers = ['ID', 'Vendor ID', 'Name', 'Email', 'Phone', 'Company', 'GST', 'Address', 'Services', 'Rating', 'Joined On']
    for header in headers:
        p.drawString(40 + headers.index(header)*50, y, header)
    y -= 20

    for row in vendors:
        for i, item in enumerate(row):
            p.drawString(40 + i*50, y, str(item))
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 40

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="vendors.pdf", as_attachment=True, mimetype='application/pdf')
    # ------------------ MAIN ------------------

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
