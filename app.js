// API Configuration
const API_BASE_URL = "http://localhost:8000/api";
let currentCandidateId = null;
let useLocalFallback = false;

// Proctoring Layer Telemetry Tracker
let proctorTabSwitches = 0;
let proctorCopyPastes = 0;

// Coding Behaviour Telemetry Tracker
let hackKeypresses = 0;
let hackDeletions = 0;
let hackPastedChars = 0;
let hackJourney = []; // Array of timed actions: {time: seconds, action: type}
let hackStartTime = Date.now();

// Setup coding textarea listener on load
setTimeout(() => {
  const hackArea = document.getElementById("hackathon-textarea");
  if (hackArea) {
    hackArea.addEventListener("keydown", (e) => {
      const elapsed = Math.max(0, Math.round((Date.now() - hackStartTime) / 1000));
      if (e.key === "Backspace" || e.key === "Delete") {
        hackDeletions++;
        hackJourney.push({time: elapsed, action: "deleted"});
      } else if (e.key.length === 1) { // Printable character
        hackKeypresses++;
        hackJourney.push({time: elapsed, action: "typed"});
      }
    });
    hackArea.addEventListener("paste", (e) => {
      const elapsed = Math.max(0, Math.round((Date.now() - hackStartTime) / 1000));
      const text = (e.clipboardData || window.clipboardData).getData('text');
      hackPastedChars += text.length;
      hackJourney.push({time: elapsed, action: "pasted"});
    });
  }
}, 500);

// Proctoring Document Event Listeners
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    proctorTabSwitches++;
    addLog(`Proctoring Alert: Browser tab switch detected (Total: ${proctorTabSwitches})`, "warning");
    syncProctoringTelemetry();
  }
});

document.addEventListener("paste", (e) => {
  // Only track paste inside input or code textareas
  if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") {
    proctorCopyPastes++;
    addLog(`Proctoring Alert: External content insertion detected (Total: ${proctorCopyPastes})`, "warning");
    syncProctoringTelemetry();
  }
});

async function syncProctoringTelemetry() {
  if (!currentCandidateId || useLocalFallback) return;
  await makeRequest("/assessment/telemetry", {
    method: "POST",
    body: JSON.stringify({
      candidate_id: currentCandidateId,
      tab_switches: proctorTabSwitches,
      copy_pastes: proctorCopyPastes
    })
  });
}


// Layer Details Technical Database
const LAYERS_DB = {
  1: {
    title: "Layer 1: Assessment Generator",
    desc: "Translates Recruiter requirements (Role, Difficulty, Weights) into dynamic, context-aware prompt templates. LangChain processes these prompts to target-generate multi-stage assignments.",
    points: [
      "Dynamic prompt construction using Jinja2 templates via LangChain",
      "Connects to internal vector stores for tailored role-matching patterns",
      "Creates dynamic test specifications: customized quiz schemas, hackathon tasks, and interview playbooks"
    ],
    tech: {
      "Framework": "LangChain",
      "LLM Engine": "GPT-4o / Claude 3.5 Sonnet",
      "Template Parser": "Pydantic & Jinja2",
      "Output Validation": "LangChain Structured Output Parser"
    }
  },
  2: {
    title: "Layer 2: Smart Quiz Engine",
    desc: "Uses an adaptive routing engine built on FastAPI. It selects questions dynamically based on the candidate's live response accuracy and target role complexity.",
    points: [
      "Difficulty levels adapt up or down in real-time during the test",
      "Assesses fundamental knowledge, complex logical concepts, and scenario thinking",
      "Sub-millisecond routing decisions optimized with fast in-memory trees"
    ],
    tech: {
      "Backend API": "FastAPI (Python)",
      "Routing Logic": "Custom Adaptive Scoring Tree",
      "Cache Store": "Redis Session Management",
      "Response Time": "< 12ms"
    }
  },
  3: {
    title: "Layer 3: Live AI Hackathon",
    desc: "A time-bound interactive coding sandbox where problem statements are customized on-the-fly. Tracks live candidate keystrokes and execution approaches.",
    points: [
      "Monitors focus duration, typing patterns, copy-paste activity, and coding flow",
      "Uses sandboxed containers to compile and run submissions",
      "Measures logical execution, time management, and creativity"
    ],
    tech: {
      "Keystroke Stream": "WebSockets",
      "Execution Environment": "Docker Sandboxed Sandbox",
      "Storage Bucket": "MinIO Object Storage (Code submissions)",
      "Tracking Agent": "Live telemetry processor"
    }
  },
  4: {
    title: "Layer 4: AI Interview Engine",
    desc: "Conducts conversational interviews. Employs fine-tuned Llama 3.1 / Mistral-7B agents to raise follow-up questions specifically targeted at weaknesses identified in prior layers.",
    points: [
      "Retrieves quiz and hackathon logs to probe candidate on specific decisions",
      "Evaluates structured reasoning, technical communication, and confidence",
      "Uses semantic vector lookups to verify answer correctness"
    ],
    tech: {
      "Inference Host": "vLLM (GPU Optimized)",
      "Model": "Llama 3.1 70B / Mistral-7B-Instruct",
      "Agent Framework": "LangGraph state machine",
      "Inference Speed": "45 tokens/second"
    }
  },
  5: {
    title: "Layer 5: Intelligence Analysis",
    desc: "Parallel background workers process the assessment data across 8 domain-specific intelligence modules, deriving multidimensional scores.",
    points: [
      "1. Knowledge: Conceptual clarity and domain comprehension",
      "2. Problem Solving: Algorithmic efficiency and error handling",
      "3. Creativity: Novel approaches and modular structuring",
      "4. Communication: Articulation of choices and active dialogue",
      "5. Reasoning: Structural decisions and optimization logic",
      "6. Execution: Task completion and clean code paradigms",
      "7. Career Readiness: Fit for the role seniority expectation",
      "8. Company Match: Aligns with hiring priorities and style"
    ],
    tech: {
      "Task Queue": "Celery Parallel Workers",
      "Broker / Backend": "Redis Broker / PostgreSQL backend",
      "Module Architecture": "Asynchronous Parallel Microservices",
      "Concurrency": "Highly parallel CPU/GPU modules"
    }
  },
  6: {
    title: "Layer 6: Scoring Engine",
    desc: "Translates the 8 dimensional profile scores into a unified index by applying the recruiter-defined weighting configuration.",
    points: [
      "Calculates weighted sums dynamically based on recruiter sliders",
      "Normalizes raw assessment metrics against standard industry benchmarks",
      "Applies premium priority overlays (e.g. higher penalty on senior level candidates for poor security logic)"
    ],
    tech: {
      "Calculation Engine": "NumPy & SciPy normalization",
      "Weight Logic": "Recruiter Priority Overlays",
      "Execution Time": "< 5ms"
    }
  },
  7: {
    title: "Layer 7: Storage & Vector Search",
    desc: "Dual storage mechanism utilizing traditional SQL storage and highly optimized vector embeddings.",
    points: [
      "PostgreSQL records all persistent metadata, logs, scores, and recruiter setups",
      "Qdrant manages vector embeddings of assessments and responses to run candidate similarity search",
      "MinIO archives code files, audio streams, and complete reports"
    ],
    tech: {
      "Relational DB": "PostgreSQL (with TimescaleDB for logs)",
      "Vector DB": "Qdrant Cluster",
      "Object Storage": "MinIO",
      "Embedding Model": "BGE-M3 (1024-dimension vectors)"
    }
  },
  8: {
    title: "Layer 8: Final Report",
    desc: "The output generation layer. Formulates structured reporting formats for human and programmatic consumption.",
    points: [
      "Interactive Recruiting Dashboard representing talent metrics",
      "Print-ready PDF report sheets generated via WeasyPrint integration",
      "Structured JSON API output for seamless ATS (Applicant Tracking System) ingestion"
    ],
    tech: {
      "PDF Engine": "WeasyPrint CSS-to-PDF",
      "API Output": "JSON API schemas",
      "ATS Compatibility": "Greenhouse / Workday standard formats"
    }
  }
};

