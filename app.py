from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from database import get_db_connection
from datetime import date, datetime
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = "super_secret_key"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= VISIT LOG =================
def log_visit():
    db = get_db_connection()
    today = date.today().isoformat()
    ip = request.remote_addr

    exists = db.execute(
        "SELECT 1 FROM site_visits WHERE visit_date=? AND visitor_ip=?",
        (today, ip)
    ).fetchone()

    if not exists:
        db.execute(
            "INSERT INTO site_visits (visit_date, visitor_ip) VALUES (?, ?)",
            (today, ip)
        )
        db.commit()
    db.close()


# ================= DAILY LIMIT =================
def check_daily_limit():
    if "quiz_attempts" not in session:
        session["quiz_attempts"] = []

    today = str(date.today())
    return session["quiz_attempts"].count(today) < 3


# ================= INDEX =================
@app.route("/")
def index():
    log_visit()
    return render_template("index.html")


# ================= START QUIZ =================
@app.route("/start-quiz", methods=["POST"])
def start_quiz():
    if not check_daily_limit():
        flash("Daily free limit reached.", "error")
        return redirect(url_for("index"))

    try:
        cls = int(request.form["class"])
        subject = request.form["subject"]
        difficulty = request.form["difficulty"]
        total_q = int(request.form["questions"])
    except:
        flash("Invalid selection", "error")
        return redirect(url_for("index"))

    db = get_db_connection()
    rows = db.execute("""
        SELECT * FROM questions
        WHERE class=? AND subject=? AND difficulty=?
        ORDER BY RANDOM()
        LIMIT ?
    """, (cls, subject, difficulty, total_q)).fetchall()

    if not rows:
        db.close()
        flash("No questions found", "error")
        return redirect(url_for("index"))

    db.execute("""
        INSERT INTO quiz_attempts (quiz_date, student_ip, class, subject)
        VALUES (?, ?, ?, ?)
    """, (date.today().isoformat(), request.remote_addr, cls, subject))
    db.commit()
    db.close()

    session["quiz"] = [dict(r) for r in rows]
    session["index"] = 0
    session["score"] = 0
    session["answers"] = []
    session["quiz_attempts"].append(str(date.today()))

    return redirect(url_for("quiz"))


# ================= QUIZ =================
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "quiz" not in session:
        return redirect(url_for("index"))

    i = session["index"]
    quiz = session["quiz"]

    if i >= len(quiz):
        return redirect(url_for("quiz_result"))

    q = quiz[i]

    if request.method == "POST":
        selected = request.form.get("answer")
        correct = q["correct_option"]

        session["answers"].append({
            "question": q["question"],
            "selected": selected,
            "correct": correct,
            "explanation": q["explanation"]
        })

        db = get_db_connection()
        if selected == correct:
            session["score"] += 1
            db.execute("""
                INSERT INTO question_stats (question_id, attempted, wrong)
                VALUES (?,1,0)
                ON CONFLICT(question_id)
                DO UPDATE SET attempted = attempted + 1
            """, (q["id"],))
        else:
            db.execute("""
                INSERT INTO question_stats (question_id, attempted, wrong)
                VALUES (?,1,1)
                ON CONFLICT(question_id)
                DO UPDATE SET attempted = attempted + 1, wrong = wrong + 1
            """, (q["id"],))
        db.commit()
        db.close()

        session["index"] += 1
        return redirect(url_for("quiz"))

    return render_template(
        "quiz_question.html",
        q=q,
        qno=i + 1,
        total=len(quiz),
        score=session["score"]
    )


# ================= RESULT =================
@app.route("/quiz/result")
def quiz_result():
    score = session.get("score", 0)
    total = len(session.get("quiz", []))
    answers = session.get("answers", [])

    session.clear()

    return render_template("quiz_result.html", score=score, total=total, answers=answers)


