import os
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from functools import wraps

# .env ဖိုင်ကို ဖတ်ခြင်း
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
CORS(app)

# Keycloak နဲ့ ချိတ်ဆက်ရန် Setup လုပ်ခြင်း
oauth = OAuth(app)
oauth.register(
    name='keycloak',
    client_id=os.environ.get("KEYCLOAK_CLIENT_ID"),
    client_secret=os.environ.get("KEYCLOAK_CLIENT_SECRET"),
    server_metadata_url=os.environ.get("KEYCLOAK_METADATA_URL"),
    client_kwargs={'scope': 'openid profile email'},
)

# Database ချိတ်ဆက်မှု
def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"), cursor_factory=psycopg2.extras.DictCursor)

# Login ဝင်ထားသူသာ ဝင်လို့ရအောင် စစ်ဆေးပေးသည့် Helper
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
    # Keycloak Login Page ဆီသို့ လွှတ်လိုက်ခြင်း
    redirect_uri = url_for('auth', _external=True)
    return oauth.keycloak.authorize_redirect(redirect_uri)

@app.route('/auth')
def auth():
    # Keycloak က ပြန်ပို့ပေးတဲ့ အချက်အလက်ကို လက်ခံခြင်း
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
        return redirect(end_session_endpoint + f"?post_logout_redirect_uri={url_for('index', _external=True)}&client_id={os.environ.get('KEYCLOAK_CLIENT_ID')}")
    
    return redirect(url_for('index'))
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=session['user'])

# API အတွက် (Expenses သိမ်းဆည်းခြင်း)
@app.route("/api/expense", methods=["POST"])
@login_required
def add_expense():
    data = request.json
    user_email = session['user']['email']
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (date, details, cat1, cat2, cat3, cat4, cat5, remarks, income, username) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (data['date'], data['details'], data['cat1'], data['cat2'], data['cat3'], data['cat4'], data['cat5'], data['remarks'], data['income'], user_email)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Saved!"}), 201

if __name__ == "__main__":
    app.run(port=5000, debug=True)