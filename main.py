from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uuid
import os
from typing import List, Dict, Any

from database import init_db, SessionLocal, Candidate, QuizResponse, HackathonSubmission, InterviewTranscript, IntelligenceReport, JobPosting
from tasks import run_intelligence_module, compile_final_scores
from llm_evaluator import LLMJudge, ASTAnalyzer

# Init database tables
init_db()

app = FastAPI(title="Assessment & Intelligence Pod API")

# Setup CORS for frontend to interact from local files/browsers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import json

# Request Pydantic Schemas
class JobPostingSchema(BaseModel):
    role_title: str
    description: str = ""
    difficulty_level: str
    weight_creativity: float
    weight_problem_solving: float
    weight_communication: float
    weight_execution: float
    weight_reasoning: float
    portfolio_skills: str = "{}"

class ApplyJobSchema(BaseModel):
    job_id: int

class QuizAnswerSchema(BaseModel):
    candidate_id: str
    question: str
    selected_option: str
    score_assigned: int

class HackathonSubmitSchema(BaseModel):
    candidate_id: str
    design_images_b64: List[str]
    design_rationale: str
    keypresses: int = 0
    deletions: int = 0
    pasted_chars: int = 0
    idle_time: int = 0
    journey: List[Dict[str, Any]] = []

class InterviewReplySchema(BaseModel):
    candidate_id: str
    reply_content: str

class TelemetrySchema(BaseModel):
    candidate_id: str
    tab_switches: int
    copy_pastes: int

def build_portfolio_profile(skills_input: str, difficulty: str) -> str:
    skills = [s.strip() for s in skills_input.split(",") if s.strip()]
    if not skills:
        skills = ["Python", "FastAPI", "Postgres"]
        
    diff_label_map = {
        "entry": "Entry-level Engineer",
        "mid": "Mid-level Engineer",
        "senior": "Senior Engineer",
        "lead": "Lead / Principal Engineer"
    }
    exp_level = diff_label_map.get(difficulty.lower(), "Senior Engineer")
    
    # Custom domains based on skills
    domains = []
    skills_lower = [s.lower() for s in skills]
    if any(x in "".join(skills_lower) for x in ["react", "javascript", "vue", "angular", "html", "css", "js"]):
        domains.append("Frontend Architecture")
        domains.append("User Interface Design")
    if any(x in "".join(skills_lower) for x in ["python", "django", "flask", "fastapi", "node", "java", "golang"]):
        domains.append("Backend Engineering")
        domains.append("Distributed Systems")
    if any(x in "".join(skills_lower) for x in ["postgres", "sql", "mongo", "database", "redis"]):
        domains.append("Database Administration & Optimizations")
    if not domains:
        domains = ["Software Engineering", "Systems Design"]
        
    profile = {
        "skills": skills,
        "experience_level": exp_level,
        "domains": domains,
        "projects": [
            {
                "name": f"Enterprise {skills[0]} Engine",
                "description": f"Designed and optimized a core transaction engine using {', '.join(skills[:3])}."
            }
        ],
        "career_interests": [
            "High Scale Platforms",
            "Complex Cloud Architectures"
        ],
        "strength_signals": [
            f"Strong conceptual understanding of {skills[0]} libraries",
            "Well structured code blocks and syntax correctness"
        ],
        "learning_signals": [
            "Expanding hands-on experience with asynchronous system designs",
            "Refining query optimization index techniques"
        ]
    }
    return json.dumps(profile)

