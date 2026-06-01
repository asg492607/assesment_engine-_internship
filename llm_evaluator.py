import os
import ast
import json
import urllib.request
import urllib.error

# Load local .env manually if exists
if os.path.exists(".env"):
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        k, v = parts[0].strip(), parts[1].strip().strip('"').strip("'")
                        if k:
                            os.environ[k] = v
    except Exception as e:
        print(f"Error loading .env file: {e}")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Determine which provider to use
if GROQ_API_KEY:
    LLM_API_KEY = GROQ_API_KEY
    LLM_API_URL = os.getenv("LLM_API_URL", "https://api.groq.com/openai/v1/chat/completions")
    # Standard stable free model on Groq
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3-8b-8192")
    PROVIDER_NAME = "Groq"
else:
    LLM_API_KEY = OPENAI_API_KEY
    LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    PROVIDER_NAME = "OpenAI"

class ASTAnalyzer:
    """
    Statically compiles and analyzes candidate Python submissions using the compiler AST,
    replacing arbitrary keyword rule checks with real syntactic metrics.
    """
    @staticmethod
    def analyze_code(code_content: str) -> dict:
        try:
            tree = ast.parse(code_content)
        except SyntaxError as e:
            print(f"AST Compilation Error: {str(e)}")
            return {
                "syntax_valid": False,
                "problem_solving": 30,
                "execution": 20,
                "creativity": 35,
                "error_details": f"SyntaxError on line {e.lineno}: {e.msg}"
            }
            
        # Count structural components
        classes = 0
        functions = 0
        async_funcs = 0
        try_blocks = 0
        loops = 0
        comprehensions = 0
        decorators = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes += 1
                decorators += len(node.decorator_list)
            elif isinstance(node, ast.AsyncFunctionDef):
                async_funcs += 1
                functions += 1
                decorators += len(node.decorator_list)
            elif isinstance(node, ast.FunctionDef):
                functions += 1
                decorators += len(node.decorator_list)
            elif isinstance(node, ast.Try):
                try_blocks += 1
            elif isinstance(node, (ast.For, ast.While)):
                loops += 1
            elif isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                comprehensions += 1
                
        # Calculate metric scores based on syntactic composition
        # Robust code handles errors (Try) and is structured (Classes/Functions)
        execution = min(50 + (try_blocks * 15) + (classes * 10), 100)
        
        # Complex algorithms use loops, comprehensions, and async logic
        problem_solving = min(55 + (functions * 8) + (async_funcs * 12) + (loops * 5), 100)
        
        # Creativity is represented by advanced structures: decorators, list comprehensions, generators
        creativity = min(60 + (comprehensions * 10) + (decorators * 12), 100)
        
        return {
            "syntax_valid": True,
            "problem_solving": int(problem_solving),
            "execution": int(execution),
            "creativity": int(creativity),
            "metrics": {
                "classes": classes,
                "functions": functions,
                "async_functions": async_funcs,
                "try_blocks": try_blocks,
                "loops": loops,
                "comprehensions": comprehensions,
                "decorators": decorators
            }
        }

