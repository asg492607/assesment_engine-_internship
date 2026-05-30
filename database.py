import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Fallback to local sqlite for easy local development, or use PostgreSQL if specified in ENV
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./assessment_pod.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class RecruiterConfig(Base):
    __tablename__ = "recruiter_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    role_title = Column(String, index=True)
    difficulty_level = Column(String, default="senior")
    weight_creativity = Column(Float, default=30.0)
    weight_problem_solving = Column(Float, default=25.0)
    weight_communication = Column(Float, default=20.0)
    weight_execution = Column(Float, default=15.0)
    weight_reasoning = Column(Float, default=10.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(String, primary_key=True, index=True) # candidate ID e.g., cand_8410
    role_title = Column(String)
    difficulty_level = Column(String)
    status = Column(String, default="initialized") # initialized, quiz_done, hackathon_done, interview_done, analyzing, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    quiz_responses = relationship("QuizResponse", back_populates="candidate")
    hackathon_submission = relationship("HackathonSubmission", uselist=False, back_populates="candidate")
    interview_transcript = relationship("InterviewTranscript", uselist=False, back_populates="candidate")
    intelligence_report = relationship("IntelligenceReport", uselist=False, back_populates="candidate")

class QuizResponse(Base):
    __tablename__ = "quiz_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"))
    question = Column(Text)
    selected_option = Column(Text)
    score_assigned = Column(Integer)
    
    candidate = relationship("Candidate", back_populates="quiz_responses")

class HackathonSubmission(Base):
    __tablename__ = "hackathon_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"))
    code_content = Column(Text)
    lines_count = Column(Integer)
    creativity_score = Column(Integer)
    problem_solving_score = Column(Integer)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    candidate = relationship("Candidate", back_populates="hackathon_submission")

class InterviewTranscript(Base):
    __tablename__ = "interview_transcripts"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"))
    question_asked = Column(Text)
    answer_given = Column(Text)
    communication_score = Column(Integer)
    reasoning_score = Column(Integer)
    
    candidate = relationship("Candidate", back_populates="interview_transcript")

class IntelligenceReport(Base):
    __tablename__ = "intelligence_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), unique=True)
    score_knowledge = Column(Integer)
    score_solving = Column(Integer)
    score_creativity = Column(Integer)
    score_communication = Column(Integer)
    score_reasoning = Column(Integer)
    score_execution = Column(Integer)
    score_career_readiness = Column(Integer)
    score_company_match = Column(Integer)
    final_weighted_score = Column(Integer)
    strengths = Column(Text)
    weaknesses = Column(Text)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    candidate = relationship("Candidate", back_populates="intelligence_report")

def init_db():
    Base.metadata.create_all(bind=engine)
