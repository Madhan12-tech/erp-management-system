# Part 1: Imports and DB Setup
from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd
from fpdf import FPDF
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///erp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# -------------------- #
# Database Models
# -------------------- #

# User authentication and role management
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')  # roles: admin or user

# Workforce module tables
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    position = db.Column(db.String(100))
    department = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True)
    join_date = db.Column(db.Date, default=datetime.utcnow)

class CheckIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class WorkLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    action = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Inventory module tables
class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact = db.Column(db.String(100))

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(300))
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))

class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    quantity = db.Column(db.Integer)
    total_price = db.Column(db.Float)
    status = db.Column(db.String(50))
    order_date = db.Column(db.DateTime, default=datetime.utcnow)

# Accounts and Purchase module tables
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(50))  # e.g. Asset, Liability, Expense, Income
    balance = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    amount = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(300))
    type = db.Column(db.String(50))  # e.g. Debit or Credit

# Projects and Sites module tables
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(300))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(50))

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    location = db.Column(db.String(150))
    manager = db.Column(db.String(150))
    status = db.Column(db.String(50))

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    name = db.Column(db.String(150), nullable=False)
    assigned_to = db.Column(db.String(150))
    due_date = db.Column(db.Date)
    status = db.Column(db.String(50))

# Create all tables
with app.app_context():
    db.create_all()
    # Part 2: Authentication Routes
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password, role='user')
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid username or password.')
            return redirect(url_for('login'))
        login_user(user)
        flash('Logged in successfully.')
        return redirect(url_for('employees'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))
    # Part 3: Workforce Module Routes (Employees, Check-ins, Logs)
@app.route('/employees')
@login_required
def employees():
    all_employees = Employee.query.all()
    return render_template('employees.html', employees=all_employees)

