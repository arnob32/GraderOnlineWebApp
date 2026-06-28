from sqlalchemy import Column, Integer, String
from app.models.base import Base


class Admin(Base):
    __tablename__ = "admins"

    id       = Column(Integer, primary_key=True, index=True)
    username = Column(String,  nullable=False, unique=True)
    email    = Column(String,  nullable=True)
    password = Column(String,  nullable=False)