// State Variables
let simulationState = {
  role: "Senior Backend Engineer (Python)",
  difficulty: "senior",
  weights: {
    creativity: 30,
    problemSolving: 25,
    communication: 20,
    execution: 15,
    reasoning: 10
  },
  candidateScores: {
    knowledge: 85,
    solving: 88,
    creativity: 75,
    communication: 90,
    reasoning: 82
  }
};

// DOM Elements
const roleTitleInput = document.getElementById("role-title");
const difficultySelect = document.getElementById("difficulty-level");
const weightStatusMsg = document.getElementById("weight-status-msg");
const layersCards = document.querySelectorAll(".flow-card");
const layerDetailsBox = document.getElementById("layer-details-box");

const startSimBtn = document.getElementById("start-simulation-btn");
const simLogsContainer = document.getElementById("sim-logs");

// Screen states
const screenIdle = document.getElementById("screen-idle");
const screenQuiz = document.getElementById("screen-quiz");
const screenHackathon = document.getElementById("screen-hackathon");
const screenInterview = document.getElementById("screen-interview");
const screenCelery = document.getElementById("screen-celery");

// Setup event listeners for weights
const sliders = ["creativity", "problem-solving", "communication", "execution", "reasoning"];
sliders.forEach(sliderName => {
  const slider = document.getElementById(`weight-${sliderName}`);
  const valDisplay = document.getElementById(`val-${sliderName}`);
  
  slider.addEventListener("input", (e) => {
    const val = parseInt(e.target.value);
    valDisplay.textContent = `${val}%`;
    const camelCaseName = sliderName.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
    simulationState.weights[camelCaseName] = val;
    validateWeights();
  });
});

function validateWeights() {
  const sum = Object.values(simulationState.weights).reduce((a, b) => a + b, 0);
  if (sum === 100) {
    weightStatusMsg.textContent = "Weights sum to exactly 100%";
    weightStatusMsg.className = "weight-status success";
    startSimBtn.disabled = false;
  } else {
    weightStatusMsg.textContent = `Weights sum to ${sum}% (Must equal 100%)`;
    weightStatusMsg.className = "weight-status warning";
    startSimBtn.disabled = true;
  }
}

// Show details panel
layersCards.forEach(card => {
  card.addEventListener("click", () => {
    layersCards.forEach(c => c.classList.remove("active"));
    card.classList.add("active");
    showLayerDetails(card.getAttribute("data-layer"));
  });
});

function showLayerDetails(layerNum) {
  const data = LAYERS_DB[layerNum];
  if (!data) return;
  
  let techHtml = "";
  for (const [key, val] of Object.entries(data.tech)) {
    techHtml += `
      <div class="tech-spec-item">
        <span>${key}</span>
        <span>${val}</span>
      </div>
    `;
  }
  
  layerDetailsBox.innerHTML = `
    <div class="layer-details-main">
      <h3>${data.title}</h3>
      <p style="font-size: 0.9rem; color: var(--text-secondary); line-height: 1.5; margin-bottom: 0.75rem;">
        ${data.desc}
      </p>
      <ul>
        ${data.points.map(pt => `<li>${pt}</li>`).join("")}
      </ul>
    </div>
    <div class="layer-details-tech-specs">
      <h4>Technology Blueprint</h4>
      ${techHtml}
    </div>
  `;
}

function addLog(text, type = "system") {
  const timestamp = new Date().toLocaleTimeString();
  const line = document.createElement("div");
  line.className = `sim-log-line ${type}`;
  line.innerHTML = `[${timestamp}] ${text}`;
  simLogsContainer.appendChild(line);
  simLogsContainer.scrollTop = simLogsContainer.scrollHeight;
}

