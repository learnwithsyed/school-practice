import sqlite3

DB_NAME = "questions.db"

def get_db_connection():
    conn = sqlite3.connect(
        DB_NAME,
        timeout=10,                 # ✅ waits instead of locking
        check_same_thread=False     # ✅ allows Flask multi-requests
    )
    conn.row_factory = sqlite3.Row
    return conn
