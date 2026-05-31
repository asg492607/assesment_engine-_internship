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

class JobPosting(Base):
    __tablename__ = "job_postings"
    
    id = Column(Integer, primary_key=True, index=True)
    role_title = Column(String, index=True)
    description = Column(Text, default="")
    portfolio_skills = Column(Text, default="{}")
    difficulty_level = Column(String, default="senior")
    weight_creativity = Column(Float, default=30.0)
    weight_problem_solving = Column(Float, default=25.0)
    weight_communication = Column(Float, default=20.0)
    weight_execution = Column(Float, default=15.0)
    weight_reasoning = Column(Float, default=10.0)
    status = Column(String, default="active")
    generated_hackathon_prompt = Column(Text, default="")
    generated_quiz_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    candidates = relationship("Candidate", back_populates="job")

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(String, primary_key=True, index=True) # candidate ID e.g., cand_8410
    job_id = Column(Integer, ForeignKey("job_postings.id"))
    role_title = Column(String)
    difficulty_level = Column(String)
    status = Column(String, default="initialized") # initialized, quiz_done, hackathon_done, interview_done, analyzing, completed
    portfolio_skills = Column(Text, default="{}") # Extracted skill graph JSON
    current_quiz_step = Column(Integer, default=1) # Quiz progress 1 to 3
    current_quiz_difficulty = Column(Integer, default=3) # Scale 1 to 5
    current_interview_step = Column(Integer, default=1) # Interview progress 1 to 3
    
    # Proctoring Layer Telemetry
    telemetry_tab_switches = Column(Integer, default=0)
    telemetry_copy_pastes = Column(Integer, default=0)
    
    # Coding Behaviour Telemetry
    telemetry_keypresses = Column(Integer, default=0)
    telemetry_deletions = Column(Integer, default=0)
    telemetry_pasted_chars = Column(Integer, default=0)
    telemetry_idle_time_seconds = Column(Integer, default=0)
    portfolio_profile = Column(Text, default="{}") # Stored Layer 0 JSON metadata
    telemetry_journey = Column(Text, default="[]") # JSON timeline event list: [{"time": elapsed, "action": action}]
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job = relationship("JobPosting", back_populates="candidates")
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
    design_images_json = Column(Text)
    design_rationale = Column(Text)
    usability_score = Column(Integer)
    aesthetics_score = Column(Integer)
    accessibility_score = Column(Integer)
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
    
    # Proctoring Layer Metrics
    score_authenticity = Column(Integer, default=100)
    integrity_risk_level = Column(String, default="Low Risk")
    
    # Coding Behaviour Metrics
    learning_pattern = Column(String, default="Structured Builder")
    confidence_pattern = Column(String, default="Decisive")
    
    # Layer 5.5 behavioral intelligence scores
    behavior_thinking_time = Column(Integer, default=70)
    behavior_exploration = Column(Integer, default=70)
    behavior_confidence = Column(Integer, default=70)
    behavior_ai_dependency = Column(Integer, default=10)
    
    # Layer 9 Matchmaking statistics
    matchmaking_role_fit = Column(Integer, default=75)
    matchmaking_culture_fit = Column(Integer, default=75)
    matchmaking_learning_velocity = Column(Integer, default=75)
    matchmaking_growth_potential = Column(Integer, default=75)
    matchmaking_recommended_roles = Column(Text, default="[]") # JSON string array
    
    final_weighted_score = Column(Integer)
    strengths = Column(Text)
    weaknesses = Column(Text)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    candidate = relationship("Candidate", back_populates="intelligence_report")

def init_db():
    Base.metadata.create_all(bind=engine)

