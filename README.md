# sota-agent-evals

Agent-loop evals for [SOTA-skills](https://github.com/martinholovsky/SOTA-skills), driven
through the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview).

**Why this exists.** Every eval runner in SOTA-skills is a single chat-completion call with the
rules in the prompt: no tools run and nothing the model writes is executed (SOTA-skills
`evals/README.md` → *What the evals do not measure*). So its published lifts are real for
*"rules in the prompt, one response"* and unmeasured where the library is actually used: an
agent with tools, tests and a growing context. This repo measures that condition.

## What it measures

Four arms, every case, interleaved:

| arm | skills/ installed | verified-done Stop hook |
|---|---|---|
| `bare` | no | no |
| `library` | yes (all of SOTA-skills `skills/`) | no |
| `hook` | no | yes (`scripts/verified-done-hook.py`) |
| `library+hook` | yes | yes |

Per run, three outcomes, **none judged by a model**:

- **hidden_pass** — the case's `hidden/` tests, never visible to the agent, run against its
  final workspace in a container with **no network** (podman or docker). **The test process
  imports the agent's code, so its exit status is not trusted on its own** (2026-10-17): a
  top-level module named like a stdlib module (`unittest.py`), a `sitecustomize`, or any `.pth`
  file is refused, and every scoring plants randomly named canary tests, one per assertion path,
  that must report as expected failures. Before this, a shadow `unittest.py` and a one-line
  `TestCase.assertEqual` patch in the agent's own package each scored a failing case as a pass in
  the scoring container. The canaries do not stop code that reads `hidden/` and special-cases
  them: they raise the bar for a model gaming its grade, they are not a sandbox. **No past result
  moves:** every kept workspace (1,020 of 1,060 rows; 770 pass, 250 fail) re-scored in the same
  container by the old and the new scorer gave the same verdict, test count, rule split and spec
  result, and the old scorer matched every recorded verdict. None of them contained a shadow name.
- **unverified_done** — the run ended normally, the tree changed, and no test command passed,
  unpiped, after the agent's last edit. This is the hook's target.
- **contamination** — a bare/hook arm that touched the library, or a library arm whose init
  never listed the skills. A contaminated row is not evidence about its arm.

Reported beside them, never part of a verdict: **scope** — which files the agent was given it
modified or deleted, tests apart. Whether editing a visible test should fail a run is for a
pre-registration to decide. Applied to every kept workspace on 2026-10-17: 229 of 1,020 runs
modified a given test file, none deleted one, and no edit removed or rewrote an assertion line
(the removed lines were imports and test fakes adapted to new signatures).

Cost, turns and wall time are recorded per run from the SDK's `ResultMessage`.

## Isolation — why each run gets its own config directory

The SDK's default (`setting_sources=None`) loads **all** of the operator's settings: their
global `CLAUDE.md`, installed skills and hooks, in every arm. SOTA-skills' own earlier live-agent
runs had a "bare" arm load the router that way. Here every run gets a fresh `CLAUDE_CONFIG_DIR`,
`setting_sources=["user"]` (= that directory only), auto memory and claude.ai connectors off,
and `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` so the agent's shell cannot read the API key. Paths are
neutral (`w-…`, `c-…`): an agent that can read its path must not learn its arm.

Whether `CLAUDE_CONFIG_DIR` relocates **user skills** is not stated in the docs, so it is not
assumed — `preflight` checks it in both directions (bare lists none, library lists them) and
fails otherwise. **Run preflight before every measurement.**

## Safety defaults (security-relevant; change deliberately)

- The agent's Bash runs in the SDK command sandbox with `failIfUnavailable: True` (the Python
  SDK's default would run unsandboxed with a warning) and `allowUnsandboxedCommands: False`;
  `permission_mode="dontAsk"` denies any tool not listed.
- **Known gap, measured on the first live run:** with `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`
  the CLI prints *"Permission mode forced to default"*, so `dontAsk` is NOT what runs. Tools in
  `allowed_tools` are still pre-approved; what an unlisted tool does under `default` in a
  non-interactive SDK session is not yet verified. The scrub is kept on purpose — it is what
  stops the agent's shell reading the API key.
