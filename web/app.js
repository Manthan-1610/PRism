const $ = (selector) => document.querySelector(selector);

const form = $("#triage-form");
const input = $("#pr-url");
const submit = $("#submit");
const loading = $("#loading");
const elapsed = $("#elapsed");
const errorBox = $("#error");
const result = $("#result");

const VERDICT_LABELS = {
  likely_spam: "Likely spam",
  needs_work: "Needs work",
  ship_it: "Ship it",
};

const SIGNAL_LABELS = {
  whitespace_only: "Whitespace only",
  size: "Size",
  has_tests: "Tests",
  linked_issue: "Linked issue",
  followed_contributing: "CONTRIBUTING",
  author_pr_events_7d: "Author activity",
  repo_pr_events_7d: "Repo activity",
};

const NOTE_PATTERN = /\s*\(((?:Second opinion|Escalation failed)[^]*)\)\s*$/;

let timer = null;

form.addEventListener("submit", (event) => {
  event.preventDefault();
  triage(input.value.trim());
});

document.querySelectorAll(".demo").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.url;
    triage(button.dataset.url);
  });
});

$("#copy-reply").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    await navigator.clipboard.writeText($("#reply").textContent);
    button.textContent = "Copied";
  } catch {
    button.textContent = "Copy failed";
  }
  setTimeout(() => { button.textContent = "Copy reply"; }, 1500);
});

const linked = new URLSearchParams(window.location.search).get("pr");
if (linked) {
  input.value = linked;
  triage(linked);
}

async function triage(prUrl) {
  if (!prUrl) return;
  setLoading(true);
  errorBox.hidden = true;
  result.hidden = true;
  try {
    const response = await fetch("/triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pr_url: prUrl }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      showError(data.error || `Triage failed (HTTP ${response.status}).`);
      return;
    }
    render(data);
  } catch (error) {
    showError(`Could not reach the PRism server: ${error.message}`);
  } finally {
    setLoading(false);
  }
}

function setLoading(on) {
  submit.disabled = on;
  loading.hidden = !on;
  clearInterval(timer);
  if (on) {
    const start = Date.now();
    elapsed.textContent = "0s";
    timer = setInterval(() => {
      elapsed.textContent = `${Math.round((Date.now() - start) / 1000)}s`;
    }, 500);
  }
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function render(data) {
  const banner = $("#banner");
  banner.className = `banner ${data.verdict}`;
  $("#verdict").textContent = VERDICT_LABELS[data.verdict] || data.verdict;

  const link = $("#pr-link");
  link.href = data.pr_url;
  link.textContent = data.pr_url.replace(/^https?:\/\/(www\.)?github\.com\//, "");

  const percent = Math.round(Number(data.confidence) * 100);
  $("#confidence-value").textContent = `${percent}%`;
  $("#confidence-bar").style.width = `${percent}%`;

  const evidence = $("#evidence");
  evidence.replaceChildren();
  for (const item of data.evidence) {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.className = "signal-name";
    name.textContent = SIGNAL_LABELS[item.signal] || item.signal;
    li.append(name, document.createTextNode(item.detail));
    evidence.append(li);
  }

  const s = data.signals;
  const ctx = data.snowflake_context || {};
  const facts = [
    ["Lines changed", s.lines_changed],
    ["Tests included", yesNo(s.has_tests)],
    ["Links an issue", yesNo(s.linked_issue)],
    ["Follows CONTRIBUTING", yesNo(s.followed_contributing)],
    ["Author PR events, 7 days", ctx.author_pr_events_7d ?? "unavailable"],
    ["Repo PR events, 7 days", ctx.repo_pr_events_7d ?? "unavailable"],
  ];
  const dl = $("#facts");
  dl.replaceChildren();
  for (const [label, value] of facts) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value;
    dl.append(dt, dd);
  }

  renderInline($("#reply"), data.contributor_reply);

  const match = data.maintainer_summary.match(NOTE_PATTERN);
  const note = $("#second-opinion");
  $("#summary").textContent = match
    ? data.maintainer_summary.slice(0, match.index)
    : data.maintainer_summary;
  note.hidden = !match;
  note.textContent = match ? match[1] : "";

  const meta = $("#meta");
  const snowflakeLabel = ctx.source === "unavailable"
    ? "unavailable (check SNOWFLAKE_* or cache)"
    : `${ctx.dataset || "Snowflake"} (${ctx.source || "unknown"})`;
  meta.replaceChildren(
    chip("Model", data.model_used),
    chip("Escalated", data.escalated ? "yes" : "no"),
    chip("Cost", `$${Number(data.cost_usd).toFixed(4)}`),
    chip("Snowflake", snowflakeLabel),
  );

  result.hidden = false;
}

// Renders the model's [text](https://...) links and `code` spans without using innerHTML.
function renderInline(element, text) {
  element.replaceChildren();
  const pattern = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|`([^`]+)`/g;
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    element.append(text.slice(last, match.index));
    if (match[3] !== undefined) {
      const code = document.createElement("code");
      code.textContent = match[3];
      element.append(code);
    } else {
      const a = document.createElement("a");
      a.href = match[2];
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = match[1];
      element.append(a);
    }
    last = match.index + match[0].length;
  }
  element.append(text.slice(last));
}

function chip(label, value) {
  const span = document.createElement("span");
  span.className = "chip";
  const strong = document.createElement("strong");
  strong.textContent = value;
  span.append(`${label}: `, strong);
  return span;
}

function yesNo(value) {
  return value ? "yes" : "no";
}