function showScreen(screenId) {
  [screenIdle, screenQuiz, screenHackathon, screenInterview, screenCelery].forEach(screen => {
    screen.classList.remove("active");
  });
  document.getElementById(screenId).classList.add("active");
}

// REST helper
async function makeRequest(endpoint, options = {}) {
  if (useLocalFallback) return null;
  try {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: { "Content-Type": "application/json" },
      ...options
    });
    if (!res.ok) throw new Error("API responded with an error status code.");
    return await res.json();
  } catch (err) {
    console.warn("Backend API not reachable. Switching to client-side offline mock simulation.");
    useLocalFallback = true;
    addLog("Warning: FastAPI Backend not reachable. Flowing on client-side simulation.", "warning");
    return null;
  }
}

// Start pipeline
startSimBtn.addEventListener("click", async () => {
  simulationState.role = roleTitleInput.value;
  simulationState.difficulty = difficultySelect.value;
  const portfolioText = document.getElementById("portfolio-skills").value;
  
  // Reset proctoring and behaviour variables for new session
  proctorTabSwitches = 0;
  proctorCopyPastes = 0;
  hackKeypresses = 0;
  hackDeletions = 0;
  hackPastedChars = 0;
  
  addLog("--- INITIALIZING ASSESSMENT ENGINE PIPELINE ---", "info");
  addLog("Assessment Integrity Layer Activated.", "success");
  addLog(`Layer 1: Parsing skills from portfolio graph: [${portfolioText}]`, "info");
  
  // Try real API first
  const payload = {
    role_title: simulationState.role,
    difficulty_level: simulationState.difficulty,
    weight_creativity: simulationState.weights.creativity,
    weight_problem_solving: simulationState.weights.problemSolving,
    weight_communication: simulationState.weights.communication,
    weight_execution: simulationState.weights.execution,
    weight_reasoning: simulationState.weights.reasoning,
    portfolio_skills: portfolioText
  };
  
  const data = await makeRequest("/assessment/generate", {
    method: "POST",
    body: JSON.stringify(payload)
  });
  
  if (data && data.candidate_id) {
    currentCandidateId = data.candidate_id;
    addLog(`Real Backend Created Candidate: [${currentCandidateId}]`, "success");
    addLog("Layer 1 Successful: Custom assessment blueprint stored in DB.", "success");
  } else {
    // Local offline mock ID
    currentCandidateId = "cand_offline_" + Math.random().toString(36).substring(7);
    addLog(`Running offline mode. Mock Candidate: [${currentCandidateId}]`, "system");
  }
  
  setTimeout(() => {
    addLog("Transitioning to Layer 2: Adaptive Quiz Engine running...", "info");
    startQuiz(1);
  }, 800);
});

// Layer 2 Quiz
async function startQuiz(quizStep = 1) {
  showScreen("screen-quiz");
  
  let quizData = null;
  if (!useLocalFallback) {
    quizData = await makeRequest(`/quiz/question?candidate_id=${currentCandidateId}`);
  }
  
  // Fallback to local schema if server offline
  if (!quizData || quizData.status === "completed") {
    if (quizStep > 3) {
      addLog("Layer 2 Successful: Adaptive Quiz completed.", "success");
      addLog("Transitioning to Layer 3: Live AI Hackathon...", "info");
      startHackathon();
      return;
    }
    
    // Offline local loop questions
    quizData = {
      step: quizStep,
      difficulty: 3,
      question: quizStep === 1 
        ? "How would you optimize a slow database query involving a massive join operation?" 
        : quizStep === 2 
        ? "What is the primary function of index lookup in relational databases?" 
        : "Which HTTP status code represents a successful REST payload creation?",
      options: quizStep === 1 ? [
        { text: "Add index constraints on foreign keys and rewrite the query using a specific execution path.", score: 95 },
        { text: "Add memory caching via Redis to completely bypass the database layer.", score: 80 },
        { text: "Split the massive table into several sub-tables manually and run queries in parallel.", score: 65 }
      ] : quizStep === 2 ? [
        { text: "To speed up data retrieval operations by using lookup structures.", score: 95 },
        { text: "To encrypt database columns securely against unauthorized table access.", score: 40 },
        { text: "To enforce unique primary keys automatically inside every table.", score: 70}
      ] : [
        { text: "201 Created", score: 95 },
        { text: "200 OK", score: 80 },
        { text: "202 Accepted", score: 70 }
      ]
    };
  }
  
  // Update header text to show adaptive progress
  const screenTitle = document.querySelector("#screen-quiz .flow-card-num");
  if (screenTitle) {
    screenTitle.textContent = `Layer 2: Adaptive Quiz (Step ${quizData.step} of 3 | Current Difficulty: ${quizData.difficulty}/5)`;
  }
  
  document.getElementById("quiz-question-title").textContent = quizData.question;
  const optionsBox = document.getElementById("quiz-options-container");
  optionsBox.innerHTML = "";
  
  quizData.options.forEach(opt => {
    const btn = document.createElement("button");
    btn.className = "quiz-option-btn";
    btn.textContent = opt.text;
    btn.onclick = async () => {
      // Accumulate score
      if (quizStep === 1) {
        simulationState.candidateScores.knowledge = opt.score;
      } else {
        simulationState.candidateScores.knowledge = Math.round((simulationState.candidateScores.knowledge + opt.score) / 2);
      }
      
      let nextStep = quizStep + 1;
      let apiDone = false;
      
      if (!useLocalFallback) {
        const res = await makeRequest("/quiz/submit", {
          method: "POST",
          body: JSON.stringify({
            candidate_id: currentCandidateId,
            question: quizData.question,
            selected_option: opt.text,
            score_assigned: opt.score
          })
        });
        if (res && res.candidate_status === "quiz_done") {
          apiDone = true;
        }
      }
      
      addLog(`Quiz Step ${quizData.step} Answered. Option Score: ${opt.score}%`, "system");
      
      if (apiDone || nextStep > 3) {
        addLog(`Layer 2 Result: Quiz completed. Final adapted knowledge rating: ${simulationState.candidateScores.knowledge}%`, "success");
        addLog("Transitioning to Layer 3: Live AI Hackathon...", "info");
        startHackathon();
      } else {
        // Load next question in adaptive loop
        startQuiz(nextStep);
      }
    };
    optionsBox.appendChild(btn);
  });
}



