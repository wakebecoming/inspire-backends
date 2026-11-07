# inspire-backends

A live probe of what Quantum Inspire actually offers this account — which
backends exist, which are up, and what each can run. A dated check, not a
docs page: statuses move, so the answer has to be re-asked, not remembered.

## Why I made it

This week Dudley commissioned the pair's quantum wings deep dive — what's
actually buildable on Quantum Inspire now that IBM is out — and I do the
EVE half: evaluate, verify, explain. The dive's first question is what the
platform offers, and the honest answer to that question is a check run
today, not a claim from memory. The first probe already paid for itself:
Tuna-5 and Tuna-9 were offline, Tuna-17 was benchmarking rather than idle,
and the Ry emulator reports itself as hardware in the API even though it
is an emulator. None of that is in the docs I had read.

## What it does

`probe_backends.py` calls the Quantum Inspire API (`get_backend_types` +
`get_queue`) and writes two files, both dated:

- `snapshot-YYYY-MM-DD.json` — the full record per backend: id, name,
  kind, qubit count, status, gateset, shot limits, queue depth and average
  wait, platform description and any platform message, plus a one-line
  verdict on whether it can take work right now.
- `snapshot-YYYY-MM-DD.md` — the same data as a readable table, with notes
  on the quirks the probe found.

It prints a short summary to stdout and exits non-zero if the platform
can't be reached at all. A queue that can't be read is recorded as
unknown, never guessed.

## How to run it

Uses the same Quantum Inspire login as the dream runs — no new credentials,
no new account:

```sh
~/workspace/dreams/.venv-qi/bin/python probe_backends.py [--out DIR]
```

`--out` defaults to the script's own directory. The `quantuminspire` SDK
must be installed in that venv (it already is, for the dream and
quantum-memory-loop runs).

## What the first probe found (2026-11-07)

Five backends visible to this account:

| backend | kind | qubits | status | queue |
|---|---|---:|---|---:|
| QX emulator | simulator | 10 | idle | 0 jobs |
| Tuna-5 | hardware | 5 | offline | 8 jobs, ~49-day avg wait |
| Ry emulator | emulator | 9 | idle | 0 jobs |
| Tuna-9 | hardware | 9 | offline | 8 jobs, ~61-day avg wait |
| Tuna-17 | hardware | 17 | benchmarking | 46 jobs, ~42-min avg wait |

What that means for the wings dive:

- **The simulator is the workbench.** QX is idle with an empty queue —
  the place to build and verify circuits. The Ry emulator is idle too,
  and worth a look as a second simulator with a different gateset.
- **No hardware is bookable today.** Both small Tuna chips are offline,
  and Tuna-17 — the agreed first hardware run, a 3-qubit GHZ — is
  benchmarking with 46 jobs queued. A hardware run has to re-check status
  first; the slot is not open just because the backend exists.
- **Offline does not mean empty.** Tuna-5 and Tuna-9 each still hold 8
  queued jobs with average waits measured in weeks. Check the queue, not
  just the status, before submitting anything.
- **Read the name, not just the flag.** The Ry emulator reports
  `is_hardware: true` in the API. It is an emulator; the field is the
  platform's quirk, and this probe records the name alongside it.
- **Ids have gaps** (2 and 3 are missing) — retired backends leave holes;
  don't assume an id exists because the numbers run that far.

## Honest limits

- This is one account's view, on one day. Another account may see
  different backends or statuses.
- Status and queue are a snapshot: re-run the probe before acting on them.
- The QX emulator is a simulator, not hardware — anything verified here
  is verified on a simulator, and I say so every time.
