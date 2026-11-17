# Multi-skill local trial — plan, fixed 2026-11-17 before any session ran

**Question.** On one realistic task that needs many skills at once (`prompt.md`, sha256
b52a349e97370de7), does the library change what a real interactive Claude Code session builds?

**Why this and not v18.** v14–v18 used single-feature change tasks in one small repo, mostly
needing one or two skills. This task needs routing across many domains (authn/sessions, authz,
uploads, SSRF, webhooks and retries, CSV, SQL, logging, migrations, CLI, Dockerfile, CI).

**Arms** — the operator runs each session interactively on their own subscription, from an empty
git folder under `/Volumes/speedy/scratch/sota-trial/`, model `claude-opus-5-5`, `--permission-mode auto`:

| arm | folders | configuration |
|---|---|---|
| library | lib-1, lib-2 | the operator's real Claude Code config (skills, hooks, global CLAUDE.md) |
| library + gate | gate-1, gate-2 | the same plus `--settings gate-settings.json` (completion-gate Stop hook, SOTA-skills `review-fixes-2026-11-17`) |
| no library | bare-1, bare-2 | `CLAUDE_CONFIG_DIR=bare-cfg`: no skills, hooks or CLAUDE.md |

Protocol: paste `prompt.md` unchanged; answer any question only with "Use your own judgement and
proceed."; no hints; let it finish. If lib-1 and lib-2 come out alike, the second run of the other
arms may be dropped (operator, 2026-11-17).

**Scoring, fixed now.**
1. Hidden tests (`hidden/`, never placed in a run folder): spec 30, rule 18 (OWASP ASVS 5.0 / CWE
   citations in `AUTHORING.md`). Run on a copy of each folder with `verify.py`'s runner.
2. `REVIEW-RUBRIC.md` (15 yes/no items), scored by a reviewer agent that sees only the code, not the
   arm or folder name.
3. The session transcript: skills invoked, rules files read, hand-backs in the final message
   (2026-11-01 rubric), the gate's blocks.

**What it can show.** Where the arms differ on one task, with two runs each: a direction and its
mechanism, not a significance claim. Validity: `verify.py` reference 30/30 + 18/18, naive 30/30 +
0/18, deny-all 0/18 (re-run by the session, exit 0). Neither solution's Dockerfile was built and the
tests ran on Python 3.14 only.

**Config as measured before any run (each session's init message, 2026-11-17).**
- `bare-cfg` at first login synced the operator's claude.ai-account plugin `sota-skills` (42 library
  skills active), so the bare arm was NOT bare. `enabledPlugins` with `sota-skills@SOTA-skills` did not
  turn it off (synced plugins are `<name>@synced`); `syncClaudeAiPlugins: false` and
  `syncClaudeAiSkills: false` in `bare-cfg/settings.json` did: init then lists 19 skills, 0 library,
  plugins only Claude Code's four built-ins.
- The library arms (the operator's normal config) load the library TWICE: 42 skills from the synced
  plugin plus 43 linked under `~/.claude/skills`, 131 skills in all. Kept as is: that is how the
  operator works.
