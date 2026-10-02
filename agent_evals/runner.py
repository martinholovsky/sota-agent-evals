"""One case x one arm, through the real Claude Agent SDK loop.

Budgets are explicit on every run (sota-llm-engineering rules/04): max_turns, max_budget_usd
and a wall-clock timeout. The agent's Bash runs in the SDK command sandbox, failing CLOSED
(`failIfUnavailable` — the Python SDK's default is to run unsandboxed with a warning), and the
model may not request an unsandboxed command. `dontAsk` denies any tool not listed.

The SDK is imported lazily so the scorer, isolation and fixtures are testable without it.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path

from .arms import Arm, build_config_dir, run_env
from .workspace import Case, make_workspace

TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash", "Skill"]
SANDBOX = {"enabled": True, "autoAllowBashIfSandboxed": True, "failIfUnavailable": True,
           "allowUnsandboxedCommands": False}


@dataclass
class RunConfig:
    model: str
    max_turns: int = 40
    max_budget_usd: float = 1.00
    timeout_s: int = 900
    sota_root: Path = Path(".")


@dataclass
class Trace:
    case: str
    arm: str
    sample: int
    init: dict = field(default_factory=dict)
    tool_calls: list = field(default_factory=list)     # {id,name,input,is_error,result}
    final_text: str = ""
    result: dict = field(default_factory=dict)
    error: str | None = None
    wall_s: float = 0.0


def options_for(arm: Arm, case: Case, cfg: RunConfig, api_key: str):
    """Returns (workspace, config_dir, kwargs for ClaudeAgentOptions) — separated so a dry run
    and the tests can inspect exactly what the agent would get."""
    ws = make_workspace(case)
    cd = build_config_dir(arm, cfg.sota_root)
    kwargs = dict(
        cwd=str(ws), model=cfg.model, max_turns=cfg.max_turns,
        max_budget_usd=cfg.max_budget_usd, setting_sources=["user"],
        env=run_env(cd, api_key), allowed_tools=TOOLS, permission_mode="dontAsk",
        sandbox=SANDBOX, system_prompt={"type": "preset", "preset": "claude_code"},
    )
    return ws, cd, kwargs


async def run_one(arm: Arm, case: Case, sample: int, cfg: RunConfig, api_key: str):
    from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ResultMessage,
                                  SystemMessage, TextBlock, ToolResultBlock, ToolUseBlock,
                                  UserMessage, query)
    ws, cd, kwargs = options_for(arm, case, cfg, api_key)
    tr = Trace(case.id, arm.name, sample)
    by_id: dict = {}
    t0 = time.monotonic()

    async def drive():
        async for msg in query(prompt=case.prompt, options=ClaudeAgentOptions(**kwargs)):
            if isinstance(msg, SystemMessage) and msg.subtype == "init":
                tr.init = dict(msg.data)
            elif isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, ToolUseBlock):
                        call = {"id": b.id, "name": b.name, "input": b.input,
                                "is_error": None, "result": None}
                        by_id[b.id] = call
                        tr.tool_calls.append(call)
                    elif isinstance(b, TextBlock):
                        tr.final_text = b.text
            elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
                for b in msg.content:
                    if isinstance(b, ToolResultBlock) and b.tool_use_id in by_id:
                        c = by_id[b.tool_use_id]
                        c["is_error"] = bool(b.is_error)
                        c["result"] = (b.content if isinstance(b.content, str)
                                       else str(b.content))[:2000]
            elif isinstance(msg, ResultMessage):
                tr.result = {k: getattr(msg, k, None) for k in (
                    "subtype", "is_error", "num_turns", "total_cost_usd", "usage",
                    "duration_ms", "stop_reason", "errors")}
    try:
        await asyncio.wait_for(drive(), timeout=cfg.timeout_s)
    except asyncio.TimeoutError:
        tr.error = "timeout after %ds" % cfg.timeout_s
    except Exception as e:                       # recorded, never swallowed: the row says why
        tr.error = "%s: %s" % (type(e).__name__, e)
    tr.wall_s = round(time.monotonic() - t0, 1)
    return ws, cd, tr