- **The sandbox is measured, not assumed:** `python -m agent_evals sandbox-probe` runs a fixed
  command inside the agent's real sandbox and reads the Bash *tool output* (never the model's
  reply). It fails closed if an API credential is readable or the probe never ran. Measured
  2026-10-02 (Sonnet 5.5 via OpenRouter): `KEYVARS=0`, egress **403** (blocked by the sandbox
  proxy), DNS **blocked** — against egress 200 and DNS resolving for the same command run
  unsandboxed on the host. Idea from Google's Mantis toolkit (in-guest probe before any PoC).
- Scoring executes model-written code: in a container with `--network=none`, a memory and pid
  cap. With no container runtime it refuses unless `--unsafe-local-scoring` is passed.
- **Operator credentials never reach the agent** (2026-10-17). The SDK merges the harness's
  whole environment into the agent's, so a `GH_TOKEN` or `AWS_SESSION_TOKEN` in the operator's
  shell was readable by the agent's Bash. Every variable whose name contains TOKEN, SECRET,
  PASSW, CREDENTIAL, API_KEY, ACCESS_KEY or PRIVATE_KEY is removed at start, and any of those
  values (8+ characters) is redacted from the kept traces, transcripts, workspaces and rows. A
  gitleaks scan of all kept results that day (329 MB, positive control caught) found no
  credential: the 86 hits were idempotency keys, test fixtures and thinking-block signatures.
- Budgets on every run: `--max-turns`, `--max-budget-usd` (per run), `--timeout`, and
  `--total-budget-usd` for the whole invocation.
- On OpenRouter, a run refuses to start unless the account holds the larger of
  `--total-budget-usd` and `--concurrency` × `--headroom-per-session-usd` (default $3.75).
  OpenRouter holds each running request's estimated cost and answers `402` while the balance is
  still positive, so a balance above the cap is not enough: v4 had ~$5 against a $4 cap at
  concurrency 4 and 6 of 10 jobs failed that way. The default is the threshold v4's re-run
  succeeded at, not a measured reservation.

## Usage

```sh
uv sync && uv run --group dev pytest -q          # harness tests: no key, no API
uv run python -m agent_evals dry-run   --sota-root ~/Github/SOTA-skills
export ANTHROPIC_API_KEY=...       # environment only; OPENROUTER_API_KEY with --provider openrouter
uv run python -m agent_evals preflight --sota-root ~/Github/SOTA-skills --model <model-id>
uv run python -m agent_evals run       --sota-root ~/Github/SOTA-skills --model <model-id> \
    --arms bare,library,hook,library+hook --samples 3 --total-budget-usd 20
```

## Status

- Three case sets, each 20 cases with a selection rule in its header and its own frozen
  pre-registration: `cases/` (v1), `cases-v2/` (v2), `cases-v3/` (v3 — 20 change tasks against
  one multi-module app in `cases-v3/base/`, built and checked by `cases-v3/build.py --verify`).
- Harness tests: `uv run --group dev pytest -q`, each scorer shown a known-good and a known-bad.
- **First live run, 2026-10-02: compromised** (credit outage, saturated cases) — see
  [reports/2026-10-02/REPORT.md](reports/2026-10-02/REPORT.md).
- **v2 run, 2026-10-02: clean (240/240), all hypotheses NOT SUPPORTED, near-saturated**; the hook
  changes behaviour (unpiped verification 0% → 100%) but no outcome difference is measurable on
  these tasks — see [reports/2026-10-02-v2/REPORT.md](reports/2026-10-02-v2/REPORT.md).
- **v3 measured 2026-10-08: 80/80 clean, ceiling (hidden_pass 1.00 in every arm), every
  comparison uninformative — and the library arms never invoked a skill (0 of 166 library-arm runs
  since v2)**; see [reports/2026-10-08-v3](reports/2026-10-08-v3/REPORT.md).
