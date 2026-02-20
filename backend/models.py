from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    is_admin = Column(Boolean, default=False)

class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(String, primary_key=True, index=True)  # UUID
    student_id = Column(Integer, ForeignKey("users.id"))
    student_name = Column(String)
    course_name = Column(String)
    data_payload = Column(JSONB)
    signature = Column(Text)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked = Column(Boolean, default=False)

    student = relationship("User", back_populates="certificates")

User.certificates = relationship("Certificate", back_populates="student")