// Layer 3 Hackathon
function startHackathon() {
  showScreen("screen-hackathon");
  hackStartTime = Date.now();
  hackJourney = [];
  const submitBtn = document.getElementById("submit-hackathon-btn");
  const textarea = document.getElementById("hackathon-textarea");
  
  submitBtn.onclick = async () => {
    const code = textarea.value;
    const lines = code.split("\n").filter(l => l.trim().length > 0).length;
    
    const creativityFactor = code.includes("yield") || code.includes("async") || code.includes("generator") ? 92 : 74;
    const problemSolvingFactor = lines > 4 ? 85 : 55;
    
    simulationState.candidateScores.creativity = creativityFactor;
    simulationState.candidateScores.solving = problemSolvingFactor;
    
    if (!useLocalFallback) {
      await makeRequest("/hackathon/submit", {
        method: "POST",
        body: JSON.stringify({
          candidate_id: currentCandidateId,
          code_content: code,
          keypresses: hackKeypresses,
          deletions: hackDeletions,
          pasted_chars: hackPastedChars,
          idle_time: 15, // Mock standard typing session inactivity pacing
          journey: hackJourney
        })
      });
    }
    
    addLog(`Layer 3 Result: Hackathon submission completed (${lines} lines of code).`, "success");
    addLog(`Analysis: Execution style evaluated (Creativity: ${creativityFactor}%, Problem Solving: ${problemSolvingFactor}%)`, "success");
    addLog("Transitioning to Layer 4: AI Interview Engine...", "info");
    startInterview();
  };
}

// Layer 4 Interview
// Layer 4 Interview
function startInterview() {
  showScreen("screen-interview");
  const qBox = document.getElementById("interview-question-text");
  const replyInput = document.getElementById("interview-reply-input");
  const sendReplyBtn = document.getElementById("submit-reply-btn");
  
  let currentStep = 1;
  
  async function loadNextQuestion() {
    replyInput.value = "";
    if (useLocalFallback) {
      if (currentStep === 1) {
        qBox.textContent = "Your database architecture conceptual answer was basic. Can you explain how you would handle query plans manually?";
      } else if (currentStep === 2) {
        qBox.textContent = "Looking at your code submission, it uses a very direct, synchronous approach. How would you refactor this to support async concurrency?";
      } else if (currentStep === 3) {
        qBox.textContent = "Finally, when deploying this solution to a highly available production environment, how do you handle monitoring, fallback safety, and logging?";
      } else {
        finishInterview();
      }
    } else {
      try {
        const data = await makeRequest(`/interview/question?candidate_id=${currentCandidateId}`);
        if (data.status === "completed" || data.step > 3) {
          finishInterview();
        } else {
          currentStep = data.step;
          qBox.textContent = data.question;
        }
      } catch (err) {
        console.error("Failed to load interview question:", err);
        addLog("Error loading dynamic interview question. Falling back to local templates.", "warning");
        useLocalFallback = true;
        loadNextQuestion();
      }
    }
  }

  function finishInterview() {
    addLog(`Layer 4 Result: 3-turn AI interview conversation completed.`, "success");
    addLog(`Analysis: Communication and reasoning profiles saved to database.`, "success");
    addLog("Transitioning to Layer 5: Parallel Intelligence Analysis...", "info");
    runCeleryWorkers();
  }

  sendReplyBtn.onclick = async () => {
    const text = replyInput.value.trim();
    if (!text) return;
    
    addLog(`Submitting turn ${currentStep} answer: "${text.substring(0, 50)}..."`, "info");
    
    const commScore = Math.min(60 + text.length * 0.5, 95);
    const reasoningScore = text.includes("pool") || text.includes("limit") || text.includes("async") || text.includes("caching") ? 90 : 70;
    
    // Incrementally average scores locally
    simulationState.candidateScores.communication = Math.round(
      (simulationState.candidateScores.communication * (currentStep - 1) + commScore) / currentStep
    );
    simulationState.candidateScores.reasoning = Math.round(
      (simulationState.candidateScores.reasoning * (currentStep - 1) + reasoningScore) / currentStep
    );
    
    if (!useLocalFallback) {
      try {
        const res = await makeRequest("/interview/reply", {
          method: "POST",
          body: JSON.stringify({
            candidate_id: currentCandidateId,
            reply_content: text
          })
        });
        
        if (res.candidate_status === "interview_done" || res.next_step > 3) {
          finishInterview();
          return;
        }
        currentStep = res.next_step;
      } catch (err) {
        console.error("Failed to submit reply:", err);
        currentStep++;
      }
    } else {
      currentStep++;
    }
    
    if (currentStep <= 3) {
      loadNextQuestion();
    } else {
      finishInterview();
    }
  };

  // Load the initial question
  loadNextQuestion();
}

