from dataclasses import dataclass


@dataclass
class AttendanceRecord:
    student_name: str
    date: str
    status: str
    arrival: str = ""
    departure: str = ""
