from app.models.attendance import AttendanceRecord
from app.models.payment import PaymentRecord

ATTENDANCE_LOGS = [
    AttendanceRecord("Ayesha Rahman", "2026-08-01", "Present", "08:10", "15:45"),
    AttendanceRecord("Ayesha Rahman", "2026-08-02", "Present", "08:12", "15:40"),
    AttendanceRecord("Ayesha Rahman", "2026-08-03", "Late", "08:28", "15:47"),
    AttendanceRecord("Rafi Islam", "2026-08-01", "Present", "08:05", "15:50"),
    AttendanceRecord("Rafi Islam", "2026-08-02", "Absent", "", ""),
]

PARENT_MARKED_ATTENDANCE = []

PAYMENT_DUE = [
    PaymentRecord("Ayesha Rahman", "Monthly Tuition", "1200", "Due"),
    PaymentRecord("Rafi Islam", "Monthly Tuition", "1500", "Due"),
    PaymentRecord("Nusrat Jahan", "Monthly Tuition", "1300", "Paid"),
]


def mark_parent_attendance(parent_name, parent_phone, child_statuses):
    from app.services.parent_service import get_parent_children

    children = get_parent_children(parent_name, parent_phone)
    if not children:
        return []

    saved = []
    for child in children:
        status = child_statuses.get(child.name, "Present")
        record = AttendanceRecord(child.name, "2026-08-16", status, "08:30", "15:45")
        ATTENDANCE_LOGS.append(record)
        saved.append(record)
        PARENT_MARKED_ATTENDANCE.append({
            "parent_name": parent_name,
            "parent_phone": parent_phone,
            "child_name": child.name,
            "status": status,
            "date": "2026-08-16",
        })

    return saved


def get_parent_dashboard(parent_name, parent_phone):
    children = []
    attendance = []
    payments = []

    from app.services.parent_service import get_parent_children

    children = get_parent_children(parent_name, parent_phone)
    child_names = {child.name for child in children}
    attendance = [rec for rec in ATTENDANCE_LOGS if rec.student_name in child_names]
    payments = [rec for rec in PAYMENT_DUE if rec.student_name in child_names]

    return {
        "children": children,
        "attendance": attendance,
        "payments": payments,
        "total_due": sum(int(item.amount) for item in payments if item.status == "Due"),
        "school_note": "Teacher attendance is the primary school record; parent entries act as confirmation for family updates.",
    }