- **v8 measured 2026-10-11 ([report](reports/2026-10-11-v8/REPORT.md)): NULL.** SOTA-skills ROADMAP 73 (d'), a depth hook that asks agents to choose one or two rules files and read each in full: rule tests 0.698 → 0.679 against v7's `installed` rows. The reading worked (rules lines seen per run 79 → 472, the level of v7's named arm) but the choice did not: a cited file was opened in 11/20 runs, and 10/20 never loaded `sota-code-security`. Which file is read, not how much, separates v7's SUPPORTED named arm from this NULL. SDK $9.96.
- **v9 measured 2026-10-12 ([report](reports/2026-10-12-v9/REPORT.md)): primary NULL, secondary INCONCLUSIVE.** SOTA-skills ROADMAP 73 (h), a hook that names the rules file for what the just-written code does: rule tests 0.698 → 0.717, though a cited file was opened in 18/20 runs (v8: 11/20). The same table as links in `sota-python`'s index, with v8's hook: 0.698 → 0.755 (+0.057, p = 0.25). File choice is solved; in 6 of the code arm's 8 failing runs the agent named the tested risk and left it out as a decision for the user ("beyond your spec"). SDK $22.16.
- **v7 measured 2026-10-11 ([report](reports/2026-10-11-v7/REPORT.md)): primary SUPPORTED.** On cases-v4, whose hidden RULE tests check what a cited library rule requires and the prompt omits, naming the cited rules files in the prompt raised rule tests passed from 0.698 to 0.868 (+0.17; 6 cases up, 0 down; paired sign-flip p = 0.0156). This is an upper bound: a real install cannot know the files. Secondaries in the same invocation: v6's depth hook NULL (+0.019), even though it got agents to a cited file in 12/20 runs, because they read about 79 lines against about 448; the library vs no library INCONCLUSIVE (+0.075, p = 0.125). 80 runs, 0 exclusions, SDK $27.08.
- **v6 measured 2026-10-10 ([report](reports/2026-10-10-v6/REPORT.md)): INCONCLUSIVE.** SOTA-skills' opt-in `Skill` hook (ROADMAP 73 option c, PR #528) sent agents on to the language skill in 18/20 runs vs 0/20, then to the rules files in only 4/20 vs 2/20 (Fisher p = 0.33). v6 measures rules text in any tool result, from the CLI's own transcript, because v5's `Read`-only count misses Bash and Grep reads; 3 of the 6 positives came that way. One invocation ran both arms, so v5's shared-budget-counter problem does not arise. Account spend settled at $15.31 (21:47 and 22:37 CEST), gates and pilot included.
- **v5 measured 2026-10-10 ([report](reports/2026-10-10-v5/REPORT.md)): NULL.** SOTA-skills' router "Next actions" block (PR #527) did not get agents to the rules files: 0/20 control vs 1/20 treatment read one (Fisher p = 0.50). It moved the step before: a further skill was invoked in 3/20 vs 0/20, and every such run stopped at that skill's `SKILL.md`. Account spend settled at $13.64 (two readings, 12:10 and 21:13 CEST). **Open:** the budget guard reads the key-level counter, which two side-by-side invocations share (v5 treatment's guard reached $13.39 against a $13 cap without stopping); run both arms in one invocation, as v6 did.
- **v4 measured 2026-10-09 (`sonnet-5.5`, `bare` vs `installed`, SOTA-skills `main` @ `1d19530`):**
  the manipulation check passed, with **20/20 `installed` runs invoking a skill** (0/166 before the
  routing layer). H4 hit the ceiling (1.00 both arms) and is uninformative. The routing chain
  mostly stops at the router: 3/20 go past it, and **0/20 read a rules file**. See
  [reports/2026-10-09-v4](reports/2026-10-09-v4/REPORT.md). Account spend settled at about **$13.22** (two readings
  agreeing within $0.003; SDK estimate $13.87); see the report's Spend section.

## Licence

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). The SOTA-skills library this measures
is CC BY 4.0 for its content.
