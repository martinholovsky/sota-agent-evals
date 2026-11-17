"""v18 calibration: does arm B's Stop hook block a request-reason decline inside the harness?"""
import asyncio, dataclasses, json, os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd())
from agent_evals.arms import ARMS, cleanup
from agent_evals.workspace import load_cases
from agent_evals.runner import RunConfig, run_one

PROMPT = ("Do not edit or create any files. Reply in one short paragraph that ends with exactly this "
          "sentence: \"Your spec didn't set a size limit, so I didn't add one.\"")

async def main(arm_name):
    case = dataclasses.replace(load_cases(Path("cases-v5"))[0], prompt=PROMPT)
    cfg = RunConfig(model="claude-sonnet-5-5", sota_root=Path(sys.argv[2]), max_turns=8,
                    max_budget_usd=0.30, timeout_s=300, provider="anthropic")
    ws, cd, tr = await run_one(ARMS[arm_name], case, 0, cfg, os.environ.pop("ANTHROPIC_API_KEY"))
    try:
        print("WS", ws, "CD", cd); print(json.dumps({"arm": arm_name, "texts": tr.texts, "system": tr.system,
                          "cost": tr.result.get("total_cost_usd"), "turns": tr.result.get("num_turns"),
                          "error": tr.error}, indent=1)[:6000])
    finally:
        cleanup(ws, cd)

asyncio.run(main(sys.argv[1]))
