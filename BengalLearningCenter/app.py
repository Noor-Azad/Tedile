from datetime import date, datetime, timedelta

from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = "bengal-learning-center-secret-key"

USERS = {
    "admin@bengallearningcenter.com": {"password": "admin123", "role": "Admin", "name": "Admin Officer"},
    "teacher@bengallearningcenter.com": {"password": "teacher123", "role": "Teacher", "name": "Farah Ahmed"},
    "parent@bengallearningcenter.com": {"password": "parent123", "role": "Parent", "name": "Rahima Karim"},
}

STAFF_ATTENDANCE = [
    {"name": "Md. Rahman", "role": "Principal", "status": "Present", "time": "8:45 AM", "email": "admin@bengallearningcenter.com", "approved": True},
    {"name": "Farah Ahmed", "role": "Teacher", "status": "Present", "time": "8:50 AM", "email": "teacher@bengallearningcenter.com", "approved": True},
    {"name": "Sajjad Ali", "role": "Teacher", "status": "Late", "time": "9:20 AM", "email": "sajjad@bengallearningcenter.com", "approved": True},
    {"name": "Nadia Islam", "role": "Office Staff", "status": "Absent", "time": "-", "email": "nadia@bengallearningcenter.com", "approved": True},
    {"name": "Imran Hossain", "role": "Accountant", "status": "Present", "time": "8:55 AM", "email": "imran@bengallearningcenter.com", "approved": True},
]

ADMIN_DATA = {
    "stats": [
        {"label": "Total Students", "value": "1245", "tone": "blue"},
        {"label": "Staff Members", "value": "87", "tone": "green"},
        {"label": "Present Staff", "value": "74", "tone": "gold"},
        {"label": "Pending Fees", "value": "218", "tone": "red"},
    ],
    "staff": [
        {"name": "Md. Rahman", "role": "Principal", "status": "Present", "time": "8:45 AM"},
        {"name": "Farah Ahmed", "role": "Teacher", "status": "Present", "time": "8:50 AM"},
        {"name": "Sajjad Ali", "role": "Teacher", "status": "Late", "time": "9:20 AM"},
        {"name": "Nadia Islam", "role": "Office Staff", "status": "Absent", "time": "-"},
        {"name": "Imran Hossain", "role": "Accountant", "status": "Present", "time": "8:55 AM"},
    ],
    "classes": [
        {"name": "Class 1-A", "present": 28, "absent": 3, "rate": 90},
        {"name": "Class 2-B", "present": 31, "absent": 2, "rate": 94},
        {"name": "Class 3-C", "present": 27, "absent": 4, "rate": 87},
        {"name": "Class 5-A", "present": 30, "absent": 1, "rate": 97},
    ],
    "notices": [
        {"title": "Parent Meeting", "category": "General", "date": "2026-08-16", "message": "Parents are invited to the monthly meeting with class teachers."},
        {"title": "Annual Sports Event", "category": "Event", "date": "2026-08-18", "message": "The school annual sports event will be held on the main field at 9:00 AM."},
        {"title": "Fee Deadline", "category": "Finance", "date": "2026-08-20", "message": "All confirmed school fees must be cleared before the due date."},
    ],
    "fees": [
        {"student": "Ayesha Rahman", "class_name": "Class 4-A", "amount": "৳ 6,000", "status": "Paid"},
        {"student": "Rafi Islam", "class_name": "Class 6-B", "amount": "৳ 5,700", "status": "Pending"},
        {"student": "Nusrat Jahan", "class_name": "Class 7-A", "amount": "৳ 2,200", "status": "Partially Paid"},
        {"student": "Tanim Hossain", "class_name": "Class 9-C", "amount": "৳ 7,800", "status": "Pending"},
    ],
}

TEACHER_DATA = {
    "stats": [
        {"label": "My Classes", "value": "6", "tone": "blue"},
        {"label": "Students Present", "value": "182", "tone": "green"},
        {"label": "Students Absent", "value": "12", "tone": "red"},
        {"label": "Assignments", "value": "09", "tone": "gold"},
    ],
    "classes": [
        {"name": "Class 5-A", "strength": 36, "attendance": 92},
        {"name": "Class 6-B", "strength": 34, "attendance": 89},
        {"name": "Class 8-C", "strength": 38, "attendance": 94},
    ],
    "tasks": [
        {"title": "Submit class attendance", "due": "Today"},
        {"title": "Prepare maths revision sheet", "due": "Tomorrow"},
        {"title": "Send parent update", "due": "Friday"},
    ],
    "notices": [
        {"title": "Science lab update", "message": "The science lab timetable is shifted to Thursday."},
        {"title": "Exam schedule", "message": "Unit test exam will be conducted next Monday."},
    ],
}

