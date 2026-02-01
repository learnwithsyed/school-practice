import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "questions.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# ================= SITE VISITS =================
cursor.execute("""
CREATE TABLE IF NOT EXISTS site_visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_date TEXT,
    visitor_ip TEXT
)
""")

# ================= QUIZ ATTEMPTS =================
cursor.execute("""
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_date TEXT,
    student_ip TEXT,
    class INTEGER,
    subject TEXT
)
""")

# ================= QUESTION STATS =================
cursor.execute("""
CREATE TABLE IF NOT EXISTS question_stats (
    question_id INTEGER PRIMARY KEY,
    attempted INTEGER DEFAULT 0,
    wrong INTEGER DEFAULT 0
)
""")

# ================= ADMINS =================
cursor.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password_hash TEXT
)
""")

# ================= WEBMASTERS =================
cursor.execute("""
CREATE TABLE IF NOT EXISTS webmasters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    username TEXT UNIQUE,
    password_hash TEXT,
    keyword TEXT,
    is_active INTEGER DEFAULT 1
)
""")

# ================= QUESTIONS =================
cursor.execute("""
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class INTEGER,
    subject TEXT,
    difficulty TEXT,
    question TEXT,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    correct_option TEXT,
    explanation TEXT,
    created_by INTEGER
)
""")

# ================= SECURITY NOTE =================
# ❌ Default admin creation REMOVED for security reasons
# ✔ Admin accounts should be created manually via:
#    - a protected admin registration page, OR
#    - a one-time separate script (not committed to GitHub)

conn.commit()
conn.close()
print("✅ Database initialized successfully (no default admin)")
