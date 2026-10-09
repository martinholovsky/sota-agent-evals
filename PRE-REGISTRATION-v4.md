# Pre-registration v4 — FROZEN 2026-10-08, before any v4 run

**Why v4.** Every library arm in v1–v3 invoked **zero** SOTA skills: 0 of 166 runs. Each arm had
the skills but none of the routing layer a real `install.sh` install has. So every "library vs
bare" verdict measured descriptions in a listing, not rules applied
([v3 report](reports/2026-10-08-v3/REPORT.md)). v3 also hit the ceiling on `claude-sonnet-5.5`
(hidden_pass 1.00 in every arm). v4 adds the missing arm, puts the manipulation check first, and
moves to a smaller model for headroom.

| pinned | value |
|---|---|
| case set | `cases-v3/`, unchanged (git tree `e1933c64912f86e6aa13483c2dd6a440505a55a3`) |
| model | `anthropic/claude-haiku-4.5` via OpenRouter, every model class pinned to it (200K context) |
| Agent SDK | `claude-agent-sdk==0.2.163` |
| SOTA-skills | `9c00cc8`, the same skills as v3's library arm, so `installed` vs `library` differs **only** by the routing layer |
| arms | `bare`, `library`, `installed` (library + the routing layer read from that commit's `install.sh`: UserPromptSubmit hook, `CLAUDE.md` directive, `skillListingBudgetFraction` by the installer's formula = 0.06) |
| per-run limits | `--max-turns 60 --max-budget-usd 0.75 --timeout 1500` (cap lowered from v3's 1.50: see Budget) |
| concurrency | 4 |
| analysis | `python -m agent_evals.analyze --v4 runs.jsonl` |

## Manipulation check (primary, evaluated first)

- **MC:** the share of `installed` runs with ≥ 1 SOTA `Skill` call. Below **0.5**, the treatment
  did not happen, and H4/H5 are reported as **MANIPULATION FAILED**, never as a null. This is
  enforced in code (`MANIPULATION_MIN`). The same rate is reported for `library`; v1–v3 predict
  it is ~0.

## Hypotheses

- **H4:** `hidden_pass` higher in `installed` than `bare`. SUPPORTED iff the paired 95% CI lies
  above 0.
- **H5:** `hidden_pass` higher in `installed` than `library`, i.e. the routing layer's own
  effect. Same rule.
- **Descriptive only:** skill-call rates and counts per arm; which skills were invoked;
  unverified_done.

## Budget and sample size

Credit was $13.99 on 2026-10-08, with OpenRouter's counter possibly still settling. **B = $7.00.**
4 jobs in flight at the $0.75 cap can overshoot by at most $3, so B + $3 ≤ the credit. The
preflight measures C, the mean per-run cost: **S = 2 if 120·C·1.15 ≤ B, else S = 1** (60 runs per
sample). A preflight PASS and a sandbox-probe PASS are required immediately before the
measurement. Spend is reported from the account **after its counter settles**, with two
readings: the v3 report's first reading was wrong for exactly that reason.

## Exclusions and validity (decided now)

- As v3: errored, contaminated and hook-mismatch rows are excluded and counted; more than 10%
  excluded in any arm is reported as compromised.
- A run that hits the $0.75 cap is an errored row.
- **Ceiling rule:** if mean hidden_pass ≥ 0.95 in both arms of a comparison, that comparison is
  uninformative.
- **Floor rule (new):** if mean hidden_pass ≤ 0.05 in both arms, likewise uninformative.

## Deviations

**Pre-measurement work, 2026-10-09. Every row below is excluded; no measurement has run.**

1. **Smoke run, `installed` arm, haiku-4.5, t01:** **0 Skill calls**, hidden pass, and it hit the
   $0.75 per-run cap ($0.759). The cap is too low for this arm: its listing is about 48k
   characters in every turn.
2. **Diagnostics** (in-session probes, no rows):
   - the `UserPromptSubmit` hook **fires** in this harness (a marker file is written);
   - the directive and the skill descriptions **reach** the model (it quoted both);
   - **ordered** to use it, haiku invokes the `Skill` tool, and it executes ("Launching skill:
     sota").

   The harness *can*; haiku does not choose to, unprompted.
3. **Pilot (c), `installed` arm, `claude-sonnet-5.5`, t01–t03, cap $1.50:** **3/3 runs invoked a
   skill**, and in each it was only the router `sota`. Then nothing: no `sota-python`, no rules
   file read. 3/3 hidden pass; about $0.40 per run by the SDK meter.

**What this changes, decided before any measurement:**
- **The per-run cap must return to $1.50**, or `installed` rows will be cut off and excluded.
- **Haiku cannot test the rules**, because it does not invoke them.
- **The pinned SOTA-skills commit `9c00cc8` predates SOTA-skills #517.** #517 changed router BUILD
  step 4 to list the files step 2 loaded and to fail on an empty list. That is the very gap pilot
  (c) shows: the router is invoked, and nothing it routes to is loaded.

The model and pin decision is the operator's and is pending.
