# Pitch notes: the judge, the cascade, and the eval

These are the parts of the 3-minute pitch that depend on Manthan's work. The numbers below were measured with `eval/run_eval.py` on the 15 labeled PRs. Re-run it if the rubric changes, and do not quote numbers that were not measured.

## Demo PRs

Both are real public PRs and are marked `DEMO` in `eval/labeled.csv`.

| Role | PR | What the audience should see |
| --- | --- | --- |
| Spam | [scikit-learn#32624](https://github.com/scikit-learn/scikit-learn/pull/32624) | A personal "My Contribution" note added to the README of one of the biggest Python projects. Red `likely_spam`, evidence, and a reply that still points the author somewhere useful. |
| Genuine beginner | [kornia#3328](https://github.com/kornia/kornia/pull/3328) | A real alpha-blending bug fix whose test sits at the repo root instead of `tests/`. Amber `needs_work`, and a reply that names the file to move. |

Backup if either fails live: [Dolibarr#36044](https://github.com/Dolibarr/dolibarr/pull/36044), a one-line merged fix, should show green `ship_it`.

## Lines for "Under the hood" (about 40 seconds)

- "Every verdict comes from open-weight models: Mistral's Ministral 3 14B judges every PR, and Meta's Llama 4 Maverick only steps in when the small model is unsure."
- "They run on DigitalOcean serverless inference. Swapping in any other open model is one line in the config."
- "The model never judges alone. Code measures the diff first: whitespace-only, tests, linked issue, CONTRIBUTING. Snowflake adds the author's public PR history. The model is told to trust those facts."
- "Escalation is explainable. It happens for three reasons only: low confidence, a ship-it verdict on a whitespace-only diff, or a ship-it for a tiny diff from an author opening 10 or more PRs a week."
- "A second opinion can only make a verdict stricter. It can never wave a PR through."
- "Every answer is validated against a schema and repaired if the model gets the format wrong."

## Lines for "Proof" (about 40 seconds)

- "We labeled 15 real Hacktoberfest-era PRs using the maintainers' own outcomes: spam labels, change requests, and merges."
- "PRism got 13 of 15 right, at about four hundredths of a cent per PR."
- "The large model was consulted on 3 of the 15. Once, it tried to approve a flawed PR, and PRism kept the stricter verdict for a human."
- "We learned that the hard way: when we let the big model win outright, accuracy dropped to 11 of 15, because it trusted the PR's own description. So we changed the rule."

The last line is the strongest one for judges. It shows the eval drove a design decision.

## Questions judges may ask, and who answers

| Question | Answer | Who |
| --- | --- | --- |
| Which models, and are they really open? | Ministral 3 14B (Mistral AI) and Llama 4 Maverick (Meta), both open-weight, served by DigitalOcean. | Manthan |
| What is original in the harness? | The signal-first prompt, the schema validation with repair, the three-rule cascade where escalation can only make a verdict stricter, and per-call cost tracking. | Manthan |
| Why not just use the big model? | It scored worse here because it trusted PR descriptions, and it costs more per call. The small model plus measured signals did better. | Manthan |
| How did you label? | Maintainer outcomes on real PRs, with a note per row in `eval/labeled.csv`. | Chahat |
| Is 15 enough? | It is a hackathon-sized sanity check, not a benchmark. The script runs on any labeled CSV. | Manthan |
| Won't it insult real beginners? | The prompt bans accusatory words and requires a concrete next step. Show the kornia reply. | Chahat |
