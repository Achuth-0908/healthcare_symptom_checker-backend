"""
Pydantic models for Healthcare Symptom Checker
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class UrgencyLevel(str, Enum):
    EMERGENCY = "emergency"
    URGENT = "urgent" 
    MODERATE = "moderate"
    LOW = "low"
    ROUTINE = "routine"
    SELF_CARE = "self_care"


class SymptomInput(BaseModel):
    symptoms: str = Field(..., description="Description of symptoms")
    age: Optional[int] = Field(None, ge=0, le=120, description="Patient age")
    gender: Optional[str] = Field(None, description="Patient gender")
    medical_history: Optional[List[str]] = Field(default=[], description="Previous medical conditions")
    current_medications: Optional[List[str]] = Field(default=[], description="Current medications")
    session_id: Optional[str] = Field(None, description="Session identifier")


class SymptomStartRequest(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120)
    sex: Optional[str] = Field(None)
    medical_history: Optional[List[str]] = Field(default=[])
    medications: Optional[List[str]] = Field(default=[])
    allergies: Optional[List[str]] = Field(default=[])


class SymptomMessage(BaseModel):
    session_id: str
    message: str
    message_type: str = Field(default="symptom")
    duration: Optional[str] = Field(None, description="Duration of symptoms")
    severity: Optional[int] = Field(None, ge=1, le=10, description="Severity level 1-10")


class Assessment(BaseModel):
    urgency: UrgencyLevel
    emergency_warning: Optional[str] = None
    probable_conditions: List[Dict[str, Any]] = Field(default=[])
    clarifying_questions: List[str] = Field(default=[])
    reasoning: str = ""
    recommendations: List[str] = Field(default=[])
    body_systems_affected: List[str] = Field(default=[])
    disclaimer: str = "This is not a medical diagnosis. Please consult a healthcare professional."


class Question(BaseModel):
    question: str
    type: str = Field(default="text")  # text, yes_no, multiple_choice
    options: Optional[List[str]] = Field(default=None)


class Condition(BaseModel):
    name: str
    probability: float = Field(..., ge=0, le=1)
    description: str
    urgency_level: UrgencyLevel
    recommendations: List[str]


class SymptomResponse(BaseModel):
    session_id: str
    assessment: Assessment
    conversation_turn: int
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationTurn(BaseModel):
    user_message: str
    assistant_response: Assessment
    timestamp: datetime = Field(default_factory=datetime.now)
    severity_reported: Optional[int] = None
    questions: Optional[List[Question]] = None

class SessionResponse(BaseModel):
    session_id: str
    message: str
    created_at: datetime = Field(default_factory=datetime.now)

class HistoryRequest(BaseModel):
    session_id: str


class HistoryResponse(BaseModel):
    session_id: str
    conversations: List[ConversationTurn]
    created_at: datetime
    last_updated: datetime


class ConversationHistory(BaseModel):
    session_id: str
    turns: List[ConversationTurn]
    total_turns: int
    created_at: datetime
    last_updated: datetime
    summary: Optional[str] = None


class ExportRequest(BaseModel):
    session_id: str
    format: str = Field(default="json", description="Export format: json, csv, or pdf")
    include_assessments: bool = Field(default=True, description="Include assessment data")
    include_timestamps: bool = Field(default=True, description="Include timestamp information")


class ExportResponse(BaseModel):
    session_id: str
    format: str
    download_url: str
    file_size: int
    created_at: datetime
    expires_at: datetime


# SQLAlchemy models for database
class SessionModel(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, index=True)
    age = Column(Integer)
    sex = Column(String)
    medical_history = Column(Text)  # JSON string
    medications = Column(Text)  # JSON string
    allergies = Column(Text)  # JSON string
    status = Column(String, default="active")
    turn_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    conversations = relationship("ConversationModel", back_populates="session")


class ConversationModel(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    turn_number = Column(Integer)
    user_message = Column(Text)
    assistant_response = Column(Text)  # JSON string
    severity_reported = Column(Integer)
    urgency_level = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("SessionModel", back_populates="conversations")


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String)
    event_type = Column(String)
    urgency_level = Column(String)
    emergency_keywords_detected = Column(Text)  # JSON string
    confidence_scores = Column(Text)  # JSON string
    audit_metadata = Column(Text)  # JSON string (renamed from metadata)
    timestamp = Column(DateTime, default=datetime.utcnow)