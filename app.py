import os
import traceback
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import psycopg2
import psycopg2.extras
from functools import wraps
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# --- Environment Check ---
REQUIRED_ENV_VARS = ["DATABASE_URL"]
missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

DATABASE_URL = os.environ["DATABASE_URL"]

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-change-me")
CORS(app)

# Initialize Flask-Login and Bcrypt
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
bcrypt = Bcrypt(app)

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email, role='user'):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
    
    def is_admin(self):
        return self.role == 'admin'

@login_manager.user_loader
def load_user(user_id):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, username, email, role FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        db.close()
        
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['email'], user_data['role'])
    except Exception as e:
        logging.error(f"Error loading user: {e}")
    return None

# --- DB Connection Helper ---
def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

# --- Admin Required Decorator ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You need admin privileges to access this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Improved DB Initialization Logic ---
def init_db():
    print("⏳ Starting database initialization...")

    try:
        db = get_db()
        cursor = db.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(256) NOT NULL,
                role VARCHAR(10) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create expenses table with user_id foreign key
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date DATE,
                details TEXT,
                cat1 DECIMAL(10,2) DEFAULT 0,
                cat2 DECIMAL(10,2) DEFAULT 0,
                cat3 DECIMAL(10,2) DEFAULT 0,
                cat4 DECIMAL(10,2) DEFAULT 0,
                cat5 DECIMAL(10,2) DEFAULT 0,
                remarks TEXT,
                income DECIMAL(10,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        db.commit()
        cursor.close()
        db.close()
        print("✅ Tables 'users' and 'expenses' are ready.")

    except psycopg2.Error as err:
        print("❌ PostgreSQL error during init_db():")
        print(err)
    except Exception as e:
        print("❌ Unexpected error during init_db():")
        traceback.print_exc()

# Always run init on load
init_db()

# --- Authentication Routes ---
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                flash('Username or email already exists.', 'error')
                cursor.close()
                db.close()
                return render_template('register.html')
            
            # Create new user
            password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                (username, email, password_hash)
            )
            result = cursor.fetchone()
            if result:
                user_id = result[0] if isinstance(result, tuple) else result['id']
            else:
                raise Exception("Failed to create user")
            db.commit()
            cursor.close()
            db.close()
            
            # Log in the new user
            user = User(user_id, username, email)
            login_user(user)
            flash('Registration successful! Welcome to Expense Tracker.', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash('An error occurred during registration. Please try again.', 'error')
            logging.error(f"Registration error: {e}")
            return render_template('register.html')
    
    return render_template('register.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html')
        
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                "SELECT id, username, email, password_hash, role FROM users WHERE username = %s OR email = %s",
                (username, username)
            )
            user_data = cursor.fetchone()
            cursor.close()
            db.close()
            
            if user_data and bcrypt.check_password_hash(user_data['password_hash'], password):
                user = User(user_data['id'], user_data['username'], user_data['email'], user_data['role'])
                login_user(user)
                flash(f'Welcome back, {user.username}!', 'success')
                
                # Redirect to admin dashboard if admin, otherwise regular dashboard
                if user.is_admin():
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')
                
        except Exception as e:
            flash('An error occurred during login. Please try again.', 'error')
            logging.error(f"Login error: {e}")
    
    return render_template('login.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# --- Dashboard Routes ---
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get all users
        cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        
        # Get expense summary by user
        cursor.execute("""
            SELECT u.username, COUNT(e.id) as expense_count, 
                   COALESCE(SUM(e.cat1 + e.cat2 + e.cat3 + e.cat4 + e.cat5), 0) as total_expenses,
                   COALESCE(SUM(e.income), 0) as total_income
            FROM users u 
            LEFT JOIN expenses e ON u.id = e.user_id 
            GROUP BY u.id, u.username
            ORDER BY total_expenses DESC
        """)
        user_summaries = cursor.fetchall()
        
        cursor.close()
        db.close()
        
        return render_template('admin_dashboard.html', users=users, user_summaries=user_summaries)
        
    except Exception as e:
        flash('Error loading admin dashboard.', 'error')
        logging.error(f"Admin dashboard error: {e}")
        return redirect(url_for('dashboard'))

# --- API Routes (Modified for User Isolation) ---
@app.route("/api/expense", methods=["POST"])
@login_required
def add_expense():
    data = request.get_json()
    required_fields = ['date', 'details']
    if not all(field in data and data[field] is not None for field in required_fields):
        return jsonify({"error": "Missing required expense fields"}), 400

    sql = (
        "INSERT INTO expenses (user_id, date, details, cat1, cat2, cat3, cat4, cat5, remarks, income) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    values = (
        current_user.id,  # Add user_id to associate expense with current user
        data['date'],
        data['details'],
        data.get('cat1', 0),
        data.get('cat2', 0),
        data.get('cat3', 0),
        data.get('cat4', 0),
        data.get('cat5', 0),
        data.get('remarks', ''),
        data.get('income', 0)
    )

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(sql, values)
        db.commit()
        cursor.close()
        db.close()
        return jsonify({"message": "Expense added successfully"}), 200
    except Exception as err:
        logging.error(f"Add expense error: {err}")
        return jsonify({"error": str(err)}), 500

@app.route("/api/expense", methods=["GET"])
@login_required
def get_expenses():
    try:
        db = get_db()
        cursor = db.cursor()
        
        # If admin, get all expenses, otherwise get only user's expenses
        if current_user.is_admin():
            cursor.execute("""
                SELECT e.date, e.details, e.cat1, e.cat2, e.cat3, e.cat4, e.cat5, e.remarks, e.income, u.username
                FROM expenses e 
                JOIN users u ON e.user_id = u.id 
                ORDER BY e.date DESC
            """)
            include_username = True
        else:
            cursor.execute(
                "SELECT date, details, cat1, cat2, cat3, cat4, cat5, remarks, income "
                "FROM expenses WHERE user_id = %s ORDER BY date DESC",
                (current_user.id,)
            )
            include_username = False
            
        rows = cursor.fetchall()
        cursor.close()
        db.close()

        expenses = []
        for row in rows:
            expense = {
                "date": row['date'].strftime("%Y-%m-%d") if hasattr(row['date'], 'strftime') else str(row['date']),
                "details": row['details'],
                "cat1": float(row['cat1']),
                "cat2": float(row['cat2']),
                "cat3": float(row['cat3']),
                "cat4": float(row['cat4']),
                "cat5": float(row['cat5']),
                "remarks": row['remarks'],
                "income": float(row['income'])
            }
            if include_username:
                expense["username"] = row['username']
            expenses.append(expense)

        return jsonify(expenses), 200
    except Exception as err:
        logging.error(f"Get expenses error: {err}")
        return jsonify({"error": str(err)}), 500

# --- Health Check ---
@app.route("/health", methods=["GET"])
def health():
    try:
        db = get_db()
        db.close()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# Legacy routes for backward compatibility
@app.route("/expense", methods=["POST", "GET"])
@login_required
def expense_legacy():
    if request.method == "POST":
        return add_expense()
    else:
        return get_expenses()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
