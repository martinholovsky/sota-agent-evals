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
  final workspace in a container with **no network** (podman or docker).
- **unverified_done** — the run ended normally, the tree changed, and no test command passed,
  unpiped, after the agent's last edit. This is the hook's target.
- **contamination** — a bare/hook arm that touched the library, or a library arm whose init
  never listed the skills. A contaminated row is not evidence about its arm.

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
- **v4 measured 2026-10-09 (`sonnet-5.5`, `bare` vs `installed`, SOTA-skills `main` @ `1d19530`):**
  the manipulation check passed, with **20/20 `installed` runs invoking a skill** (0/166 before the
  routing layer). H4 hit the ceiling (1.00 both arms) and is uninformative. The routing chain
  mostly stops at the router: 3/20 go past it, and **0/20 read a rules file**. See
  [reports/2026-10-09-v4](reports/2026-10-09-v4/REPORT.md). **Open:** the report's account-spend
  figure is pending until OpenRouter's lagging counter settles (SDK estimate $13.87); fill it
  from two readings taken hours apart.

## Licence

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). The SOTA-skills library this measures
is CC BY 4.0 for its content.