// Layer 5 Celery
async function runCeleryWorkers() {
  showScreen("screen-celery");
  const grid = document.getElementById("celery-module-grid");
  grid.innerHTML = "";
  
  const modules = [
    "Knowledge", "Problem Solving", "Creativity", "Communication", 
    "Reasoning", "Execution", "Career Readiness", "Company Match"
  ];
  
  addLog("Firing parallel Celery workers across 8 modules...", "info");
  
  if (!useLocalFallback) {
    // Trigger Celery jobs in the Python backend
    await makeRequest(`/assessment/trigger_analysis?candidate_id=${currentCandidateId}`, {
      method: "POST"
    });
  }
  
  modules.forEach((mod, index) => {
    const badge = document.createElement("div");
    badge.className = "tech-badge";
    badge.style.padding = "0.5rem";
    badge.style.textAlign = "center";
    badge.style.border = "1px solid var(--border-glass)";
    badge.textContent = `⏳ ${mod}`;
    grid.appendChild(badge);
    
    setTimeout(() => {
      badge.textContent = `✅ ${mod}`;
      badge.style.borderColor = "var(--secondary)";
      badge.style.color = "var(--secondary)";
      addLog(`Celery Worker: ${mod} module completed analysis.`, "system");
      
      if (index === modules.length - 1) {
        setTimeout(() => {
          addLog("Layer 5 Successful: All 8 parallel modules calculated.", "success");
          addLog("Running Layer 6: Dynamic Scoring Calculation...", "info");
          finalizeAssessment();
        }, 500);
      }
    }, 350 * (index + 1));
  });
}

// Final Report Calculations & Render
async function finalizeAssessment() {
  addLog("Layer 7: Storing assessment results to PostgreSQL and creating Qdrant embeddings...", "info");
  
  let reportData = null;
  
  if (!useLocalFallback) {
    // Wait for the backend to auto-process and retrieve report
    // Poll status first
    let statusData = await makeRequest(`/assessment/status/${currentCandidateId}`);
    if (statusData && statusData.status === "completed") {
      reportData = await makeRequest(`/assessment/report/${currentCandidateId}`);
    } else {
      // Small delay and retry
      await new Promise(r => setTimeout(r, 1000));
      reportData = await makeRequest(`/assessment/report/${currentCandidateId}`);
    }
  }
  
  // Offline calculation logic if API failed/unreachable
  if (!reportData) {
    const weights = simulationState.weights;
    const scores = simulationState.candidateScores;
    const totalWeight = weights.creativity + weights.problemSolving + weights.communication + weights.execution + weights.reasoning;
    const executionScore = Math.round((scores.solving + scores.creativity) / 2);
    
    const finalScore = Math.round(
      ((scores.creativity * weights.creativity) +
      (scores.solving * weights.problemSolving) +
      (scores.communication * weights.communication) +
      (executionScore * weights.execution) +
      (scores.reasoning * weights.reasoning)) / (totalWeight || 1)
    );
    
    reportData = {
      candidate_id: currentCandidateId,
      role_title: simulationState.role,
      difficulty_level: simulationState.difficulty,
      match_score_percentage: finalScore,
      intelligence_breakdown: {
        knowledge_intelligence: scores.knowledge,
        problem_solving_intelligence: scores.solving,
        creativity_intelligence: scores.creativity,
        communication_intelligence: scores.communication,
        execution_intelligence: executionScore,
        reasoning_intelligence: scores.reasoning,
        career_readiness: Math.round((scores.knowledge + scores.reasoning) / 2) + 5,
        company_match: Math.round((scores.communication * 0.4) + (scores.knowledge * 0.6))
      },
      report_feedback: {
        strengths: finalScore >= 80 ? "Exceptional analytical depth, architectural safety logic, clean abstraction models." : "Reliable logical flow, solid documentation, good execution speed.",
        weaknesses: finalScore >= 80 ? "Prone to over-engineering simple pipeline loops; could choose more standard constructs." : "Inconsistent coverage of structural edge cases in heavy async systems."
      },
      storage_references: {
        postgres_transaction_id: "tx_offline_transaction_id_81a82f",
        qdrant_vector_id: "vec_offline_vector_id_331e",
        minio_hackathon_bucket_url: "s3://assessments/submissions/offline_src.tar.gz"
      },
      portfolio_profile: {
        skills: simulationState.role.includes("Python") ? ["Python", "FastAPI", "PostgreSQL"] : ["JavaScript", "React", "Node.js"],
        experience_level: simulationState.difficulty.toUpperCase(),
        domains: ["Web Systems", "Asynchronous Pipelines"],
        projects: [
          {name: "Task Dispatcher Simulator", description: "Created an interactive flow rendering microservices pipeline."}
        ],
        strength_signals: ["Excellent structural modularity"],
        learning_signals: ["Actively refining testing frameworks"]
      },
      telemetry_journey: hackJourney.length > 0 ? hackJourney : [
        {time: 2, action: "typed"},
        {time: 5, action: "typed"},
        {time: 12, action: "pasted"},
        {time: 18, action: "deleted"}
      ],
      behavioral_intelligence: {
        thinking_time: hackJourney.length > 0 ? 80 : 65,
        exploration: hackDeletions > 0 ? 75 : 60,
        confidence: hackKeypresses > 0 ? 85 : 70,
        ai_dependency: hackPastedChars > 100 ? 60 : 15
      },
      matchmaking_intelligence: {
        role_fit: finalScore,
        culture_fit: 82,
        learning_velocity: 80,
        growth_potential: 85,
        recommended_roles: simulationState.role.includes("Python") ? 
          ["Backend Engineer", "Platform Engineer", "API Specialist"] : 
          ["Frontend Engineer", "UI Developer", "Fullstack Architect"]
      },
      system_metadata: {
        engine_version: "2.1-LlamaAgentOffline",
        timestamp_processed: new Date().toISOString()
      }
    };
  }
  
  addLog("Layer 7 Successful: DB records written. Embedding synced to vector database.", "success");
  addLog("Layer 8: Report generated successfully.", "success");
  
  // Render report details
  renderCandidateReport(reportData);
  
  // Refresh recruiter talent pool database records
  await loadTalentPool();
  
  showScreen("screen-idle");
  addLog("--- WORKFLOW COMPLETED: SUCCESSFUL REPORT DISPATCH ---", "success");
  document.getElementById("report-panel-container").scrollIntoView({ behavior: "smooth" });
}

