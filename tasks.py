import os
import time
from celery import Celery
from sqlalchemy.orm import Session
from database import SessionLocal, Candidate, IntelligenceReport, HackathonSubmission, QuizResponse, InterviewTranscript
from vector_store import store_candidate_vector

# Configure Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

@celery_app.task
def run_intelligence_module(candidate_id: str, module_name: str):
    """
    Simulates a heavy processing pipeline for a specific intelligence module.
    In production, this would invoke deep analysis, vector similarity calculations,
    and LLM scoring.
    """
    print(f"Starting Celery Worker: {module_name} analysis for candidate {candidate_id}...")
    time.sleep(1.5) # Simulate workload
    
    db: Session = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return {"error": "candidate not found"}
        
        # Base evaluations off candidate replies
        quiz_res = db.query(QuizResponse).filter(QuizResponse.candidate_id == candidate_id).all()
        hack_sub = db.query(HackathonSubmission).filter(HackathonSubmission.candidate_id == candidate_id).first()
        int_trans = db.query(InterviewTranscript).filter(InterviewTranscript.candidate_id == candidate_id).first()
        
        # Calculate standard score baseline based on actual candidate data
        quiz_score = sum([q.score_assigned for q in quiz_res]) / len(quiz_res) if quiz_res else 75
        hack_solve = hack_sub.problem_solving_score if hack_sub else 70
        hack_create = hack_sub.creativity_score if hack_sub else 70
        int_comm = int_trans.communication_score if int_trans else 70
        int_reason = int_trans.reasoning_score if int_trans else 70
        
        score = 75 # default
        if module_name == "Knowledge":
            score = quiz_score
        elif module_name == "Problem Solving":
            score = hack_solve
        elif module_name == "Creativity":
            score = hack_create
        elif module_name == "Communication":
            score = int_comm
        elif module_name == "Reasoning":
            score = int_reason
        elif module_name == "Execution":
            score = int((hack_solve + hack_create) / 2)
        elif module_name == "Career Readiness":
            difficulty_bonus = 15 if candidate.difficulty_level == "senior" else 5
            score = min(int(quiz_score * 0.5 + int_reason * 0.5) + difficulty_bonus, 100)
        elif module_name == "Company Match":
            score = int((int_comm * 0.4) + (quiz_score * 0.6))
            
        print(f"Finished {module_name} analysis for candidate {candidate_id}. Score calculated: {score}%")
        return {
            "candidate_id": candidate_id,
            "module": module_name,
            "score": int(score)
        }
    finally:
        db.close()

@celery_app.task
def compile_final_scores(results_list: list, candidate_id: str, weights: dict):
    """
    Combines the parallel module scores using custom recruiter priority weights,
    writes the final IntelligenceReport row to DB, and completes the pipeline.
    """
    print(f"Compiling final scores for candidate {candidate_id}...")
    db: Session = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return {"error": "candidate not found"}
            
        # Parse module results list
        module_scores = {}
        for res in results_list:
            if res and "module" in res:
                module_scores[res["module"]] = res["score"]
                
        # Fill missing values with defaults if workers fail
        for mod in ["Knowledge", "Problem Solving", "Creativity", "Communication", "Reasoning", "Execution", "Career Readiness", "Company Match"]:
            if mod not in module_scores:
                module_scores[mod] = 75
                
        # Extract weights
        w_creativity = weights.get("weight_creativity", 30)
        w_solving = weights.get("weight_problem_solving", 25)
        w_comm = weights.get("weight_communication", 20)
        w_exec = weights.get("weight_execution", 15)
        w_reason = weights.get("weight_reasoning", 10)
        total_w = w_creativity + w_solving + w_comm + w_exec + w_reason
        
        final_score = int(
            ((module_scores["Creativity"] * w_creativity) +
             (module_scores["Problem Solving"] * w_solving) +
             (module_scores["Communication"] * w_comm) +
             (module_scores["Execution"] * w_exec) +
             (module_scores["Reasoning"] * w_reason)) / (total_w or 1)
        )
        
        # Decide strengths/weaknesses
        if final_score >= 85:
            strengths = "Exceptional analytical depth, architectural safety logic, clean abstraction models."
            weaknesses = "Prone to over-engineering simple pipeline loops; could choose more standard constructs."
        elif final_score >= 70:
            strengths = "Reliable logical flow, solid documentation, good execution speed."
            weaknesses = "Inconsistent coverage of structural edge cases in heavy async systems."
        else:
            strengths = "Good interpersonal explanation structure and verbal reasoning."
            weaknesses = "Exhibits gaps in low-latency processing architectures and memory management patterns."
            
        # Create/Update report
        report = db.query(IntelligenceReport).filter(IntelligenceReport.candidate_id == candidate_id).first()
        if not report:
            report = IntelligenceReport(candidate_id=candidate_id)
            db.add(report)
            
        # Calculate Authenticity & Integrity Risk Level
        switches = candidate.telemetry_tab_switches or 0
        pastes = candidate.telemetry_copy_pastes or 0
        auth_score = max(30, 100 - (switches * 10) - (pastes * 15))
        
        if auth_score >= 85:
            risk_level = "Low Risk"
        elif auth_score >= 60:
            risk_level = "Medium Risk"
        else:
            risk_level = "High Risk"
            
        report.score_knowledge = module_scores["Knowledge"]
        report.score_solving = module_scores["Problem Solving"]
        report.score_creativity = module_scores["Creativity"]
        report.score_communication = module_scores["Communication"]
        report.score_reasoning = module_scores["Reasoning"]
        report.score_execution = module_scores["Execution"]
        report.score_career_readiness = module_scores["Career Readiness"]
        report.score_company_match = module_scores["Company Match"]
        report.score_authenticity = int(auth_score)
        report.integrity_risk_level = risk_level
        
        report.final_weighted_score = final_score
        report.strengths = strengths
        report.weaknesses = weaknesses
        
        candidate.status = "completed"
        db.commit()
        print(f"IntelligenceReport persisted for candidate {candidate_id}. Match score: {final_score}%, Authenticity: {auth_score}%, Risk: {risk_level}")
        
        # Upsert vector score data to Qdrant Vector database
        store_candidate_vector(candidate_id, module_scores, candidate.role_title)
        
        return {"status": "success", "final_score": final_score}
    except Exception as e:
        db.rollback()
        print(f"Error compiling scores: {str(e)}")
        raise e
    finally:
        db.close()

