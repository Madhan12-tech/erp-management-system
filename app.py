from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

app = Flask(__name__)
app.secret_key = 'vanes_secret_key'

# -------------------- Database Initialization --------------------
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )''')

    # Vendors table
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        address TEXT,
        gst TEXT,
        company TEXT,
        remarks TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# -------------------- Register --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']
        role = request.form['role']

        if password != confirm:
            flash("Passwords do not match", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        try:
            conn = sqlite3.connect('database.db')
            conn.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                         (name, email, hashed_password, role))
            conn.commit()
            flash("Registered successfully", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists", "danger")
            return redirect(url_for('register'))

    return render_template('login_register.html')

# -------------------- Login --------------------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user'] = user[1]
            session['role'] = user[4]
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('login'))

    return render_template('login_register.html')

# -------------------- Dashboard --------------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

# -------------------- Logout --------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------------------- Vendor Management --------------------
@app.route('/vendors')
def vendors():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    data = conn.execute("SELECT * FROM vendors").fetchall()
    conn.close()
    return render_template('vendors.html', vendors=data)

@app.route('/add_vendor', methods=['POST'])
def add_vendor():
    vendor_id = request.form['vendor_id']
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    gst = request.form['gst']
    company = request.form['company']
    remarks = request.form['remarks']

    conn = sqlite3.connect('database.db')
    conn.execute("INSERT INTO vendors (vendor_id, name, email, phone, address, gst, company, remarks) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (vendor_id, name, email, phone, address, gst, company, remarks))
    conn.commit()
    conn.close()
    return redirect(url_for('vendors'))

@app.route('/delete_vendor/<int:id>')
def delete_vendor(id):
    conn = sqlite3.connect('database.db')
    conn.execute("DELETE FROM vendors WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('vendors'))

# -------------------- Export Functions --------------------
@app.route('/export_vendors_csv')
def export_vendors_csv():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()
    return send_file(BytesIO(df.to_csv(index=False).encode()),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='vendors.csv')

@app.route('/export_vendors_excel')
def export_vendors_excel():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendors')
    output.seek(0)
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True,
                     download_name='vendors.xlsx')

@app.route('/export_vendors_pdf')
def export_vendors_pdf():
    conn = sqlite3.connect('database.db')
    data = conn.execute("SELECT * FROM vendors").fetchall()
    conn.close()
    output = BytesIO()
    p = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica", 12)
    p.drawString(30, y, "Vendor List")
    y -= 30
    for row in data:
        line = f"{row[1]} | {row[2]} | {row[3]} | {row[4]}"
        p.drawString(30, y, line)
        y -= 20
        if y < 40:
            p.showPage()
            y = height - 50
    p.save()
    output.seek(0)
    return send_file(output,
                     mimetype='application/pdf',
                     as_attachment=True,
                     download_name='vendors.pdf')

# -------------------- Run Server --------------------
if __name__ == '__main__':
    app.run(debug=True)
    
