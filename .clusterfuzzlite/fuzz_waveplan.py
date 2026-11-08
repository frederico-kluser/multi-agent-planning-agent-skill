"""CI-only Atheris target: validate/schedule/render data, never execute commands."""
import sys
from pathlib import Path

import atheris

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
with atheris.instrument_imports():
    import json
    import waveplan


def TestOneInput(data):
    if len(data) > 16384:
        return
    try:
        text = data.decode("utf-8")
        waveplan.check_nesting(text)
        plan = json.loads(text, object_pairs_hook=waveplan.pairs_hook, parse_constant=waveplan.constant_hook)
    except (UnicodeError, ValueError, RecursionError, waveplan.PlanError):
        return
    try:
        waveplan.validate_plan(plan)
    except waveplan.PlanError:
        return
    # Unexpected errors and invariant violations must propagate as real crashes.
    before = waveplan.canonical_digest(plan)
    result = waveplan.schedule_plan(plan)
    assert result["plan_digest"] == before
    waveplan.render_plan(plan)
    waveplan.brief_task(plan, plan["tasks"][0]["id"])
    assert waveplan.canonical_digest(plan) == before


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
