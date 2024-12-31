from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import io
import csv

app = Flask(__name__)
app.secret_key = "secret_key"  # Replace with a strong secret key


def init_db():
    with sqlite3.connect('tasks.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Medium',
                status TEXT NOT NULL DEFAULT 'Pending',
                due_date TEXT DEFAULT NULL,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    with sqlite3.connect('tasks.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,))
        tasks = cursor.fetchall()
    return render_template('index.html', tasks=tasks)


@app.route('/view/<int:id>')
def view_task(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect('tasks.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (id, session['user_id']))
        task = cursor.fetchone()
    if task:
        return render_template('view.html', task=task)
    return "Task not found or access denied!", 404


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        with sqlite3.connect('tasks.db') as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                return "Username already exists!"
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('tasks.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                return redirect(url_for('dashboard'))
            else:
                return "Invalid credentials!"
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/add', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    title = request.form['title']
    description = request.form['description']
    priority = request.form['priority']
    due_date = request.form['due_date']
    user_id = session['user_id']
    with sqlite3.connect('tasks.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (title, description, priority, due_date, user_id) VALUES (?, ?, ?, ?, ?)",
            (title, description, priority, due_date, user_id)
        )
        conn.commit()
    return redirect(url_for('dashboard'))


@app.route('/delete/<int:id>')
def delete_task(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect('tasks.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (id,))
        conn.commit()
    return redirect(url_for('dashboard'))


@app.route('/complete/<int:id>')
def complete_task(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect('tasks.db') as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = 'Completed' WHERE id = ?", (id,))
        conn.commit()
    return redirect(url_for('dashboard'))


@app.route('/export')
def export_tasks():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    with sqlite3.connect('tasks.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description, priority, status, due_date FROM tasks WHERE user_id = ?", (user_id,))
        tasks = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Title', 'Description', 'Priority', 'Status', 'Due Date'])
    writer.writerows(tasks)
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='tasks.csv'
    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
