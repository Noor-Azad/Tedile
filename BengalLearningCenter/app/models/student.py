from dataclasses import dataclass


@dataclass
class Student:
    name: str
    class_name: str
    parent_name: str
    parent_phone: str
    attendance: int = 0
    status: str = "Good"
