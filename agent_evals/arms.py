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
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Arm:
    name: str
    library: bool          # SOTA-skills skills/ installed into the run's user config
    hook: bool             # scripts/verified-done-hook.py registered on its four events


ARMS = {
    "bare": Arm("bare", library=False, hook=False),
    "library": Arm("library", library=True, hook=False),
    "hook": Arm("hook", library=False, hook=True),
    "library+hook": Arm("library+hook", library=True, hook=True),
}

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
    return d


OPENROUTER_BASE = "https://openrouter.ai/api"


def run_env(config_dir: Path, api_key: str, provider: str = "anthropic", model: str = "") -> dict[str, str]:
    env = {
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
