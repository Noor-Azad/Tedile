from app.models.user import User

USERS = {
    "admin@bengallearningcenter.com": User("admin@bengallearningcenter.com", "admin123", "Admin", "Admin Officer"),
    "teacher@bengallearningcenter.com": User("teacher@bengallearningcenter.com", "teacher123", "Teacher", "Farah Ahmed"),
    "parent@bengallearningcenter.com": User("parent@bengallearningcenter.com", "parent123", "Parent", "Rahima Karim", "01700000001"),
}


def authenticate_user(email, password, role):
    user = USERS.get(email.lower())
    if not user:
        return None
    if user.password != password:
        return None
    if user.role != role:
        return None
    return user
