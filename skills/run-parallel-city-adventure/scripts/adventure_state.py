#!/usr/bin/env python3
"""Deterministic state manager for a parallel-city adventure."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
VERIFICATION = {"observation", "photo", "location", "self-report", "skip"}


def clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def read_state(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def emit(state: dict[str, Any], output: str | None = None) -> None:
    payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
    if output:
        Path(output).write_text(payload + "\n", encoding="utf-8")
    print(payload)


def validate_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version", "adventure_id", "seed", "identity", "initial_minutes",
        "initial_budget", "verification_preferences", "metrics", "visited",
        "choices", "flags",
    }
    missing = required - set(state)
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
        return errors
    if state["schema_version"] != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    prefs = state["verification_preferences"]
    if not isinstance(prefs, list) or not prefs or any(v not in VERIFICATION for v in prefs):
        errors.append("invalid verification_preferences")
    metrics = state["metrics"]
    bounds = {
        "time_remaining": (0, int(state["initial_minutes"])),
        "energy": (0, 100),
        "budget_remaining": (0, int(state["initial_budget"])),
        "clues": (0, 999),
        "relationship": (-5, 5),
        "reputation": (-5, 5),
    }
    for key, (lower, upper) in bounds.items():
        value = metrics.get(key)
        if not isinstance(value, int) or not lower <= value <= upper:
            errors.append(f"metric {key} must be an integer in [{lower}, {upper}]")
    if len(state["visited"]) != len(set(state["visited"])):
        errors.append("visited checkpoint IDs must be unique")
    if len(state["flags"]) != len(set(state["flags"])):
        errors.append("flags must be unique")
    return errors


def new_state(args: argparse.Namespace) -> dict[str, Any]:
    prefs = parse_csv(args.verification)
    invalid = sorted(set(prefs) - VERIFICATION)
    if invalid or not prefs:
        raise ValueError(f"invalid verification methods: {invalid or prefs}")
    seed = args.seed if args.seed is not None else secrets.randbelow(2**31)
    return {
        "schema_version": SCHEMA_VERSION,
        "adventure_id": f"city-{seed:08x}",
        "seed": seed,
        "identity": args.identity,
        "initial_minutes": args.minutes,
        "initial_budget": args.budget,
        "verification_preferences": prefs,
        "metrics": {
            "time_remaining": args.minutes,
            "energy": 100,
            "budget_remaining": args.budget,
            "clues": 0,
            "relationship": 0,
            "reputation": 0,
        },
        "visited": [],
        "choices": [],
        "flags": [],
    }


def update_state(args: argparse.Namespace) -> dict[str, Any]:
    state = read_state(args.state)
    errors = validate_state(state)
    if errors:
        raise ValueError("; ".join(errors))
    if args.checkpoint in state["visited"]:
        raise ValueError(f"checkpoint already visited: {args.checkpoint}")
    metrics = state["metrics"]
    metrics["time_remaining"] = clamp(metrics["time_remaining"] + args.time, 0, state["initial_minutes"])
    metrics["energy"] = clamp(metrics["energy"] + args.energy, 0, 100)
    metrics["budget_remaining"] = clamp(metrics["budget_remaining"] + args.budget, 0, state["initial_budget"])
    metrics["clues"] = max(0, metrics["clues"] + args.clues)
    metrics["relationship"] = clamp(metrics["relationship"] + args.relationship, -5, 5)
    metrics["reputation"] = clamp(metrics["reputation"] + args.reputation, -5, 5)
    new_flags = parse_csv(args.flags)
    state["flags"] = list(dict.fromkeys(state["flags"] + new_flags))
    state["visited"].append(args.checkpoint)
    state["choices"].append({
        "checkpoint": args.checkpoint,
        "choice": args.choice,
        "verification": args.verification,
        "delta": {
            "time": args.time, "energy": args.energy, "budget": args.budget,
            "clues": args.clues, "relationship": args.relationship,
            "reputation": args.reputation,
        },
        "flags_added": new_flags,
    })
    errors = validate_state(state)
    if errors:
        raise ValueError("; ".join(errors))
    return state


def ending_for(state: dict[str, Any]) -> dict[str, Any]:
    errors = validate_state(state)
    if errors:
        raise ValueError("; ".join(errors))
    metrics = state["metrics"]
    if metrics["clues"] >= 3 and metrics["reputation"] >= 1:
        key, reason = "keeper-of-the-map", "collected three clues and earned positive reputation"
    elif metrics["relationship"] >= 2:
        key, reason = "trusted-companion", "built a strong relationship during the route"
    elif metrics["time_remaining"] == 0 or metrics["energy"] <= 10:
        key, reason = "last-minute-return", "finished with no time or very little energy remaining"
    else:
        key, reason = "unfinished-thread", "left a valid unresolved thread for replay"
    return {
        "ending_key": key,
        "reason": reason,
        "metrics": metrics,
        "visited_count": len(state["visited"]),
        "flags": state["flags"],
    }


def self_test() -> None:
    args = argparse.Namespace(
        identity="tester", minutes=60, budget=50,
        verification="observation,self-report", seed=7,
    )
    state = new_state(args)
    assert not validate_state(state)
    assert ending_for(state)["ending_key"] == "unfinished-thread"
    with tempfile.TemporaryDirectory() as directory:
        state_path = Path(directory) / "state.json"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        update_args = argparse.Namespace(
            state=str(state_path), checkpoint="wanning", choice="follow-water",
            verification="observation", time=-15, energy=-10, budget=-5,
            clues=3, relationship=0, reputation=1, flags="water-line",
        )
        updated = update_state(update_args)
        assert updated["metrics"]["time_remaining"] == 45
        assert updated["metrics"]["budget_remaining"] == 45
        assert ending_for(updated)["ending_key"] == "keeper-of-the-map"
        state_path.write_text(json.dumps(updated), encoding="utf-8")
        try:
            update_state(update_args)
        except ValueError as exc:
            assert "already visited" in str(exc)
        else:
            raise AssertionError("duplicate checkpoint was accepted")
    print("SELF_TEST_OK")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="create a new state")
    new.add_argument("--identity", required=True)
    new.add_argument("--minutes", type=int, default=75)
    new.add_argument("--budget", type=int, default=0)
    new.add_argument("--verification", default="observation,self-report")
    new.add_argument("--seed", type=int)
    new.add_argument("--output")

    update = sub.add_parser("update", help="apply one checkpoint choice")
    update.add_argument("--state", required=True)
    update.add_argument("--checkpoint", required=True)
    update.add_argument("--choice", required=True)
    update.add_argument("--verification", required=True, choices=sorted(VERIFICATION))
    update.add_argument("--time", type=int, default=0)
    update.add_argument("--energy", type=int, default=0)
    update.add_argument("--budget", type=int, default=0)
    update.add_argument("--clues", type=int, default=0)
    update.add_argument("--relationship", type=int, default=0)
    update.add_argument("--reputation", type=int, default=0)
    update.add_argument("--flags", default="")
    update.add_argument("--output")

    validate = sub.add_parser("validate", help="validate a state file")
    validate.add_argument("--state", required=True)

    ending = sub.add_parser("ending", help="classify a valid ending")
    ending.add_argument("--state", required=True)

    sub.add_parser("self-test", help="run built-in deterministic checks")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "new":
            if args.minutes <= 0 or args.budget < 0:
                raise ValueError("minutes must be positive and budget non-negative")
            emit(new_state(args), args.output)
        elif args.command == "update":
            emit(update_state(args), args.output)
        elif args.command == "validate":
            errors = validate_state(read_state(args.state))
            emit({"valid": not errors, "errors": errors})
            return 0 if not errors else 1
        elif args.command == "ending":
            emit(ending_for(read_state(args.state)))
        else:
            self_test()
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
