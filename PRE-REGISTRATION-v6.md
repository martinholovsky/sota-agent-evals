# Pre-registration v6 — FROZEN 2026-10-10, before any v6 run

**Why v6.** v4: with the library and the routing layer installed, 20/20 runs invoked the `sota`
router and 0/20 read a rules file, where every rule and Audit checklist lives. v5 put a "Next
actions" block at the top of the router: 0/20 vs 1/20, **NULL** ([report](reports/2026-10-10-v5/REPORT.md)),
and the three runs it sent on to a language skill stopped at that skill's `SKILL.md`. SOTA-skills
ROADMAP 73 then chose option (c): a hook, not more text. v6 measures it.

**The treatment.** SOTA-skills `scripts/skill-depth-hook.py`
([PR #528](https://github.com/martinholovsky/SOTA-skills/pull/528)), registered as a PostToolUse hook
on the `Skill` tool. After the router loads, it names the language skill for the file types in the
working directory. After a `sota-*` skill loads, it says that skill's `SKILL.md` is only an index and
lists the absolute path of each of its rules files. Nothing else differs between the arms.

| pinned | value |
|---|---|
| case set | `cases-v3/`, unchanged (git tree `e1933c64912f86e6aa13483c2dd6a440505a55a3`) |
| model | `anthropic/claude-sonnet-5.5` via OpenRouter, as v4 and v5 |
| Agent SDK | `claude-agent-sdk==0.2.163`; the CLI version is recorded from each run's init |
| root | ONE SOTA-skills checkout for both arms: PR #528 @ `31b0359`. Its `skills/` and `scripts/install.sh` are identical to `main` @ `b807e3f` (`git diff --stat b807e3f 31b0359 -- skills scripts/install.sh` is empty); router sha256[:16] `4e2540fca371fba7`, the same as v5's control |
| control arm | `installed`: skills + the installer's routing layer (hook, CLAUDE.md directive, listing budget) |
| treatment arm | `installed+depth`: the same, plus the PostToolUse `Skill` hook above |
| harness | sota-agent-evals `8680c76` (this file is committed after it) |
| per-run limits | `--max-turns 60 --max-budget-usd 1.50 --timeout 1500`, as v4 and v5 |
| samples | 1 per case per arm: 40 runs |
| execution | **one invocation**, `--arms installed,installed+depth`, jobs interleaved case by case, `--concurrency 4`. One invocation fixes v5's deviation 1 (two invocations shared one budget counter) |
| analysis | `python -m agent_evals.analyze --v6 runs.jsonl` |

## What changed in the instrument since v5, and why

v5's primary counted a `Read` call on a rules file. A model that reads with `sed -n`, `cat` or `grep`
through Bash scores 0 on that, and this harness's maintainer reads every rules file that way (the
SOTA-skills session of 2026-10-10: 174 Bash calls, 2 Reads, 0 of them on a rules file). v5's own
traces show no such read in either arm, so v5's result stands, but a hook that sends the model to
the rules could easily be followed through Bash. v6 therefore asks the **content** question.

- **Rules text in context** = a tool result in the run carried at least one line of rules-file text.
  Fingerprints: every line of ≥ 50 characters in any `skills/sota-*/rules/*.md` of the pinned root,
  minus any line that also appears in a `SKILL.md` (a skill load already puts those in context). The
  router's own `skills/sota/rules/` are excluded, as in v5. A line matches with or without a `Read`
  (`cat -n`) or `grep -n` prefix. `agent_evals/score.py:transcript_depth()` computes it.
- **The source is Claude Code's own session transcript** (`projects/**` under the run's config
  directory, including any oversized result spilled to `tool-results/`), copied into
  `transcripts/` before cleanup. v5 deleted it.
- Controls run before freezing: the SOTA-skills session transcript scores 148 rules lines seen
  (positive). The 1,258 files of `cases-v3/` hold 0 fingerprint lines (negative). Three mutants of
  the scorer and the capture each fail the labelled tests (117 pass).

## Gates, immediately before the measurement (any failure stops v6)

1. `preflight` PASS and `sandbox-probe` PASS against the root, as in v5.
2. **Pilot**: one case (`t01`), both arms, the measurement's flags, output to a separate directory and
   **never analysed**. It passes only if (a) both rows have a CLI transcript (`context.transcripts ≥ 1`),
   (b) the treatment row shows the hook's text reached the model (`hint_router + hint_skill > 0`), and
   (c) the control row shows none. The Claude Code docs do not say whether the `Skill` tool fires
   PostToolUse; (b) is how that is learned, not assumed. If (b) fails, v6 stops and the hook is
   redesigned; no measurement is run.

## Validity checks (evaluated first, in this order; the analysis enforces each)

1. One `router_sha` across the file, and only the two arms above. Otherwise **INVALID**.
2. Every valid row has a transcript to score. Otherwise **INVALID**.
3. No control row received the hook's text. Otherwise **INVALID** (the arms are not separated).
4. **Manipulation**: ≥ 0.5 of valid runs invoked a SOTA skill in **both** arms, and ≥ 0.5 of the
   treatment's valid runs received the hook's text. Otherwise **MANIPULATION FAILED**, never a null.

## Primary outcome and decision rule (unchanged from v5 except the measure)

- **Primary** = share of valid runs with rules text in context.
- **SUPPORTED** iff Fisher's exact one-sided p < **0.05** **and** treatment − control ≥ **0.20**.
- **NULL** iff treatment − control ≤ **0.05**, a negative difference included.
- **INCONCLUSIVE** otherwise.
- Power: if control is 0/20, treatment needs ≥ 5/20 for p < 0.05 (p = 0.0236).

## Descriptive, decided now (no verdict attached)

- Per arm: v5's `rules_read` (a `Read` of a rules file) and `rules_named`, `further_skill`,
  `past_router`, the hook-hint rate, mean rules lines seen, hidden_pass, mean cost and turns per run.
  **Cost per run is reported because the hook asks the agent to read more.**
- Which rules files were reached, by case, and by which tool.
- hidden_pass sat at 1.00 in both arms of v4 and v5, so v6 is **not** expected to say whether
  reading the rules changes outcomes, and the report will not claim it does.

## Exclusions

As v5: errored, contaminated and hook-mismatch rows are excluded and counted; more than 10% excluded
in either arm is reported as **compromised** beside the verdict; a run that hits the $1.50 cap is an
errored row; an OpenRouter in-flight `402` is re-run unchanged once after the invocation finishes, and
the errored row is kept and counted.

## Budget

Account credit read 2026-10-10 21:13 CEST: **$34.55**. v5 cost $13.64 on the account for 40 runs
(SDK estimate $16.40). `--total-budget-usd 24`; the pre-flight guard requires the larger of $24 and
4 × $3.75. Spend is reported from the account after its counter settles, with two readings hours apart.

## Deviations

None yet. Any change after this file is committed is listed here with its date and reason, before
the result it could affect is read.
