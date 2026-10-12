# Pre-registration v10 — FROZEN 2026-10-12, before any v10 run

**Why v10.** v9 got agents to the right rules file: with the code-rules hook (ROADMAP 73 (h)), a
cited file was opened in 18/20 runs. Rule tests still did not move (0.698 → 0.717, NULL;
[report](reports/2026-10-12-v9/REPORT.md)). In 6 of the 8 code-arm runs that failed a rule test, the
agent named the tested risk and left it out as a decision for the user ("a policy choice beyond
your spec"; "Decision for you: … which I left out on purpose").

The hypothesis is that the rule arrives as advice beyond the task, and the agent has an exit that
licenses handing it back. The library itself offers that exit: router principle 2 says to stop and
ask on security-relevant choices, and principle 5 says that a control "deliberately handled
elsewhere" only needs to be mentioned. The model's own scope default points the same way. v7's
named arm, the one arm that moved outcomes (0.868), presented the files as guidelines that "apply
to this task".

The operator chose on 2026-10-12 to test one arm first (ROADMAP 73 (j)): the wording that makes the
rule part of the task and closes the hand-back exit. A second arm, a bare "MANDATORY" label, runs
only if this one's result calls for it.

**The treatment.** SOTA-skills branch `roadmap-73-j` @ `a9d5865`. `scripts/code-rules-hook.py` is
v9's hook with one sentence block appended to its message (`APPLY`):

```text
These rules apply to this change: they are part of what was asked, not extras beyond the spec. Build what each one requires now, with a conservative default (a cap, a limit, an allow-list, a guard). Do not hand it back as a question or a note instead of building it, unless the user's request explicitly rules it out. In your final message, name each default you chose in one line, so the user can change it.
```

The trigger table, the file selection, the per-edit and per-session limits, and the read-in-full
instruction are unchanged (`git diff b97dabc a9d5865 -- scripts/code-rules-hook.py` adds only
`APPLY`, its use, a self-test check and a docstring note).

| arm | what it adds to `installed` |
|---|---|
| `installed+apply` | the code-rules hook from the root above, installed exactly as v9's `installed+code` |

**What would refute it.** The primary below compares this arm with v9's `installed+code`, which
differs only in the wording. If the hand-back exit is what stops the rules landing, the gain should
be at least the bar (+0.09). A difference of 0.02 or less (NULL) refutes the wording as the lever
for this hook.

| pinned | value |
|---|---|
| case set | `cases-v4`, as v7–v9 (git tree `33e4aa795f9a2e49d6893893f98c8193fe861e37`) |
| model, SDK, limits | as v7: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50, 1500 s, 1 sample per case, concurrency 4 |
| root | SOTA-skills `a9d5865`. Its `skills/` and `scripts/install.sh` are identical to v7's root `330bc4a` and v9's `52d1da0`; router sha256[:16] `4e2540fca371fba7` |
| treatment arm | `installed+apply`: 20 runs, one invocation |
| controls | v9's 20 `installed+code` rows (primary) and v7's 20 `installed` rows (secondary), reused, not re-run |
| harness | sota-agent-evals `d95972c`, 147 tests |
| analysis | `python -m agent_evals.analyze --v10 runs.jsonl reports/2026-10-12-v9/runs.jsonl reports/2026-10-11-v7/runs.jsonl` |

**Reused controls.** As in v9, at the operator's request to keep paid runs few. v9's rows are from
about 2 hours earlier, v7's from about 12 hours earlier. Drift on the provider's side would read as
an effect, and the report states this beside each verdict.

## Gates (any failure stops v10)

1. `preflight` PASS and `sandbox-probe` PASS against the root.
2. **Pilot**, case `w07` (a CSV export), never analysed. It passes if the row has a transcript and
   the transcript contains the hook's text naming `01-input-injection.md` and the `APPLY` wording
   ("they are part of what was asked").

## Validity, manipulation, decision rule (enforced by `analyze_v10`)

- **INVALID** if any of these holds:
  - more than one router across the three files;
  - an arm other than `installed+apply` in the v10 file;
  - any row whose prompt named rules files;
  - an `installed+apply` row that received the depth hook's text or the linked table;
  - a v9 `installed+code` row that carries the `APPLY` wording (the wrong file);
  - any control row that received any treatment;
  - a valid row with no transcript;
  - a group with no valid rows.
- **MANIPULATION FAILED** if the `APPLY` wording reached fewer than 0.5 of the treatment's valid runs.
- **Primary**: v9 `installed+code` → `installed+apply`. **Secondary**: v7 `installed` →
  `installed+apply`. Each uses v7's paired rule: pooled rule tests over the cases scored in both
  arms, with an exact one-sided sign-flip test over the per-case differences.
  - **SUPPORTED** iff p < 0.05 and the difference ≥ 0.09.
  - **NULL** iff the difference ≤ 0.02.
  - **INCONCLUSIVE** otherwise.
- The secondary does not qualify or replace the primary.

## Descriptive, decided now (no verdict attached)

- **Spec tests, as a harm check.** Telling the agent to build beyond the spec could break what the
  spec asked for. The report gives spec-test passes per arm. Any run that fails its spec tests in
  this arm and passed them in v9's code arm is quoted.
- **Hand-backs.** For every `installed+apply` run that fails a rule test, the report quotes the final
  message on the tested topic and says whether the agent built the rule, named it and left it out,
  or did not mention it. The same three-way reading is applied to v9's 8 failing code-arm runs,
  read before this run (6 named and left out).
- Per arm: runs that opened a cited rules file, mean rules lines seen, mean cost and turns.
- Per case: rule tests across v7 `installed`, v7 named, v9 code and v10.

**Next step, decided now.** If the primary is SUPPORTED, the second arm ("MANDATORY" label only) runs
next, to separate the label from the closed exit. If it is NULL, the label arm does not run, since a
label is the weaker form of the same instruction. The report then reads the hand-back quotes to see
whether the agents still defer and on what grounds. If INCONCLUSIVE, the operator decides.

## Exclusions and budget

- Exclusions as v7.
- Credit read 2026-10-12 02:18 CEST: **$10.85**. The usage counter read $939.1477 at 00:29 and at
  02:18, so it has settled. v9 billed $19.24 against $23.33 estimated by the SDK.
- Expected cost: 20 runs at about $0.58–0.70 each (SDK; v9's code arm averaged $0.579), about
  $12–14, plus about $0.90 for the gates and pilot. `--total-budget-usd 15`. The guard needs
  max($15, 4 × $3.75) = $15 of credit, so **the main run waits for a top-up**. The gates fit in the
  credit left.

## Deviations

None yet.
