from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import uuid
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = 'secretkey'

# ---------- DB SETUP ----------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT
                )''')

    # Create vendors table
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor_id TEXT,
                    name TEXT,
                    category TEXT,
                    email TEXT,
                    phone TEXT,
                    address TEXT,
                    status TEXT,
                    rating INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )''')

    conn.commit()
    conn.close()

init_db()
# ---------- HOME ----------
@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (uname, pwd))
        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = uname
            flash("Login successful", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('login'))

    return render_template("login.html")

# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (uname, pwd))
            conn.commit()
            flash("Registration successful", "success")
            return redirect(url_for('login'))
        except:
            flash("Username already exists", "danger")
        finally:
            conn.close()

    return render_template("register.html")

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html")
    # ---------- VENDOR LIST ----------
@app.route('/vendors')
def vendors():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM vendors ORDER BY id DESC")
    vendors = c.fetchall()
    conn.close()
    return render_template("vendors.html", vendors=vendors)

# ---------- ADD VENDOR ----------
@app.route('/add_vendor', methods=['POST'])
def add_vendor():
    if 'user' not in session:
        return redirect(url_for('login'))

    vendor_id = "VDR-" + str(uuid.uuid4())[:8]
    name = request.form['name']
    category = request.form['category']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    status = request.form['status']
    rating = request.form.get('rating', 0)
    created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''INSERT INTO vendors 
        (vendor_id, name, category, email, phone, address, status, rating, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (vendor_id, name, category, email, phone, address, status, rating, created, created))
    conn.commit()
    conn.close()

    flash("Vendor added successfully!", "success")
    return redirect(url_for('vendors'))
    # ---------- VIEW VENDOR (AJAX) ----------
@app.route('/view_vendor/<int:id>')
def view_vendor(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM vendors WHERE id=?", (id,))
    vendor = c.fetchone()
    conn.close()

    return vendor  # JSON sent via fetch (in JS popup)

# ---------- EDIT VENDOR ----------
@app.route('/edit_vendor/<int:id>', methods=['POST'])
def edit_vendor(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    category = request.form['category']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    status = request.form['status']
    rating = request.form.get('rating', 0)
    updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''UPDATE vendors SET
                    name=?, category=?, email=?, phone=?,
                    address=?, status=?, rating=?, updated_at=?
                 WHERE id=?''',
              (name, category, email, phone, address, status, rating, updated, id))
    conn.commit()
    conn.close()

    flash("Vendor updated successfully!", "info")
    return redirect(url_for('vendors'))

# ---------- DELETE VENDOR ----------
@app.route('/delete_vendor/<int:id>', methods=['POST'])
def delete_vendor(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM vendors WHERE id=?", (id,))
    conn.commit()
    conn.close()

    flash("Vendor deleted.", "warning")
    return redirect(url_for('vendors'))
    # ---------- EXPORT CSV ----------
@app.route('/export_vendors_csv')
def export_vendors_csv():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM vendors")
    data = c.fetchall()
    conn.close()

    output = BytesIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Vendor ID', 'Name', 'Category', 'Email', 'Phone', 'Address', 'Status', 'Rating', 'Created', 'Updated'])
    writer.writerows(data)
    output.seek(0)

    return send_file(output, mimetype='text/csv', download_name='vendors.csv', as_attachment=True)

# ---------- EXPORT EXCEL ----------
@app.route('/export_vendors_excel')
def export_vendors_excel():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendors')
    output.seek(0)

    return send_file(output, download_name='vendors.xlsx', as_attachment=True)

# ---------- EXPORT PDF ----------
@app.route('/export_vendors_pdf')
def export_vendors_pdf():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT vendor_id, name, category, email, phone, status FROM vendors")
    data = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 50, "Vendor List")

    p.setFont("Helvetica", 10)
    y = height - 80
    for row in data:
        line = " | ".join(str(col) for col in row)
        p.drawString(50, y, line)
        y -= 18
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name='vendors.pdf', as_attachment=True)
    # ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True)
