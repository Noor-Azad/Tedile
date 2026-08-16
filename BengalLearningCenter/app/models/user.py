from dataclasses import dataclass


@dataclass
class User:
    email: str
    password: str
    role: str
    name: str
    phone: str = ""
