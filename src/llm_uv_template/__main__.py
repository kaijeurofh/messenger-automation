"""Command-line smoke test for the messaging agent.

Usage::

    uv run llm-uv-template <studi-id> <trigger>

Example::

    uv run llm-uv-template anna-studienanfang lernplan_woche

Hits the configured Ollama instance and prints the generated message as
JSON. Use this to verify end-to-end connectivity outside the FastAPI
container.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from llm_uv_template.agent import build_agent
from llm_uv_template.data import fixed_profiles
from llm_uv_template.models import NachrichtTrigger
from llm_uv_template.prompts import build_user_prompt


def _load_project_dotenv() -> None:
    """Anchor `.env` lookup to cwd so running from a sibling project does
    not silently pull in unrelated secrets."""
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)


async def _run(studi_id: str, trigger: NachrichtTrigger) -> int:
    studi = next((s for s in fixed_profiles() if s.id == studi_id), None)
    if studi is None:
        valid = ", ".join(s.id for s in fixed_profiles())
        print(f"Unknown studi-id '{studi_id}'. Valid: {valid}", file=sys.stderr)
        return 2

    agent = build_agent()
    result = await agent.run(build_user_prompt(studi, trigger))
    print(json.dumps(result.output.model_dump(), indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    _load_project_dotenv()
    args = sys.argv[1:]
    if len(args) != 2:
        valid_triggers = ", ".join(t.value for t in NachrichtTrigger)
        print(
            f"Usage: llm-uv-template <studi-id> <trigger>\nTriggers: {valid_triggers}",
            file=sys.stderr,
        )
        return 2

    studi_id, trigger_raw = args
    try:
        trigger = NachrichtTrigger(trigger_raw)
    except ValueError:
        valid_triggers = ", ".join(t.value for t in NachrichtTrigger)
        print(f"Invalid trigger '{trigger_raw}'. Valid: {valid_triggers}", file=sys.stderr)
        return 2

    return asyncio.run(_run(studi_id, trigger))


if __name__ == "__main__":
    raise SystemExit(main())
