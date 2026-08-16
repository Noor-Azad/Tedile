from app.models.student import Student

PARENT_CHILDREN = [
    Student("Ayesha Rahman", "Class 4-A", "Rahima Karim", "01700000001", 96, "Good"),
    Student("Rafi Islam", "Class 6-B", "Rahima Karim", "01700000001", 89, "Needs Follow-up"),
    Student("Nusrat Jahan", "Class 7-A", "Mofiz Uddin", "01720000009", 92, "Good"),
]


def get_parent_children(parent_name, parent_phone):
    return [
        child for child in PARENT_CHILDREN
        if child.parent_name.lower() == parent_name.lower()
        and (not parent_phone or child.parent_phone == parent_phone)
    ]
