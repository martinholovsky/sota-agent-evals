# v16: the shipped default on today's library, depth. Run 2026-10-27

**Verdict by the frozen rule: INCONCLUSIVE.** On cases-v5, v14's shipped-default arm
(`installed+table+code`) installed from SOTA-skills `3287dd07` put **1,054.3** rules-file lines in
front of the agent per run, against **930.8** for the same arm on `4a5fee40` (v14's rows, reused as
declared). That is **+13.3%** (+123.5 lines per run), with 13 cases up, 6 down, 1 equal, and a
one-sided sign-flip p = **0.107**. SUPPORTED needed p < 0.05 **and** at least +20%; NULL needed
+5% or less. The result is between them. The offline replay predicted +0.9% (NULL) if agents read
the same files; they did not.

Pre-registration: [PRE-REGISTRATION-v16.md](../../PRE-REGISTRATION-v16.md), frozen at `6536d76`
before any v16 run. Treatment root built with `git archive 3287dd07`, root digest
`452b21b4f34a5eb1` (checked by `--expect-root-digest` before any spend, and on every row). Router
`ad7fb225bda66ec8` on every treatment row; control rows on `75b678d9bdad7b29`. CLI **2.1.286** in
every transcript of both arms (bundled with `claude-agent-sdk==0.2.163`), so a CLI difference is
ruled out; the provider-side confound declared in the pre-registration is not.

**Gates.** Harness 199/199 tests passed. Preflight PASS (2 runs, $0.23), sandbox-probe PASS (egress
403, DNS blocked, 0 credential-named variables in the sandbox), pilot w09 PASS: `hint_code` 6,
`table_router` 1, root digest `452b21b4f34a5eb1` ([pilot-w09.jsonl](pilot-w09.jsonl), never
analysed). Then one invocation of all 20 cases, `--concurrency 2`, `--total-budget-usd 19`. No
errors, no excluded rows, no rules-file read errors, not compromised, nothing invalid.

## Results

| | control: `4a5fee40` (v14, 2026-10-13) | treatment: `3287dd07` (2026-10-27) |
|---|---|---|
| **rules-file lines seen per run (primary)** | **930.8** | **1,054.3 (+13.3%)** |
| rules-file `Read` calls per run | 3.25 | 3.20 |
| a cited rules file reached | 13/20 | 13/20 |
| past the router | 19/20 | 18/20 |
| hook text in context (`hint_code` > 0) | 20/20 | 20/20 |
| router table in context | 20/20 | 20/20 |
| cited rule tests (19 cases, w02 out) | 0.667 | 0.767 (2 up, 0 down, p = 0.25) |
| all 32 rule tests | 22/32 | 25/32 |
| cost per run (SDK estimate) | $0.571 | $0.611 |
| turns per run | 23.95 | 24.40 |

Manipulation: passed (the hook spoke in 20/20 treatment runs; the table reached 20/20 in each arm).

**Per case (lines seen):** w16 688 → 2,031, w08 813 → 1,539, w11 1,046 → 1,714, w14 239 → 570,
w17 1,185 → 1,538, w15 969 → 1,256, w02 1,275 → 1,539; down: w03 1,594 → 1,119, w01 1,208 → 851,
w09 1,313 → 1,046, w12 990 → 758, w18 946 → 758, w04 1,572 → 1,553; w05 0 → 0. The other six
(w06, w07, w10, w13, w19, w20) moved up by under 1.5%. Full table: [analysis-preregistered.json](analysis-preregistered.json).

## Descriptive (no verdict; decided in the pre-registration)

From [replay-descriptive.txt](replay-descriptive.txt) (`tools/v16_replay.py`, no model calls):

- **The instrument holds across roots.** v14's transcripts re-score to exactly their recorded
  18,615 lines against their own root (positive control). Against the union of both roots'
  fingerprints the arms read 18,615 and 21,086: the same +13.3%.
- **Not file growth.** Files read in full would predict 1,063.8 lines per run on today's root
  (×1.009 per file read); the number of rules-file reads per run is flat (3.25 → 3.20). The gain
  is in *which* files were read, concentrated in a few cases.
- **Not the CLAUDE.md block.** Its new section names three `sota-shell-scripting` rules files. Lines
  from those files fell, from 1,420 of 18,615 (7.6%) to 1,090 of 21,086 (5.2%).
- **Not the hook.** Replaying each arm's own edits through each root's hook names the same files
  under both roots (66 → 66 for the control's edits, 71 → 71 for the treatment's), and the replay
  matches the real hook in 20/20 runs of each arm.

## What this changes (SOTA-skills ROADMAP 73)

As pre-registered for INCONCLUSIVE: reported as such, and **no second sample** is run without a new
operator decision. The $25 cap leaves room for about one more invocation, but the decision is not
this report's. What can be said: today's library moved depth in the direction the citation and
manifest work intended, by about two-thirds of the effect the rule required, and the move is not
explained by file size, the CLAUDE.md block or the hook. It cannot be separated from the date
(provider routing, served weights or sampling between 2026-10-13 and 2026-10-27), and one sample
per case is lumpy: three cases account for most of the gain.

## Budget

Credit read before the gates: **$63.87** on the account (21:46Z, read twice; total credits
$1,175.00, usage $1,111.13). SDK estimate: gates $0.27, pilot $0.60, run $12.21, **$13.08** in all.
The key's usage counter, the spend of record, read **$10.84** above the pre-gate reading at 22:13Z;
it lags, and the settled figure is recorded below when read hours later.

Settled spend of record: *to be read and filled in hours after the run.*

## Deviations

None. The pilot's flags (`--concurrency 1 --total-budget-usd 1.50`) were not specified in the
pre-registration; it is never analysed.
