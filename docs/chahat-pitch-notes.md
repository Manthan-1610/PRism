# Pitch notes: the judge, the cascade, and the eval

These are the parts of the 3-minute pitch that depend on Manthan's work. The numbers below were measured with `eval/run_eval.py` on the 15 labeled PRs. Re-run it if the rubric changes, and do not quote numbers that were not measured.

## Demo PRs

Both are real public PRs and are marked `DEMO` in `eval/labeled.csv`.

| Role | PR | What the audience should see |
| --- | --- | --- |
| Spam | [scikit-learn#32624](https://github.com/scikit-learn/scikit-learn/pull/32624) | A personal "My Contribution" note added to the README of one of the biggest Python projects. Red `likely_spam`, evidence, and a reply that still points the author somewhere useful. |
| Genuine beginner | [kornia#3328](https://github.com/kornia/kornia/pull/3328) | A real alpha-blending bug fix whose test sits at the repo root instead of `tests/`. Amber `needs_work`, and a reply that names the file to move. |

Backup if either fails live: [Dolibarr#36044](https://github.com/Dolibarr/dolibarr/pull/36044), a one-line merged fix, should show green `ship_it`.

## Running the demo

- Start the server with `PRISM_USE_CACHE=1` so GitHub is never called live. Each verdict takes about 3 to 6 seconds, or about 20 seconds when it escalates. The page shows a seconds counter while it waits.
- Click the three buttons under the search box instead of typing URLs. Each button runs one demo PR.
- You can also open `http://127.0.0.1:8000/?pr=<url>` to land straight on a verdict, which works well as browser bookmarks.
- Point at three things in order: the colored verdict, the "Why" list, then the reply.
- Model output can vary slightly between runs. If a verdict comes out differently on stage, say so and show the evidence. Explaining a borderline call honestly lands better with judges than pretending it can't happen.
- Screenshots of all three verdicts are in `docs/screenshots/` for the slides and as a fallback if the network drops.

## Lines for "Under the hood" (about 40 seconds)

- "Every verdict comes from open-weight models: Mistral's Ministral 3 14B judges every PR, and Meta's Llama 4 Maverick only steps in when the small model is unsure."
- "They run on DigitalOcean serverless inference. Swapping in any other open model is one line in the config."
- "The model never judges alone. Code measures the diff first: whitespace-only, tests, linked issue, CONTRIBUTING. Snowflake adds the author's public PR history. The model is told to trust those facts."
- "Escalation is explainable. It happens for three reasons only: low confidence, a ship-it verdict on a whitespace-only diff, or a ship-it for a tiny diff from an author opening 10 or more PRs a week."
- "A second opinion can only make a verdict stricter. It can never wave a PR through."
- "Every answer is validated against a schema and repaired if the model gets the format wrong."

## Lines for "Proof" (about 40 seconds)

- "We labeled 15 real Hacktoberfest-era PRs using the maintainers' own outcomes: spam labels, change requests, and merges."
- "With live Snowflake activity on every row, the latest run scored 10 of 15 at about five hundredths of a cent per PR."
- "An earlier run hit 13 of 15. The gap is mostly borderline ship-it calls where the model asked for more polish. Spam and needs_work stayed strong."
- "We learned the cascade the hard way: when we let the big model win outright, accuracy dropped to 11 of 15, because it trusted the PR's own description. So escalation can only make a verdict stricter."

The last line is still the strongest one for judges. It shows the eval drove a design decision.

## Questions judges may ask, and who answers

| Question | Answer | Who |
| --- | --- | --- |
| Which models, and are they really open? | Ministral 3 14B (Mistral AI) and Llama 4 Maverick (Meta), both open-weight, served by DigitalOcean. Weights are published by the vendors; we never call OpenAI or Anthropic. | Manthan |
| Why can escalation only be stricter? | When we let the large model win outright, accuracy fell to 11/15 because it trusted PR descriptions. Stricter-only stops that rubber-stamp failure mode. | Manthan |
| Is 15 enough? | It is a hackathon-sized sanity check, not a published benchmark: 5 spam / 5 needs_work / 5 ship_it, labeled from maintainer outcomes. The script runs on any larger CSV later. | Manthan |
| What is original in the harness? | The signal-first prompt, schema validation with repair, the three-rule cascade where escalation can only make a verdict stricter, and per-call cost tracking. | Manthan |
| Why not just use the big model? | It scored worse here because it trusted PR descriptions, and it costs more per call. The small model plus measured signals did better. | Manthan |
| How did you label? | Maintainer outcomes on real PRs, with a note per row in `eval/labeled.csv`. | Chahat |
| Won't it insult real beginners? | The prompt bans accusatory words and requires a concrete next step. Show the kornia reply. | Chahat |

### Ready answers (say these out loud)

**1. Which models, and why are they open-weight?**
"Every verdict is from open-weight models only: Mistral's Ministral 3 14B judges every PR, and Meta's Llama 4 Maverick escalates when the small model is unsure. Both publish weights; we run them on DigitalOcean serverless inference. The proprietary DigitalOcean models are left unused on purpose so we stay eligible for the open-source AI track."

**2. Why can escalation only make a verdict stricter?**
"We measured it. When the large model's answer always won, we got 11 out of 15 because Llama trusted the PR body's story over the diff. After we changed the rule so a second opinion can only move toward needs_work or likely_spam, never toward ship_it, we stopped that failure mode. The cascade is there for caution, not to rubber-stamp merges."

**3. Why is 15 PRs enough for a hackathon check?**
"Fifteen is not a leaderboard benchmark. It is a balanced sanity set: five spam, five needs_work, five ship_it, labeled from what maintainers actually did. It was enough to catch a real design mistake, the 11/15 cascade, and to prove the fix. The eval script takes any labeled CSV, so the same harness scales after the hackathon."
