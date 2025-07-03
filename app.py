from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret123'

# ---------- DB SETUP ----------
def init_db():
    conn = sqlite3.connect('erp.db')
    c = conn.cursor()

    # Login Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    ''')

    # Vendor Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gst TEXT,
            address TEXT
        )
    ''')

    # Vendor Communication Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendor_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            contact_person TEXT,
            mobile TEXT,
            email TEXT,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )
    ''')

    # Vendor Bank Details Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendor_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            acc_holder TEXT,
            bank_name TEXT,
            acc_number TEXT,
            ifsc TEXT,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )
    ''')

    # Insert dummy user
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', 'admin123'))

    conn.commit()
    conn.close()

# Call DB init
init_db()

# ---------- LOGIN ----------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        conn = sqlite3.connect('erp.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (uname, pwd))
        user = c.fetchone()
        conn.close()
        if user:
            session['user'] = uname
            return redirect('/dashboard')  # ✅ GO TO DASHBOARD INSTEAD
        else:
            flash("Invalid Credentials")
            return redirect('/login')
    return render_template('login.html')
    # ---------- VENDOR REGISTRATION ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        # --- Vendor Details ---
        vendor_name = request.form.get('vendor_name')
        gst = request.form.get('gst')
        address = request.form.get('address')

        # --- Contact Lists (arrays) ---
        contact_names = request.form.getlist('contact_person')
        contact_mobiles = request.form.getlist('mobile')
        contact_emails = request.form.getlist('email')

        # --- Bank Info ---
        acc_holder = request.form.get('acc_holder')
        bank_name = request.form.get('bank_name')
        acc_number = request.form.get('acc_number')
        ifsc = request.form.get('ifsc')

        conn = sqlite3.connect('erp.db')
        c = conn.cursor()

        # Insert into vendors
        c.execute("INSERT INTO vendors (name, gst, address) VALUES (?, ?, ?)",
                  (vendor_name, gst, address))
        vendor_id = c.lastrowid

        # Insert all contact entries
        for i in range(len(contact_names)):
            if contact_names[i]:
                c.execute('''INSERT INTO vendor_contacts
                             (vendor_id, contact_person, mobile, email)
                             VALUES (?, ?, ?, ?)''',
                          (vendor_id, contact_names[i], contact_mobiles[i], contact_emails[i]))

        # Insert bank info
        c.execute('''INSERT INTO vendor_bank
                     (vendor_id, acc_holder, bank_name, acc_number, ifsc)
                     VALUES (?, ?, ?, ?, ?)''',
                  (vendor_id, acc_holder, bank_name, acc_number, ifsc))

        conn.commit()
        conn.close()

        flash("Vendor Registered Successfully!")
        return redirect('/dashboard')

    return render_template('register.html')
    # ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html')


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------- MAIN ----------
if __name__ == '__main__':
    app.run(debug=True)
