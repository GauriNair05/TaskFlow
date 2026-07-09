from flask import Flask, render_template, request, redirect, url_for, session, jsonify 
import os
import psycopg2
from psycopg2.extras import DictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'temporary_local_secret_key'

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn
    pass

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        cur.execute("SELECT * FROM users WHERE username = %s;", (username,))
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid username or password. Please try again."
            
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    cur.execute("SELECT * FROM tasks WHERE assigned_to = %s ORDER BY task_id ASC;", (session['user_id'],))
    user_tasks = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('dashboard.html', tasks=user_tasks)


@app.route('/seed')
def seed_database():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        hashed_password = generate_password_hash('password123')
        
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) ON CONFLICT (username) DO NOTHING;",
            ('admin', hashed_password, 'Admin')
        )
        
        conn.commit()
        cur.close()
        conn.close()
        return "Database seeded successfully! User 'admin' with password 'password123' is ready."
    except Exception as e:
        return f"Error seeding database: {e}"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/task/update', methods=['POST'])
def update_task_status():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    # Read the JSON data sent by JavaScript
    data = request.get_json()
    task_id = data.get('task_id')
    new_status = data.get('status')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Update the specific task's status in Supabase
        cur.execute(
            "UPDATE tasks SET status = %s WHERE task_id = %s AND assigned_to = %s;",
            (new_status, task_id, session['user_id'])
        )
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    
if __name__ == '__main__':
    app.run(debug=True)