@app.route('/employee/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if request.method == 'POST':
        name = request.form.get('name')
        position = request.form.get('position')
        department = request.form.get('department')
        email = request.form.get('email')
        new_emp = Employee(name=name, position=position, department=department, email=email)
        db.session.add(new_emp)
        db.session.commit()
        flash('New employee added.')
        return redirect(url_for('employees'))
    return render_template('add_employee.html')

@app.route('/employee/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_employee(id):
    emp = Employee.query.get_or_404(id)
    if request.method == 'POST':
        emp.name = request.form.get('name')
        emp.position = request.form.get('position')
        emp.department = request.form.get('department')
        emp.email = request.form.get('email')
        db.session.commit()
        flash('Employee details updated.')
        return redirect(url_for('employees'))
    return render_template('edit_employee.html', employee=emp)

@app.route('/employee/delete/<int:id>')
@login_required
def delete_employee(id):
    emp = Employee.query.get_or_404(id)
    db.session.delete(emp)
    db.session.commit()
    flash('Employee deleted.')
    return redirect(url_for('employees'))

# Check-in routes
@app.route('/checkins')
@login_required
def checkins():
    all_checkins = CheckIn.query.all()
    return render_template('checkins.html', checkins=all_checkins)

@app.route('/checkin/add', methods=['POST'])
@login_required
def add_checkin():
    emp_id = request.form.get('employee_id')
    new_checkin = CheckIn(employee_id=emp_id)
    db.session.add(new_checkin)
    db.session.commit()
    flash('Check-in recorded.')
    return redirect(url_for('checkins'))

@app.route('/checkin/delete/<int:id>')
@login_required
def delete_checkin(id):
    ci = CheckIn.query.get_or_404(id)
    db.session.delete(ci)
    db.session.commit()
    flash('Check-in entry deleted.')
    return redirect(url_for('checkins'))

# Work log routes
@app.route('/logs')
@login_required
def logs():
    all_logs = WorkLog.query.all()
    return render_template('logs.html', logs=all_logs)

@app.route('/log/add', methods=['POST'])
@login_required
def add_log():
    emp_id = request.form.get('employee_id')
    action = request.form.get('action')
    new_log = WorkLog(employee_id=emp_id, action=action)
    db.session.add(new_log)
    db.session.commit()
    flash('Work log entry added.')
    return redirect(url_for('logs'))

@app.route('/log/delete/<int:id>')
@login_required
def delete_log(id):
    log = WorkLog.query.get_or_404(id)
    db.session.delete(log)
    db.session.commit()
    flash('Work log entry deleted.')
    return redirect(url_for('logs'))
    # Part 4: Inventory Module Routes (Items, Suppliers, Purchase Orders)
@app.route('/items')
@login_required
def items():
    all_items = Item.query.all()
    return render_template('items.html', items=all_items)

@app.route('/item/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        quantity = request.form.get('quantity', type=int)
        price = request.form.get('price', type=float)
        supplier_id = request.form.get('supplier_id', type=int)
        new_item = Item(name=name, description=description, quantity=quantity, price=price, supplier_id=supplier_id)
        db.session.add(new_item)
        db.session.commit()
        flash('New item added to inventory.')
        return redirect(url_for('items'))
    suppliers = Supplier.query.all()
    return render_template('add_item.html', suppliers=suppliers)

@app.route('/item/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    item = Item.query.get_or_404(id)
    if request.method == 'POST':
        item.name = request.form.get('name')
        item.description = request.form.get('description')
        item.quantity = request.form.get('quantity', type=int)
        item.price = request.form.get('price', type=float)
        item.supplier_id = request.form.get('supplier_id', type=int)
        db.session.commit()
        flash('Item updated.')
        return redirect(url_for('items'))
    suppliers = Supplier.query.all()
    return render_template('edit_item.html', item=item, suppliers=suppliers)

@app.route('/item/delete/<int:id>')
@login_required
def delete_item(id):
    item = Item.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted.')
    return redirect(url_for('items'))

# Supplier routes
@app.route('/suppliers')
@login_required
def suppliers():
    all_suppliers = Supplier.query.all()
    return render_template('suppliers.html', suppliers=all_suppliers)

@app.route('/supplier/add', methods=['GET', 'POST'])
@login_required
def add_supplier():
    if request.method == 'POST':
        name = request.form.get('name')
        contact = request.form.get('contact')
        new_supplier = Supplier(name=name, contact=contact)
        db.session.add(new_supplier)
        db.session.commit()
        flash('New supplier added.')
        return redirect(url_for('suppliers'))
    return render_template('add_supplier.html')

@app.route('/supplier/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    if request.method == 'POST':
        supplier.name = request.form.get('name')
        supplier.contact = request.form.get('contact')
        db.session.commit()
        flash('Supplier updated.')
        return redirect(url_for('suppliers'))
    return render_template('edit_supplier.html', supplier=supplier)

@app.route('/supplier/delete/<int:id>')
@login_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    db.session.delete(supplier)
    db.session.commit()
    flash('Supplier deleted.')
    return redirect(url_for('suppliers'))

# Purchase order routes
@app.route('/orders')
@login_required
def orders():
    all_orders = PurchaseOrder.query.all()
    return render_template('orders.html', orders=all_orders)

@app.route('/order/add', methods=['GET', 'POST'])
@login_required
def add_order():
    if request.method == 'POST':
        item_id = request.form.get('item_id', type=int)
        supplier_id = request.form.get('supplier_id', type=int)
        quantity = request.form.get('quantity', type=int)
        total_price = request.form.get('total_price', type=float)
        status = request.form.get('status')
        new_order = PurchaseOrder(item_id=item_id, supplier_id=supplier_id, quantity=quantity, total_price=total_price, status=status)
        db.session.add(new_order)
        db.session.commit()
        flash('Purchase order created.')
        return redirect(url_for('orders'))
    items = Item.query.all()
    suppliers = Supplier.query.all()
    return render_template('add_order.html', items=items, suppliers=suppliers)

@app.route('/order/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_order(id):
    order = PurchaseOrder.query.get_or_404(id)
    if request.method == 'POST':
        order.item_id = request.form.get('item_id', type=int)
        order.supplier_id = request.form.get('supplier_id', type=int)
        order.quantity = request.form.get('quantity', type=int)
        order.total_price = request.form.get('total_price', type=float)
        order.status = request.form.get('status')
        db.session.commit()
        flash('Purchase order updated.')
        return redirect(url_for('orders'))
    items = Item.query.all()
    suppliers = Supplier.query.all()
    return render_template('edit_order.html', order=order, items=items, suppliers=suppliers)

@app.route('/order/delete/<int:id>')
@login_required
def delete_order(id):
    order = PurchaseOrder.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    flash('Purchase order deleted.')
    return redirect(url_for('orders'))
    # Part 5: Accounts & Purchase Module Routes (Accounts, Transactions)
@app.route('/accounts')
@login_required
def accounts():
    all_accounts = Account.query.all()
    return render_template('accounts.html', accounts=all_accounts)

@app.route('/account/add', methods=['GET', 'POST'])
@login_required
def add_account():
    if request.method == 'POST':
        name = request.form.get('name')
        acc_type = request.form.get('type')
        balance = request.form.get('balance', type=float)
        new_account = Account(name=name, type=acc_type, balance=balance)
        db.session.add(new_account)
        db.session.commit()
        flash('New account added.')
        return redirect(url_for('accounts'))
    return render_template('add_account.html')

@app.route('/account/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_account(id):
    account = Account.query.get_or_404(id)
    if request.method == 'POST':
        account.name = request.form.get('name')
        account.type = request.form.get('type')
        account.balance = request.form.get('balance', type=float)
        db.session.commit()
        flash('Account updated.')
        return redirect(url_for('accounts'))
    return render_template('edit_account.html', account=account)

@app.route('/account/delete/<int:id>')
@login_required
def delete_account(id):
    account = Account.query.get_or_404(id)
    db.session.delete(account)
    db.session.commit()
    flash('Account deleted.')
    return redirect(url_for('accounts'))

# Transaction routes
@app.route('/transactions')
@login_required
def transactions():
    all_transactions = Transaction.query.all()
    return render_template('transactions.html', transactions=all_transactions)

@app.route('/transaction/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        account_id = request.form.get('account_id', type=int)
        amount = request.form.get('amount', type=float)
        description = request.form.get('description')
        txn_type = request.form.get('type')
        new_txn = Transaction(account_id=account_id, amount=amount, description=description, type=txn_type)
        db.session.add(new_txn)
        db.session.commit()
        flash('Transaction recorded.')
        return redirect(url_for('transactions'))
    accounts = Account.query.all()
    return render_template('add_transaction.html', accounts=accounts)

@app.route('/transaction/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    txn = Transaction.query.get_or_404(id)
    if request.method == 'POST':
        txn.account_id = request.form.get('account_id', type=int)
        txn.amount = request.form.get('amount', type=float)
        txn.description = request.form.get('description')
        txn.type = request.form.get('type')
        db.session.commit()
        flash('Transaction updated.')
        return redirect(url_for('transactions'))
    accounts = Account.query.all()
    return render_template('edit_transaction.html', transaction=txn, accounts=accounts)

@app.route('/transaction/delete/<int:id>')
@login_required
def delete_transaction(id):
    txn = Transaction.query.get_or_404(id)
    db.session.delete(txn)
    db.session.commit()
    flash('Transaction deleted.')
    return redirect(url_for('transactions'))
    # Part 6: Projects & Sites Module Routes (Projects, Sites, Tasks)
@app.route('/projects')
@login_required
def projects():
    all_projects = Project.query.all()
    return render_template('projects.html', projects=all_projects)

@app.route('/project/add', methods=['GET', 'POST'])
@login_required
def add_project():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        start_date = request.form.get('start_date')  # format 'YYYY-MM-DD'
        end_date = request.form.get('end_date')
        status = request.form.get('status')
        new_project = Project(name=name, description=description, start_date=start_date, end_date=end_date, status=status)
        db.session.add(new_project)
        db.session.commit()
        flash('New project created.')
        return redirect(url_for('projects'))
    return render_template('add_project.html')

@app.route('/project/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_project(id):
    project = Project.query.get_or_404(id)
    if request.method == 'POST':
        project.name = request.form.get('name')
        project.description = request.form.get('description')
        project.start_date = request.form.get('start_date')
        project.end_date = request.form.get('end_date')
        project.status = request.form.get('status')
        db.session.commit()
        flash('Project updated.')
        return redirect(url_for('projects'))
    return render_template('edit_project.html', project=project)

@app.route('/project/delete/<int:id>')
@login_required
def delete_project(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted.')
    return redirect(url_for('projects'))

# Site routes
@app.route('/sites')
@login_required
def sites():
    all_sites = Site.query.all()
    return render_template('sites.html', sites=all_sites)

@app.route('/site/add', methods=['GET', 'POST'])
@login_required
def add_site():
    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        location = request.form.get('location')
        manager = request.form.get('manager')
        status = request.form.get('status')
        new_site = Site(project_id=project_id, location=location, manager=manager, status=status)
        db.session.add(new_site)
        db.session.commit()
        flash('New site added.')
        return redirect(url_for('sites'))
    projects = Project.query.all()
    return render_template('add_site.html', projects=projects)

@app.route('/site/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_site(id):
    site = Site.query.get_or_404(id)
    if request.method == 'POST':
        site.project_id = request.form.get('project_id', type=int)
        site.location = request.form.get('location')
        site.manager = request.form.get('manager')
        site.status = request.form.get('status')
        db.session.commit()
        flash('Site updated.')
        return redirect(url_for('sites'))
    projects = Project.query.all()
    return render_template('edit_site.html', site=site, projects=projects)

@app.route('/site/delete/<int:id>')
@login_required
def delete_site(id):
    site = Site.query.get_or_404(id)
    db.session.delete(site)
    db.session.commit()
    flash('Site deleted.')
    return redirect(url_for('sites'))

# Task routes
@app.route('/tasks')
@login_required
def tasks():
    all_tasks = Task.query.all()
    return render_template('tasks.html', tasks=all_tasks)

@app.route('/task/add', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        name = request.form.get('name')
        assigned_to = request.form.get('assigned_to')
        due_date = request.form.get('due_date')  # format 'YYYY-MM-DD'
        status = request.form.get('status')
        new_task = Task(project_id=project_id, name=name, assigned_to=assigned_to, due_date=due_date, status=status)
        db.session.add(new_task)
        db.session.commit()
        flash('New task created.')
        return redirect(url_for('tasks'))
    projects = Project.query.all()
    return render_template('add_task.html', projects=projects)

@app.route('/task/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Task.query.get_or_404(id)
    if request.method == 'POST':
        task.project_id = request.form.get('project_id', type=int)
        task.name = request.form.get('name')
        task.assigned_to = request.form.get('assigned_to')
        task.due_date = request.form.get('due_date')
        task.status = request.form.get('status')
        db.session.commit()
        flash('Task updated.')
        return redirect(url_for('tasks'))
    projects = Project.query.all()
    return render_template('edit_task.html', task=task, projects=projects)

@app.route('/task/delete/<int:id>')
@login_required
def delete_task(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.')
    return redirect(url_for('tasks'))
    # Part 7: Export Functions (PDF and Excel for each module)
@app.route('/employees/export/pdf')
@login_required
def export_employees_pdf():
    employees = Employee.query.all()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Employees Report", ln=1)
    pdf.set_font("Arial", size=12)
    for emp in employees:
        pdf.cell(0, 10, f"ID: {emp.id} | Name: {emp.name} | Position: {emp.position} | Department: {emp.department}", ln=1)
    pdf_output = pdf.output(dest='S').encode('latin-1')
    return send_file(io.BytesIO(pdf_output), attachment_filename="employees_report.pdf", as_attachment=True)

@app.route('/employees/export/excel')
@login_required
def export_employees_excel():
    employees = Employee.query.all()
    df = pd.DataFrame([(emp.id, emp.name, emp.position, emp.department, emp.email, emp.join_date) for emp in employees],
                      columns=['ID', 'Name', 'Position', 'Department', 'Email', 'Join Date'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Employees')
    output.seek(0)
    return send_file(output, attachment_filename="employees.xlsx", as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/items/export/pdf')
@login_required
def export_items_pdf():
    items = Item.query.all()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Inventory Items Report", ln=1)
    pdf.set_font("Arial", size=12)
    for item in items:
        pdf.cell(0, 10, f"ID: {item.id} | Name: {item.name} | Qty: {item.quantity} | Price: {item.price}", ln=1)
    pdf_output = pdf.output(dest='S').encode('latin-1')
    return send_file(io.BytesIO(pdf_output), attachment_filename="inventory_items_report.pdf", as_attachment=True)

@app.route('/items/export/excel')
@login_required
def export_items_excel():
    items = Item.query.all()
    df = pd.DataFrame([(item.id, item.name, item.quantity, item.price, item.supplier_id) for item in items],
                      columns=['ID', 'Name', 'Quantity', 'Price', 'Supplier ID'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Items')
    output.seek(0)
    return send_file(output, attachment_filename="items.xlsx", as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/accounts/export/pdf')
@login_required
def export_accounts_pdf():
    accounts = Account.query.all()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Accounts Report", ln=1)
    pdf.set_font("Arial", size=12)
    for acc in accounts:
        pdf.cell(0, 10, f"ID: {acc.id} | Name: {acc.name} | Type: {acc.type} | Balance: {acc.balance}", ln=1)
    pdf_output = pdf.output(dest='S').encode('latin-1')
    return send_file(io.BytesIO(pdf_output), attachment_filename="accounts_report.pdf", as_attachment=True)

@app.route('/accounts/export/excel')
@login_required
def export_accounts_excel():
    accounts = Account.query.all()
    df = pd.DataFrame([(acc.id, acc.name, acc.type, acc.balance) for acc in accounts],
                      columns=['ID', 'Name', 'Type', 'Balance'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Accounts')
    output.seek(0)
    return send_file(output, attachment_filename="accounts.xlsx", as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/projects/export/pdf')
@login_required
def export_projects_pdf():
    projects = Project.query.all()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Projects Report", ln=1)
    pdf.set_font("Arial", size=12)
    for proj in projects:
        pdf.cell(0, 10, f"ID: {proj.id} | Name: {proj.name} | Status: {proj.status}", ln=1)
    pdf_output = pdf.output(dest='S').encode('latin-1')
    return send_file(io.BytesIO(pdf_output), attachment_filename="projects_report.pdf", as_attachment=True)

@app.route('/projects/export/excel')
@login_required
def export_projects_excel():
    projects = Project.query.all()
    df = pd.DataFrame([(proj.id, proj.name, proj.start_date, proj.end_date, proj.status) for proj in projects],
                      columns=['ID', 'Name', 'Start Date', 'End Date', 'Status'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')
    output.seek(0)
    return send_file(output, attachment_filename="projects.xlsx", as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    # Part 8: Run the Flask Application
if __name__ == '__main__':
    app.run(debug=True)
    
    
    
