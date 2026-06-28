# schemas/auth.py
from pydantic import BaseModel


class LoginPayload(BaseModel):
    role:     str
    email:    str
    password: str


class StudentSignupPayload(BaseModel):
    first_name:    str
    last_name:     str
    email:         str
    password:      str
    student_code:  str
    semester_id:   int
    department_id: int


class TeacherSignupPayload(BaseModel):
    first_name:    str
    last_name:     str
    email:         str
    password:      str
    teacher_code:  str
    department_id: int