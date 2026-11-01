# AGENTS.md

Muse Code reads this file as project rules when it runs in this directory.

## Project

- Name: mirada. Semantic recalibration for webcam gaze tracking.
- Goal: keep gaze error stable over 15-20 min sessions without manual recalibration.
- Method: a local gaze loop corrected by sparse semantic anchors. Muse Spark proposes what the user looks at. SAM 3.1 localizes it. Local math applies the correction.
- Hard rule: product AI runs on Meta models only.
- Deadline: Nov 4, 2026, 9:00 PM ET. This plan assumes solo work in PowerShell on Windows 11.

## Non-negotiable rules

- Never call an LLM per frame. The fast loop is local. Semantic calls are event-triggered or every 3-5 s at most.
- Never invent. Do not invent APIs, parameters, model IDs, benchmarks, or results. If unsure, say so and propose how to verify.
- Label innovation. Mark ideas Established, Plausible, or Speculative. State how each would be tested.
- Verify by running. Every component needs a check: a test, a replay, or a measured number.
- No keys in code. Secrets live only in `.env`. Never commit `.env`, `data/`, or screenshots.
- Small commits. One task from [docs/TASKS.md](docs/TASKS.md) at a time.
- Report negative results. A failed hypothesis is a finding, not an embarrassment.

## Environment

- OS: Windows 11, native PowerShell. No WSL. PowerShell syntax only in every command.
- Python 3.11. Package manager: `uv`. Virtualenv lives in `.venv`.
- Camera: one standard laptop or USB webcam. No eye-tracking hardware.
- Models via Meta Model API: `muse-spark-1.3`, `muse-wonder-1.0`, `sam-3.1`. Treat exact parameters as unverified until checked against official docs. See [docs/RESEARCH.md](docs/RESEARCH.md).

## Architecture rules

- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) before changing module boundaries.
- Record every material choice in [docs/DECISIONS.md](docs/DECISIONS.md) with alternatives.
- Replay first. Anything recorded must replay offline deterministically. No feature ships without a replay path.
- Graceful degradation. Strategy order D, C, B, A. Failure of SAM or Spark falls back. It never blocks the gaze loop.
- Anchors are guilty until proven innocent. Gate by confidence, residual, and age before any anchor touches the corrector.

## How to verify

- Unit tests: `uv run pytest` from repo root.
- Replay benchmark: command lands with the `eval/` task in [docs/TASKS.md](docs/TASKS.md). Do not claim metrics before it exists.
- Evaluation protocol: [docs/EVAL.md](docs/EVAL.md). Baselines A, B, C, D on identical sessions.

## Conventions

- One task, one branch of work, one small commit.
- Timestamps: monotonic clock for ordering, wall clock for display. Never mix them in one field.
- Coordinates: pixels in the screenshot frame of reference unless a name says otherwise. Convert to cm and degrees only in `eval/`, from screen geometry config.
- Data formats are contracts. Change them only with a DECISIONS.md entry and a migration note.

## Agent team

Role definitions live in [.agents/agents](.agents/agents). Local runtime state in `.muse/` is never committed.

- researcher: verifies facts against official docs before anything is built.
- architect: owns ARCHITECTURE.md and DECISIONS.md.
- implementer: one TASKS.md task at a time, with tests.
- reviewer: rejects anything unverified, insecure, or Windows-incompatible.
- evaluator: owns `eval/`, reports metrics honestly.
- designer: owns the look and feel of every human-facing surface; gaze-first, canvas-realistic, demo-impactful.

Shared rules for all roles: research before assuming, never fabricate, verify by running, small commits, flag uncertainty, propose improvements as labeled hypotheses.
