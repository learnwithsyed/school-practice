from database import get_db_connection

def create_feedback_table():
    db = get_db_connection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_role TEXT,
            username TEXT,
            message TEXT NOT NULL,
            created_at TEXT
        )
    """)
    db.commit()
    db.close()
    print("✅ Feedback table created successfully")

if __name__ == "__main__":
    create_feedback_table()