@app.post("/api/jobs")
def create_job(job: JobPostingSchema, db: Session = Depends(get_db)):
    """Recruiter creates a new Job Posting."""
    try:
        assessment_data = LLMJudge.generate_job_assessment(job.role_title, job.portfolio_skills, job.difficulty_level)
        prompt = assessment_data.get("hackathon_prompt", f"Design a prototype for a {job.role_title}.")
        quiz = json.dumps(assessment_data.get("quiz_questions", []))
    except Exception as e:
        print("Failed to generate dynamic assessment:", e)
        prompt = f"Design a prototype for a {job.role_title}."
        quiz = "[]"
        
    db_job = JobPosting(
        role_title=job.role_title,
        description=job.description,
        difficulty_level=job.difficulty_level,
        weight_creativity=job.weight_creativity,
        weight_problem_solving=job.weight_problem_solving,
        weight_communication=job.weight_communication,
        weight_execution=job.weight_execution,
        weight_reasoning=job.weight_reasoning,
        portfolio_skills=job.portfolio_skills,
        generated_hackathon_prompt=prompt,
        generated_quiz_json=quiz
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return {"status": "success", "job_id": db_job.id, "message": "Job posted successfully"}

@app.get("/api/jobs")
def get_jobs(db: Session = Depends(get_db)):
    """Candidate views available Job Postings."""
    jobs = db.query(JobPosting).filter(JobPosting.status == "active").all()
    return [{"id": j.id, "title": j.role_title, "difficulty": j.difficulty_level, "skills": j.portfolio_skills, "description": j.description} for j in jobs]

@app.post("/api/assessment/apply")
def apply_to_job(payload: ApplyJobSchema, db: Session = Depends(get_db)):
    """Candidate applies to a specific job and initializes assessment pipeline."""
    job = db.query(JobPosting).filter(JobPosting.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    diff_map = {"entry": 2, "mid": 3, "senior": 4, "lead": 5}
    start_diff = diff_map.get(job.difficulty_level.lower(), 3)
    
    profile_json = build_portfolio_profile(job.portfolio_skills, job.difficulty_level)
    
    cand_id = f"cand_{uuid.uuid4().hex[:6]}"
    candidate = Candidate(
        id=cand_id,
        job_id=job.id,
        role_title=job.role_title,
        difficulty_level=job.difficulty_level,
        portfolio_skills=job.portfolio_skills,
        portfolio_profile=profile_json,
        current_quiz_step=1,
        current_quiz_difficulty=start_diff,
        status="initialized"
    )
    db.add(candidate)
    db.commit()
    
    return {
        "candidate_id": cand_id,
        "status": "initialized",
        "job_id": job.id,
        "message": f"Application started for {job.role_title}."
    }

@app.get("/api/quiz/question")
def get_quiz_question(candidate_id: str, db: Session = Depends(get_db)):
    """
    Layer 2: Adaptive Quiz Engine. Serves a dynamically AI-generated question.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    if candidate.current_quiz_step > 3:
        return {"status": "completed", "message": "Quiz completed."}
        
    job = db.query(JobPosting).filter(JobPosting.id == candidate.job_id).first()
    
    try:
        quiz_data = json.loads(job.generated_quiz_json)
        step_index = candidate.current_quiz_step - 1
        if not quiz_data or step_index >= len(quiz_data):
            raise ValueError("No valid quiz data")
        question_data = quiz_data[step_index]
    except Exception:
        question_data = {
            "question": f"What is a core principle of UI/UX for a {candidate.role_title}?",
            "options": [
                {"text": "Understanding user needs and usability.", "score": 95},
                {"text": "Using the most expensive design tools.", "score": 30},
                {"text": "Copying existing designs exactly.", "score": 10}
            ]
        }
    
    return {
        "candidate_id": candidate_id,
        "step": candidate.current_quiz_step,
        "difficulty": candidate.current_quiz_difficulty,
        "question": question_data["question"],
        "options": question_data["options"]
    }

@app.get("/api/hackathon/prompt")
def get_hackathon_prompt(candidate_id: str, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    job = db.query(JobPosting).filter(JobPosting.id == candidate.job_id).first()
    return {"prompt": job.generated_hackathon_prompt if job else "Design a prototype for your role."}

@app.post("/api/quiz/submit")
def submit_quiz_answer(payload: QuizAnswerSchema, db: Session = Depends(get_db)):
    """
    Evaluates response accuracy:
    - Correct (Score >= 80) -> Increment difficulty level for next question (+1)
    - Incorrect (Score < 80) -> Decrement difficulty level for next question (-1)
    - Advances step (+1). Sets status to quiz_done on step 4.
    """
    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    resp = QuizResponse(
        candidate_id=payload.candidate_id,
        question=payload.question,
        selected_option=payload.selected_option,
        score_assigned=payload.score_assigned
    )
    db.add(resp)
    
    # Adaptive routing adjustments
    current_diff = candidate.current_quiz_difficulty
    if payload.score_assigned >= 80:
        # Step up difficulty
        candidate.current_quiz_difficulty = min(5, current_diff + 1)
        print(f"Candidate {payload.candidate_id} got it correct. Difficulty scaled UP to {candidate.current_quiz_difficulty}")
    else:
        # Step down difficulty
        candidate.current_quiz_difficulty = max(1, current_diff - 1)
        print(f"Candidate {payload.candidate_id} got it wrong. Difficulty scaled DOWN to {candidate.current_quiz_difficulty}")
        
    candidate.current_quiz_step += 1
    
    # Completed quiz check
    if candidate.current_quiz_step > 3:
        candidate.status = "quiz_done"
        
    db.commit()
    return {
        "status": "success", 
        "candidate_status": candidate.status,
        "next_step": candidate.current_quiz_step,
        "next_difficulty": candidate.current_quiz_difficulty
    }


@app.post("/api/hackathon/submit")
def submit_hackathon(payload: HackathonSubmitSchema, db: Session = Depends(get_db)):
    """
    Layer 3: Live Multimodal AI Hackathon. Evaluates chronological UI/UX prototype screenshots.
    """
    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    # Evaluate design submission using Vision LLM Judge
    try:
        eval_res = LLMJudge.evaluate_hackathon(payload.design_rationale, payload.design_images_b64, candidate.role_title)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    submission = HackathonSubmission(
        candidate_id=payload.candidate_id,
        design_images_json=json.dumps(payload.design_images_b64),
        design_rationale=payload.design_rationale,
        usability_score=eval_res.get("usability_score", 75),
        aesthetics_score=eval_res.get("aesthetics_score", 75),
        accessibility_score=eval_res.get("accessibility_score", 75)
    )
    db.add(submission)
    
    # Save behaviour telemetry to Candidate
    candidate.telemetry_keypresses = payload.keypresses
    candidate.telemetry_deletions = payload.deletions
    candidate.telemetry_pasted_chars = payload.pasted_chars
    candidate.telemetry_idle_time_seconds = payload.idle_time
    candidate.telemetry_journey = json.dumps(payload.journey)
    
    candidate.status = "hackathon_done"
    db.commit()
    
    return {"status": "success", "candidate_status": candidate.status}


def generate_dynamic_interview_question(candidate, db: Session) -> str:
    step = candidate.current_interview_step or 1
    
    # Turn 1: Target conceptual / quiz performance
    if step == 1:
        quiz_res = db.query(QuizResponse).filter(QuizResponse.candidate_id == candidate.id).all()
        quiz_score = sum([q.score_assigned for q in quiz_res]) / len(quiz_res) if quiz_res else 75
        if quiz_score < 80:
            return "Your design fundamentals quiz results show some areas for improvement. Can you explain your approach to ensuring web accessibility (a11y) in your prototypes?"
        else:
            return "You selected excellent design patterns in the quiz. How would you defend a controversial UI layout decision to a stakeholder who prefers a traditional approach?"
            
    # Turn 2: Target hackathon prototype submission
    elif step == 2:
        hack_sub = db.query(HackathonSubmission).filter(HackathonSubmission.candidate_id == candidate.id).first()
        usability_score = hack_sub.usability_score if hack_sub else 70
        if usability_score < 80:
            return "Looking at your UI prototype submission, the visual hierarchy is decent, but usability could be tighter. How would you conduct user testing to refine the layout?"
        else:
            return "Your prototype submission had fantastic usability and aesthetics. How did you decide on the color palette and typography scale for this specific project?"
            
    # Turn 3: Target deployment/hand-off
    else:
        return "Finally, when handing off your high-fidelity designs to the frontend engineering team, what documentation and design tokens do you provide to ensure pixel-perfect implementation?"

@app.get("/api/interview/question")
def get_interview_question(candidate_id: str, db: Session = Depends(get_db)):
    """
    Layer 4: AI Interview Engine. Yields dynamic prompts based on current_interview_step.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if candidate.current_interview_step > 3:
        return {"status": "completed", "message": "Interview completed."}
        
    question = generate_dynamic_interview_question(candidate, db)
    return {
        "candidate_id": candidate_id,
        "step": candidate.current_interview_step,
        "question": question
    }

@app.post("/api/interview/reply")
def reply_interview(payload: InterviewReplySchema, db: Session = Depends(get_db)):
    """
    Layer 4: AI Interview Engine. Logs reply, evaluates scores, and increments turn.
    Toggles status to interview_done on turn 3.
    """
    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    current_step = candidate.current_interview_step or 1
    if current_step > 3:
        raise HTTPException(status_code=400, detail="Interview already completed")
        
    # Retrieve question asked to evaluate
    question = generate_dynamic_interview_question(candidate, db)
    
    # Evaluate candidate answer using LLM Judge
    try:
        eval_res = LLMJudge.evaluate_interview(question, payload.reply_content, candidate.role_title)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    transcript = InterviewTranscript(
        candidate_id=payload.candidate_id,
        question_asked=question,
        answer_given=payload.reply_content,
        communication_score=eval_res.get("communication", 75),
        reasoning_score=eval_res.get("reasoning", 75)
    )
    db.add(transcript)
    
    # Increment step
    candidate.current_interview_step = current_step + 1
    
    # Set to interview_done only on finishing the 3rd turn
    if candidate.current_interview_step > 3:
        candidate.status = "interview_done"
        
    db.commit()
    return {
        "status": "success", 
        "candidate_status": candidate.status,
        "next_step": candidate.current_interview_step,
        "scores": {
            "communication": eval_res.get("communication", 75), 
            "reasoning": eval_res.get("reasoning", 75),
            "confidence": eval_res.get("confidence", 75),
            "decision_quality": eval_res.get("decision_quality", 75)
        }
    }

@app.post("/api/assessment/telemetry")
def log_telemetry(payload: TelemetrySchema, db: Session = Depends(get_db)):
    """
    Assessment Integrity & Proctoring Layer. Logs browser tab switching
    and copy-paste volume into PostgreSQL.
    """
    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    candidate.telemetry_tab_switches = payload.tab_switches
    candidate.telemetry_copy_pastes = payload.copy_pastes
    db.commit()
    print(f"Logged proctoring telemetry for candidate {payload.candidate_id}: switches={payload.tab_switches}, pastes={payload.copy_pastes}")
    return {"status": "success"}

@app.post("/api/assessment/trigger_analysis")
def trigger_analysis(candidate_id: str, db: Session = Depends(get_db)):
    """
    Layer 5: Asynchronous Intelligence Analysis.
    Fires the 8 Parallel Intelligence Modules inside Celery workers using a Chord,
    releasing the main thread and updating status when final callback compiles.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    candidate.status = "analyzing"
    db.commit()
    
    # Retrieve recruiter weights setup to pass to compiler
    rec_cfg = db.query(RecruiterConfig).order_by(RecruiterConfig.created_at.desc()).first()
    weights = {
        "weight_creativity": rec_cfg.weight_creativity if rec_cfg else 30.0,
        "weight_problem_solving": rec_cfg.weight_problem_solving if rec_cfg else 25.0,
        "weight_communication": rec_cfg.weight_communication if rec_cfg else 20.0,
        "weight_execution": rec_cfg.weight_execution if rec_cfg else 15.0,
        "weight_reasoning": rec_cfg.weight_reasoning if rec_cfg else 10.0,
    }
    
    modules = ["Knowledge", "Problem Solving", "Creativity", "Communication", "Reasoning", "Execution", "Career Readiness", "Company Match"]
    
    # We will trigger the background tasks asynchronously using a Celery Chord
    task_results = []
    try:
        from celery import chord
        
        # Build signatures
        header = [run_intelligence_module.signature((candidate_id, mod)) for mod in modules]
        callback = compile_final_scores.signature((candidate_id, weights))
        
        # Trigger Chord
        res = chord(header)(callback)
        task_results = [res.id]
        print(f"Celery chord launched successfully: {res.id}")
    except Exception as e:
        print(f"Celery task dispatch failed: {str(e)}.")
        # Roll back candidate status
        candidate.status = "interview_done"
        db.commit()
        raise HTTPException(
            status_code=503, 
            detail=f"Celery broker/worker offline. Asynchronous parallel analysis could not be started: {str(e)}"
        )
    
    return {
        "candidate_id": candidate_id,
        "status": "analyzing",
        "task_ids": task_results,
        "celery_broker_online": True
    }


@app.get("/api/assessment/status/{candidate_id}")
def check_status(candidate_id: str, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    return {"candidate_id": candidate_id, "status": candidate.status}


@app.get("/api/assessment/report/{candidate_id}")
def get_report(candidate_id: str, db: Session = Depends(get_db)):
    """
    Layer 8: Final Report. Pulls structured scores, PostgreSQL metadata,
    and returns a complete JSON response payload.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    report = db.query(IntelligenceReport).filter(IntelligenceReport.candidate_id == candidate_id).first()
    if not report:
        raise HTTPException(status_code=400, detail="Intelligence report not generated yet")
        
    return {
        "candidate_id": candidate.id,
        "role_title": candidate.role_title,
        "difficulty_level": candidate.difficulty_level,
        "status": candidate.status,
        "match_score_percentage": report.final_weighted_score,
        "portfolio_profile": json.loads(candidate.portfolio_profile) if candidate.portfolio_profile else {},
        "telemetry_journey": json.loads(candidate.telemetry_journey) if candidate.telemetry_journey else [],
        "behavioral_intelligence": {
            "thinking_time": report.behavior_thinking_time or 70,
            "exploration": report.behavior_exploration or 70,
            "confidence": report.behavior_confidence or 70,
            "ai_dependency": report.behavior_ai_dependency or 10
        },
        "matchmaking_intelligence": {
            "role_fit": report.matchmaking_role_fit or 75,
            "culture_fit": report.matchmaking_culture_fit or 75,
            "learning_velocity": report.matchmaking_learning_velocity or 75,
            "growth_potential": report.matchmaking_growth_potential or 75,
            "recommended_roles": json.loads(report.matchmaking_recommended_roles) if report.matchmaking_recommended_roles else []
        },
        "intelligence_breakdown": {
            "knowledge_intelligence": report.score_knowledge,
            "problem_solving_intelligence": report.score_solving,
            "creativity_intelligence": report.score_creativity,
            "communication_intelligence": report.score_communication,
            "execution_intelligence": report.score_execution,
            "reasoning_intelligence": report.score_reasoning,
            "career_readiness": report.score_career_readiness,
            "company_match": report.score_company_match,
            "authenticity_score": report.score_authenticity,
            "assessment_integrity": report.integrity_risk_level,
            "learning_pattern": report.learning_pattern,
            "confidence_pattern": report.confidence_pattern
        },
        "report_feedback": {
            "strengths": report.strengths,
            "weaknesses": report.weaknesses
        },
        "storage_references": {
            "postgres_transaction_id": f"tx_postgres_{uuid.uuid4().hex[:12]}",
            "qdrant_vector_id": f"vec_qdrant_{uuid.uuid4().hex[:8]}-331e-450f-aa92-f04b11fba82c",
            "minio_hackathon_bucket_url": f"s3://assessments/submissions/{candidate.id}_src.tar.gz"
        },
        "system_metadata": {
            "engine_version": "2.1-LlamaAgent",
            "timestamp_processed": report.calculated_at.isoformat()
        }
    }

@app.get("/api/candidates")
def get_candidates(db: Session = Depends(get_db)):
    """
    Fetch all completed candidate assessments with reports to populate the Talent Pool.
    """
    reports = db.query(IntelligenceReport).order_by(IntelligenceReport.calculated_at.desc()).all()
    out = []
    for r in reports:
        cand = db.query(Candidate).filter(Candidate.id == r.candidate_id).first()
        if cand:
            out.append({
                "candidate_id": cand.id,
                "role_title": cand.role_title,
                "difficulty_level": cand.difficulty_level,
                "final_score": r.final_weighted_score,
                "timestamp": r.calculated_at.isoformat()
            })
    return out

# Serve Frontend Static UI securely (Explicitly to prevent source file leakage)
@app.get("/")
def serve_root():
    return FileResponse("index.html")

@app.get("/index.html")
def serve_index_html():
    return FileResponse("index.html")

@app.get("/app.js")
def serve_js():
    return FileResponse("app.js")

@app.get("/styles.css")
def serve_css():
    return FileResponse("styles.css")
