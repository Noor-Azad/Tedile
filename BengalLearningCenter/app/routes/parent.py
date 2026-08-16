from datetime import date, timedelta

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models.document import DocumentUpload
from app.services.dashboard_service import get_parent_dashboard, mark_parent_attendance
from app.services.storage_service import StorageService

parent_bp = Blueprint("parent", __name__)


def get_week_dates(selected_date=None):
    current = date.fromisoformat(selected_date) if selected_date else date.today()
    start_of_week = current - timedelta(days=current.weekday())
    return [start_of_week + timedelta(days=i) for i in range(7)]


@parent_bp.route("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        return render_template("index.html", error="Please log in first.")

    if user.get("role") != "Parent":
        return render_template("dashboard.html", user=user, role=user.get("role"), data={})

    payload = get_parent_dashboard(user.get("name", ""), user.get("phone", ""))
    payload["uploaded_documents"] = session.get("uploaded_documents", [])
    return render_template(
        "dashboard.html",
        user=user,
        role=user.get("role"),
        data=payload,
    )


@parent_bp.route("/documents/upload", methods=["POST"])
def upload_document():
    user = session.get("user")
    if not user:
        return redirect(url_for("auth.login_page"))

    upload_file = request.files.get("file")
    category = request.form.get("category", "documents")
    if not upload_file or not upload_file.filename:
        return redirect(url_for("parent.dashboard"))

    storage = StorageService()
    record_id = user.get("email") or user.get("name") or "parent"
    public_url, storage_key = storage.upload_file(upload_file, category, record_id)

    uploaded_documents = session.setdefault("uploaded_documents", [])
    document_record = {
        "category": category,
        "filename": upload_file.filename,
        "storage_key": storage_key,
        "url": public_url,
    }
    uploaded_documents.append(document_record)
    session["uploaded_documents"] = uploaded_documents

    try:
        if db is not None and hasattr(db, "session"):
            db_document = DocumentUpload(
                owner_id=user.get("email") or user.get("name") or "anonymous",
                category=category,
                file_name=upload_file.filename,
                s3_key=storage_key,
                file_url=public_url,
                mime_type=upload_file.mimetype or "application/octet-stream",
            )
            db.session.add(db_document)
            db.session.commit()
    except Exception:
        if db is not None and hasattr(db, "session"):
            db.session.rollback()

    if public_url.startswith("/uploads/"):
        return redirect(url_for("parent.dashboard"))

    return redirect(url_for("parent.dashboard"))


@parent_bp.route("/attendance")
def attendance_page():
    user = session.get("user")
    if not user:
        return render_template("index.html", error="Please log in first.")

    selected_date = request.args.get("date") or date.today().isoformat()
    week_dates = get_week_dates(selected_date)
    payload = get_parent_dashboard(user.get("name", ""), user.get("phone", ""))
    return render_template(
        "attendance.html",
        user=user,
        role=user.get("role"),
        data=payload,
        week_dates=week_dates,
        selected_date=selected_date,
        records=[],
        can_mark_self=False,
    )


@parent_bp.route("/attendance/mark", methods=["POST"])
def mark_attendance():
    user = session.get("user")
    if not user or user.get("role") != "Parent":
        return redirect(url_for("auth.login_page"))

    child_statuses = {}
    for key, value in request.form.items():
        if key.startswith("child_"):
            child_name = key.replace("child_", "", 1)
            child_statuses[child_name] = value

    mark_parent_attendance(user.get("name", ""), user.get("phone", ""), child_statuses)
    return redirect(url_for("parent.attendance_page"))