// Function to render candidate details to DOM
function renderCandidateReport(reportData) {
  document.getElementById("report-candidate-name").textContent = `Candidate ID: ${reportData.candidate_id}`;
  document.getElementById("report-role-name").textContent = `${reportData.role_title} (${reportData.difficulty_level.toUpperCase()})`;
  
  const circle = document.getElementById("score-ring-svg");
  const percentDisplay = document.getElementById("report-percentage");
  
  const finalScoreVal = reportData.match_score_percentage;
  const offset = 251.2 - (finalScoreVal / 100) * 251.2;
  circle.style.strokeDashoffset = offset;
  percentDisplay.textContent = `${finalScoreVal}%`;
  
  // Update bars
  const b = reportData.intelligence_breakdown;
  document.getElementById("bar-knowledge").style.width = `${b.knowledge_intelligence}%`;
  document.getElementById("score-val-knowledge").textContent = `${b.knowledge_intelligence}%`;
  
  document.getElementById("bar-solving").style.width = `${b.problem_solving_intelligence}%`;
  document.getElementById("score-val-solving").textContent = `${b.problem_solving_intelligence}%`;
  
  document.getElementById("bar-creativity").style.width = `${b.creativity_intelligence}%`;
  document.getElementById("score-val-creativity").textContent = `${b.creativity_intelligence}%`;
  
  document.getElementById("bar-communication").style.width = `${b.communication_intelligence}%`;
  document.getElementById("score-val-communication").textContent = `${b.communication_intelligence}%`;
  
  document.getElementById("bar-reasoning").style.width = `${b.reasoning_intelligence}%`;
  document.getElementById("score-val-reasoning").textContent = `${b.reasoning_intelligence}%`;
  
  // Render proctoring assessment integrity metrics
  const authScore = b.authenticity_score !== undefined ? b.authenticity_score : 100;
  const integrityStatus = b.assessment_integrity || "Low Risk";
  
  document.getElementById("bar-authenticity").style.width = `${authScore}%`;
  document.getElementById("score-val-authenticity").textContent = `${authScore}%`;
  
  const badge = document.getElementById("integrity-risk-badge");
  if (badge) {
    badge.textContent = integrityStatus;
    if (integrityStatus === "Low Risk") {
      badge.style.background = "rgba(16, 185, 129, 0.15)";
      badge.style.borderColor = "rgba(16, 185, 129, 0.3)";
      badge.style.color = "var(--secondary)";
    } else if (integrityStatus === "Medium Risk") {
      badge.style.background = "rgba(245, 158, 11, 0.15)";
      badge.style.borderColor = "rgba(245, 158, 11, 0.3)";
      badge.style.color = "var(--accent-orange)";
    } else {
      badge.style.background = "rgba(239, 68, 68, 0.15)";
      badge.style.borderColor = "rgba(239, 68, 68, 0.3)";
      badge.style.color = "#ef4444";
    }
  }
  
  // Render coding behaviour patterns
  document.getElementById("score-val-learning-pattern").textContent = b.learning_pattern || "Structured Builder";
  document.getElementById("score-val-confidence-pattern").textContent = b.confidence_pattern || "Decisive";
  
  // Render dynamic SVG Radar chart profile
  drawRadarChart(b);
  
  // Strengths and comments
  const commentBox = document.getElementById("report-overall-comment");
  if (finalScoreVal >= 85) {
    commentBox.textContent = "Excellent Alignment Fit";
    commentBox.style.color = "var(--secondary)";
  } else if (finalScoreVal >= 70) {
    commentBox.textContent = "Good Alignment Fit";
    commentBox.style.color = "var(--primary)";
  } else {
    commentBox.textContent = "Alternative Placement Advised";
    commentBox.style.color = "var(--accent-orange)";
  }
  
  document.getElementById("top-strength-desc").textContent = reportData.report_feedback.strengths;
  document.getElementById("focus-area-desc").textContent = reportData.report_feedback.weaknesses;
  
  // Layer 0 Portfolio Profile
  const portLoading = document.getElementById("portfolio-profile-loading");
  const portDetails = document.getElementById("portfolio-profile-details");
  
  if (reportData.portfolio_profile && reportData.portfolio_profile.skills) {
    portLoading.style.display = "none";
    portDetails.style.display = "flex";
    
    const profile = reportData.portfolio_profile;
    document.getElementById("port-experience").textContent = profile.experience_level || "Senior Developer";
    document.getElementById("port-domains").textContent = (profile.domains || []).join(", ");
    
    const projectsContainer = document.getElementById("port-projects");
    if (profile.projects && profile.projects.length > 0) {
      projectsContainer.innerHTML = profile.projects.map(p => `
        <div style="font-weight: 600; color: var(--primary);">${p.name}</div>
        <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.15rem;">${p.description}</div>
      `).join("");
    } else {
      projectsContainer.textContent = "No project logs extracted.";
    }
    
    document.getElementById("port-strength").textContent = (profile.strength_signals && profile.strength_signals.length > 0) ? profile.strength_signals[0] : "-";
    document.getElementById("port-learning").textContent = (profile.learning_signals && profile.learning_signals.length > 0) ? profile.learning_signals[0] : "-";
  } else {
    portLoading.style.display = "block";
    portLoading.textContent = "No Layer 0 Portfolio details found.";
    portDetails.style.display = "none";
  }
  
  // Render Layer 5.5 Behavioral Intelligence
  const beh = reportData.behavioral_intelligence || { thinking_time: 70, exploration: 70, confidence: 70, ai_dependency: 10 };
  document.getElementById("bar-behavior-thinking").style.width = `${beh.thinking_time}%`;
  document.getElementById("score-val-behavior-thinking").textContent = `${beh.thinking_time}%`;
  document.getElementById("bar-behavior-exploration").style.width = `${beh.exploration}%`;
  document.getElementById("score-val-behavior-exploration").textContent = `${beh.exploration}%`;
  document.getElementById("bar-behavior-confidence").style.width = `${beh.confidence}%`;
  document.getElementById("score-val-behavior-confidence").textContent = `${beh.confidence}%`;
  document.getElementById("bar-behavior-aidep").style.width = `${beh.ai_dependency}%`;
  document.getElementById("score-val-behavior-aidep").textContent = `${beh.ai_dependency}%`;
  
  // Render Layer 9 Matchmaking Intelligence
  const mat = reportData.matchmaking_intelligence || { role_fit: 75, culture_fit: 75, learning_velocity: 75, growth_potential: 75, recommended_roles: [] };
  document.getElementById("match-role-fit").textContent = `${mat.role_fit}%`;
  document.getElementById("match-culture-fit").textContent = `${mat.culture_fit}%`;
  document.getElementById("match-learning-velocity").textContent = `${mat.learning_velocity}%`;
  document.getElementById("match-growth-potential").textContent = `${mat.growth_potential}%`;
  
  const recRolesContainer = document.getElementById("match-recommended-roles");
  if (mat.recommended_roles && mat.recommended_roles.length > 0) {
    recRolesContainer.innerHTML = mat.recommended_roles.map(r => `<span class="hiring-badge">${r}</span>`).join("");
  } else {
    recRolesContainer.innerHTML = `<span class="hiring-badge">-</span>`;
  }

  // Layer 3 Journey Replay
  initJourneyPlayer(reportData.telemetry_journey);

  // JSON Output
  document.getElementById("json-code-box").textContent = JSON.stringify(reportData, null, 2);
}

