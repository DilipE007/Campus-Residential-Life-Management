from flask import Flask, render_template, request, redirect, session
import sqlite3
import datetime

app = Flask(__name__)
app.secret_key = "secret"

# ================= DB =================
def get_db():
    return sqlite3.connect("database.db")

# ================= INIT =================
def init_db():
    conn = get_db()
    cur = conn.cursor()

    # USERS (FULL DETAILS)
    cur.execute('''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        room TEXT,
        reg_no TEXT,
        year TEXT,
        department TEXT,
        parent_name TEXT,
        parent_phone TEXT,
        address TEXT
    )''')

    # ROOMS
    cur.execute('''CREATE TABLE IF NOT EXISTS rooms(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_no TEXT,
        capacity INTEGER,
        ac TEXT,
        bathroom TEXT
    )''')

    # ROOM ALLOCATION
    cur.execute('''CREATE TABLE IF NOT EXISTS room_allocations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_no TEXT,
        student TEXT
    )''')

    # FEES
    cur.execute('''CREATE TABLE IF NOT EXISTS fees(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        amount INTEGER,
        status TEXT
    )''')

    # ATTENDANCE
    cur.execute('''CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student TEXT,
        date TEXT,
        status TEXT
    )''')

    # MESS
    cur.execute('''CREATE TABLE IF NOT EXISTS mess(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT,
        breakfast TEXT,
        lunch TEXT,
        dinner TEXT
    )''')

    # COMPLAINTS
    cur.execute('''CREATE TABLE IF NOT EXISTS complaints(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        issue TEXT,
        status TEXT
    )''')

    # EMERGENCY
    cur.execute('''CREATE TABLE IF NOT EXISTS emergency(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student TEXT,
        name TEXT,
        phone TEXT,
        relation TEXT
    )''')

    # DEFAULT ROOMS
    cur.execute("SELECT COUNT(*) FROM rooms")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO rooms(room_no,capacity,ac,bathroom) VALUES ('101',2,'AC','Attached')")
        cur.execute("INSERT INTO rooms(room_no,capacity,ac,bathroom) VALUES ('102',3,'Non-AC','Common')")

    # DEFAULT MESS
    cur.execute("SELECT COUNT(*) FROM mess")
    if cur.fetchone()[0] == 0:
        days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        for d in days:
            cur.execute("INSERT INTO mess(day,breakfast,lunch,dinner) VALUES (?,?,?,?)",
                        (d,"Idli","Meals","Chapati"))

    conn.commit()
    conn.close()

init_db()

