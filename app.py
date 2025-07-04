from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'secret123'

# ---------------- DATABASE INITIALIZATION ----------------
def init_db():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    # Employees table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            designation TEXT,
            email TEXT,
            phone TEXT,
            username TEXT,
            password TEXT
        )
    ''')

    # Vendors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gst TEXT,
            address TEXT,
            phone TEXT,
            email TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']

        conn = sqlite3.connect('erp.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE username=? AND password=?", (uname, pwd))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    return render_template('login.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


# ---------------- EMPLOYEE REGISTRATION ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        cursor.execute('''
            INSERT INTO employees (name, designation, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, designation, email, phone, username, password))
        conn.commit()
        flash('Employee registered successfully!', 'success')
        return redirect(url_for('register'))

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    conn.close()

    return render_template('register.html', employees=employees)


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for('login'))
    return render_template('dashboard.html')


# ---------------- VENDOR REGISTRATION ----------------
@app.route('/vendors', methods=['GET', 'POST'])
def vendors():
    conn = sqlite3.connect('erp.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        gst = request.form['gst']
        address = request.form['address']
        phone = request.form['phone']
        email = request.form['email']

        cursor.execute('''
            INSERT INTO vendors (name, gst, address, phone, email)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, gst, address, phone, email))
        conn.commit()
        flash('Vendor registered successfully!', 'success')
        return redirect(url_for('vendors'))

    cursor.execute("SELECT * FROM vendors")
    vendors = cursor.fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors)


# ---------------- RUN FLASK ----------------
if __name__ == '__main__':
    app.run(debug=True)