let replayInterval = null;
let replayTimeline = [];
let replayIndex = 0;
let isReplaying = false;

function initJourneyPlayer(journey) {
  if (replayInterval) {
    clearInterval(replayInterval);
    replayInterval = null;
  }
  
  const loadingEl = document.getElementById("journey-replay-loading");
  const detailsEl = document.getElementById("journey-replay-details");
  const playBtn = document.getElementById("replay-play-btn");
  const playIcon = document.getElementById("replay-play-icon");
  const playText = document.getElementById("replay-play-text");
  const logBox = document.getElementById("replay-log-box");
  const progressFill = document.getElementById("replay-progress-fill");
  const currentTimeEl = document.getElementById("replay-current-time");
  const totalTimeEl = document.getElementById("replay-total-time");
  
  isReplaying = false;
  replayIndex = 0;
  playIcon.textContent = "▶";
  playText.textContent = "Play Replay";
  progressFill.style.width = "0%";
  currentTimeEl.textContent = "0s";
  
  if (!journey || journey.length === 0) {
    loadingEl.style.display = "block";
    loadingEl.textContent = "No journey replay timeline logged for this session.";
    detailsEl.style.display = "none";
    return;
  }
  
  loadingEl.style.display = "none";
  detailsEl.style.display = "flex";
  
  replayTimeline = journey.sort((a, b) => a.time - b.time);
  const totalDuration = replayTimeline[replayTimeline.length - 1].time || 10;
  totalTimeEl.textContent = `${totalDuration}s`;
  
  logBox.innerHTML = `<div style="color: var(--text-muted);">Loaded ${replayTimeline.length} timeline actions. Click Play.</div>`;
  
  playBtn.onclick = () => {
    if (isReplaying) {
      clearInterval(replayInterval);
      replayInterval = null;
      isReplaying = false;
      playIcon.textContent = "▶";
      playText.textContent = "Resume Replay";
      addPlayLog("Playback paused.");
    } else {
      isReplaying = true;
      playIcon.textContent = "⏸";
      playText.textContent = "Pause";
      
      if (replayIndex >= replayTimeline.length) {
        replayIndex = 0;
        logBox.innerHTML = "";
      }
      
      addPlayLog("Playback started...");
      
      let currentTick = replayIndex > 0 ? replayTimeline[replayIndex - 1].time : 0;
      
      replayInterval = setInterval(() => {
        currentTick++;
        currentTimeEl.textContent = `${currentTick}s`;
        const percentage = Math.min(100, (currentTick / totalDuration) * 100);
        progressFill.style.width = `${percentage}%`;
        
        while (replayIndex < replayTimeline.length && replayTimeline[replayIndex].time <= currentTick) {
          const evt = replayTimeline[replayIndex];
          let color = "var(--text-primary)";
          if (evt.action === "pasted") color = "var(--accent-orange)";
          if (evt.action === "deleted") color = "#ef4444";
          if (evt.action === "typed") color = "var(--secondary)";
          
          addPlayLog(`[Time: ${evt.time}s] Action: <span style="color: ${color}; font-weight: bold; text-transform: uppercase;">${evt.action}</span>`);
          replayIndex++;
        }
        
        if (currentTick >= totalDuration || replayIndex >= replayTimeline.length) {
          clearInterval(replayInterval);
          replayInterval = null;
          isReplaying = false;
          playIcon.textContent = "▶";
          playText.textContent = "Replay Again";
          addPlayLog("Playback completed.");
        }
      }, 300);
    }
  };
  
  function addPlayLog(msg) {
    const div = document.createElement("div");
    div.innerHTML = msg;
    logBox.appendChild(div);
    logBox.scrollTop = logBox.scrollHeight;
  }
}

