import os
import ast
import json
import urllib.request
import urllib.error

# Environment Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

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
    Falls back gracefully to compiler AST/heurisitics if API keys are missing.
    """
    @staticmethod
    def _call_llm(prompt: str, system_prompt: str) -> dict:
        if not OPENAI_API_KEY:
            return None # Force fallback
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
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
            with urllib.request.urlopen(req, timeout=8.0) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                content = res_json["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            print(f"LLM API Call failed: {str(e)}. Using fallback analyzer.")
            return None

    @classmethod
    def evaluate_hackathon(cls, code_content: str, role_title: str) -> dict:
        """
        Invokes LLM Judge to evaluate Code Quality, Architecture and Execution.
        """
        system = "You are an expert Principal AI Code Judge. Evaluate the submitted code and return a JSON object with scores: problem_solving (0-100), execution (0-100), architecture (0-100), and a string summary (max 25 words)."
        prompt = f"Role: {role_title}\nCode Submission:\n{code_content}\nEvaluate syntax, robustness, modularity, and algorithmic efficiency."
        
        llm_result = cls._call_llm(prompt, system)
        if llm_result:
            return llm_result
            
        # Fail-safe local AST evaluation
        ast_res = ASTAnalyzer.analyze_code(code_content)
        return {
            "problem_solving": ast_res["problem_solving"],
            "execution": ast_res["execution"],
            "architecture": ast_res["creativity"],
            "summary": "Statically compiled and parsed via AST compiler tree."
        }

    @classmethod
    def evaluate_interview(cls, question: str, answer: str, role_title: str) -> dict:
        """
        Invokes LLM Judge to evaluate candidate interview transcript.
        """
        system = "You are an expert AI Interview Judge. Evaluate the answer and return a JSON object with scores: reasoning (0-100), confidence (0-100), communication (0-100), decision_quality (0-100), and a string summary (max 25 words)."
        prompt = f"Role: {role_title}\nQuestion: {question}\nCandidate Answer: {answer}\nEvaluate clarity, reasoning patterns, confidence level, and structural correctness."
        
        llm_result = cls._call_llm(prompt, system)
        if llm_result:
            return llm_result
            
        # Semantic fallback score calculation
        comm = min(60 + len(answer) * 0.4, 95)
        reasoning = 90 if ("pool" in answer or "limit" in answer or "asynchronous" in answer) else 70
        confidence = 85 if len(answer) > 40 else 70
        decision = 80 if ("connection" in answer or "handling" in answer) else 70
        
        return {
            "reasoning": int(reasoning),
            "confidence": int(confidence),
            "communication": int(comm),
            "decision_quality": int(decision),
            "summary": "Transcript analyzed via semantic keyword and size heuristics."
        }
