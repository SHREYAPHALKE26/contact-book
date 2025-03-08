from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Database setup
def get_db_connection():
    conn = sqlite3.connect('contacts.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Create users table if it doesn't exist
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    # Create contacts table if it doesn't exist
    conn.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    # Add user_id column if it doesn't exist
    try:
        conn.execute('ALTER TABLE contacts ADD COLUMN user_id INTEGER')
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()

init_db()

# Home Page
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            user_obj = User(user['id'])
            login_user(user_obj)
            flash('Logged in successfully!')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!')
        finally:
            conn.close()
    return render_template('register.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!')
    return redirect(url_for('login'))

# Add Contact
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_contact():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']

        conn = get_db_connection()
        conn.execute('INSERT INTO contacts (name, phone, email, address, user_id) VALUES (?, ?, ?, ?, ?)',
                     (name, phone, email, address, current_user.id))
        conn.commit()
        conn.close()
        flash('Contact added successfully!')
        return redirect(url_for('index'))
    return render_template('add_contact.html')

# View Contact
@app.route('/view')
@login_required
def view_contacts():
    conn = get_db_connection()
    contacts = conn.execute('SELECT * FROM contacts WHERE user_id = ?', (current_user.id,)).fetchall()
    conn.close()
    return render_template('view_contacts.html', contacts=contacts)

# Search Contact
@app.route('/search', methods=['GET', 'POST'])
@login_required
def search_contact():
    if request.method == 'POST':
        search_term = request.form['search']
        conn = get_db_connection()
        contacts = conn.execute('SELECT * FROM contacts WHERE (name LIKE ? OR phone LIKE ?) AND user_id = ?',
                                (f'%{search_term}%', f'%{search_term}%', current_user.id)).fetchall()
        conn.close()
        return render_template('view_contacts.html', contacts=contacts)
    return render_template('search_contact.html')

# Update Contact
@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update_contact(id):
    conn = get_db_connection()
    contact = conn.execute('SELECT * FROM contacts WHERE id = ? AND user_id = ?', (id, current_user.id)).fetchone()
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']

        conn.execute('UPDATE contacts SET name = ?, phone = ?, email = ?, address = ? WHERE id = ?',
                     (name, phone, email, address, id))
        conn.commit()
        conn.close()
        flash('Contact updated successfully!')
        return redirect(url_for('view_contacts'))
    return render_template('update_contact.html', contact=contact)

# Delete Contact
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_contact(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM contacts WHERE id = ? AND user_id = ?', (id, current_user.id))
    conn.commit()
    conn.close()
    flash('Contact deleted successfully!')
    return redirect(url_for('view_contacts'))

if __name__ == '__main__':
    app.run(debug=True)