// Draw dynamic custom SVG Radar Chart representing candidate scores
function drawRadarChart(breakdown) {
  const svg = document.getElementById("radar-chart-svg");
  svg.innerHTML = "";
  
  const axes = [
    { name: "Knowledge", val: breakdown.knowledge_intelligence || 75 },
    { name: "Problem Solving", val: breakdown.problem_solving_intelligence || 75 },
    { name: "Creativity", val: breakdown.creativity_intelligence || 75 },
    { name: "Communication", val: breakdown.communication_intelligence || 75 },
    { name: "Reasoning", val: breakdown.reasoning_intelligence || 75 }
  ];
  
  const center = 110;
  const maxRadius = 80;
  const numPoints = axes.length;
  
  // Helper to map angles to SVG points
  const getPointCoords = (index, value) => {
    const angle = (Math.PI * 2 / numPoints) * index - Math.PI / 2;
    const r = (value / 100) * maxRadius;
    const x = center + r * Math.cos(angle);
    const y = center + r * Math.sin(angle);
    return { x, y };
  };
  
  // Draw web rings representing scale steps: 25%, 50%, 75%, 100%
  const steps = [25, 50, 75, 100];
  steps.forEach(step => {
    let pointsStr = "";
    for (let i = 0; i < numPoints; i++) {
      const { x, y } = getPointCoords(i, step);
      pointsStr += `${x},${y} `;
    }
    const polygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
    polygon.setAttribute("points", pointsStr.trim());
    polygon.setAttribute("fill", "none");
    polygon.setAttribute("stroke", "rgba(255, 255, 255, 0.08)");
    polygon.setAttribute("stroke-width", "1");
    svg.appendChild(polygon);
  });
  
  // Draw axes lines and labels
  axes.forEach((axis, i) => {
    const outerPoint = getPointCoords(i, 100);
    const labelPoint = getPointCoords(i, 115);
    
    // Line
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", center);
    line.setAttribute("y1", center);
    line.setAttribute("x2", outerPoint.x);
    line.setAttribute("y2", outerPoint.y);
    line.setAttribute("stroke", "rgba(255, 255, 255, 0.12)");
    line.setAttribute("stroke-width", "1");
    svg.appendChild(line);
    
    // Label text
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", labelPoint.x);
    text.setAttribute("y", labelPoint.y + 4);
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("fill", "var(--text-secondary)");
    text.setAttribute("font-size", "9px");
    text.setAttribute("font-weight", "500");
    text.textContent = axis.name;
    svg.appendChild(text);
  });
  
  // Draw Candidate scoring polygon shape
  let scorePoints = [];
  axes.forEach((axis, i) => {
    const { x, y } = getPointCoords(i, axis.val);
    scorePoints.push(`${x},${y}`);
  });
  
  const scorePolygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
  scorePolygon.setAttribute("points", scorePoints.join(" "));
  scorePolygon.setAttribute("fill", "rgba(59, 130, 246, 0.25)");
  scorePolygon.setAttribute("stroke", "var(--primary)");
  scorePolygon.setAttribute("stroke-width", "2");
  svg.appendChild(scorePolygon);
  
  // Draw small circles at value nodes
  axes.forEach((axis, i) => {
    const { x, y } = getPointCoords(i, axis.val);
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", x);
    circle.setAttribute("cy", y);
    circle.setAttribute("r", "4");
    circle.setAttribute("fill", "var(--secondary)");
    circle.setAttribute("stroke", "rgba(255,255,255,0.8)");
    circle.setAttribute("stroke-width", "1");
    svg.appendChild(circle);
  });
}

// Fetch and load database records into the Recruiter Talent Pool grid
async function loadTalentPool() {
  const data = await makeRequest("/candidates");
  const rowsContainer = document.getElementById("talent-pool-rows");
  if (!rowsContainer) return;
  
  if (data && data.length > 0) {
    rowsContainer.innerHTML = "";
    data.forEach(cand => {
      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border-glass)";
      tr.style.cursor = "pointer";
      tr.className = "pool-row";
      
      const dateFormatted = new Date(cand.timestamp).toLocaleString();
      
      tr.innerHTML = `
        <td style="padding: 0.75rem 1rem; color: var(--primary); font-weight: 500;">${cand.candidate_id}</td>
        <td style="padding: 0.75rem 1rem;">${cand.role_title}</td>
        <td style="padding: 0.75rem 1rem; text-transform: uppercase; font-size: 0.75rem;">${cand.difficulty_level}</td>
        <td style="padding: 0.75rem 1rem; text-align: right; font-weight: 600; color: var(--secondary);">${cand.final_score}%</td>
        <td style="padding: 0.75rem 1rem; text-align: right; color: var(--text-muted);">${dateFormatted}</td>
      `;
      
      tr.onclick = async () => {
        addLog(`Loading scorecard and reports for selected candidate: ${cand.candidate_id}`, "info");
        const details = await makeRequest(`/assessment/report/${cand.candidate_id}`);
        if (details) {
          renderCandidateReport(details);
          document.getElementById("report-panel-container").scrollIntoView({ behavior: "smooth" });
        }
      };
      
      rowsContainer.appendChild(tr);
    });
  } else {
    rowsContainer.innerHTML = `
      <tr>
        <td colspan="5" style="padding: 1.5rem; text-align: center; color: var(--text-muted);">No candidate reports saved in database yet. Run the simulation to add records!</td>
      </tr>
    `;
  }
}

// Copy JSON utility
document.getElementById("copy-json-btn").addEventListener("click", () => {
  const code = document.getElementById("json-code-box").textContent;
  navigator.clipboard.writeText(code).then(() => {
    const btn = document.getElementById("copy-json-btn");
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = "Copy JSON"; }, 1500);
  });
});

// Refresh button trigger
document.getElementById("refresh-pool-btn").addEventListener("click", async () => {
  addLog("Querying PostgreSQL candidates database list...", "info");
  await loadTalentPool();
});

// Init load
showLayerDetails(1);
validateWeights();
loadTalentPool();
drawRadarChart({
  knowledge_intelligence: 0,
  problem_solving_intelligence: 0,
  creativity_intelligence: 0,
  communication_intelligence: 0,
  reasoning_intelligence: 0
});
addLog("Visual system ready. Click on any architecture layer to inspect details.", "system");

