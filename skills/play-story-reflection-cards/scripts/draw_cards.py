#!/usr/bin/env python3
"""Reproducible draw engine for the story reflection card skill."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import secrets
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable


SCRIPT_VERSION = "storycards/v1"
STATE_VERSION = "draw-1.0"
MODES = {"solo", "friends", "creative"}
VISUALS = {"text", "image", "photo"}
DEFAULT_DECK = Path(__file__).resolve().parent.parent / "references" / "starter-deck.json"
CREATIVE_POOLS = {
    "opening": {"notice", "trace"},
    "turn": {"crossroads", "weave"},
    "afterimage": {"voice", "ember"},
}


def normalize_seed(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = re.sub(r"\s+", " ", normalized.strip())
    return normalized.casefold()


def random_seed() -> str:
    return base64.b32encode(secrets.token_bytes(10)).decode("ascii").rstrip("=").lower()


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().casefold() for item in value.split(",") if item.strip()]


def load_deck(path: str | Path = DEFAULT_DECK) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_deck(deck: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if deck.get("schema_version") != "card-1.0":
        errors.append("unsupported card schema")
    if not deck.get("deck_version"):
        errors.append("missing deck_version")
    cards = deck.get("cards")
    if not isinstance(cards, list) or len(cards) != 24:
        errors.append("starter deck must contain exactly 24 cards")
        return errors
    ids = [card.get("id") for card in cards]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        errors.append("card IDs must be present and unique")
    families = deck.get("families", {})
    required_modes = {"solo", "friends", "creative"}
    for card in cards:
        family = card.get("family")
        if family not in families:
            errors.append(f"{card.get('id')}: unknown family")
        prompts = card.get("prompts", {})
        if set(prompts) != required_modes:
            errors.append(f"{card.get('id')}: prompts must cover all modes")
        if not card.get("lighter") or not card.get("art_brief"):
            errors.append(f"{card.get('id')}: missing lighter or art_brief")
    family_counts: dict[str, int] = {}
    for card in cards:
        family_counts[card["family"]] = family_counts.get(card["family"], 0) + 1
    if any(family_counts.get(name) != 4 for name in families):
        errors.append("each family must contain exactly four cards")
    return errors


def eligible(cards: Iterable[dict[str, Any]], exclusions: set[str]) -> list[dict[str, Any]]:
    result = []
    for card in cards:
        tags = {tag.casefold() for tag in card.get("topic_tags", [])}
        if tags & exclusions:
            continue
        result.append(card)
    return result


def rank_key(
    card_id: str,
    *,
    deck_version: str,
    seed: str,
    mode: str,
    cycle: int,
    slot: str,
) -> tuple[str, str]:
    payload = "\n".join(
        [SCRIPT_VERSION, deck_version, seed, mode, str(cycle), slot, card_id]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), card_id


def ranked(
    cards: Iterable[dict[str, Any]],
    *,
    deck_version: str,
    seed: str,
    mode: str,
    cycle: int,
    slot: str,
) -> list[dict[str, Any]]:
    return sorted(
        cards,
        key=lambda card: rank_key(
            card["id"],
            deck_version=deck_version,
            seed=seed,
            mode=mode,
            cycle=cycle,
            slot=slot,
        ),
    )


def choose_single(
    cards: list[dict[str, Any]],
    *,
    deck_version: str,
    seed: str,
    mode: str,
    cycle: int,
    history: set[str],
    last_family: str | None,
    slot: str = "single",
    family_filter: set[str] | None = None,
) -> tuple[dict[str, Any], int, set[str]]:
    pool = [card for card in cards if not family_filter or card["family"] in family_filter]
    if not pool:
        raise ValueError("no cards remain after exclusions")
    remaining = [card for card in pool if card["id"] not in history]
    if not remaining:
        cycle += 1
        pool_ids = {card["id"] for card in pool}
        history = {card_id for card_id in history if card_id not in pool_ids}
        remaining = pool
    ordered = ranked(
        remaining,
        deck_version=deck_version,
        seed=seed,
        mode=mode,
        cycle=cycle,
        slot=slot,
    )
    different_family = [card for card in ordered if card["family"] != last_family]
    return (different_family or ordered)[0], cycle, history


def draw_ids(
    deck: dict[str, Any],
    *,
    seed: str,
    mode: str,
    cycle: int,
    history: list[str],
    last_family: str | None,
    exclusions: set[str],
    lighter: bool = False,
) -> tuple[list[dict[str, Any]], int, list[str], str | None]:
    cards = eligible(deck["cards"], exclusions)
    if not cards:
        raise ValueError("topic exclusions leave no eligible cards")
    used = set(history)
    selected: list[dict[str, Any]] = []

    if lighter:
        card, cycle, used = choose_single(
            cards,
            deck_version=deck["deck_version"],
            seed=seed,
            mode=mode,
            cycle=cycle,
            history=used,
            last_family=last_family,
            slot="lighter",
            family_filter={"notice"},
        )
        selected.append(card)
    elif mode != "creative":
        card, cycle, used = choose_single(
            cards,
            deck_version=deck["deck_version"],
            seed=seed,
            mode=mode,
            cycle=cycle,
            history=used,
            last_family=last_family,
        )
        selected.append(card)
    else:
        for slot, families in CREATIVE_POOLS.items():
            card, cycle, used = choose_single(
                cards,
                deck_version=deck["deck_version"],
                seed=seed,
                mode=mode,
                cycle=cycle,
                history=used,
                last_family=None,
                slot=slot,
                family_filter=families,
            )
            selected.append(card)
            used.add(card["id"])

    new_history = [card_id for card_id in history if card_id in used]
    for card in selected:
        if card["id"] not in new_history:
            new_history.append(card["id"])
    return selected, cycle, new_history, selected[-1]["family"] if selected else last_family


def present_card(
    card: dict[str, Any],
    *,
    deck: dict[str, Any],
    mode: str,
    visual: str,
    slot: str,
) -> dict[str, Any]:
    family = deck["families"][card["family"]]
    output = {
        "id": card["id"],
        "slot": slot,
        "family": card["family"],
        "family_label": family["label"],
        "symbol": family["symbol"],
        "spoken_label": family["spoken_label"],
        "title": card["title"],
        "kernel": card["kernel"],
        "prompt": card["prompts"][mode]["prompt"],
        "lighter": card["lighter"],
        "alt_text": card["alt_template"],
    }
    if mode == "solo":
        output["optional_followup"] = card["prompts"][mode]["optional_followup"]
    elif mode == "friends":
        output["host_note"] = card["prompts"][mode]["host_note"]
    if visual == "image":
        output["art_brief"] = card["art_brief"]
        output["essential_text_in_raster"] = False
    elif visual == "photo":
        output["photo_rule"] = (
            "Ground the prompt in one visible non-sensitive detail. Do not infer identity, "
            "location, emotion, relationships, health, or backstory."
        )
    return output


def make_state(
    *,
    deck: dict[str, Any],
    seed: str,
    mode: str,
    visual: str,
    exclusions: list[str],
    cycle: int = 0,
    history: list[str] | None = None,
    draw_log: list[str] | None = None,
    last_family: str | None = None,
    action: str = "draw",
    lighter: bool = False,
) -> dict[str, Any]:
    history = list(history or [])
    draw_log = list(draw_log or [])
    cards, cycle, history, last_family = draw_ids(
        deck,
        seed=seed,
        mode=mode,
        cycle=cycle,
        history=history,
        last_family=last_family,
        exclusions=set(exclusions),
        lighter=lighter,
    )
    draw_log.extend(card["id"] for card in cards)
    if lighter:
        slots = ["lighter"]
    elif mode == "creative":
        slots = list(CREATIVE_POOLS)
    else:
        slots = ["single"]
    return {
        "schema_version": STATE_VERSION,
        "deck_version": deck["deck_version"],
        "seed": seed,
        "replay_code": seed,
        "mode": mode,
        "visual": visual,
        "cycle": cycle,
        "history": history,
        "draw_log": draw_log,
        "last_family": last_family,
        "excluded_topics": exclusions,
        "current": {
            "action": action,
            "cards": [
                present_card(card, deck=deck, mode=mode, visual=visual, slot=slot)
                for card, slot in zip(cards, slots)
            ],
        },
        "controls": ["answer", "riff", "lighter", "another", "pass", "stop"],
    }


def emit(payload: dict[str, Any], output: str | None = None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
    print(text)


def validate_state(state: dict[str, Any], deck: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if state.get("schema_version") != STATE_VERSION:
        errors.append("unsupported state schema")
    if state.get("deck_version") != deck.get("deck_version"):
        errors.append("deck version mismatch")
    if state.get("mode") not in MODES or state.get("visual") not in VISUALS:
        errors.append("invalid mode or visual")
    known = {card["id"] for card in deck["cards"]}
    if any(card_id not in known for card_id in state.get("history", [])):
        errors.append("state contains unknown card ID")
    return errors


def self_test(deck: dict[str, Any]) -> None:
    assert not validate_deck(deck), validate_deck(deck)
    solo = make_state(
        deck=deck, seed=normalize_seed("moss-17"), mode="solo", visual="text", exclusions=[]
    )
    assert [card["id"] for card in solo["current"]["cards"]] == ["E03"]
    creative = make_state(
        deck=deck, seed=normalize_seed("NIGHT BUS"), mode="creative", visual="text", exclusions=[]
    )
    assert [card["id"] for card in creative["current"]["cards"]] == ["N04", "W03", "E01"]
    image = make_state(
        deck=deck, seed=normalize_seed("moss-17"), mode="solo", visual="image", exclusions=[]
    )
    assert solo["current"]["cards"][0]["id"] == image["current"]["cards"][0]["id"]
    stream = make_state(
        deck=deck, seed=normalize_seed("full-cycle"), mode="solo", visual="text", exclusions=[]
    )
    for _ in range(23):
        stream = make_state(
            deck=deck,
            seed=stream["seed"],
            mode=stream["mode"],
            visual=stream["visual"],
            exclusions=stream["excluded_topics"],
            cycle=stream["cycle"],
            history=stream["history"],
            draw_log=stream["draw_log"],
            last_family=stream["last_family"],
            action="another",
        )
    assert len(stream["draw_log"]) == 24
    assert len(set(stream["draw_log"])) == 24
    stream = make_state(
        deck=deck,
        seed=stream["seed"],
        mode=stream["mode"],
        visual=stream["visual"],
        exclusions=stream["excluded_topics"],
        cycle=stream["cycle"],
        history=stream["history"],
        draw_log=stream["draw_log"],
        last_family=stream["last_family"],
        action="another",
    )
    assert stream["cycle"] == 1
    assert len(stream["history"]) == 1
    excluded = make_state(
        deck=deck,
        seed=normalize_seed("exclude-connection"),
        mode="solo",
        visual="text",
        exclusions=["connection"],
    )
    chosen_id = excluded["current"]["cards"][0]["id"]
    chosen = next(card for card in deck["cards"] if card["id"] == chosen_id)
    assert "connection" not in chosen["topic_tags"]
    print("SELF_TEST_OK")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deck", default=str(DEFAULT_DECK))
    sub = parser.add_subparsers(dest="command", required=True)

    draw = sub.add_parser("draw", help="start a deterministic draw stream")
    draw.add_argument("--mode", choices=sorted(MODES), default="solo")
    draw.add_argument("--visual", choices=sorted(VISUALS), default="text")
    draw.add_argument("--seed")
    draw.add_argument("--exclude", default="")
    draw.add_argument("--output")

    nxt = sub.add_parser("next", help="consume the current draw and advance")
    nxt.add_argument("--state", required=True)
    nxt.add_argument("--action", choices=["another", "pass", "lighter"], required=True)
    nxt.add_argument("--visual", choices=sorted(VISUALS))
    nxt.add_argument("--exclude-add", default="")
    nxt.add_argument("--output")

    check = sub.add_parser("validate-state", help="validate a draw state")
    check.add_argument("--state", required=True)

    sub.add_parser("validate-deck", help="validate deck structure")
    sub.add_parser("self-test", help="run built-in golden checks")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        deck = load_deck(args.deck)
        deck_errors = validate_deck(deck)
        if deck_errors:
            raise ValueError("; ".join(deck_errors))
        if args.command == "draw":
            seed = normalize_seed(args.seed) if args.seed else random_seed()
            state = make_state(
                deck=deck,
                seed=seed,
                mode=args.mode,
                visual=args.visual,
                exclusions=list(dict.fromkeys(parse_csv(args.exclude))),
            )
            emit(state, args.output)
        elif args.command == "next":
            previous = json.loads(Path(args.state).read_text(encoding="utf-8"))
            state_errors = validate_state(previous, deck)
            if state_errors:
                raise ValueError("; ".join(state_errors))
            exclusions = list(
                dict.fromkeys(previous["excluded_topics"] + parse_csv(args.exclude_add))
            )
            state = make_state(
                deck=deck,
                seed=previous["seed"],
                mode=previous["mode"],
                visual=args.visual or previous["visual"],
                exclusions=exclusions,
                cycle=previous["cycle"],
                history=previous["history"],
                draw_log=previous["draw_log"],
                last_family=previous["last_family"],
                action=args.action,
                lighter=args.action == "lighter",
            )
            emit(state, args.output)
        elif args.command == "validate-state":
            state = json.loads(Path(args.state).read_text(encoding="utf-8"))
            errors = validate_state(state, deck)
            emit({"valid": not errors, "errors": errors})
            return 0 if not errors else 1
        elif args.command == "validate-deck":
            emit({"valid": True, "errors": []})
        else:
            self_test(deck)
        return 0
    except (ValueError, OSError, json.JSONDecodeError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
