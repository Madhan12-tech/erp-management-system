from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from io import BytesIO
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime

app = Flask(__name__)
app.secret_key = "vanes_secret_key"

# ----------- DB SETUP -----------
def init_db():
    conn = sqlite3.connect("database.db")
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
        vendor_id TEXT UNIQUE,
        name TEXT,
        email TEXT,
        phone TEXT,
        company TEXT,
        gst_number TEXT,
        address TEXT,
        services TEXT,
        status TEXT,
        created_at TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ----------- AUTO VENDOR ID -----------
def generate_vendor_id():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM vendors")
    count = c.fetchone()[0]
    conn.close()
    return f"VENDOR{1001 + count}"

# ----------- REGISTER -----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form.get("role", "employee")

        if not all([name, email, password]):
            flash("All fields are required!", "danger")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)

        try:
            conn = sqlite3.connect("database.db")
            conn.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                         (name, email, hashed, role))
            conn.commit()
            flash("Registered successfully!", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already exists!", "danger")
        finally:
            conn.close()

    return render_template("register.html")

# ----------- LOGIN -----------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password_input = request.form["password"]

        conn = sqlite3.connect("database.db")
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user[3], password_input):
            session["user"] = user[1]
            session["role"] = user[4]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

# ----------- DASHBOARD -----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"])

# ----------- LOGOUT -----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ----------- VENDORS PAGE -----------
@app.route("/vendors")
def vendors():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    vendors = conn.execute("SELECT * FROM vendors").fetchall()
    conn.close()
    return render_template("vendors.html", vendors=vendors)

# ----------- ADD VENDOR -----------
@app.route("/add_vendor", methods=["POST"])
def add_vendor():
    if "user" not in session:
        return redirect(url_for("login"))

    data = (
        generate_vendor_id(),
        request.form["name"],
        request.form["email"],
        request.form["phone"],
        request.form["company"],
        request.form["gst_number"],
        request.form["address"],
        request.form["services"],
        request.form["status"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    conn = sqlite3.connect("database.db")
    conn.execute('''
        INSERT INTO vendors (vendor_id, name, email, phone, company, gst_number, address, services, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()
    conn.close()

    flash("Vendor added successfully!", "success")
    return redirect(url_for("vendors"))

# ----------- EXPORT VENDORS CSV -----------
@app.route("/export/vendors/csv")
def export_vendors_csv():
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return send_file(output, mimetype="text/csv", as_attachment=True, download_name="vendors.csv")

# ----------- EXPORT VENDORS EXCEL -----------
@app.route("/export/vendors/excel")
def export_vendors_excel():
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Vendors")

    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name="vendors.xlsx")

# ----------- EXPORT VENDORS PDF -----------
@app.route("/export/vendors/pdf")
def export_vendors_pdf():
    conn = sqlite3.connect("database.db")
    vendors = conn.execute("SELECT * FROM vendors").fetchall()
    conn.close()

    output = BytesIO()
    p = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    y = height - 40

    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y, "Vendor List")
    y -= 30

    p.setFont("Helvetica", 10)
    for vendor in vendors:
        line = f"{vendor[1]} | {vendor[2]} | {vendor[3]} | {vendor[4]}"
        p.drawString(30, y, line)
        y -= 20
        if y < 40:
            p.showPage()
            y = height - 40

    p.save()
    output.seek(0)
    return send_file(output, mimetype="application/pdf", as_attachment=True, download_name="vendors.pdf")

# ----------- MAIN RUN -----------
if __name__ == "__main__":
    app.run(debug=True)
