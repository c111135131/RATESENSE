/* Demographic / usage survey. One question shown at a time; each "Next"
   click submits ONLY that question's answer and waits for the backend to
   confirm before advancing (requirement: don't move on until the answer
   is actually saved). Resume works the same way every other page in this
   app resumes (SRS §6): AppState.experimentId (LocalStorage) is all that's
   needed -- on load we ask the backend "how far did this experiment get?"
   and render from there. */

const SURVEY_QUESTIONS = [
  {
    field: "age", type: "radio",
    title: "1. What is your age?",
    options: ["Under 18", "18-24", "25-34", "35-44", "45-54", "55-64", "65 and above"],
  },
  {
    field: "gender", type: "radio",
    title: "2. What is your gender?",
    options: ["Male", "Female", "Non-binary", "Prefer not to say"],
    hasOther: true,
  },
  {
    field: "occupation", type: "radio",
    title: "3. What is your occupation?",
    options: ["Student", "Employed full-time", "Employed part-time", "Self-employed", "Unemployed", "Retired"],
    hasOther: true,
  },
  {
    field: "watch_hours", type: "radio",
    title: "4. How many hours per week do you spend watching video content on streaming platforms?",
    options: ["None / Less than 1 hour", "1-5 hours", "6-10 hours", "11-20 hours", "More than 20 hours"],
  },
  {
    field: "platforms", type: "checkbox",
    title: "5. On which platforms do you use the variable speed playback feature? (Select all that apply)",
    options: ["YouTube", "Netflix", "Facebook", "X / Twitter", "Instagram", "TikTok", "None"],
  },
  {
    field: "content_types", type: "checkbox",
    title: "6. For what type of content do you most frequently use variable speed playback? (Select all that apply)",
    options: ["Educational content", "Entertainment content", "News and informational content"],
    hasOther: true,
  },
  {
    field: "preferred_speed", type: "radio",
    title: "7. What is your preferred playback speed when using the variable speed playback feature?",
    options: ["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"],
  },
  {
    field: "adjust_behavior", type: "radio",
    title: "8. Do you adjust the speed throughout the video?",
    options: [
      "No, I never change the video speed",
      "No, I change it at the beginning and leave it",
      "I'll sometimes change it",
      "Yes, I change it depending on the part of the video",
    ],
    hasOther: true,
  },
  {
    field: "reasons", type: "checkbox",
    title: "9. Why do you use variable speed playback? (Select all that apply)",
    options: [
      "To save time",
      "I want to watch boring videos faster",
      "To better understand complex material",
      "To rewatch content at a different speed",
    ],
    hasOther: true,
  },
  {
    field: "satisfaction", type: "radio",
    title: "10. How satisfied are you with the variable speed playback feature?",
    options: ["Very satisfied", "Satisfied", "Neutral", "Dissatisfied", "Very dissatisfied"],
  },
];

Pages.userQuestionnaire = async () => {
  let progress;
  try {
    progress = await Api.getSurveyProgress(AppState.experimentId);
  } catch (e) {
    showToast(e.message);
    progress = { current_question: 0 };
  }

  if (progress.completed) {
    Router.advance();
    return;
  }
  renderSurveyQuestion(progress.current_question);
};

function renderSurveyQuestion(index) {
  const total = SURVEY_QUESTIONS.length;
  if (index >= total) {
    Router.advance();
    return;
  }

  const q = SURVEY_QUESTIONS[index];
  const progressPct = Math.round((index / total) * 100);
  const inputType = q.type === "checkbox" ? "checkbox" : "radio";

  renderInto(pageShell(`
    <div class="survey-progress-wrap">
      <div class="survey-progress-track"><div class="survey-progress-fill" style="width:${progressPct}%;"></div></div>
      <div class="survey-progress-label">Question ${index + 1} of ${total}</div>
    </div>
    <div class="survey-card">
      <h2 class="survey-question-title">${escapeHtml(q.title)}</h2>
      <div class="survey-options" id="surveyOptions">
        ${q.options.map((opt) => `
          <label class="survey-option">
            <input type="${inputType}" name="surveyAnswer" value="${escapeHtml(opt)}" />
            <span>${escapeHtml(opt)}</span>
          </label>
        `).join("")}
        ${q.hasOther ? `
          <label class="survey-option">
            <input type="${inputType}" name="surveyAnswer" value="Other" />
            <span>Other:</span>
            <input type="text" id="surveyOtherText" class="survey-other-input" placeholder="Please specify" maxlength="300" />
          </label>
        ` : ""}
      </div>
      <p class="field-error" id="surveyError"></p>
    </div>
    <div class="btn-row">
      <button class="btn" id="surveyNextBtn">${index === total - 1 ? "CONTINUE" : "NEXT"}</button>
    </div>
  `));

  document.getElementById("surveyNextBtn").addEventListener("click", () => handleSurveyNext(index, q));
}

async function handleSurveyNext(index, q) {
  const errorEl = document.getElementById("surveyError");
  errorEl.textContent = "";

  const checked = Array.from(document.querySelectorAll('input[name="surveyAnswer"]:checked'));
  if (checked.length === 0) {
    errorEl.textContent = "Please select an answer before continuing.";
    return;
  }

  let values = checked.map((el) => el.value);
  if (values.includes("Other")) {
    const otherInput = document.getElementById("surveyOtherText");
    const rawOther = otherInput ? otherInput.value.trim() : "";
    // Defense-in-depth only: strip tags + escape before this ever leaves
    // the browser. The REAL trust boundary is the backend's
    // sanitize_text() (backend/app/sanitize.py) -- client-side JS can
    // always be bypassed (e.g. a raw curl POST), so the server re-does
    // this independently and never trusts what the client claims to have
    // already cleaned.
    const cleanOther = sanitizeClientText(rawOther);
    values = values.map((v) => (v === "Other" ? (cleanOther ? `Other: ${cleanOther}` : "Other") : v));
  }
  const value = values.join(", ");

  const nextBtn = document.getElementById("surveyNextBtn");
  nextBtn.disabled = true;

  try {
    const resp = await Api.submitSurveyAnswer(AppState.experimentId, {
      experiment_id: AppState.experimentId,
      question_index: index,
      field: q.field,
      value,
    });

    if (resp.completed) {
      Router.advance();
    } else {
      renderSurveyQuestion(resp.current_question);
    }
  } catch (e) {
    nextBtn.disabled = false;
    errorEl.textContent = e.message;
  }
}

/* Strip HTML tags, then let the browser's own escaping (via .textContent)
   neutralize anything left -- defense-in-depth companion to the backend's
   sanitize_text(). */
function sanitizeClientText(value) {
  const withoutTags = String(value).replace(/<[^>]*>/g, "");
  return escapeHtml(withoutTags).slice(0, 300);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}