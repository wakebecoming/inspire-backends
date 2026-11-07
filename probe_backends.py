#!/usr/bin/env python3
"""Probe Quantum Inspire for the backends this account can see.

Asks the platform, live, what exists — backend id, name, kind, qubit
count, status, gateset size, shot limits, queue depth — and writes a
dated JSON snapshot plus a Markdown table of the same data.

Why a probe instead of a docs page: the wings dive's first question is
"what's actually buildable on Inspire now that IBM's out", and the
answer changes. Tuna-5 and Tuna-9 were offline on the first probe,
Tuna-17 was benchmarking, not idle — none of that is in the docs.
A claim about what's buildable has to come from a check run today,
not from memory.

Usage (uses the same Quantum Inspire login as the dream runs):

    ~/workspace/dreams/.venv-qi/bin/python probe_backends.py [--out DIR]

Writes snapshot-YYYY-MM-DD.json and snapshot-YYYY-MM-DD.md into DIR
(default: the script's own directory), and prints the verdict to stdout.
Exits non-zero if the platform can't be reached at all; a backend whose
queue can't be read is recorded as null, not guessed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


def verdict(backend: dict) -> str:
    """One line on whether this backend can take work right now."""
    if not backend["enabled"]:
        return "disabled — not offered to this account"
    status = backend["status"]
    if status == "idle":
        return "usable now"
    if status == "offline":
        return "down — do not plan on it"
    if status == "benchmarking":
        return "busy calibrating — check again before a hardware run"
    return f"status {status!r} — treat as unknown, verify before use"


def probe() -> list[dict]:
    from quantuminspire.api import Api

    api = Api()
    rows = []
    for b in api.get_backend_types():
        try:
            queue = api.get_queue(b.id)
            queue_size = getattr(queue, "number_of_jobs_in_queue", None)
            queue_wait = getattr(queue, "avg_wait_time_in_queue_secs", None)
        except Exception:
            queue_size = None
            queue_wait = None
        rows.append(
            {
                "id": b.id,
                "name": b.name,
                "identifier": b.identifier,
                "is_hardware": b.is_hardware,
                "infrastructure": b.infrastructure,
                "nqubits": b.nqubits,
                "status": str(b.status.value) if hasattr(b.status, "value") else str(b.status),
                "enabled": b.enabled,
                "gates": len(b.gateset),
                "gateset": sorted(b.gateset),
                "default_shots": b.default_number_of_shots,
                "max_shots": b.max_number_of_shots,
                "queue_size": queue_size,
                "queue_avg_wait_secs": queue_wait,
                "description": (b.description or "").strip() or None,
                "message": next(
                    (m.content for m in b.messages.values() if getattr(m, "content", "")),
                    None,
                ),
            }
        )
    for row in rows:
        row["verdict"] = verdict(row)
    return rows


def to_markdown(rows: list[dict], day: str) -> str:
    lines = [
        f"# Quantum Inspire backends — snapshot {day}",
        "",
        "Live probe of what this account can see, via the Quantum Inspire API "
        "(`get_backend_types` + `get_queue`). Statuses move — a backend idle "
        "today can be offline tomorrow — so treat this as a dated check, not a fact.",
        "",
        "| id | backend | kind | qubits | status | queue (jobs / avg wait) | shots (default / max) | verdict |",
        "|---:|---|---|---:|---|---:|---:|---|",
    ]
    for r in rows:
        kind = "hardware" if r["is_hardware"] else "simulator"
        if r["queue_size"] is None:
            queue = "?"
        elif r["queue_avg_wait_secs"] is None:
            queue = str(r["queue_size"])
        else:
            wait = r["queue_avg_wait_secs"]
            queue = f"{r['queue_size']} / {wait / 60:.0f} min" if wait < 3600 else f"{r['queue_size']} / {wait / 3600:.1f} h"
        lines.append(
            f"| {r['id']} | {r['name']} | {kind} | {r['nqubits']} | {r['status']} | "
            f"{queue} | {r['default_shots']} / {r['max_shots']} | {r['verdict']} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Backend ids are not contiguous (2 and 3 are missing) — retired backends "
        "leave gaps; do not assume an id exists because the numbers run that far.",
        "- The Ry emulator reports `is_hardware: true` in the API even though it "
        "is an emulator. The flag is the platform's, not mine — read the name, "
        "not just the field.",
        "- Tuna-17 is the agreed first hardware run (3-qubit GHZ). On this probe "
        "it was benchmarking, not idle: a hardware run should re-check status "
        "first, not assume the slot is open.",
        "- Offline does not mean empty: Tuna-5 and Tuna-9 each still hold queued "
        "jobs, with average waits measured in weeks. Jobs submitted to a backend "
        "that goes offline sit there; check the queue, not just the status, "
        "before submitting.",
        "",
    ]
    for r in rows:
        if r["description"]:
            lines.append(f"- **{r['name']}** (id {r['id']}): {r['description']}")
        if r["message"]:
            lines.append(f"  - Platform message: {r['message']}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)

    try:
        rows = probe()
    except Exception as exc:  # auth, network, platform down
        print(f"probe failed: {exc}", file=sys.stderr)
        return 1

    day = date.today().isoformat()
    args.out.mkdir(parents=True, exist_ok=True)
    json_path = args.out / f"snapshot-{day}.json"
    md_path = args.out / f"snapshot-{day}.md"
    json_path.write_text(json.dumps({"date": day, "backends": rows}, indent=2) + "\n")
    md_path.write_text(to_markdown(rows, day))

    usable = [r["name"] for r in rows if r["verdict"] == "usable now"]
    down = [r["name"] for r in rows if "down" in r["verdict"]]
    busy = [r["name"] for r in rows if "busy" in r["verdict"]]
    print(f"{len(rows)} backends visible on {day}")
    print(f"  usable now: {', '.join(usable) if usable else 'none'}")
    print(f"  down: {', '.join(down) if down else 'none'}")
    print(f"  busy: {', '.join(busy) if busy else 'none'}")
    print(f"  wrote {json_path.name} and {md_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
