# models/__init__.py — import all models here so create_all sees them
from app.models.base import Base
from app.models.admin import Admin

from app.models.annotation import Annotation
from app.models.delivery_log import DeliveryLog
from app.models.department import Department
from app.models.enrollment_models import SubjectEnrollment, RetakeRequest
from app.models.exam import Exam
from app.models.exam_attempt import ExamAttemptRecord
from app.models.feedback_template import FeedbackTemplate
from app.models.mark import Mark
from app.models.question import Question
from app.models.question_mark import QuestionMark

from app.models.semester import Semester
from app.models.student import Student
from app.models.subject import Subject
from app.models.submission import Submission
from app.models.teacher import Teacher