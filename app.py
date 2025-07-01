from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'vanes_secret_key'

DATABASE = 'database.db'

# ----------- Initialize Database -----------
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Users table for login/register
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    # Vendors table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            tag TEXT NOT NULL DEFAULT 'pending',
            notes TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.before_first_request
def setup():
    init_db()

# ----------- Helper: Login Required Decorator -----------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ----------- User Registration -----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        if not all([name, email, password, confirm_password, role]):
            flash("All fields are required.", "danger")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect(DATABASE)
            conn.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                         (name, email, hashed_password, role))
            conn.commit()
            flash("Registered successfully! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
            return redirect(url_for('register'))
        finally:
            conn.close()
    return render_template('register.html')

# ----------- User Login -----------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password_input = request.form.get('password')

        conn = sqlite3.connect(DATABASE)
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user[3], password_input):
            session['user'] = user[1]   # name
            session['role'] = user[4]
            flash(f"Welcome, {user[1]}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

# ----------- Dashboard -----------
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=session.get('user'))

# ----------- Logout -----------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

# ----------- Vendor Management Routes -----------

@app.route('/vendors')
@login_required
def vendors():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    vendors = conn.execute('SELECT * FROM vendors ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('vendors.html', vendors=vendors)

@app.route('/vendors/<int:id>')
@login_required
def get_vendor(id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    vendor = conn.execute('SELECT * FROM vendors WHERE id = ?', (id,)).fetchone()
    conn.close()
    if vendor:
        return jsonify(dict(vendor))
    else:
        return jsonify({"error": "Vendor not found"}), 404

@app.route('/vendors/add', methods=['POST'])
@login_required
def add_vendor():
    data = request.form
    name = data.get('name')
    company = data.get('company')
    email = data.get('email')
    phone = data.get('phone')
    tag = data.get('tag') or 'pending'
    notes = data.get('notes')
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not all([name, company, email, phone]):
        flash("Please fill all mandatory fields (Name, Company, Email, Phone).", "danger")
        return redirect(url_for('vendors'))

    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute('''
            INSERT INTO vendors (name, company, email, phone, tag, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, company, email, phone, tag, notes, created_at))
        conn.commit()
        flash("Vendor added successfully!", "success")
    except Exception as e:
        flash(f"Error adding vendor: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('vendors'))

@app.route('/vendors/edit', methods=['POST'])
@login_required
def edit_vendor():
    data = request.form
    vid = data.get('id')
    name = data.get('name')
    company = data.get('company')
    email = data.get('email')
    phone = data.get('phone')
    tag = data.get('tag')
    notes = data.get('notes')

    if not all([vid, name, company, email, phone]):
        flash("Missing data to update vendor.", "danger")
        return redirect(url_for('vendors'))

    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute('''
            UPDATE vendors SET name=?, company=?, email=?, phone=?, tag=?, notes=?
            WHERE id=?
        ''', (name, company, email, phone, tag, notes, vid))
        conn.commit()
        flash("Vendor updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating vendor: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('vendors'))

@app.route('/vendors/delete', methods=['POST'])
@login_required
def delete_vendor():
    vid = request.form.get('id')
    if not vid:
        flash("Vendor ID missing for deletion.", "danger")
        return redirect(url_for('vendors'))

    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute('DELETE FROM vendors WHERE id = ?', (vid,))
        conn.commit()
        flash("Vendor deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting vendor: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('vendors'))

@app.route('/vendors/tag', methods=['POST'])
@login_required
def update_tag():
    vid = request.form.get('id')
    new_tag = request.form.get('tag')
    if not vid or not new_tag:
        flash("Vendor ID or new tag missing.", "danger")
        return redirect(url_for('vendors'))

    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute('UPDATE vendors SET tag = ? WHERE id = ?', (new_tag, vid))
        conn.commit()
        flash("Vendor tag updated!", "success")
    except Exception as e:
        flash(f"Error updating tag: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('vendors'))

# ----------- Vendor Export Routes -----------

def fetch_all_vendors():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    vendors = conn.execute('SELECT * FROM vendors ORDER BY id DESC').fetchall()
    conn.close()
    return [dict(v) for v in vendors]

@app.route('/vendors/export/csv')
@login_required
def export_csv():
    vendors = fetch_all_vendors()
    df = pd.DataFrame(vendors)
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='vendors.csv')

@app.route('/vendors/export/excel')
@login_required
def export_excel():
    vendors = fetch_all_vendors()
    df = pd.DataFrame(vendors)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendors')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='vendors.xlsx')

@app.route('/vendors/export/pdf')
@login_required
def export_pdf():
    vendors = fetch_all_vendors()
    output = BytesIO()
    p = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, height - 50, "Vendors List")
    p.setFont("Helvetica", 10)

    y = height - 80
    row_height = 18
    for v in vendors:
        text = f"{v['id']:3} | {v['name'][:15]:15} | {v['company'][:15]:15} | {v['email'][:20]:20} | {v['phone'][:12]:12} | {v['tag']}"
        p.drawString(40, y, text)
        y -= row_height
        if y < 50:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 10)

    p.save()
    output.seek(0)
    return send_file(output, mimetype='application/pdf', as_attachment=True, download_name='vendors.pdf')


if __name__ == '__main__':
    app.run(debug=True)
