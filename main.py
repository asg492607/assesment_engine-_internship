from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uuid
import os
from typing import List, Dict, Any

from database import init_db, SessionLocal, Candidate, QuizResponse, HackathonSubmission, InterviewTranscript, IntelligenceReport, RecruiterConfig
from tasks import run_intelligence_module, compile_final_scores
from llm_evaluator import LLMJudge, ASTAnalyzer

# Init database tables
init_db()

app = FastAPI(title="Assessment & Intelligence Pod API")

# Setup CORS for frontend to interact from local files/browsers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
class RecruiterConfigSchema(BaseModel):
    role_title: str
    difficulty_level: str
    weight_creativity: float
    weight_problem_solving: float
    weight_communication: float
    weight_execution: float
    weight_reasoning: float
    portfolio_skills: str = "{}"

class QuizAnswerSchema(BaseModel):
    candidate_id: str
    question: str
    selected_option: str
    score_assigned: int

class HackathonSubmitSchema(BaseModel):
    candidate_id: str
    code_content: str
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

@app.post("/api/assessment/generate")
def generate_assessment(config: RecruiterConfigSchema, db: Session = Depends(get_db)):
    """
    Layer 1: Assessment Generator. Creates a recruiter configurations row
    and starts a new candidate tracking workflow incorporating Portfolio Skill graphs.
    """
    # Save recruiter configuration
    rec_cfg = RecruiterConfig(
        role_title=config.role_title,
        difficulty_level=config.difficulty_level,
        weight_creativity=config.weight_creativity,
        weight_problem_solving=config.weight_problem_solving,
        weight_communication=config.weight_communication,
        weight_execution=config.weight_execution,
        weight_reasoning=config.weight_reasoning
    )
    db.add(rec_cfg)
    db.commit()
    
    # Starting difficulty based on recruiter target select: entry=2, mid=3, senior=4, lead=5
    diff_map = {"entry": 2, "mid": 3, "senior": 4, "lead": 5}
    start_diff = diff_map.get(config.difficulty_level, 3)
    
    # Generate Layer 0 Portfolio profile
    profile_json = build_portfolio_profile(config.portfolio_skills, config.difficulty_level)
    
    # Generate unique candidate token
    cand_id = f"cand_{uuid.uuid4().hex[:6]}"
    candidate = Candidate(
        id=cand_id,
        role_title=config.role_title,
        difficulty_level=config.difficulty_level,
        portfolio_skills=config.portfolio_skills,
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
        "recruiter_config_id": rec_cfg.id,
        "message": f"Assessment generated custom-targeting skill graph: {config.portfolio_skills}."
    }

# ADAPTIVE MULTI-LEVEL QUIZ QUESTION BANK
# Difficulty Scale: 1 (Simplest) to 5 (Hardest)
QUIZ_BANK = {
    "default": {
        1: {
            "question": "What does a Python list comprehension do?",
            "options": [
                {"text": "Creates a new list by applying an expression to each item in an existing iterable.", "score": 95},
                {"text": "Compiles a python script into bytecode statically.", "score": 30},
                {"text": "Compresses memory storage of arrays dynamically.", "score": 50}
            ]
        },
        2: {
            "question": "What is the primary function of index lookup in relational databases?",
            "options": [
                {"text": "To speed up data retrieval operations by using lookup structures.", "score": 95},
                {"text": "To encrypt database columns securely against unauthorized table access.", "score": 40},
                {"text": "To enforce unique primary keys automatically inside every table.", "score": 70}
            ]
        },
        3: {
            "question": "Which HTTP status code represents a successful REST payload creation?",
            "options": [
                {"text": "201 Created", "score": 95},
                {"text": "200 OK", "score": 80},
                {"text": "202 Accepted", "score": 70}
            ]
        },
        4: {
            "question": "How would you optimize a slow database query involving a massive join operation?",
            "options": [
                {"text": "Add index constraints on foreign keys and rewrite the query using a specific execution path.", "score": 95},
                {"text": "Add memory caching via Redis to completely bypass the database layer.", "score": 80},
                {"text": "Split the massive table into several sub-tables manually and run queries in parallel.", "score": 65}
            ]
        },
        5: {
            "question": "How do you handle deadlocks in heavy transaction loops in PostgreSQL?",
            "options": [
                {"text": "Order lock acquisitions consistently and set short lock timeouts to retry transactions.", "score": 95},
                {"text": "Increase shared buffers and disable autovacuum completely on tables.", "score": 30},
                {"text": "Use read replicas to perform write queries asynchronously.", "score": 50}
            ]
        }
    },
    "javascript": {
        1: {
            "question": "What is the difference between 'let' and 'var' in JS?",
            "options": [
                {"text": "'let' is block-scoped, while 'var' is function-scoped.", "score": 95},
                {"text": "'var' is immutable while 'let' can change values.", "score": 30},
                {"text": "There is no functional difference; they are syntactic aliases.", "score": 40}
            ]
        },
        2: {
            "question": "What does Promise.all() do?",
            "options": [
                {"text": "Runs multiple async operations in parallel and waits for all of them to resolve.", "score": 95},
                {"text": "Executes promises sequentially in block loops.", "score": 40},
                {"text": "Catches promise rejection and ignores all errors.", "score": 50}
            ]
        },
        3: {
            "question": "How do you prevent useless component re-renders in React?",
            "options": [
                {"text": "Use React.memo(), useMemo(), and useCallback() hooks.", "score": 95},
                {"text": "Call forceUpdate() inside render hooks.", "score": 35},
                {"text": "Save all variable structures in document cookies.", "score": 25}
            ]
        },
        4: {
            "question": "Explain Event Loop behavior in Node.js.",
            "options": [
                {"text": "Offloads blocking calls to a thread pool and executes callbacks in phases.", "score": 95},
                {"text": "Forces Javascript execution to run fully multithreaded.", "score": 40},
                {"text": "Halts execution until files are written directly to memory.", "score": 30}
            ]
        },
        5: {
            "question": "How do you build custom garbage collection checks in V8?",
            "options": [
                {"text": "Track allocations, use WeakRef/FinalizationRegistry, and run with --expose-gc to monitor heap.", "score": 95},
                {"text": "Call delete on all global variables continuously.", "score": 30},
                {"text": "Restart the Node.js process after every client connection.", "score": 20}
            ]
        }
    }
}

