from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = "library_secret"

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, author TEXT, category TEXT, available TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, book_id INTEGER, status TEXT)")
    # Insert default admin if not exists
    if not c.execute("SELECT * FROM admins WHERE username='admin'").fetchone():
        c.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ('admin', 'admin123'))
    conn.commit()
    conn.close()

init_db()

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                         (request.form['name'], request.form['email'], request.form['password']))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Email already exists"
        conn.close()
        return redirect('/login')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?",
                            (request.form['email'], request.form['password'])).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect('/user_dashboard')
        return "Invalid credentials"
    return render_template('login.html')

'''@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('user_dashboard.html', name=session['user_name'])'''

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    conn = get_db_connection()
    total_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE user_id = ?", (user_id,)).fetchone()[0]
    approved_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE user_id = ? AND status = 'Approved'", (user_id,)).fetchone()[0]
    pending_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE user_id = ? AND status = 'Pending'", (user_id,)).fetchone()[0]
    rejected_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE user_id = ? AND status = 'Rejected'", (user_id,)).fetchone()[0]
    conn.close()

    return render_template('user_dashboard.html',
                           name=session['user_name'],
                           total_requests=total_requests,
                           approved_requests=approved_requests,
                           pending_requests=pending_requests,
                           rejected_requests=rejected_requests)


@app.route('/books')
def books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return render_template('books.html', books=books)

@app.route('/request_book/<int:book_id>')
def request_book(book_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()

    # Check if already requested
    existing = conn.execute('SELECT * FROM requests WHERE user_id=? AND book_id=? AND status=?',
                            (user_id, book_id, 'Pending')).fetchone()

    if not existing:
        conn.execute('INSERT INTO requests (user_id, book_id, status) VALUES (?, ?, ?)',
                     (user_id, book_id, 'Pending'))
        conn.commit()

    conn.close()
    # ✅ Redirect to request status page after requesting
    return redirect('/my_requests')


@app.route('/my_requests')
def my_requests():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()
    requests = conn.execute('''
        SELECT requests.id AS request_id, books.title, books.author, requests.status
        FROM requests
        JOIN books ON requests.book_id = books.id
        WHERE requests.user_id = ?
    ''', (user_id,)).fetchall()
    conn.close()
    return render_template('my_requests.html', requests=requests)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM admins WHERE username=? AND password=?",
                             (request.form['username'], request.form['password'])).fetchone()
        conn.close()
        if admin:
            session['admin'] = admin['username']
            return redirect('/admin_dashboard')
        return "Invalid admin credentials"
    return render_template('admin_login.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')

    conn = get_db_connection()

    total_books = conn.execute('SELECT COUNT(*) FROM books').fetchone()[0]
    pending_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE status = 'Pending'").fetchone()[0]
    rejected_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE status = 'Rejected'").fetchone()[0]
    approved_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE status = 'Approved'").fetchone()[0]


    conn.close()
    return render_template('admin_dashboard.html',
                           total_books=total_books,
                           pending_requests=pending_requests,
                           rejected_requests=rejected_requests,
                           approved_requests=approved_requests)




@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        image_file = request.files['image']

        image_filename = ''
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_filename = filename

        conn = get_db_connection()
        conn.execute('INSERT INTO books (title, author, category, available, image) VALUES (?, ?, ?, ?, ?)',
                     (title, author, category, 'Yes', image_filename))
        conn.commit()
        conn.close()

        return redirect('/manage_books')
    return render_template('add_book.html')


@app.route('/manage_books')
def manage_books():
    if 'admin' not in session:
        return redirect('/admin_login')
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return render_template('manage_books.html', books=books)

@app.route('/delete_book/<int:book_id>')
def delete_book(book_id):
    if 'admin' not in session:
        return redirect('/admin_login')
    conn = get_db_connection()
    conn.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    return redirect('/manage_books')

@app.route('/manage_requests')
def manage_requests():
    if 'admin' not in session:
        return redirect('/admin_login')
    conn = get_db_connection()
    requests = conn.execute("""
        SELECT r.id, u.name, b.title, r.status
        FROM requests r
        JOIN users u ON r.user_id = u.id
        JOIN books b ON r.book_id = b.id
    """).fetchall()
    conn.close()
    return render_template('manage_requests.html', requests=requests)

@app.route('/approve_request/<int:request_id>')
def approve_request(request_id):
    if 'admin' not in session:
        return redirect('/admin_login')
    conn = get_db_connection()
    conn.execute("UPDATE requests SET status='Approved' WHERE id=?", (request_id,))
    book_id = conn.execute("SELECT book_id FROM requests WHERE id=?", (request_id,)).fetchone()['book_id']
    conn.execute("UPDATE books SET available='Borrowed' WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    return redirect('/manage_requests')


@app.route('/reject_request/<int:request_id>')
def reject_request(request_id):
    if 'admin' not in session:
        return redirect('/admin_login')
    conn = get_db_connection()
    conn.execute("UPDATE requests SET status='rejected' WHERE id=?", (request_id,))
    conn.commit()
    conn.close()
    return redirect('/manage_requests')


@app.route('/mark_returned/<int:request_id>')
def mark_returned(request_id):
    if 'admin' not in session:
        return redirect('/admin_login')
    conn = get_db_connection()
    conn.execute("UPDATE requests SET status='Returned' WHERE id=?", (request_id,))
    book_id = conn.execute("SELECT book_id FROM requests WHERE id=?", (request_id,)).fetchone()['book_id']
    conn.execute("UPDATE books SET available='Available' WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    return redirect('/manage_requests')


@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        available = request.form.get('available', 'Yes')
        
        image = book['image']  # existing image
        image_file = request.files.get('image')

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = filename  # update image only if new uploaded

        conn.execute('''
            UPDATE books
            SET title=?, author=?, category=?, available=?, image=?
            WHERE id=?
        ''', (title, author, category, available, image, book_id))

        conn.commit()
        conn.close()
        return redirect('/manage_books')

    conn.close()
    return render_template('edit_book.html', book=book)

@app.route('/check_statuses')
def check_statuses():
    conn = get_db_connection()
    rows = conn.execute("SELECT id, status FROM requests").fetchall()
    conn.close()
    result = "<h2>Request Statuses:</h2><ul>"
    for row in rows:
        result += f"<li>Request ID: {row['id']} — Status: {row['status']}</li>"
    result += "</ul>"
    return result

   
@app.route('/delete_request/<int:request_id>')    
def delete_request(request_id):
    if 'admin' not in session:
        return redirect('/admin_login')
    conn = get_db_connection()
    conn.execute("DELETE FROM requests WHERE id=?", (request_id,))
    conn.commit()
    conn.close()
    return redirect('/manage_requests')

@app.route('/delete_user_request/<int:request_id>', methods=['POST'])
def delete_user_request(request_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db_connection()
    conn.execute("DELETE FROM requests WHERE id=? AND user_id=?", (request_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect('/my_requests')





if __name__ == '__main__':
    app.run(debug=True)