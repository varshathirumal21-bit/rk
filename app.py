from flask import Flask, render_template, request, redirect, url_for, session, Response, send_file
import sqlite3
import csv
import io
import zipfile
from PIL import Image, ImageDraw
import os

app = Flask(__name__)
app.secret_key = 'rk_solutions_production_key'

DB_FILE = 'rk.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            name TEXT,
            is_admin INTEGER,
            wallet_balance REAL,
            membership_count INTEGER,
            smartbook_count INTEGER,
            paid_earning REAL,
            member_id TEXT,
            city TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT,
            customer_name TEXT,
            phone_number TEXT,
            city TEXT,
            lead_status TEXT,
            reg_date TEXT,
            youtube_link TEXT,
            kw1 TEXT,
            kw2 TEXT,
            kw3 TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_date TEXT,
            name TEXT,
            youtube_code TEXT,
            kw1 TEXT,
            kw2 TEXT,
            kw3 TEXT,
            uploaded_files TEXT
        )
    ''')
    
    # Insert default users if table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (phone, name, is_admin, wallet_balance, membership_count, smartbook_count, paid_earning, member_id, city) VALUES ('9876543210', 'Ravi Kumar', 0, 1200, 15, 22, 8250, 'LP1001', 'Coimbatore')")
        cursor.execute("INSERT INTO users (phone, name, is_admin, wallet_balance, membership_count, smartbook_count, paid_earning, member_id, city) VALUES ('9000000000', 'Admin RK', 1, 5000, 50, 50, 25000, 'ADMIN01', 'Tirupattur')")
        cursor.execute("INSERT INTO admin_requests (request_date, name, youtube_code, kw1, kw2, kw3, uploaded_files) VALUES ('17-05-2026', 'Raju', '2026001', 'AI tools for students', 'Best laptop for coding under 50000', 'How to learn Python in 30 days', 'Yes')")
        conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        phone = request.form['phone']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
        user_row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_row:
            session['phone'] = user_row['phone']
            session['is_admin'] = user_row['is_admin']
            session['name'] = user_row['name']
            if user_row['is_admin'] == 1:
                return redirect(url_for('admin_panel'))
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid mobile number. Try 9876543210 (User) or 9000000000 (Admin)."
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    phone = session.get('phone', '9876543210')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user_row = cursor.fetchone()
    cursor.close()
    conn.close()
    user = dict(user_row) if user_row else {'name': 'Ravi Kumar', 'wallet_balance': 1200, 'membership_count': 15, 'smartbook_count': 22, 'paid_earning': 8250, 'member_id': 'LP1001', 'city': 'Coimbatore'}
    return render_template('dashboard.html', user=user)

@app.route('/customers')
def customers():
    status_filter = request.args.get('status', 'All')
    date_filter = request.args.get('date', '')
    search_query = request.args.get('search', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM customers WHERE 1=1"
    params = []
    
    if status_filter != 'All':
        query += " AND lead_status = ?"
        params.append(status_filter)
    if date_filter:
        query += " AND reg_date LIKE ?"
        params.append(f"%{date_filter}%")
    if search_query:
        query += " AND (customer_name LIKE ? OR phone_number LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
        
    cursor.execute(query, tuple(params))
    customer_list = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('customers.html', customers=customer_list, active_filter=status_filter, search=search_query, date=date_filter)

@app.route('/customer/<int:c_id>')
def customer_detail(c_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE id = ?", (c_id,))
    c_row = cursor.fetchone()
    cursor.close()
    conn.close()
    customer = dict(c_row) if c_row else None
    return render_template('customer_detail.html', customer=customer)

@app.route('/add_customer_form')
def add_customer_form():
    return render_template('add_customer.html')

@app.route('/payment_gateway', methods=['POST'])
def payment_gateway():
    session['temp_customer'] = {
        'customer_id': request.form['customer_id'],
        'customer_name': request.form['customer_name'],
        'phone_number': request.form['phone_number'],
        'city': request.form['city'],
        'lead_status': request.form['lead_status'],
        'reg_date': '20 May 2025',
        'youtube_link': request.form['youtube_link'],
        'kw1': request.form['kw1'],
        'kw2': request.form['kw2'],
        'kw3': request.form['kw3']
    }
    plan = request.form['plan_type']
    amount = 955 if plan == 'membership' else 300
    return render_template('payment.html', amount=amount, plan=plan)

@app.route('/confirm_payment', methods=['POST'])
def confirm_payment():
    c_data = session.get('temp_customer')
    if c_data:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customers (customer_id, customer_name, phone_number, city, lead_status, reg_date, youtube_link, kw1, kw2, kw3)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (c_data['customer_id'], c_data['customer_name'], c_data['phone_number'], c_data['city'], 
              c_data['lead_status'], c_data['reg_date'], c_data['youtube_link'], c_data['kw1'], c_data['kw2'], c_data['kw3']))
        conn.commit()
        cursor.close()
        conn.close()
    return render_template('order_status.html')

@app.route('/training')
def training():
    lang = request.args.get('lang', 'English')
    return render_template('training.html', lang=lang)

@app.route('/training_videos')
def training_videos():
    videos = [{"id": i, "title": f"{i}. IT & Python Mastery Tutorial Video #{i}", "link": "https://www.youtube.com/watch?v=_uQrJ0SmZfk"} for i in range(1, 21)]
    return render_template('training_videos.html', videos=videos)

@app.route('/sales_scripts')
def sales_scripts():
    scripts = [{"id": i, "title": f"Sales_Script_Document_{i}.txt", "content": f"RK Solutions Sales Script #{i}: Welcome partner. Use this proven pitch to close memberships (Rs 955) and smart books (Rs 300) easily with clients."} for i in range(1, 51)]
    return render_template('sales_scripts.html', scripts=scripts)

@app.route('/faq')
def faq():
    faqs = [
        ("How do I register a new customer?", "Go to Customers, click '+ Add New Customer', fill details, and complete payment."),
        ("What are the membership fees?", "Membership is Rs 955 and Smart Book is Rs 300."),
        ("How do I download posters and smart books?", "Navigate to Training and click the respective resource icon to view or download real files."),
        ("Can admin manage everything?", "Yes! Admin has full access to view, add, and modify customers, training materials, reports, and content requests.")
    ]
    return render_template('faq.html', faqs=faqs)

@app.route('/smart_books')
def smart_books():
    books = [{"id": i, "title": f"Sample_SmartBook_Handbook_{i}.pdf"} for i in range(1, 51)]
    return render_template('smart_books.html', books=books)

@app.route('/download_smartbook/<int:book_id>')
def download_smartbook(book_id):
    buffer = io.BytesIO()
    buffer.write(f"RK Solutions - Sample Smart Book Handbook #{book_id}\nOfficial Educational PDF Document.".encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=f'SmartBook_Handbook_{book_id}.pdf')

@app.route('/download_posters')
def download_posters():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for i in range(1, 51):
            img = Image.new('RGB', (600, 600), color=(92, 45, 145))
            d = ImageDraw.Draw(img)
            d.text((50, 240), f"RK SOLUTIONS\nPromotional Poster #{i}\n\n- Join Membership Today!\n- Smart Book Available", fill=(255, 255, 255))
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=85)
            img_io.seek(0)
            zf.writestr(f"RK_Poster_{i}.jpg", img_io.read())
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='RK_Solutions_50_Posters.zip')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/export_excel')
def export_excel():
    return redirect(url_for('export_csv'))

@app.route('/admin_panel')
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_requests")
    requests = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('admin.html', requests=requests)

@app.route('/admin/edit/<int:req_id>', methods=['GET', 'POST'])
def admin_edit(req_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        r_date = request.form['request_date']
        name = request.form['name']
        y_code = request.form['youtube_code']
        kw1 = request.form['kw1']
        kw2 = request.form['kw2']
        kw3 = request.form['kw3']
        uploaded = request.form['uploaded_files']
        
        cursor.execute("""
            UPDATE admin_requests SET request_date=?, name=?, youtube_code=?, kw1=?, kw2=?, kw3=?, uploaded_files=?
            WHERE id=?
        """, (r_date, name, y_code, kw1, kw2, kw3, uploaded, req_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_panel'))
        
    cursor.execute("SELECT * FROM admin_requests WHERE id = ?", (req_id,))
    req = dict(cursor.fetchone())
    cursor.close()
    conn.close()
    return render_template('admin_edit.html', req=req)

@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO admin_requests (request_date, name, youtube_code, kw1, kw2, kw3, uploaded_files)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (request.form['request_date'], request.form['name'], request.form['youtube_code'], 
              request.form['kw1'], request.form['kw2'], request.form['kw3'], request.form['uploaded_files']))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_panel'))
    return render_template('admin_add.html')

@app.route('/export_csv')
def export_csv():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id, customer_name, phone_number, city, lead_status, reg_date FROM customers")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Customer ID', 'Customer Name', 'Phone Number', 'City', 'Lead Status', 'Registration Date'])
    for row in data:
        writer.writerow([row['customer_id'], row['customer_name'], row['phone_number'], row['city'], row['lead_status'], row['reg_date']])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=customer_report.csv"})

@app.resource if False else route_profile := app.route('/profile')
def profile():
    phone = session.get('phone', '9876543210')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user_row = cursor.fetchone()
    cursor.close()
    conn.close()
    user = dict(user_row) if user_row else {'name': 'Ravi Kumar', 'wallet_balance': 1200, 'membership_count': 15, 'smartbook_count': 22, 'paid_earning': 8250, 'member_id': 'LP1001', 'city': 'Coimbatore'}
    return render_template('profile.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)