PARENT_DATA = {
    "stats": [
        {"label": "Child Attendance", "value": "96%", "tone": "green"},
        {"label": "Fees Due", "value": "৳ 5,700", "tone": "red"},
        {"label": "Notices", "value": "03", "tone": "blue"},
        {"label": "Messages", "value": "02", "tone": "gold"},
    ],
    "child": [
        {"name": "Ayesha Rahman", "class_name": "Class 4-A", "attendance": 96, "status": "Good"},
        {"name": "Rafi Islam", "class_name": "Class 6-B", "attendance": 89, "status": "Needs Follow-up"},
    ],
    "fees": [
        {"title": "Tuition Fees", "amount": "৳ 4,800", "status": "Paid"},
        {"title": "Exam Fees", "amount": "৳ 900", "status": "Pending"},
    ],
    "notices": [
        {"title": "Parent Meeting", "date": "2026-08-16", "message": "Please attend the monthly meeting with the class teacher."},
        {"title": "Holiday Notice", "date": "2026-08-20", "message": "School will remain closed on the national holiday."},
    ],
}


def get_dashboard_data(role):
    if role == "Admin":
        return ADMIN_DATA
    if role == "Teacher":
        return TEACHER_DATA
    return PARENT_DATA


def get_week_dates(selected_date=None):
    current = selected_date or date.today()
    if isinstance(current, str):
        try:
            current = date.fromisoformat(current)
        except ValueError:
            current = date.today()
    start_of_week = current - timedelta(days=current.weekday())
    return [start_of_week + timedelta(days=i) for i in range(7)]


def build_week_rows(records, week_dates, selected_date, role):
    week_rows = []
    for record in records:
        daily = []
        for day in week_dates:
            iso_day = day.isoformat()
            if role == "Parent":
                status = "Good"
                time = "08:30 AM"
            elif record.get("name") == "Farah Ahmed" and iso_day == selected_date and record.get("approved") is False:
                status = record.get("submitted_status", record.get("status", "Present"))
                time = record.get("time", "8:50 AM")
            elif record.get("status") == "Pending Approval" and iso_day == record.get("selected_date"):
                status = "Pending Approval"
                time = record.get("time", "-")
            elif day.weekday() < 5:
                status = record.get("status", "Present")
                time = record.get("time", "8:50 AM")
            else:
                status = "Absent"
                time = "-"
            daily.append({"date": day, "status": status, "time": time})
        week_rows.append({
            "name": record["name"],
            "role": record["role"],
            "days": daily,
        })
    return week_rows


@app.route("/")
def login_page():
    if session.get("user"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "")

    user = USERS.get(email)
    if not user or user["password"] != password or user["role"] != role:
        return render_template("index.html", error="Invalid email, password, or selected role.")

    session["user"] = {"email": email, "name": user["name"], "role": user["role"]}
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        return redirect(url_for("login_page"))

    role = user["role"]
    data = get_dashboard_data(role)
    return render_template("dashboard.html", user=user, role=role, data=data)


@app.route("/attendance")
def attendance_page():
    user = session.get("user")
    if not user:
        return redirect(url_for("login_page"))

    selected_date = request.args.get("date") or date.today().isoformat()
    week_dates = get_week_dates(selected_date)
    role = user["role"]

    if role == "Parent":
        records = [
            {"name": "Ayesha Rahman", "class_name": "Class 4-A", "status": "Good", "attendance": 96},
            {"name": "Rafi Islam", "class_name": "Class 6-B", "status": "Needs Follow-up", "attendance": 89},
        ]
        week_rows = []
        for record in records:
            week_rows.append({
                "name": record["name"],
                "role": record["class_name"],
                "days": [{"date": day, "status": record["status"], "time": "08:30 AM"} for day in week_dates],
            })
    else:
        records = list(STAFF_ATTENDANCE)
        week_rows = build_week_rows(records, week_dates, selected_date, role)

    return render_template(
        "attendance.html",
        user=user,
        role=role,
        records=records,
        week_rows=week_rows,
        week_dates=week_dates,
        selected_date=selected_date,
        can_mark_self=(role == "Teacher"),
        current_teacher=user["name"],
    )


@app.route("/attendance/self-mark", methods=["POST"])
def mark_self_attendance():
    user = session.get("user")
    if not user or user["role"] != "Teacher":
        return redirect(url_for("login_page"))

    status = request.form.get("status", "Present")
    selected_date = request.form.get("attendance_date") or date.today().isoformat()
    current_time = datetime.now().strftime("%I:%M %p")

    for record in STAFF_ATTENDANCE:
        if record["name"] == user["name"]:
            record["status"] = "Pending Approval"
            record["submitted_status"] = status
            record["time"] = current_time
            record["approved"] = False
            record["selected_date"] = selected_date
            break

    return redirect(url_for("attendance_page", date=selected_date))


@app.route("/attendance/approve", methods=["POST"])
def approve_teacher_attendance():
    user = session.get("user")
    if not user or user["role"] != "Admin":
        return redirect(url_for("login_page"))

    selected_date = request.form.get("attendance_date") or date.today().isoformat()

    for record in STAFF_ATTENDANCE:
        if record.get("role") == "Teacher" and not record.get("approved", True):
            record["status"] = record.get("submitted_status", "Present")
            record["approved"] = True
            record["time"] = record.get("time", "8:50 AM")

    return redirect(url_for("attendance_page", date=selected_date))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False, host="0.0.0.0", port=5001)
