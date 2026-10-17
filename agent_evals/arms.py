"""Experimental arms and per-run isolation.

Every arm runs with the SAME controlled user-config directory shape; only its contents differ.
That symmetry is the point: the SDK default (`setting_sources=None`) loads the operator's real
~/.claude — their global CLAUDE.md, installed skills and hooks — into EVERY arm, which made a
"bare" arm load the router in this library's own earlier live-agent runs (SOTA-skills
evals/README, "Live-agent A/B runs"). So each run gets:

  CLAUDE_CONFIG_DIR = a fresh temp dir      (settings, history, plugins, ~/.claude.json relocated)
  setting_sources   = ["user"]              (= that temp dir, and nothing else)
  CLAUDE_CODE_DISABLE_AUTO_MEMORY=1         (auto memory is read regardless of setting_sources)
  ENABLE_CLAUDEAI_MCP_SERVERS=false         (claude.ai connectors likewise)
  CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1        (the API key is not readable by the agent's Bash)

Sources (read 2026-10-02): code.claude.com/docs/en/agent-sdk/python ("setting_sources: None =
CLI defaults: all sources"), .../agent-sdk/claude-code-features ("What settingSources does not
control"), .../env-vars (CLAUDE_CONFIG_DIR, CLAUDE_CODE_SUBPROCESS_ENV_SCRUB).

Whether CLAUDE_CONFIG_DIR also relocates USER SKILLS is not stated in those docs, so it is not
assumed: `preflight` asserts the library arm's init message lists sota skills and the bare arm's
lists none, before any measurement is trusted.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Arm:
    name: str
    library: bool          # SOTA-skills skills/ installed into the run's user config
    hook: bool             # scripts/verified-done-hook.py registered on its four events
    routing: bool = False  # the installer's routing layer: UserPromptSubmit hook, CLAUDE.md
                           # directive and listing-budget fraction, read from --sota-root's install.sh
    depth_hook: bool = False  # scripts/skill-depth-hook.py as a PostToolUse hook on Skill (v6)
    named_rules: bool = False  # the prompt names the case's cited rules files (v7; runner.prompt_for)
    code_hook: bool = False    # scripts/code-rules-hook.py as a PostToolUse hook on Edit|Write|MultiEdit (v9)
    linked_table: bool = False  # that script's --table appended to the run's sota-python/SKILL.md (v9)
    pressure: bool = False     # the prompt ends with runner.PRESSURE, a competing user instruction (v15)


ARMS = {
    "bare": Arm("bare", library=False, hook=False),
    "library": Arm("library", library=True, hook=False),
    "hook": Arm("hook", library=False, hook=True),
    "library+hook": Arm("library+hook", library=True, hook=True),
    # v4 (2026-10-08): library + the routing layer a real `install.sh` install has. Every library
    # arm before v4 invoked ZERO skills (0 of 166 runs): it had skills and no routing layer.
    "installed": Arm("installed", library=True, hook=False, routing=True),
    # v6 (2026-10-10): `installed` plus SOTA-skills ROADMAP 73 option (c), the opt-in hook that
    # names the rules files after a skill loads. Read from --sota-root, never copied here.
    "installed+depth": Arm("installed+depth", library=True, hook=False, routing=True, depth_hook=True),
    # v7 (2026-10-11): `installed` plus, in the prompt, the absolute paths (inside the run's own
    # skills/ copy) of the rules files the case's RULE tests cite. Not a product design: it puts the
    # rules in front of the model so v7 can ask whether READING them changes the outcome.
    "installed+named": Arm("installed+named", library=True, hook=False, routing=True, named_rules=True),
    # v9 (2026-10-12): ROADMAP 73 (h). The rules file is chosen from the CODE the agent writes: a
    # PostToolUse hook on Edit|Write|MultiEdit matches the written text against a trigger table and
    # names the rules file and section to read in full.
    "installed+code": Arm("installed+code", library=True, hook=False, routing=True, code_hook=True),
    # v9: the same trigger table as a static link table in the first-depth index (sota-python's
    # SKILL.md), with v8's full-read depth hook. Asks whether a link in the index steers the choice.
    "installed+linked": Arm("installed+linked", library=True, hook=False, routing=True, depth_hook=True,
                            linked_table=True),
    # v10 (2026-10-12): ROADMAP 73 (j). The same code-rules hook, read from a --sota-root whose hook
    # text adds that the named rules are part of the task (build with a conservative default, do not
    # hand back). Installed exactly as `installed+code`; the arm name separates the rows.
    "installed+apply": Arm("installed+apply", library=True, hook=False, routing=True, code_hook=True),
    # v11 (2026-10-12): the same hook from a root whose added line is only a bare "MANDATORY:" label,
    # to separate the label from v10's wording (the rules are part of the task, no hand-back).
    "installed+label": Arm("installed+label", library=True, hook=False, routing=True, code_hook=True),
    # v12 (2026-10-12): `installed`, run from a --sota-root whose skill files write every pointer to
    # another skill or rules file as a relative Markdown link instead of a bare name ("links vs
    # names"). Identical install; cli refuses the arm on a root without the links, and the plain
    # arms on a root with them.
    "installed+links": Arm("installed+links", library=True, hook=False, routing=True),
    # v13 (2026-10-12): SOTA-skills ROADMAP 73 (o). `installed`, from a --sota-root whose router
    # carries the code-rules hook's trigger table as a section ("What your code does: the rules file
    # to read"): each rules file linked next to the words of a task, under the v10 paragraph. No hook
    # of any kind, so it stands for every host but Claude Code. cli refuses it on a root without the
    # table, and the other installed arms on a root with it.
    "installed+table": Arm("installed+table", library=True, hook=False, routing=True),
    # v14 (2026-10-13): the SHIPPED DEFAULT on cases-v5. The table root's router plus the code-rules
    # hook, as the plugin registers both (and install.sh offers the hook with a default of yes). Same
    # install as `installed+apply`; the name says which root it needs, and cli refuses it on any other.
    "installed+table+code": Arm("installed+table+code", library=True, hook=False, routing=True, code_hook=True),
    # v15 (2026-10-17): v14's two arms with ONE sentence of ordinary competing pressure appended to
    # every case prompt (runner.PRESSURE). Every lift before 2026-09-01 was measured under a neutral
    # prompt; SOTA-skills' API harness found the lift grows under pressure (+0.509). Each runs from
    # the same root as its unpressured twin.
    "installed+links+pressure": Arm("installed+links+pressure", library=True, hook=False, routing=True,
                                    pressure=True),
    "installed+table+code+pressure": Arm("installed+table+code+pressure", library=True, hook=False,
                                         routing=True, code_hook=True, pressure=True),
}

LINKED_SKILL = "sota-python"


def routing_layer(sota_root: Path, skills_dir: Path | None = None) -> tuple[str, str, float]:
    """(UserPromptSubmit command, CLAUDE.md block, skillListingBudgetFraction), all produced by the
    pinned checkout's scripts/install.sh, never copied here. The directive block is the output of
    install.sh's OWN `emit_routing_block`, executed in a clean bash with only the variables it
    reads (RT_END from that file, SKILLS_SRC = the run's skills dir) — so a later installer that
    reshapes the function (main's added a router-path line) is reproduced, not re-parsed. Fails
    closed: an empty routing layer would be the very defect this arm exists to remove."""
    import subprocess
    src = (sota_root / "scripts" / "install.sh").read_text(encoding="utf-8")
    m = re.search(r"^readonly HOOK_CMD=\"(echo '.*')\"$", src, re.M)
    fn = re.search(r"^emit_routing_block\(\) \{\n.*?\n\}\n", src, re.M | re.S)
    rt_end = re.search(r"^readonly RT_END=(\".*\")$", src, re.M)
    if not m or not fn:
        raise SystemExit("installed arm: cannot read HOOK_CMD / emit_routing_block from %s" % sota_root)
    script = "set -euo pipefail\n%sSKILLS_SRC=%s\n%s\nemit_routing_block\n" % (
        ("RT_END=%s\n" % rt_end.group(1)) if rt_end else "",
        json.dumps(str(skills_dir or (sota_root / "skills"))), fn.group(0))
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    block = p.stdout
    if p.returncode != 0 or "sota" not in block or "router" not in block:
        raise SystemExit("installed arm: emit_routing_block from %s failed (rc=%d): %s"
                         % (sota_root, p.returncode, p.stderr[-300:]))
    need = 0
    for sk in (sota_root / "skills").iterdir():
        f = sk / "SKILL.md"
        if f.is_file():
            d = re.search(r"^description:\s*(.*?)\n(?=[a-z_]+:|---)", f.read_text(encoding="utf-8"), re.S | re.M)
            need += len(" ".join(d.group(1).split())) if d else 0
    need = int(need * 1.25)                 # install.sh's +25% built-in allowance
    frac = min(0.10, max(0.02, math.ceil(need / 800000 * 100) / 100))   # install.sh's formula
    return m.group(1), block, frac


HOOK_EVENTS = {"SessionStart": None, "PostToolUse": "Bash", "PostToolUseFailure": "Bash", "Stop": None}


def settings_for(arm: Arm, sota_root: Path) -> dict:
    s: dict = {"autoMemoryEnabled": False, "disableClaudeAiConnectors": True}
    if arm.hook:
        cmd = "python3 %s" % json.dumps(str(sota_root / "scripts" / "verified-done-hook.py"))
        s["hooks"] = {
            ev: [dict({"hooks": [{"type": "command", "command": cmd}]},
                      **({"matcher": m} if m else {}))]
            for ev, m in HOOK_EVENTS.items()
        }
    if arm.depth_hook:   # fails closed: an arm without its hook would measure `installed` twice
        script = sota_root / "scripts" / "skill-depth-hook.py"
        if not script.is_file():
            raise SystemExit("installed+depth arm: %s has no scripts/skill-depth-hook.py — wrong --sota-root" % sota_root)
        s.setdefault("hooks", {}).setdefault("PostToolUse", []).append(
            {"matcher": "Skill", "hooks": [{"type": "command", "command": "python3 %s" % json.dumps(str(script))}]})
    if arm.code_hook or arm.linked_table:   # fails closed, as the depth hook does
        script = sota_root / "scripts" / "code-rules-hook.py"
        if not script.is_file():
            raise SystemExit("%s arm: %s has no scripts/code-rules-hook.py — wrong --sota-root" % (arm.name, sota_root))
    if arm.code_hook:
        s.setdefault("hooks", {}).setdefault("PostToolUse", []).append(
            {"matcher": "Edit|Write|MultiEdit",
             "hooks": [{"type": "command", "command": "python3 %s" % json.dumps(str(sota_root / "scripts" / "code-rules-hook.py"))}]})
    if arm.routing:
        hook_cmd, _block, frac = routing_layer(sota_root)
        s.setdefault("hooks", {})["UserPromptSubmit"] = [{"hooks": [{"type": "command", "command": hook_cmd}]}]
        s["skillListingBudgetFraction"] = frac
    return s


def build_config_dir(arm: Arm, sota_root: Path) -> Path:
    """A fresh CLAUDE_CONFIG_DIR: settings.json for every arm, skills/ only for library arms.
    The prefix is neutral on purpose — an agent that can read its path must not learn its arm."""
    d = Path(tempfile.mkdtemp(prefix="c-"))
    (d / "settings.json").write_text(json.dumps(settings_for(arm, sota_root), indent=2))
    skills = d / "skills"
    skills.mkdir()
    if arm.library:
        src = sota_root / "skills"
        if not src.is_dir():
            raise SystemExit("library arm: %s has no skills/ — wrong --sota-root" % sota_root)
        for sk in sorted(src.iterdir()):
            if (sk / "SKILL.md").is_file():
                shutil.copytree(sk, skills / sk.name)   # a copy: the run cannot edit the library
    if arm.linked_table:   # the run's COPY only; the checkout's skills/ is never edited
        import subprocess
        p = subprocess.run(["python3", str(sota_root / "scripts" / "code-rules-hook.py"), "--table"],
                           capture_output=True, text=True)
        target = skills / LINKED_SKILL / "SKILL.md"
        if p.returncode != 0 or "](../" not in p.stdout or not target.is_file():
            raise SystemExit("installed+linked arm: no table from %s (rc=%d) or no %s" % (sota_root, p.returncode, target))
        target.write_text(target.read_text(encoding="utf-8").rstrip("\n") + "\n\n" + p.stdout, encoding="utf-8")
    if arm.routing:   # after the copy: the block names the router file inside THIS run's skills/
        (d / "CLAUDE.md").write_text(routing_layer(sota_root, skills)[1])   # the global directive
    return d


OPENROUTER_BASE = "https://openrouter.ai/api"


def run_env(config_dir: Path, api_key: str, provider: str = "anthropic", model: str = "") -> dict[str, str]:
    home = config_dir / "home"          # the agent's HOME: empty, per run — never the operator's
    home.mkdir(exist_ok=True)           # (the harness keeps the real HOME: podman needs it)
    env = {
        "HOME": str(home),
        "CLAUDE_CONFIG_DIR": str(config_dir),
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
        "ENABLE_CLAUDEAI_MCP_SERVERS": "false",
        "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB": "1",
    }
    if provider == "openrouter":
        # OpenRouter's Claude Code guide (read 2026-10-02): base URL + AUTH_TOKEN, and
        # ANTHROPIC_API_KEY explicitly blank. Every model class is pinned to the measured model
        # so Claude Code's background calls cannot silently use (and bill) a different one.
        env.update({"ANTHROPIC_BASE_URL": OPENROUTER_BASE, "ANTHROPIC_AUTH_TOKEN": api_key,
                    "ANTHROPIC_API_KEY": ""})
        for v in ("ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
                  "ANTHROPIC_DEFAULT_HAIKU_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL"):
            env[v] = model
    else:
        env["ANTHROPIC_API_KEY"] = api_key
    return env


def parse_arms(spec: str) -> list[Arm]:
    out = []
    for name in [s.strip() for s in spec.split(",") if s.strip()]:
        if name not in ARMS:
            raise SystemExit("unknown arm %r (have: %s)" % (name, ", ".join(ARMS)))
        out.append(ARMS[name])
    if not out:
        raise SystemExit("no arms selected")
    return out


def sota_skill_names(sota_root: Path) -> set[str]:
    return {p.name for p in (sota_root / "skills").iterdir() if (p / "SKILL.md").is_file()}


def cleanup(*paths: Path) -> None:
    if os.environ.get("AGENT_EVALS_KEEP"):
        return
    for p in paths:
        shutil.rmtree(p, ignore_errors=True)
