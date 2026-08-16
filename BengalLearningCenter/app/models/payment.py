from dataclasses import dataclass


@dataclass
class PaymentRecord:
    student_name: str
    title: str
    amount: str
    status: str