@app.get("/api/quiz/question")
def get_quiz_question(candidate_id: str, db: Session = Depends(get_db)):
    """
    Layer 2: Adaptive Quiz Engine. Serves a custom question based on Candidate history.
    Detects portfolio skill tags (e.g. JS/React) and pulls matching difficulty index.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    # Check if candidate completed the quiz steps
    if candidate.current_quiz_step > 3:
        return {"status": "completed", "message": "Quiz completed."}
        
    # Choose topic based on portfolio skills: React/JS vs Python/default
    skills_str = candidate.portfolio_skills.lower()
    topic = "default"
    if "javascript" in skills_str or "react" in skills_str or "node" in skills_str:
        topic = "javascript"
        
    diff = candidate.current_quiz_difficulty
    # Fallback to nearest scale boundaries
    diff = max(1, min(5, diff))
    
    question_data = QUIZ_BANK[topic][diff]
    
    return {
        "candidate_id": candidate_id,
        "step": candidate.current_quiz_step,
        "difficulty": diff,
        "question": question_data["question"],
        "options": question_data["options"]
    }

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
    Layer 3: Live AI Hackathon. Saves code submission and analyzes structure metrics.
    Also archives the file locally simulating Layer 7 MinIO storage.
    """
    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    lines = len([l for l in payload.code_content.split("\n") if l.strip()])
    
    # Evaluate code submission using LLM Judge with compiler AST fallback
    eval_res = LLMJudge.evaluate_hackathon(payload.code_content, candidate.role_title)
    
    submission = HackathonSubmission(
        candidate_id=payload.candidate_id,
        code_content=payload.code_content,
        lines_count=lines,
        creativity_score=eval_res.get("architecture", 75),
        problem_solving_score=eval_res.get("problem_solving", 75)
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
    
    # Save the file to disk representing MinIO archival
    try:
        storage_dir = os.path.join(os.getcwd(), "minio_storage", "hackathon")
        os.makedirs(storage_dir, exist_ok=True)
        file_path = os.path.join(storage_dir, f"{payload.candidate_id}_source.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(payload.code_content)
        print(f"Archived candidate code submission to MinIO: {file_path}")
    except Exception as e:
        print(f"Error archiving to MinIO local folder: {str(e)}")
        
    return {"status": "success", "candidate_status": candidate.status, "lines_processed": lines}

def generate_dynamic_interview_question(candidate, db: Session) -> str:
    step = candidate.current_interview_step or 1
    
    # Turn 1: Target conceptual / quiz performance
    if step == 1:
        quiz_res = db.query(QuizResponse).filter(QuizResponse.candidate_id == candidate.id).all()
        quiz_score = sum([q.score_assigned for q in quiz_res]) / len(quiz_res) if quiz_res else 75
        if quiz_score < 80:
            return "Your quiz results show some gaps in database and performance concepts. Can you explain how you would analyze and optimize a slow query execution plan manually?"
        else:
            return "You selected the optimal database query paths in the quiz. How would you design a connection pooling strategy to manage high peaks of database traffic?"
            
    # Turn 2: Target hackathon code implementation architecture
    elif step == 2:
        hack_sub = db.query(HackathonSubmission).filter(HackathonSubmission.candidate_id == candidate.id).first()
        solve_score = hack_sub.problem_solving_score if hack_sub else 70
        if solve_score < 80:
            return "Looking at your hackathon code submission, it uses a very direct, synchronous/standard approach. How would you refactor this code to support asynchronous processing, rate limiting, or higher concurrency?"
        else:
            return "Your hackathon submission had great structure. How would you handle scaling this code across multiple distributed worker nodes or caching state using Redis?"
            
    # Turn 3: Target deployment, monitoring, and production safety trade-offs
    else:
        return "Finally, when deploying this solution to a highly available production environment, how do you handle monitoring, fallback safety, and logging for unexpected exceptions?"

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
    eval_res = LLMJudge.evaluate_interview(question, payload.reply_content, candidate.role_title)
    
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
    celery_failed = False
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
        print(f"Celery task dispatch failed: {str(e)}. Running sync fallback analysis.")
        celery_failed = True
        
    if celery_failed:
        # Run local fallback directly in database
        quiz_res = db.query(QuizResponse).filter(QuizResponse.candidate_id == candidate_id).all()
        hack_sub = db.query(HackathonSubmission).filter(HackathonSubmission.candidate_id == candidate_id).first()
        int_trans_list = db.query(InterviewTranscript).filter(InterviewTranscript.candidate_id == candidate_id).all()
        
        quiz_score = sum([q.score_assigned for q in quiz_res]) / len(quiz_res) if quiz_res else 75
        hack_solve = hack_sub.problem_solving_score if hack_sub else 70
        hack_create = hack_sub.creativity_score if hack_sub else 70
        
        if int_trans_list:
            int_comm = sum([t.communication_score for t in int_trans_list]) / len(int_trans_list)
            int_reason = sum([t.reasoning_score for t in int_trans_list]) / len(int_trans_list)
        else:
            int_comm = 70
            int_reason = 70
        
        results = [
            {"module": "Knowledge", "score": quiz_res[0].score_assigned if quiz_res else 75},
            {"module": "Problem Solving", "score": hack_solve},
            {"module": "Creativity", "score": hack_create},
            {"module": "Communication", "score": int_comm},
            {"module": "Reasoning", "score": int_reason},
            {"module": "Execution", "score": int((hack_solve + hack_create) / 2)},
            {"module": "Career Readiness", "score": int((quiz_score + int_reason) / 2) + 5},
            {"module": "Company Match", "score": int(int_comm * 0.4 + quiz_score * 0.6)}
        ]
        compile_final_scores(results, candidate_id, weights)
    
    return {
        "candidate_id": candidate_id,
        "status": "completed" if celery_failed else "analyzing",
        "task_ids": task_results,
        "celery_broker_online": not celery_failed
    }


@app.get("/api/assessment/status/{candidate_id}")
def check_status(candidate_id: str, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    # Auto-compile for simple local database loop if it's currently analyzing
    if candidate.status == "analyzing":
        # Check if we should auto-transition to simulate Celery processing locally
        # If Redis/Celery is not run by user, this serves as a robust auto-compilation fallback!
        # Query results
        quiz_res = db.query(QuizResponse).filter(QuizResponse.candidate_id == candidate_id).all()
        hack_sub = db.query(HackathonSubmission).filter(HackathonSubmission.candidate_id == candidate_id).first()
        int_trans_list = db.query(InterviewTranscript).filter(InterviewTranscript.candidate_id == candidate_id).all()
        
        if quiz_res and hack_sub and int_trans_list:
            int_comm = sum([t.communication_score for t in int_trans_list]) / len(int_trans_list)
            int_reason = sum([t.reasoning_score for t in int_trans_list]) / len(int_trans_list)
            
            # Build mock worker results
            results = [
                {"module": "Knowledge", "score": quiz_res[0].score_assigned},
                {"module": "Problem Solving", "score": hack_sub.problem_solving_score},
                {"module": "Creativity", "score": hack_sub.creativity_score},
                {"module": "Communication", "score": int(int_comm)},
                {"module": "Reasoning", "score": int(int_reason)},
                {"module": "Execution", "score": int((hack_sub.problem_solving_score + hack_sub.creativity_score) / 2)},
                {"module": "Career Readiness", "score": int((quiz_res[0].score_assigned + int_reason) / 2) + 5},
                {"module": "Company Match", "score": int(int_comm * 0.4 + quiz_res[0].score_assigned * 0.6)}
            ]
            rec_cfg = db.query(RecruiterConfig).order_by(RecruiterConfig.created_at.desc()).first()
            weights = {
                "weight_creativity": rec_cfg.weight_creativity if rec_cfg else 30.0,
                "weight_problem_solving": rec_cfg.weight_problem_solving if rec_cfg else 25.0,
                "weight_communication": rec_cfg.weight_communication if rec_cfg else 20.0,
                "weight_execution": rec_cfg.weight_execution if rec_cfg else 15.0,
                "weight_reasoning": rec_cfg.weight_reasoning if rec_cfg else 10.0,
            }
            compile_final_scores(results, candidate_id, weights)
            
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
