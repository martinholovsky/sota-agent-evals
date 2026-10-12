# Pre-registration v12 — FROZEN 2026-10-12, before any v12 run

**Why v12.** SOTA-skills points from one skill file to another by NAME, never by path: page 8 of its
`docs/skill-map.drawio` (PR #533) counts 1,395 mentions of another skill's name across 346 skill files,
727 of them followed by `rules/NN`, and 0 Markdown links into another skill's directory. To follow
`` `sota-code-security` rules/06 §3 `` an agent must turn the name into a directory and the number into a
filename it has not seen. The operator asked (2026-10-12) to test relative links against names, and to
decide from the result whether to unify how the library refers to other files.

**What v7–v11 already show** (read from the kept transcripts before this pre-registration):
- In v7's `installed` arm, 14 of 20 runs loaded the router and opened no skill file or rules file at
  all. A cited rules file was reached in 5/20 (w01, w08, w09, w19, w20). Of those five, w01 and w19
  followed a skill's own rules index, w09 grepped the rules directory for the topic, w20 listed it,
  and w08 found its cited file by grepping after reading two SKILL.md files.
- Every failed Read of a rules path in v6–v11 (8 of 8) was a **guessed filename** for the one rules file
  the router points at by name and number only, `sota-shell-scripting` rules/06 (the real file is
  `06-ad-hoc-commands.md`; agents tried `06-agent-issued-commands.md`, `06-commands-you-type.md`, …).

So the hypothesis is not only about deep pointers: if the router's routing table links each skill's
`SKILL.md`, an agent may leave the router more often.

**The treatment.** SOTA-skills `f9de23f` (main after #533) with `tools/linkify.py` (this repo) applied to
`skills/`. It rewrites every pointer as a relative Markdown link and keeps the visible text
byte-identical, adding only the `(target)`:

| written today | in the treatment | count |
|---|---|---|
| `` `sota-x` rules/06 §3 `` | ``[`sota-x` rules/06](../../sota-x/rules/06-topic.md) §3`` | 779 |
| `` `rules/04` §1 `` (own skill) | ``[`rules/04`](04-topic.md) §1`` | 2,675 |
| `` `sota-x` `` | ``[`sota-x`](../sota-x/SKILL.md)`` | 627 |

Frontmatter, fenced code, existing links and inline code that is not exactly a pointer are left alone.
9 pointers whose number resolves to no file are left as text. 333 of 346 files change. The resulting
`skills/` tree is `c127f728033f2c953ceb720ae156c78e7c27eeac` (reproduced from `f9de23f` + the script).
The router grows from 44,449 to 49,690 bytes (+12%); that cost is part of the treatment.

| arm | what it is |
|---|---|
| `installed+links` | `installed`, run from the root above. `cli` refuses the arm on a root without the links and the plain arms on a root with them |

**Control.** v7's 20 `installed` rows, reused. `f9de23f`'s `skills/` and `scripts/install.sh` are
identical to v7's root `330bc4a` (`git diff --stat 330bc4a f9de23f -- skills scripts/install.sh` is empty),
so the control library is the treatment's minus the links. They are annotated with v12's reach fields
from their kept transcripts by `analyze --annotate-reach` (result: reached 5/20, the same five cases as
the ad-hoc count above; 2 failed rules Reads).

| pinned | value |
|---|---|
| case set | `cases-v4` (git tree `33e4aa795f9a2e49d6893893f98c8193fe861e37`) |
| model, SDK, limits | as v7: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50, 1500 s, 1 sample per case |
| execution | two invocations of 10 cases (`w01`–`w10`, `w11`–`w20`), `--concurrency 2`, `--total-budget-usd 6` each (auto top-up keeps credit below one $15 invocation, as v10's deviation 1) |
| roots | treatment: SOTA-skills worktree at `b098e3e` (= `f9de23f` + linkify; not pushed, the tree hash above pins it), router sha256[:16] `8ec08de83a3c950e`; control router `4e2540fca371fba7` |
| harness | sota-agent-evals `bb88b6c`, 152 tests |
| analysis | `python -m agent_evals.analyze --v12 runs.jsonl v7-installed-annotated.jsonl` |

## Gates (any failure stops v12)

1. `preflight` PASS and `sandbox-probe` PASS against the treatment root.
2. **Pilot**, case `w07`, never analysed. It passes if the row has a transcript in which the router's
   linked routing table appears (`links_router` > 0).

## Validity, manipulation, decision rule (enforced by `analyze_v12`)

- **INVALID** if: an arm other than `installed+links` in the v12 file; either arm has more than one
  router, or both arms have the same one; a row's prompt named rules files; a row carries any hook or
  table marker; a row lacks the reach fields; a control row saw the linked router; an arm has no
  valid rows.
- **MANIPULATION FAILED** if the linked router reached fewer than 0.5 of the treatment's valid runs.
- **Primary: a cited rules file reached** (a tool input names it), paired by case. Exact one-sided
  sign test over the discordant cases.
  - **SUPPORTED** iff p < 0.05 and the reach rate rises by ≥ 0.20. At n = 20 the p-value binds first:
    p < 0.05 needs at least 5 cases up with none down, already +0.25.
  - **NULL** iff the rise is ≤ 0.05 (at most one case net).
  - **INCONCLUSIVE** otherwise.
- **Secondary: rule tests**, v7's paired rule (SUPPORTED iff p < 0.05 and ≥ +0.09; NULL iff ≤ +0.02).
  It does not qualify the primary. Rule outcomes also depend on whether a rule that is read gets
  built (v9–v11), so links alone may move reach without moving outcomes.

## Descriptive, decided now

- Runs past the router (any skill call, SKILL.md read or rules file), per arm.
- Failed rules Reads (guessed filenames), per arm.
- For each run that reached a cited file: the route (a link followed, the skill's own index, grep, ls).
- Spec tests, mean cost, turns, rules lines seen.

**What each result would mean for unifying the references.** SUPPORTED: unify on relative links
(router first), as a separate, gated SOTA-skills change. NULL: links are not the lever; unify for
readability only, with no claim about agents. INCONCLUSIVE: the operator decides.

## Budget

Credit read 2026-10-12 11:18 CEST: $15.86, usage $959.1445, auto top-up on. Expected: 20 runs at about
$0.37–0.45 (v7 `installed` averaged $0.366), about $8–9, plus about $0.75 for the gates and pilot.

## Deviations

None yet.
