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
    
    # Run seed function
    db = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(Candidate).count() == 0:
            print("Seeding database with default recruiter candidates...")
            
            # Seed Recruiter Configurations
            cfg1 = RecruiterConfig(
                role_title="Senior Python Architect",
                difficulty_level="senior",
                weight_creativity=30.0,
                weight_problem_solving=25.0,
                weight_communication=20.0,
                weight_execution=15.0,
                weight_reasoning=10.0
            )
            db.add(cfg1)
            db.commit()
            
            # Seed Candidate 1: cand_9240 (High Performer)
            c1 = Candidate(id="cand_9240", role_title="Senior Python Architect", difficulty_level="senior", status="completed")
            db.add(c1)
            
            qr1 = QuizResponse(candidate_id="cand_9240", question="Optimizing database queries?", selected_option="Add index constraints and rewrite joins.", score_assigned=95)
            db.add(qr1)
            
            hs1 = HackathonSubmission(candidate_id="cand_9240", code_content="async def main(): pass", lines_count=18, creativity_score=92, problem_solving_score=88)
            db.add(hs1)
            
            it1 = InterviewTranscript(candidate_id="cand_9240", question_asked="Pooling?", answer_given="Yes, using connection pools handles high spikes.", communication_score=90, reasoning_score=85)
            db.add(it1)
            
            ir1 = IntelligenceReport(
                candidate_id="cand_9240",
                score_knowledge=95,
                score_solving=88,
                score_creativity=92,
                score_communication=90,
                score_reasoning=85,
                score_execution=90,
                score_career_readiness=92,
                score_company_match=93,
                final_weighted_score=90,
                strengths="Exceptional architectural safety patterns and code execution flow.",
                weaknesses="Over-engineers helper pipelines."
            )
            db.add(ir1)
            
            # Seed Candidate 2: cand_7102 (Mid Performer)
            c2 = Candidate(id="cand_7102", role_title="Senior Python Architect", difficulty_level="senior", status="completed")
            db.add(c2)
            
            qr2 = QuizResponse(candidate_id="cand_7102", question="Optimizing database queries?", selected_option="Add caching layer via Redis.", score_assigned=80)
            db.add(qr2)
            
            hs2 = HackathonSubmission(candidate_id="cand_7102", code_content="def main(): pass", lines_count=8, creativity_score=74, problem_solving_score=75)
            db.add(hs2)
            
            it2 = InterviewTranscript(candidate_id="cand_7102", question_asked="Pooling?", answer_given="I would spin up connection threads manually.", communication_score=78, reasoning_score=72)
            db.add(it2)
            
            ir2 = IntelligenceReport(
                candidate_id="cand_7102",
                score_knowledge=80,
                score_solving=75,
                score_creativity=74,
                score_communication=78,
                score_reasoning=72,
                score_execution=74,
                score_career_readiness=76,
                score_company_match=79,
                final_weighted_score=76,
                strengths="Steady execution rhythm, solid understanding of local session caching.",
                weaknesses="Gaps in scale planning and socket stream pools."
            )
            db.add(ir2)
            
            db.commit()
            print("Database seeding completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {str(e)}")
    finally:
        db.close()

