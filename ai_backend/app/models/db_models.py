"""SQLAlchemy database models for the local AI backend."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def new_id(prefix):
    return "{}-{}".format(prefix, uuid.uuid4())


def utc_now():
    return datetime.utcnow()


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(String, primary_key=True, default=lambda: new_id("RPT"))
    patient_id = Column(String, nullable=False, index=True)
    order_id = Column(String, nullable=False, index=True)
    specimen_id = Column(String, nullable=False, index=True)
    current_version = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="AI_DRAFT")
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    versions = relationship("ReportVersion", back_populates="report", cascade="all, delete-orphan")


class ReportVersion(Base):
    __tablename__ = "report_versions"

    report_version_id = Column(String, primary_key=True, default=lambda: new_id("RPV"))
    report_id = Column(String, ForeignKey("reports.report_id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    source_context_hash = Column(String, nullable=False)
    report_text = Column(Text, nullable=False)
    model_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="AI_DRAFT")
    created_at = Column(DateTime, nullable=False, default=utc_now)

    report = relationship("Report", back_populates="versions")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    chat_session_id = Column(String, primary_key=True, default=lambda: new_id("CHS"))
    report_id = Column(String, ForeignKey("reports.report_id"), nullable=False, index=True)
    patient_id = Column(String, nullable=False)
    order_id = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(String, primary_key=True, default=lambda: new_id("MSG"))
    chat_session_id = Column(String, ForeignKey("chat_sessions.chat_session_id"), nullable=False, index=True)
    report_id = Column(String, ForeignKey("reports.report_id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(String, primary_key=True, default=lambda: new_id("AUD"))
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    patient_id = Column(String, nullable=True)
    order_id = Column(String, nullable=True)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class BiologistAction(Base):
    __tablename__ = "biologist_actions"

    action_id = Column(String, primary_key=True, default=lambda: new_id("BIO"))
    report_id = Column(String, ForeignKey("reports.report_id"), nullable=False, index=True)
    action = Column(String, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
