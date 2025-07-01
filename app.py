# app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ------------------------- Database Setup ----------------------------

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id TEXT,
        name TEXT,
        email TEXT,
        phone TEXT,
        company TEXT,
        address TEXT,
        city TEXT,
        state TEXT,
        country TEXT,
        gst TEXT,
        pan TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ------------------------- Authentication ----------------------------

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

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')
        role = request.form['role']

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for('register'))

        hashed = generate_password_hash(password)
        try:
            conn = sqlite3.connect('database.db')
            conn.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                         (name, email, hashed, role))
            conn.commit()
            conn.close()
            flash("Registration successful", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already registered", "warning")

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))

# ------------------------- Dashboard ----------------------------

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

# ------------------------- Vendor Management ----------------------------

@app.route('/vendors')
def vendors():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    rows = conn.execute("SELECT * FROM vendors").fetchall()
    conn.close()
    return render_template('vendors.html', vendors=rows)

@app.route('/add_vendor', methods=['POST'])
def add_vendor():
    if 'user' not in session:
        return redirect(url_for('login'))

    form = request.form
    conn = sqlite3.connect('database.db')
    count = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0] + 1
    vendor_id = f"VND{str(count).zfill(4)}"
    conn.execute('''INSERT INTO vendors (vendor_id, name, email, phone, company, address, city, state, country, gst, pan)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (vendor_id, form['name'], form['email'], form['phone'], form['company'], form['address'],
                  form['city'], form['state'], form['country'], form['gst'], form['pan']))
    conn.commit()
    conn.close()
    flash("Vendor added successfully", "success")
    return redirect(url_for('vendors'))

@app.route('/delete_vendor/<int:id>')
def delete_vendor(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    conn.execute("DELETE FROM vendors WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Vendor deleted", "info")
    return redirect(url_for('vendors'))

@app.route('/export/vendors/csv')
def export_vendors_csv():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return send_file(output, download_name="vendors.csv", as_attachment=True, mimetype='text/csv')

@app.route('/export/vendors/excel')
def export_vendors_excel():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="vendors.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/export/vendors/pdf')
def export_vendors_pdf():
    conn = sqlite3.connect('database.db')
    data = conn.execute("SELECT * FROM vendors").fetchall()
    conn.close()
    output = BytesIO()
    c = canvas.Canvas(output, pagesize=letter)
    width, height = letter

    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y, "Vendor List")
    c.setFont("Helvetica", 10)
    y -= 30

    for row in data:
        text = f"{row[1]} | {row[2]} | {row[3]} | {row[4]}"
        c.drawString(30, y, text)
        y -= 20
        if y < 40:
            c.showPage()
            y = height - 40

    c.save()
    output.seek(0)
    return send_file(output, download_name="vendors.pdf", as_attachment=True, mimetype='application/pdf')

# ------------------------- Run ----------------------------

if __name__ == '__main__':
    app.run(debug=True)
    