# ================= FEEDBACK (USER / WEBMASTER) =================
@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        message = request.form["message"]

        role = session.get("role", "guest")
        if role == "webmaster":
            username = f"webmaster_{session.get('webmaster_id')}"
        elif role == "admin":
            username = "admin"
        else:
            username = "guest"

        db = get_db_connection()
        db.execute("""
            INSERT INTO feedback (user_role, username, message, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            role,
            username,
            message,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        db.commit()
        db.close()

        return redirect(url_for("feedback_success"))

    return render_template("feedback.html")


# ================= ADMIN LOGIN =================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        db = get_db_connection()
        admin = db.execute(
            "SELECT * FROM admins WHERE username=?",
            (request.form["username"],)
        ).fetchone()
        db.close()

        if admin and check_password_hash(admin["password_hash"], request.form["password"]):
            session.clear()
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))

        flash("Invalid credentials", "error")

    return render_template("admin_login.html")


# ================= ADMIN DASHBOARD =================
@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    db = get_db_connection()
    webmasters = db.execute(
        "SELECT id, name, username FROM webmasters ORDER BY id DESC"
    ).fetchall()
    db.close()

    return render_template("admin_dashboard.html", webmasters=webmasters)


# ================= ADMIN ANALYTICS =================
@app.route("/admin/analytics")
def admin_analytics():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    db = get_db_connection()

    total_students = db.execute(
        "SELECT COUNT(DISTINCT student_ip) FROM quiz_attempts"
    ).fetchone()[0]

    most_attempted_class = db.execute("""
        SELECT class, COUNT(*) as cnt
        FROM quiz_attempts
        GROUP BY class
        ORDER BY cnt DESC
        LIMIT 1
    """).fetchone()

    difficult_questions = db.execute("""
        SELECT q.question, qs.wrong, qs.attempted
        FROM question_stats qs
        JOIN questions q ON q.id = qs.question_id
        ORDER BY qs.wrong DESC
        LIMIT 5
    """).fetchall()

    daily_traffic = db.execute("""
        SELECT visit_date, COUNT(*) as visits
        FROM site_visits
        GROUP BY visit_date
        ORDER BY visit_date DESC
        LIMIT 7
    """).fetchall()

    db.close()

    return render_template(
        "admin_analytics.html",
        total_students=total_students,
        most_attempted_class=most_attempted_class,
        difficult_questions=difficult_questions,
        daily_traffic=daily_traffic
    )


# ================= ADMIN FEEDBACK =================
@app.route("/admin/feedback")
def admin_feedback():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    db = get_db_connection()
    feedbacks = db.execute("""
        SELECT * FROM feedback
        ORDER BY created_at DESC
    """).fetchall()
    db.close()

    return render_template("admin_feedback.html", feedbacks=feedbacks)


# ================= ADMIN LOGOUT =================
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# ================= WEBMASTER =================
@app.route("/webmaster/signup", methods=["GET", "POST"])
def webmaster_signup():
    if request.method == "POST":
        db = get_db_connection()
        try:
            db.execute("""
                INSERT INTO webmasters (name, username, password_hash, keyword)
                VALUES (?, ?, ?, ?)
            """, (
                request.form["name"],
                request.form["username"],
                generate_password_hash(request.form["password"]),
                request.form["keyword"]
            ))
            db.commit()
            flash("Signup successful. Please login.", "success")
            return redirect(url_for("webmaster_login"))
        except:
            flash("Username already exists", "error")
        finally:
            db.close()

    return render_template("webmaster_signup.html")


@app.route("/webmaster/login", methods=["GET", "POST"])
def webmaster_login():
    if request.method == "POST":
        db = get_db_connection()
        user = db.execute(
            "SELECT * FROM webmasters WHERE username=?",
            (request.form["username"],)
        ).fetchone()
        db.close()

        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session.clear()
            session["role"] = "webmaster"
            session["webmaster_id"] = user["id"]
            return redirect(url_for("webmaster_dashboard"))

        flash("Invalid login", "error")

    return render_template("webmaster_login.html")


@app.route("/webmaster/dashboard")
def webmaster_dashboard():
    if session.get("role") != "webmaster":
        return redirect(url_for("webmaster_login"))
    return render_template("webmaster_dashboard.html")


@app.route("/webmaster/questions")
def webmaster_questions():
    if session.get("role") != "webmaster":
        return redirect(url_for("webmaster_login"))

    db = get_db_connection()
    questions = db.execute(
        "SELECT * FROM questions WHERE created_by=?",
        (session["webmaster_id"],)
    ).fetchall()
    db.close()

    return render_template("view_questions.html", questions=questions)

@app.route("/webmaster/questions/add", methods=["GET", "POST"])
def add_question():
    if session.get("role") != "webmaster":
        return redirect(url_for("webmaster_login"))

    if request.method == "POST":
        db = get_db_connection()
        db.execute("""
            INSERT INTO questions
            (class, subject, difficulty, question,
             option_a, option_b, option_c, option_d,
             correct_option, explanation, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(request.form["class"]),
            request.form["subject"],
            request.form["difficulty"],
            request.form["question"],
            request.form["option_a"],
            request.form["option_b"],
            request.form["option_c"],
            request.form["option_d"],
            request.form["correct_option"],
            request.form["explanation"],
            session["webmaster_id"]
        ))
        db.commit()
        db.close()

        flash("Question added successfully", "success")
        return redirect(url_for("webmaster_questions"))

    return render_template("add_question.html")

@app.route("/webmaster/upload", methods=["GET", "POST"])
def upload_excel():
    if session.get("role") != "webmaster":
        return redirect(url_for("webmaster_login"))

    if request.method == "POST":
        file = request.files.get("file")

        if not file or file.filename == "":
            flash("No file selected", "error")
            return redirect(url_for("upload_excel"))

        path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(path)

        try:
            df = pd.read_excel(path)

            db = get_db_connection()
            cursor = db.cursor()

            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO questions
                    (class, subject, difficulty, question,
                     option_a, option_b, option_c, option_d,
                     correct_option, explanation, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(row["class"]),
                    str(row["subject"]).strip(),
                    str(row["difficulty"]).strip(),
                    str(row["question"]).strip(),
                    str(row["option_a"]).strip(),
                    str(row["option_b"]).strip(),
                    str(row["option_c"]).strip(),
                    str(row["option_d"]).strip(),        # ✅ prevents NULL
                    str(row["correct_option"]).strip().upper(),
                    str(row["explanation"]).strip(),
                    session["webmaster_id"]
                ))

            # ✅ commit ONCE (important)
            db.commit()
            db.close()

            flash("Excel uploaded successfully", "success")
            return redirect(url_for("webmaster_questions"))

        except Exception as e:
            flash(f"Upload failed: {e}", "error")
            return redirect(url_for("upload_excel"))

    return render_template("upload_excel.html")

@app.route("/webmaster/logout")
def webmaster_logout():
    session.clear()
    return redirect(url_for("webmaster_login"))

@app.route("/feedback/success")
def feedback_success():
    return render_template("feedback_success.html")

from datetime import date

@app.context_processor
def inject_globals():
    return {
        "current_year": date.today().year,
        "current_date": date.today().strftime("%d %B %Y")
    }

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

# ================= RUN =================
if __name__ == "__main__":
    app.run()

