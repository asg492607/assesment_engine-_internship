(() => {
const API_BASE_URL = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1") || window.location.origin.includes("file:")
  ? "http://localhost:8000/api"
  : `${window.location.origin}/api`;

let currentCandidateId = null;
let currentStep = 1; // 1: Quiz, 2: Hackathon, 3: Interview

// DOM Elements
const sectionRole = document.getElementById("role-selection");
const sectionRecruiter = document.getElementById("recruiter-dashboard");
const sectionCandidate = document.getElementById("candidate-dashboard");
const sectionAssessment = document.getElementById("assessment-container");

// View Router
document.getElementById("btn-role-recruiter").addEventListener("click", () => {
  sectionRole.style.display = "none";
  sectionRecruiter.style.display = "block";
  loadTalentPool();
});

document.getElementById("btn-role-candidate").addEventListener("click", () => {
  sectionRole.style.display = "none";
  sectionCandidate.style.display = "block";
  loadCandidateJobBoard();
});

document.getElementById("btn-return-home").addEventListener("click", () => {
  document.getElementById("assessment-complete").style.display = "none";
  sectionAssessment.style.display = "none";
  sectionCandidate.style.display = "block";
  loadCandidateJobBoard();
});

// Helper for API
async function makeRequest(endpoint, options = {}) {
  options.headers = options.headers || {};
  if (!options.headers["Content-Type"] && !(options.body instanceof FormData)) {
    options.headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_BASE_URL}${endpoint}`, options);
  if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
  return await res.json();
}

// ---------------------------------------------------------
// RECRUITER WORKFLOW
// ---------------------------------------------------------
document.getElementById("btn-create-job").addEventListener("click", async () => {
  const title = document.getElementById("job-title").value;
  const skills = document.getElementById("job-skills").value;
  const diff = document.getElementById("job-difficulty").value;
  
  if (!title || !skills) return alert("Please fill all fields");
  
  try {
    document.getElementById("btn-create-job").textContent = "Publishing...";
    await makeRequest("/jobs", {
      method: "POST",
      body: JSON.stringify({
        role_title: title,
        description: "Generated dynamically via API",
        difficulty_level: diff,
        portfolio_skills: skills,
        weight_creativity: 30,
        weight_problem_solving: 25,
        weight_communication: 20,
        weight_execution: 15,
        weight_reasoning: 10
      })
    });
    alert("Job Posted Successfully!");
    document.getElementById("job-title").value = "";
    document.getElementById("job-skills").value = "";
    document.getElementById("btn-create-job").textContent = "Create & Publish Job";
  } catch (err) {
    alert("Failed to post job: " + err.message);
    document.getElementById("btn-create-job").textContent = "Create & Publish Job";
  }
});

document.getElementById("btn-refresh-pool").addEventListener("click", loadTalentPool);

async function loadTalentPool() {
  const tbody = document.getElementById("talent-pool-body");
  tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:2rem;">Fetching data...</td></tr>`;
  try {
    const data = await makeRequest("/candidates");
    if (!data || data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:2rem; color:#94a3b8;">No candidates yet.</td></tr>`;
      return;
    }
    
    let html = "";
    data.forEach(c => {
      html += `<tr style="border-bottom:1px solid #e2e8f0;">
        <td style="padding:0.75rem 0.5rem; font-family:monospace;">${c.candidate_id}</td>
        <td style="padding:0.75rem 0.5rem;">${c.role_title}</td>
        <td style="padding:0.75rem 0.5rem; font-weight:600; color:#2563eb;">${c.final_score}%</td>
        <td style="padding:0.75rem 0.5rem;">Completed</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:2rem; color:red;">Failed to load pool.</td></tr>`;
  }
}

// ---------------------------------------------------------
// CANDIDATE WORKFLOW
// ---------------------------------------------------------
async function loadCandidateJobBoard() {
  const tbody = document.getElementById("job-board-body");
  tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:2rem;">Fetching jobs...</td></tr>`;
  try {
    const data = await makeRequest("/jobs");
    if (!data || data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:2rem; color:#94a3b8;">No open jobs available.</td></tr>`;
      return;
    }
    
    let html = "";
    data.forEach(j => {
      html += `<tr style="border-bottom:1px solid #e2e8f0;">
        <td style="padding:0.75rem 0.5rem; font-weight:600;">${j.title}</td>
        <td style="padding:0.75rem 0.5rem; text-transform:capitalize;">${j.difficulty}</td>
        <td style="padding:0.75rem 0.5rem;">${j.skills}</td>
        <td style="padding:0.75rem 0.5rem;">
          <button class="btn btn-primary" onclick="window.applyToJob(${j.id})" style="padding:0.4rem 1rem; font-size:0.8rem;">Apply Now</button>
        </td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:2rem; color:red;">Failed to load jobs.</td></tr>`;
  }
}

window.applyToJob = async function(jobId) {
  try {
    const data = await makeRequest("/assessment/apply", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId })
    });
    currentCandidateId = data.candidate_id;
    sectionCandidate.style.display = "none";
    sectionAssessment.style.display = "block";
    startQuiz();
  } catch (err) {
    alert("Application failed: " + err.message);
  }
};

// ---------------------------------------------------------
// ASSESSMENT PIPELINE: PROCTORING & TELEMETRY
// ---------------------------------------------------------
let proctorTabSwitches = 0;
let proctorCopyPastes = 0;
document.addEventListener("visibilitychange", () => { if (document.hidden && currentCandidateId) proctorTabSwitches++; });
document.addEventListener("paste", () => { if (currentCandidateId) proctorCopyPastes++; });

let hackKeypresses = 0;
let hackDeletions = 0;
let hackPastedChars = 0;
let hackJourney = [];

setTimeout(() => {
  const hackArea = document.getElementById("hackathon-textarea");
  if(hackArea) {
    hackArea.addEventListener("keydown", (e) => {
      hackJourney.push({ time: Math.floor(Date.now() / 1000), action: "typed" });
      if (e.key === "Backspace" || e.key === "Delete") hackDeletions++;
      else if (e.key.length === 1) hackKeypresses++;
    });
    hackArea.addEventListener("paste", (e) => {
      const paste = (e.clipboardData || window.clipboardData).getData('text');
      hackPastedChars += paste.length;
      hackJourney.push({ time: Math.floor(Date.now() / 1000), action: "pasted" });
    });
  }
}, 1000);

// ---------------------------------------------------------
// ASSESSMENT PIPELINE: QUIZ LAYER
// ---------------------------------------------------------
async function startQuiz() {
  document.getElementById("layer-quiz").style.display = "block";
  document.getElementById("layer-hackathon").style.display = "none";
  document.getElementById("layer-interview").style.display = "none";
  fetchQuizQuestion();
}

async function fetchQuizQuestion() {
  try {
    const data = await makeRequest(`/quiz/question?candidate_id=${currentCandidateId}`);
    document.getElementById("quiz-question").textContent = data.question;
    const optsDiv = document.getElementById("quiz-options");
    optsDiv.innerHTML = "";
    
    data.options.forEach(opt => {
      const btn = document.createElement("button");
      btn.className = "btn btn-secondary";
      btn.style.textAlign = "left";
      btn.textContent = opt.text;
      btn.onclick = async () => {
        await makeRequest("/quiz/submit", {
          method: "POST",
          body: JSON.stringify({
            candidate_id: currentCandidateId,
            question: data.question,
            selected_option: opt.text,
            score_assigned: opt.score
          })
        });
        currentStep++;
        if (currentStep <= 3) {
          fetchQuizQuestion();
        } else {
          document.getElementById("layer-quiz").style.display = "none";
          startHackathon();
        }
      };
      optsDiv.appendChild(btn);
    });
  } catch (e) { alert("Error fetching quiz: " + e.message); }
}

// ---------------------------------------------------------
// ASSESSMENT PIPELINE: HACKATHON LAYER
// ---------------------------------------------------------
async function startHackathon() {
  document.getElementById("layer-hackathon").style.display = "block";
  hackJourney = [];
  
  try {
    const res = await fetch(`/api/hackathon/prompt?candidate_id=${currentCandidateId}`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById("hackathon-dynamic-prompt").innerText = data.prompt;
    }
  } catch (e) {
    console.error("Failed to load AI prompt", e);
  }
}

let screenStream = null;
let captureInterval = null;
let screenCaptures = [];

document.getElementById("btn-start-screenshare").addEventListener("click", async () => {
    try {
        screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        const videoElement = document.getElementById("screen-video");
        videoElement.srcObject = screenStream;
        videoElement.style.display = "block";
        document.getElementById("btn-start-screenshare").style.display = "none";
        document.getElementById("btn-submit-hackathon").style.display = "inline-block";
        document.getElementById("screenshare-status").innerText = "Recording your design journey... (Capturing every 10s)";
        document.getElementById("screenshare-status").style.color = "#10b981";
        
        // Start capture interval
        captureInterval = setInterval(() => {
            captureFrame();
        }, 10000);
        
    } catch (e) {
        alert("Screen sharing is required for the hackathon.");
    }
});

function captureFrame() {
    const videoElement = document.getElementById("screen-video");
    const canvas = document.getElementById("screen-canvas");
    if (videoElement.videoWidth === 0) return; // Video not loaded yet
    canvas.width = videoElement.videoWidth / 2; // scale down
    canvas.height = videoElement.videoHeight / 2;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
    const b64Full = canvas.toDataURL("image/jpeg", 0.5); // 50% quality compression
    screenCaptures.push(b64Full.split(',')[1]);
    
    // Limit to max 10 frames to avoid crashing LLM payload size limits
    if (screenCaptures.length > 10) screenCaptures.shift();
}

document.getElementById("btn-submit-hackathon").addEventListener("click", async () => {
  const rationale = document.getElementById("hackathon-textarea").value;
  
  if (!screenStream || screenCaptures.length === 0) {
    if (screenStream) captureFrame(); // Just capture one quickly if they clicked fast
    else return alert("Please start screen sharing first.");
  }
  
  // Capture the final exact frame
  captureFrame();
  
  // Stop tracks
  screenStream.getTracks().forEach(track => track.stop());
  clearInterval(captureInterval);
  
  let realIdleTime = 0;
  if (hackJourney.length > 1) {
    for (let i = 1; i < hackJourney.length; i++) {
      const diff = hackJourney[i].time - hackJourney[i-1].time;
      if (diff >= 5) realIdleTime += diff;
    }
  }
  
  try {
    document.getElementById("btn-submit-hackathon").textContent = "Uploading Journey...";
    await makeRequest("/hackathon/submit", {
      method: "POST",
      body: JSON.stringify({
        candidate_id: currentCandidateId,
        design_images_b64: screenCaptures,
        design_rationale: rationale,
        keypresses: hackKeypresses,
        deletions: hackDeletions,
        pasted_chars: hackPastedChars,
        idle_time: realIdleTime,
        journey: hackJourney
      })
    });
    document.getElementById("btn-submit-hackathon").textContent = "Submit Prototype Journey";
    document.getElementById("layer-hackathon").style.display = "none";
    startInterview();
  } catch (err) { 
    alert("Error submitting prototype: " + err.message); 
    document.getElementById("btn-submit-hackathon").textContent = "Submit Prototype Journey";
  }
});

// ---------------------------------------------------------
// ASSESSMENT PIPELINE: INTERVIEW LAYER
// ---------------------------------------------------------
let interviewStep = 1;
async function startInterview() {
  document.getElementById("layer-interview").style.display = "block";
  fetchInterviewQuestion();
}

async function fetchInterviewQuestion() {
  try {
    const res = await makeRequest(`/interview/question?candidate_id=${currentCandidateId}`);
    if (res.status === "completed") {
      document.getElementById("layer-interview").style.display = "none";
      finishAssessment();
    } else {
      addChatMsg("AI Architect", res.question);
    }
  } catch(e) {
    console.error("Failed to load interview question", e);
  }
}

function addChatMsg(sender, text) {
  const div = document.createElement("div");
  div.style.padding = "0.75rem";
  div.style.borderRadius = "6px";
  div.style.background = sender === "AI Architect" ? "#e0e7ff" : "#f1f5f9";
  div.innerHTML = `<strong>${sender}:</strong> ${text}`;
  document.getElementById("interview-chat").appendChild(div);
  document.getElementById("interview-chat").scrollTop = document.getElementById("interview-chat").scrollHeight;
}

document.getElementById("btn-submit-interview").addEventListener("click", async () => {
  const input = document.getElementById("interview-input");
  const reply = input.value;
  if (!reply) return;
  
  addChatMsg("You", reply);
  input.value = "";
  
  try {
    const res = await makeRequest("/interview/reply", {
      method: "POST",
      body: JSON.stringify({
        candidate_id: currentCandidateId,
        reply_content: reply
      })
    });
    
    if (res.candidate_status === "interview_done") {
      document.getElementById("layer-interview").style.display = "none";
      finishAssessment();
    } else {
      interviewStep++;
      fetchInterviewQuestion();
    }
  } catch (e) { alert("Interview error: " + e.message); }
});

async function finishAssessment() {
  // Sync Proctoring Data and Trigger Async Analysis
  try {
    await makeRequest("/assessment/telemetry", {
      method: "POST",
      body: JSON.stringify({
        candidate_id: currentCandidateId,
        tab_switches: proctorTabSwitches,
        copy_pastes: proctorCopyPastes
      })
    });
    await makeRequest(`/assessment/trigger_analysis?candidate_id=${currentCandidateId}`, { method: "POST" });
  } catch(e) { console.error("Sync error", e); }
  
  document.getElementById("assessment-complete").style.display = "block";
}

})();
