from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, os

app = Flask(__name__)
app.secret_key = 'secretkey'

# --- DB Connection ---
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- Initialize DB with admin user ---
def init_db():
    if not os.path.exists("database.db"):
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            contact TEXT,
            email TEXT UNIQUE,
            password TEXT
        )''')
        cur.execute("INSERT INTO users (name, role, contact, email, password) VALUES (?, ?, ?, ?, ?)", 
                    ("Admin User", "Admin", "9999999999", "admin@ducting.com", "admin123"))

        cur.execute('''CREATE TABLE vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    gst TEXT,
    address TEXT,
    bank_name TEXT,
    account_number TEXT,
    ifsc TEXT
)''')

        cur.execute('''CREATE TABLE vendor_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER,
    name TEXT,
    phone TEXT,
    email TEXT,
    FOREIGN KEY(vendor_id) REFERENCES vendors(id)
)''')
        conn.commit()
        conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cur.fetchone()

        if user:
            session['user'] = user['name']
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password!", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

@app.route('/vendor_registration', methods=['GET', 'POST'])
def vendor_registration():
    if request.method == 'POST':
        vendor_name = request.form['vendor_name']
        gst = request.form['gst']
        address = request.form['address']
        bank_name = request.form['bank_name']
        account_number = request.form['account_number']
        ifsc = request.form['ifsc']

        contacts = []
        for i in range(len(request.form.getlist('contact_name'))):
            contacts.append({
                'name': request.form.getlist('contact_name')[i],
                'phone': request.form.getlist('contact_phone')[i],
                'email': request.form.getlist('contact_email')[i],
            })

        conn = get_db()
        cur = conn.cursor()

        # Insert vendor
        cur.execute("INSERT INTO vendors (name, gst, address, bank_name, account_number, ifsc) VALUES (?, ?, ?, ?, ?, ?)",
                    (vendor_name, gst, address, bank_name, account_number, ifsc))
        vendor_id = cur.lastrowid

        # Insert contacts
        for contact in contacts:
            cur.execute("INSERT INTO vendor_contacts (vendor_id, name, phone, email) VALUES (?, ?, ?, ?)",
                        (vendor_id, contact['name'], contact['phone'], contact['email']))

        conn.commit()
        flash("Vendor registered successfully!", "success")
        return redirect(url_for('vendor_registration'))

    return render_template('vendor_registration.html')



if __name__ == '__main__':
    app.run(debug=True)
