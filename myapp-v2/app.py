import os
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from functools import wraps

# Read .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "any-secret-key-123")
CORS(app)

# --- Keycloak (OAuth) Setup ---
oauth = OAuth(app)
oauth.register(
    name='keycloak',
    client_id=os.environ.get("KEYCLOAK_CLIENT_ID"),
    client_secret=os.environ.get("KEYCLOAK_CLIENT_SECRET"),
    server_metadata_url=os.environ.get("KEYCLOAK_METADATA_URL"),
    client_kwargs={'scope': 'openid profile email'},
)

# --- Database Connection ---
def get_db():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL"), 
        cursor_factory=psycopg2.extras.DictCursor
    )

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                details TEXT NOT NULL,
                cat1 NUMERIC DEFAULT 0,
                cat2 NUMERIC DEFAULT 0,
                cat3 NUMERIC DEFAULT 0,
                cat4 NUMERIC DEFAULT 0,
                cat5 NUMERIC DEFAULT 0,
                remarks TEXT,
                income NUMERIC DEFAULT 0,
                username TEXT NOT NULL
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database table 'expenses' is ready.")
    except Exception as e:
        print(f"❌ Database error: {e}")

init_db()

# --- Auth Helper ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    redirect_uri = url_for('auth', _external=True)
    return oauth.keycloak.authorize_redirect(redirect_uri)

@app.route('/auth')
def auth():
    token = oauth.keycloak.authorize_access_token()
    user_info = token.get('userinfo')
    if user_info:
        session['user'] = user_info
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    metadata = oauth.keycloak.load_server_metadata()
    end_session_endpoint = metadata.get('end_session_endpoint')
    if end_session_endpoint:
        # Logout URL with proper parameters for Keycloak
        return redirect(end_session_endpoint + 
                        f"?post_logout_redirect_uri={url_for('index', _external=True)}" +
                        f"&client_id={os.environ.get('KEYCLOAK_CLIENT_ID')}")
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=session['user'])

# --- Unified Expense API (Fixing 405 error) ---

@app.route("/api/expense", methods=["GET", "POST"])
@login_required
def handle_expense():
    user_email = session['user']['email']
    
    if request.method == "POST":
        # Data သိမ်းဆည်းခြင်း
        data = request.json
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO expenses (date, details, cat1, cat2, cat3, cat4, cat5, remarks, income, username) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (data['date'], data['details'], data['cat1'], data['cat2'], data['cat3'], 
                 data['cat4'], data['cat5'], data['remarks'], data.get('income', 0), user_email)
            )
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({"message": "Successfully saved!"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    else:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM expenses WHERE username = %s ORDER BY date DESC", (user_email,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            expenses = []
            for row in rows:
                expenses.append({
                    "date": str(row['date']),
                    "details": row['details'],
                    "cat1": float(row['cat1']),
                    "cat2": float(row['cat2']),
                    "cat3": float(row['cat3']),
                    "cat4": float(row['cat4']),
                    "cat5": float(row['cat5']),
                    "income": float(row['income']),
                    "remarks": row['remarks']
                })
            return jsonify(expenses), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)