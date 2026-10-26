# v16: the shipped default on today's library, depth. FROZEN 2026-10-26, before any v16 run

**Question (SOTA-skills ROADMAP 73, routing depth).** Does the shipped default on today's library
put more rules-file text in front of the agent than the same default did on 2026-10-13? Between
SOTA-skills `4a5fee40` (v14's treatment root) and `origin/main` today, the library changed. Every
rules section and Audit checklist item now cites the other. Declared routing manifests for all 42
skills fixed 20 index-row routing gaps. Drifted duplicates were reconciled. The router's trigger
table and the code-rules hook still ship. v14 measured the default on the old root: a cited rules
file was reached in 13/20 runs, and 930.8 rules lines were seen per run. v16 asks only whether
today's library moves that depth. It does not ask whether outcomes move.

| arm | root | what it gets |
|---|---|---|
| control: `installed+table+code` | SOTA-skills `4a5fee40` (`git archive`); router `75b678d9bdad7b29`; root digest `59eb17746b106339` | v14's treatment rows, **reused** (2026-10-13) |
| treatment: `installed+table+code` | SOTA-skills `origin/main` @ `3287dd07949ac68bf3ea30233c29c3fbcc810a96` (`git archive`); router `ad7fb225bda66ec8`; root digest `452b21b4f34a5eb1` | the same arm, installed the same way from today's root |

**The control is reused, as declared.** The control rows are v14's
(`reports/2026-10-13-v14/runs.jsonl`, 20 rows, transcripts kept locally under
`results/v14-2026-10-13/`). The reason is budget: the operator capped v16 at **$25** on 2026-10-26.
Re-running the old root as well would double the run cost and push gates, pilot and both arms past
the cap. This file is the declaration that a later pre-registration must make before reusing rows.

**The confound this buys, stated now.** The two arms ran on different dates: 2026-10-13 and the
date of the v16 run. They share the model id `anthropic/claude-sonnet-5.5` via OpenRouter, but
that id does not pin what serves it. A change in the provider's routing, the served weights or the
sampling defaults between the two dates would move depth with no change in the library. Nothing in
this design separates that from the library's effect. The CLI version from each run's init is
recorded so a version difference can at least be seen. The harness also changed since v14
(sota-agent-evals #1, as declared in v15). It added the scorer's shadow guard and canaries, which
are scoring only. Credential-named variables no longer reach the agent; no case needs one. Both
changes are declared, not measured. Any difference v16 finds is a difference between **(today's
library, today's date)** and **(v14's library, v14's date)**.

**What differs between the two roots.** `diff -rq` over the two `git archive` trees gives 415
entries: 399 files differ and 16 exist only in today's tree.

| area | changed | only in `origin/main` |
|---|---|---|
| `skills/*/rules/*.md` | 293 (of 298) | 2 (`sota-llm-engineering` rules/07, `sota-rust` rules/09) |
| `skills/*/SKILL.md` | 43 (router included) | |
| `scripts/` | 11 | 6 entries |
| `evals/` | 21 | 5 entries |
| `docs/` | 14 | 3 entries |
| other (`commands/`, root files, `hooks/`, `.claude-plugin/`, `.github/`) | 17 | |

Rules files grew from 5,370,924 to 5,851,817 bytes (+9.0%), and SKILL.md files from 538,891 to
562,667 bytes (+4.4%). The fingerprint lines the scorer counts went from 54,403 to 58,062 (+6.7%).
What the arm actually reads from a root, and how it changed:
- **`skills/`**: everything above. The router changed in 4 lines: one principle paragraph and the
  `sota-docs-workflow` routing row. Its "What your code does" table section is byte-identical.
- **`scripts/code-rules-hook.py`**: the hook's text is unchanged. It gained four hook-only trigger
  rows: containers and sandboxes, LSM profiles, command-line interfaces, and PAM. It widened the
  authorization pattern to `roles?`, skips an agent's `scratchpad/`, and reads YAML, `.conf` and
  similar config files for the host-config rows only.
- **`scripts/install.sh`**: the routing hook command is the same. The CLAUDE.md block that
  `emit_routing_block` writes, which this arm installs as the run's global CLAUDE.md, gained a
  13-line "Shell habits a rule re-read does not fix" section. **It names three rules files**
  (`sota-shell-scripting` rules/04, 09 and 06). That could pull reads of those files that come from
  this block and not from the rules text. Their share of the depth is therefore reported apart
  (below). In v14, 6 of 20 runs already read `sota-shell-scripting` rules/06. Those reads were 7.6%
  of the lines seen.
- **Not in this arm:** today's plugin also registers a zsh `=word` PreToolUse hook
  (`hooks/hooks.json`, `scripts/zsh-equals-hook.py`). This arm registers exactly v14's hooks, the
  routing hook and the code-rules hook. So v16 measures v14's arm on today's library, not today's
  full plugin.

| pinned | value |
|---|---|
| case set | `cases-v5/` @ `a144b7e`, git tree `4cf378691832009ca7dbaf4b447ea6e6bcd89ec9` (re-checked 2026-10-26), 20 tasks, 32 rule tests (30 cited); every cited rules file exists in both roots |
| model, SDK, limits | as v14: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163` (`uv.lock`), `--max-turns 60`, `--max-budget-usd 1.50` per run, `--timeout 1500`, `--samples 1` |
| execution | **one invocation** of all 20 cases, `--arms installed+table+code`, `--concurrency 2` (as v14), `--total-budget-usd 19`, `--expect-root-digest 452b21b4f34a5eb1` |
| root guard | `--expect-root-digest` refuses a `--sota-root` whose `cli.root_digest()` is not the one pinned here, before any spend. The digest covers `skills/`, `scripts/code-rules-hook.py` and `scripts/install.sh`. Every row records its `root_digest`, and the analysis refuses a treatment row without the pinned value |
| harness | this commit; 199 tests (`uv run --group dev pytest -q`, 199 passed 2026-10-26) |
| analysis | `python -m agent_evals.analyze --v16 <v16 runs.jsonl> reports/2026-10-13-v14/runs.jsonl cases-v5/tasks` |

Build the treatment root with nothing but `git archive` (no checkout, so no `__pycache__` and no
local edits):

```sh
mkdir -p ~/v16-root && git -C ~/Github/SOTA-skills archive 3287dd07949ac68bf3ea30233c29c3fbcc810a96 | tar -x -C ~/v16-root
```

## Outcomes and decision rule (enforced by `analyze_v16`)

- **Primary: rules-file text reached per run** is v6's content measure: the lines of rules-file
  text that reached the model through any tool result, from the CLI's own transcript. It is the
  per-row field `context.rules_lines_seen` that `score.transcript_depth()` already writes, scored
  against the fingerprints of the root the row ran on. Each arm is scored against its own library
  because that is the text it could reach (see the instrument note below).
- **Rule:** paired by case over all 20 cases, with an exact one-sided sign-flip test over the
  per-case differences. This is v7's paired rule, with depth in place of rule tests. The effect
  size is the **relative pooled difference**, (Σ treatment − Σ control) / Σ control.
  - **SUPPORTED** if p < **0.05** and the relative difference is ≥ **+0.20**.
  - **NULL** if the relative difference is ≤ **+0.05**, a fall included.
  - Otherwise **INCONCLUSIVE**.
- **Why these thresholds.** +0.20 is about 186 lines per run over v14's 930.8. That is
  two-thirds of one more mid-size rules file read in full per run, which is the smallest change
  worth acting on in ROADMAP 73. It is 22× the size-only drift measured below (+0.9%) and 4× the
  +5.1% that a one-sentence prompt change moved depth at v14's own root (v14 → v15's default arm,
  p = 0.32). +0.05 covers both of those, so a NULL means the library added nothing beyond what a
  bigger file or ordinary run-to-run variation gives.
- **Secondary**, each with no verdict of its own:
  - cited rule tests (v14's primary: 19 cases, w02 out), computed with v7's paired rule;
  - all 32 rule tests;
  - reach of a cited rules file (v12's paired sign test);
  - `past_router`;
  - rules-file `Read` calls per run (`depth.rules_read`), a count that does not grow with file
    size;
  - cost per run (SDK estimate) and turns.
- **Descriptive, decided now:** `tools/v16_replay.py` runs over the v16 results directory. It
  re-scores both arms against the union of both roots' fingerprints, as a check on the instrument,
  and gives the lines from `sota-shell-scripting` rules files per arm, so that today's CLAUDE.md
  block can be seen apart from everything else. Neither carries a verdict.
- **Manipulation (MANIPULATION FAILED, never a null):** the code hook spoke (`hint_code` > 0) in at
  least 0.5 of the treatment's valid runs, and the router table (`table_router` > 0) reached at
  least 0.5 of the valid runs in **each** arm.
- **Validity (INVALID if any fails):**
  - each file holds only `installed+table+code`;
  - control rows ran on router `75b678d9bdad7b29` and treatment rows on `ad7fb225bda66ec8`;
  - every treatment row carries root digest `452b21b4f34a5eb1`;
  - no prompt names rules files;
  - no row carries a depth-hook, index-table, label or pressure marker;
  - every valid row has a transcript and the `rules_lines_seen`, `cited_reached` and
    `table_router` fields;
  - the control saw rules text, so the relative difference is defined.
  The analysis is COMPROMISED if more than 0.10 of an arm's rows are excluded. A row without
  rule-test results is excluded, as in v14.

**The instrument across two roots.** A fingerprint is a rules line of 50 characters or more that
is not also in a SKILL.md, so the fingerprint set depends on the root. Re-scoring v14's 20
transcripts gives these figures:
- against v14's root: **18,615** lines, exactly what the rows recorded (positive control);
- against today's root: 17,607 (94.6%), so today's edits rewrote about 5% of the lines v14's
  agents read;
- against the union of both: 18,615.

Scoring each arm against its own root counts what each library's files actually say. The union
re-score is the sensitivity check.

## Prediction, recorded before the run (offline replay, no model calls)

Run `python3 tools/v16_replay.py results/v14-2026-10-13 <root 4a5fee40> <root 3287dd07>` (the
transcripts are local and not committed). It gives four results:
1. **Hook naming does not change on v14's code.** Replaying v14's code edits, in order, through
   each root's `code-rules-hook.py` `select()` names 66 files under both roots, the same files in
   every run. Under the old root the replay matches the files the real hook named in **20/20**
   transcripts (positive control). None of the four new hook-only rows fires on these edits.
2. **File growth is small for the files agents read.** The rules files v14's runs read hold
   19,491 fingerprint lines on v14's root and 19,662 on today's (**×1.009**). The library as a
   whole grew ×1.067, but mostly in files these tasks do not reach.
3. **Mechanical prediction:** if agents read the same files in full, depth is **938.9 lines per
   run against 930.8 (+0.9%), which is NULL** by the rule above. A SUPPORTED therefore needs agents
   to follow something new: the cross-citations, the reconciled index rows, or the CLAUDE.md
   block's three shell-scripting files. Or it comes from the date confound.
4. **Unmeasurable here:** whether agents follow the new citations. That is what v16 measures.

Agents on today's library may write other code and read other files. This replay predicts the
hook's naming and the size effect, not the run.

## What can be detected, stated now

Depth per case is lumpy. Agents read whole files, so a case moves by the size of a file (about
200 to 1,000 lines) or not at all. Between v14 and v15's default arm, 7 of 20 cases did not move.
With about 13 cases moving by similar amounts, p < 0.05 needs about 10 of the 13 to go up. Fewer,
or a gain made up of a few large moves, reads INCONCLUSIVE even when the pooled gain is above
+0.20. One sample per case, one model, two dates. **A NULL does not show the library edits did
nothing.** It shows they did not add a fifth or more to the rules text this default puts in context
on these 20 tasks, at this model's behaviour on that date. Citations could still change *which*
section is read, or audits, which this design does not measure. **A SUPPORTED cannot be attributed
to one edit.** The citations, the index-row fixes, the CLAUDE.md block and the date all move
together here.

## What each result changes (SOTA-skills ROADMAP 73)

- **SUPPORTED:** today's library reaches measurably more rules text under the same default. The
  shell-scripting share and the union re-score say whether that is the library's text or the
  CLAUDE.md block. If it is the library's text, the citation and manifest work gets its first
  agent-harness depth row. Whether that depth moves rule tests is a separate question, for a later
  pre-registration (the secondary here is descriptive).
- **NULL:** the library edits did not change how much rules text the default puts in front of the
  agent, as the replay predicted. ROADMAP 73's depth lever stays the hook and the table. The edits
  are judged on their own grounds (correctness, audit coverage), not on depth.
- **INCONCLUSIVE:** reported as such. No second sample is run without a new operator decision. The
  $25 cap leaves no room for one.
- **MANIPULATION FAILED or INVALID:** reported, with the harness and the root checked before
  anything else. No re-run without an operator decision.

## Gates (any failure stops v16)

1. `preflight` PASS and `sandbox-probe` PASS against the treatment root, with the root guard on.
2. **Pilot**, case `w09`, one run, never analysed. It passes if its row shows the hook spoke
   (`hint_code` > 0), the table reached the model (`table_router` > 0), and the row carries root
   digest `452b21b4f34a5eb1`. The replay predicts the hook names w09's cited file
   (`sota-code-security` rules/01), as it did in v14.

## Budget

The spend of record is the OpenRouter key's usage counter, read before and after, hours apart
(README; the counter lags). The SDK estimate is reported beside it.

Credit read before the gates: **<filled by the operator's session>**.

The cap is $25 for gates, pilot and run together (operator, 2026-10-26). Expected spend, at v14's
cost per run:
- gates about $0.3 (v14: $0.27);
- pilot about $0.6;
- run about $11.4 (20 × $0.571).

That comes to about $12.3. Worst case under the flags:
- preflight 2 runs × $0.50 and sandbox-probe $0.50, so $1.50;
- pilot $1.50 (one run at the per-run cap);
- run `--total-budget-usd 19`, plus up to 2 × $1.50 in flight when the guard trips, so $22.

That sums to $25.00. The run guard needs credit of max($19, 2 × $3.75) = $19. If the budget stop
or the account leaves a case without a valid row, only that case is run again with this table
unchanged, inside the remaining cap, and recorded as a deviation. A case is never re-run because
of its score.

## Deviations

None yet.