# ================= REGISTER =================
# REGISTER
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        f = request.form
        conn = get_db()
        cur = conn.cursor()

        # 🔍 CHECK IF USER EXISTS
        cur.execute("SELECT * FROM users WHERE username=?", (f["username"],))
        existing = cur.fetchone()

        if existing:
            conn.close()
            return "⚠️ Username already exists! Try different username"

        # ✅ INSERT NEW USER
        cur.execute("""INSERT INTO users
        (username,password,role,room,reg_no,year,department,parent_name,parent_phone,address)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (f["username"], f["password"], f["role"], "Not Assigned",
         f.get("reg_no",""), f.get("year",""), f.get("department",""),
         f.get("parent_name",""), f.get("parent_phone",""), f.get("address","")))

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("register.html")

# ================= LOGIN =================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?",
                    (request.form["username"], request.form["password"]))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = user[1]
            session["role"] = user[3]
            return redirect("/dashboard")

        return "Invalid Login"

    return render_template("login.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    role = session["role"]

    # ================= ADMIN =================
    if role == "admin":
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT username, room FROM users WHERE role='student'")
        students = cur.fetchall()

        cur.execute("SELECT COUNT(*) FROM users WHERE role='student'")
        total_students = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM rooms")
        total_rooms = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM users WHERE room!='Not Assigned'")
        occupied = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
        pending_complaints = cur.fetchone()[0]

        cur.execute("SELECT SUM(amount) FROM fees")
        fees = cur.fetchone()[0] or 0

        conn.close()

        return render_template("admin_dashboard.html",
                               students=students,
                               total_students=total_students,
                               total_rooms=total_rooms,
                               occupied=occupied,
                               pending_complaints=pending_complaints,
                               fees=fees)

    # ================= STAFF =================
    elif role == "staff":
        return render_template("staff_dashboard.html")

    # ================= STUDENT =================
    else:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT room FROM users WHERE username=?", (session["user"],))
        room = cur.fetchone()

        # attendance %
        cur.execute("SELECT COUNT(*) FROM attendance WHERE student=?", (session["user"],))
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM attendance WHERE student=? AND status='Present'", (session["user"],))
        present = cur.fetchone()[0]

        percent = round((present/total)*100,2) if total else 0

        # fees
        cur.execute("SELECT SUM(amount) FROM fees WHERE user=?", (session["user"],))
        paid = cur.fetchone()[0] or 0
        due = 5000 - paid

        notifications = []

        if due > 0:
            notifications.append("⚠ Fee Pending")

        if percent < 75:
            notifications.append("⚠ Low Attendance")

        conn.close()

        return render_template("student_dashboard.html",
                               room=room,
                               attendance_percentage=percent,
                               notifications=notifications)
# ================= ROOMS =================
@app.route("/rooms", methods=["GET","POST"])
def rooms():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST" and session["role"] == "student":
        room = request.form["room"]

        cur.execute("UPDATE users SET room=? WHERE username=?", (room, session["user"]))
        cur.execute("INSERT INTO room_allocations(room_no,student) VALUES (?,?)",
                    (room, session["user"]))
        conn.commit()

    cur.execute("SELECT * FROM rooms")
    rooms = cur.fetchall()

    cur.execute("SELECT * FROM room_allocations")
    allocations = cur.fetchall()

    conn.close()

    return render_template("rooms.html", rooms=rooms, allocations=allocations, role=session["role"])

# ================= MESS =================
@app.route("/mess")
def mess():
    if "user" not in session:
        return redirect("/")

    today = datetime.datetime.now().strftime("%A")
    week = request.args.get("week")

    conn = get_db()
    cur = conn.cursor()

    if week:
        # FULL WEEK (for all roles)
        cur.execute("SELECT * FROM mess")
        menu = cur.fetchall()
        view = "week"
    else:
        # TODAY ONLY
        cur.execute("SELECT * FROM mess WHERE day=?", (today,))
        menu = cur.fetchall()
        view = "today"

    conn.close()

    return render_template("mess.html",
                           menu=menu,
                           role=session["role"],
                           view=view,
                           today=today) 

# ================= FEES =================
@app.route("/fees", methods=["GET","POST"])
def fees():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    if session["role"] == "student" and request.method == "POST":
        cur.execute("INSERT INTO fees(user,amount,status) VALUES (?,?,?)",
                    (session["user"], request.form["amount"], "Paid"))
        conn.commit()

    if session["role"] == "admin":
        cur.execute("SELECT * FROM fees")
        data = cur.fetchall()
        conn.close()
        return render_template("fees_admin.html", fees=data)

    else:
        cur.execute("SELECT * FROM fees WHERE user=?", (session["user"],))
        data = cur.fetchall()

        total_paid = sum([x[2] for x in data])
        due = max(5000 - total_paid, 0)

        conn.close()
        return render_template("fees_student.html", fees=data, due=due)

# ================= ATTENDANCE =================
@app.route("/attendance", methods=["GET","POST"])
def attendance():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    if session["role"] == "staff" and request.method == "POST":
        cur.execute("INSERT INTO attendance(student,date,status) VALUES (?,?,?)",
                    (request.form["student"], request.form["date"], request.form["status"]))
        conn.commit()

    if session["role"] == "student":
        cur.execute("SELECT * FROM attendance WHERE student=?", (session["user"],))
        data = cur.fetchall()
        conn.close()
        return render_template("attendance_student.html", data=data)

    elif session["role"] == "staff":
        cur.execute("SELECT username FROM users WHERE role='student'")
        students = cur.fetchall()
        conn.close()
        return render_template("attendance_staff.html", students=students)

    else:
        cur.execute("SELECT * FROM attendance")
        data = cur.fetchall()
        conn.close()
        return render_template("attendance_admin.html", data=data)

# ================= COMPLAINT =================
@app.route("/complaint", methods=["GET","POST"])
def complaint():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    # ✅ ONLY STUDENT CAN SUBMIT
    if session["role"] == "student" and request.method == "POST":
        issue = request.form["issue"]
        cur.execute("INSERT INTO complaints(user,issue,status) VALUES (?,?,?)",
                    (session["user"], issue, "Pending"))
        conn.commit()

    # 🔍 STUDENT → see only their complaints
    if session["role"] == "student":
        cur.execute("SELECT * FROM complaints WHERE user=?", (session["user"],))

    # 🔍 ADMIN & STAFF → see ALL complaints
    else:
        cur.execute("SELECT * FROM complaints")

    data = cur.fetchall()
    conn.close()

    return render_template("complaint.html",
                           data=data,
                           role=session["role"]) 
@app.route("/resolve_complaint/<int:id>")
def resolve_complaint(id):
    if session["role"] not in ["admin", "staff"]:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE complaints SET status='Resolved' WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/complaint") 


# ================= EMERGENCY =================
@app.route("/emergency", methods=["GET","POST"])
def emergency():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    # STUDENT → ADD CONTACT
    if session["role"] == "student" and request.method == "POST":
        cur.execute("INSERT INTO emergency(student,name,phone) VALUES (?,?,?)",
                    (session["user"], request.form["name"], request.form["phone"]))
        conn.commit()

    # ADMIN → SEE ALL STUDENTS
    if session["role"] == "admin":
        cur.execute("SELECT * FROM emergency")
    else:
        cur.execute("SELECT * FROM emergency WHERE student=?", (session["user"],))

    data = cur.fetchall()
    conn.close()

    return render_template("emergency_student.html",
                           data=data,
                           role=session["role"]) 

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True) 