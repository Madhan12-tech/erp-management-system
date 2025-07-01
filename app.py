from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import io
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = 'vanes_secret_key'

# --------- Database Initialization ---------
def init_db():
    conn = sqlite3.connect('database.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            address TEXT,
            gstin TEXT,
            status TEXT DEFAULT 'Active'
        )
    ''')
    conn.commit()
    conn.close()

# Call init_db once at startup (fixes before_first_request error)
init_db()

# --------- User Registration ---------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        confirm_password = request.form.get('confirm_password')

        if not all([name, email, password, role, confirm_password]):
            flash("All fields are required", "danger")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect('database.db')
            conn.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                         (name, email, hashed_password, role))
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
            return redirect(url_for('register'))
        finally:
            conn.close()
    return render_template('register.html')

# --------- User Login ---------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = sqlite3.connect('database.db')
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user[3], password):
            session['user'] = user[1]
            session['role'] = user[4]
            flash(f"Welcome {user[1]}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')

# --------- Dashboard ---------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

# --------- Logout ---------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))

# --------- Vendor Management ---------
@app.route('/vendors')
def vendors():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    vendors_list = conn.execute("SELECT * FROM vendors").fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors_list)

@app.route('/vendors/add', methods=['POST'])
def add_vendor():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    address = request.form.get('address')
    gstin = request.form.get('gstin')

    conn = sqlite3.connect('database.db')
    try:
        conn.execute(
            "INSERT INTO vendors (name, email, phone, address, gstin) VALUES (?, ?, ?, ?, ?)",
            (name, email, phone, address, gstin)
        )
        conn.commit()
        flash("Vendor added successfully", "success")
    except sqlite3.IntegrityError:
        flash("Vendor email must be unique", "danger")
    finally:
        conn.close()
    return redirect(url_for('vendors'))

@app.route('/vendors/delete/<int:vendor_id>')
def delete_vendor(vendor_id):
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    conn.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
    conn.commit()
    conn.close()
    flash("Vendor deleted", "info")
    return redirect(url_for('vendors'))

# --------- Export Vendors to Excel ---------
@app.route('/vendors/export/excel')
def export_vendors_excel():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    vendors = conn.execute("SELECT id, name, email, phone, address, gstin, status FROM vendors").fetchall()
    conn.close()

    df = pd.DataFrame(vendors, columns=['ID', 'Name', 'Email', 'Phone', 'Address', 'GSTIN', 'Status'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendors')
    output.seek(0)

    return send_file(output, attachment_filename="vendors.xlsx", as_attachment=True)

# --------- Export Vendors to PDF ---------
@app.route('/vendors/export/pdf')
def export_vendors_pdf():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    vendors = conn.execute("SELECT id, name, email, phone, address, gstin, status FROM vendors").fetchall()
    conn.close()

    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Vendor List")
    y -= 30
    c.setFont("Helvetica", 10)

    for v in vendors:
        line = f"{v[0]}. {v[1]} | {v[2]} | {v[3]} | {v[4]} | {v[5]} | {v[6]}"
        c.drawString(40, y, line)
        y -= 20
        if y < 40:
            c.showPage()
            y = height - 40

    c.save()
    output.seek(0)
    return send_file(output, attachment_filename="vendors.pdf", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
