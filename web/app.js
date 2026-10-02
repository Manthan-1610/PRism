const form = document.querySelector("#triage-form");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const verdict = document.querySelector("#verdict");
const evidence = document.querySelector("#evidence");
const reply = document.querySelector("#reply");
const summary = document.querySelector("#summary");
const meta = document.querySelector("#meta");
const submit = document.querySelector("#submit");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prUrl = document.querySelector("#pr-url").value.trim();
  submit.disabled = true;
  result.hidden = true;
  status.textContent = "Reading the PR, checking public history, asking the model…";
  try {
    const response = await fetch("/triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pr_url: prUrl }),
    });
    const data = await response.json();
    if (!response.ok) {
      status.textContent = data.error || "Triage failed.";
      return;
    }
    status.textContent = "";
    render(data);
  } catch (error) {
    status.textContent = error.message;
  } finally {
    submit.disabled = false;
  }
});

function render(data) {
  verdict.textContent = data.verdict;
  verdict.className = `verdict ${data.verdict}`;
  evidence.replaceChildren();
  for (const item of data.evidence) {
    const li = document.createElement("li");
    li.textContent = `${item.signal}: ${item.detail}`;
    evidence.append(li);
  }
  reply.textContent = data.contributor_reply;
  summary.textContent = data.maintainer_summary;
  const ctx = data.snowflake_context;
  meta.textContent = [
    `model ${data.model_used}`,
    data.escalated ? "escalated" : "small model",
    `$${Number(data.cost_usd).toFixed(4)}`,
    `${ctx.dataset}`,
    `author PRs in 7d: ${ctx.author_pr_events_7d}`,
    `source: ${ctx.source}`,
  ].join(" · ");
  result.hidden = false;
}

document.querySelector("#copy-reply").addEventListener("click", async () => {
  await navigator.clipboard.writeText(reply.textContent);
});
