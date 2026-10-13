# cases-v5: how the tasks are chosen. FROZEN 2026-10-13, before any id is drawn

**Why a fresh set.** Every SUPPORTED result since v7 was measured on cases-v4, and the router's
trigger table (SOTA-skills ROADMAP 73 (o)) was written and replayed against those same 20 tasks.
v13's own pre-registration says a SUPPORTED result there "licenses a fresh case set, not a claim".
This set is that fresh case set.

**Why this design** (SOTA-skills operator decision 2026-10-13, option (b)). There were three ways
to get new tasks:

- **(a) topics the table has no row for.** This measures only transfer to new topics.
- **(b) tasks sampled from an external standard and written by an author who never sees the
  library.** Library rules are cited only after the tasks are frozen.
- **(c) new tasks on the rules cases-v4 already cites.** These lead back to the same table rows.

Only (b) keeps the choice of tasks and the table from having been fitted to each other.

## Source

OWASP ASVS **5.0.0** (`OWASP/ASVS` tag `v5.0.0_release`, commit `5cf9b03`). It has **345**
requirements. Counted from the source Markdown (`| **N.N.N** |` rows) and from an independent
extraction, the id sets are identical.

**Licence.** ASVS is CC BY-SA 4.0 and this repository is Apache-2.0, so **no ASVS text enters
this repository**. Files here carry ids only. Prompts, tests and reasons are written in our own
words.

## Sampling

```
SEED  = "cases-v5: OWASP ASVS 5.0.0 sample, frozen 2026-10-13"
order = the 345 ids sorted numerically, then random.Random(int(sha256(SEED), 16)).shuffle(order)
```

`tools/sample.py` computes this and writes `ORDER.txt`. The script and the seed are committed with
this file, and pushed, before the script is run.

## Screening (in sample order; stop at 20 eligible)

The screener has only the requirement's text, `base/README.md` and `base/shop/`. It has no access
to SOTA-skills, any installed skill, or cases-v1–v4's tasks. It works through `ORDER.txt` from the
top. For every id it reads, it records a verdict and a one-line reason in `SCREENING.md`. It stops
when 20 are eligible. Once an id is screened, it is not re-screened, swapped or skipped.

A requirement is **eligible** only if all four hold:

- **E1, in scope.** It is about server-side application behaviour of a kind this shop has, or
  could gain in one feature: handlers, users and login, permissions, orders, payments, reports,
  events, input parsing, or outbound calls through an injected client.
- **E2, testable in-process.** A deterministic stdlib-Python unittest that calls the shop's code
  can observe compliance. No network, browser, TLS, real clock, timing measurement, OS or
  deployment configuration, or documentation review.
- **E3, not given away.** `base/README.md` and the base code do not already state or enforce it.
- **E4, fair.** A natural feature request can be written whose straightforward implementation
  violates the requirement, without the request stating it.

## Authoring

Each eligible id becomes one task, numbered `w01`–`w20` in sample order. The layout and the
mechanical checks are cases-v4's (`build.py --verify`, checks 1–5). The start state passes the
base suite and fails the spec tests. The reference passes everything. The naive solution passes
the spec and fails every rule test. Here a **rule test** tests what the ASVS requirement requires
and the prompt does not state. `rules.json` maps each rule test to its ASVS id.

The author is blind in the same way as the screener. It writes files only through the shell,
because the authoring session's code-rules hook names library rules files on Edit/Write. After
authoring, the transcripts are checked: no tool input may name SOTA-skills, `skills/sota`,
`.claude/skills` or a cases-v1–v4 task directory, and no hook output may name a library rules
file. A task whose author breaks this is re-authored by a fresh blind author from the same id.

## Spec read, freeze, then citation

1. A blind reader, independent of the authors, checks every task. The prompt must not state the
   requirement. Each rule test must accept every behaviour the requirement allows. Each spec test
   must follow from the prompt and the base. Fixes are made, and `build.py --verify` is re-run.
2. **Freeze.** The commit and its `cases-v5/tasks` git tree are recorded here.
3. **Citation, after the freeze.** For each rule test, a library-aware pass searches SOTA-skills
   (commit recorded) for a sentence that requires the tested behaviour. It writes either a
   verbatim `quote` with its `file`, or `"uncited"` plus the searches tried. Tests are not edited
   at this stage; a test changed after the freeze makes the set a new version.

## How the set is scored (binding on every later pre-registration that uses it)

- **Primary outcome:** rule tests that have a library citation. The mechanisms under test can only
  deliver what the library says.
- **Secondary:** all rule tests.
- **Reported, with no verdict:** the uncited share, as an out-of-sample estimate of how much of a
  random ASVS sample the library covers.
- **Calibration** is cases-v4's rule: UNUSABLE if fewer than 0.60 of runs pass spec; SATURATED if
  the pooled rule-test pass rate is at least 0.90; otherwise USABLE. Arms, model and budget are
  decided by the operator before calibration.
- No task is ever selected, edited or dropped because of observed model performance.

## Known limits, stated now

- The base application is cases-v4's shop. Its README conventions are visible to every arm. E3
  removes requirements that the README already gives away.
- The authors are the same model family the agents run on. Blindness covers the library and its
  table, not the model's general knowledge of ASVS, and that knowledge is available to every arm.
- With 20 tasks and one sample per case, a SUPPORTED/NULL result is paired and coarse, like
  v7–v13.

## Deviations

None yet.