class LLMJudge:
    """
    Real LLM Judge evaluating Code Submissions and Conversational Responses.
    """
    @staticmethod
    def _call_llm(prompt: str, system_prompt: str) -> dict:
        if not LLM_API_KEY:
            return None # Force fallback
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}"
        }
        
        data = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        
        req = urllib.request.Request(
            LLM_API_URL, 
            data=json.dumps(data).encode("utf-8"), 
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10.0) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                content = res_json["choices"][0]["message"]["content"]
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                return json.loads(content)
        except Exception as e:
            print(f"LLM API Call failed ({PROVIDER_NAME}): {str(e)}.")
            return None

    @staticmethod
    def _call_llm_vision(prompt: str, system_prompt: str, base64_images: list) -> dict:
        if not LLM_API_KEY:
            return None
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}"
        }
        
        user_content = [{"type": "text", "text": prompt}]
        for b64 in base64_images:
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
            
        data = {
            "model": "llama-3.2-11b-vision-preview",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        
        req = urllib.request.Request(
            LLM_API_URL, 
            data=json.dumps(data).encode("utf-8"), 
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=20.0) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                content = res_json["choices"][0]["message"]["content"]
                # Sometimes Groq wraps json in markdown tags
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                return json.loads(content)
        except Exception as e:
            print(f"Vision API Call failed ({PROVIDER_NAME}): {str(e)}.")
            return None

    @classmethod
    def evaluate_hackathon(cls, design_rationale: str, base64_images: list, role_title: str) -> dict:
        """
        Invokes Multimodal LLM Judge to evaluate chronological Design Prototypes.
        """
        system = "You are an uncompromising, ruthless Principal UI/UX Design Judge. You must heavily penalize poor color contrast, misaligned typography, confusing layouts, or lack of accessibility. Evaluate the chronological prototype frames and return EXACTLY a JSON object: {\"usability_score\": 0-100, \"aesthetics_score\": 0-100, \"accessibility_score\": 0-100, \"summary\": \"max 25 words\"}."
        prompt = f"Role: {role_title}\nCandidate Design Rationale:\n{design_rationale}\nAnalyze these chronological screenshots of the candidate's workflow. Be ruthlessly strict. Grade final aesthetics, usability choices, and workflow efficiency. Deduct points for any flaws."
        
        llm_result = cls._call_llm_vision(prompt, system, base64_images)
        if not llm_result:
            raise ValueError(f"{PROVIDER_NAME} API key is missing or Vision LLM API call failed. Real Multimodal evaluation is strictly required.")
        return llm_result

    @classmethod
    def evaluate_interview(cls, question: str, answer: str, role_title: str) -> dict:
        """
        Invokes LLM Judge to evaluate candidate interview transcript.
        """
        system = "You are a highly critical, strict AI Design Interviewer. You actively penalize vague answers, buzzwords without substance, and poor reasoning. Return EXACTLY a JSON object: {\"reasoning\": 0-100, \"confidence\": 0-100, \"communication\": 0-100, \"decision_quality\": 0-100, \"summary\": \"max 25 words\"}."
        prompt = f"Role: {role_title}\nQuestion: {question}\nCandidate Answer: {answer}\nBe extremely strict. Evaluate clarity, defensible reasoning, confidence level, and architectural correctness. Fail them if they give weak answers."
        
        llm_result = cls._call_llm(prompt, system)
        if not llm_result:
            raise ValueError(f"{PROVIDER_NAME} API key is missing or LLM API call failed. Real LLM evaluation is strictly required.")
        return llm_result

    @classmethod
    def generate_job_assessment(cls, role_title: str, skills: str, difficulty: str) -> dict:
        """
        Dynamically generates the Hackathon Prompt and a 3-question UI/UX Multiple Choice Quiz
        specifically tailored to the job posting.
        """
        system = """You are an expert, uncompromising Principal UI/UX Design Recruiter. 
You must generate a highly challenging, difficult assessment for a design job.
Return EXACTLY a JSON object with this schema:
{
    "hackathon_prompt": "A rigorous 2-3 sentence design challenge that forces complex UI problem solving.",
    "quiz_questions": [
        {
            "question": "A difficult, highly technical UI/UX theory question",
            "options": [
                {"text": "Correct Option", "score": 95},
                {"text": "Plausible but flawed Option", "score": 50},
                {"text": "Wrong Option", "score": 10}
            ]
        }
    ]
}
The quiz_questions array MUST contain exactly 3 questions. Do NOT wrap output in markdown, return raw JSON.
"""
        prompt = f"Role: {role_title}\nRequired Skills: {skills}\nDifficulty Level: {difficulty}\nGenerate the UI/UX design assessment JSON."
        
        llm_result = cls._call_llm(prompt, system)
        if not llm_result:
            raise ValueError("LLM API call failed to generate dynamic assessment.")
        return llm_result
