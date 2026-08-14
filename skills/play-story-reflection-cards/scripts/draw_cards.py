#!/usr/bin/env python3
"""故事反思卡技能的可复现抽卡引擎。"""

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


class ChineseHelpFormatter(argparse.HelpFormatter):
    """将 argparse 自动生成的帮助栏目和用法前缀显示为中文。"""

    SECTION_NAMES = {
        "positional arguments": "位置参数",
        "options": "选项",
        "optional arguments": "选项",
    }

    def start_section(self, heading: str | None) -> None:
        super().start_section(self.SECTION_NAMES.get(heading, heading))

    def _format_usage(
        self,
        usage: str | None,
        actions: list[argparse.Action],
        groups: list[argparse._MutuallyExclusiveGroup],
        prefix: str | None,
    ) -> str:
        return super()._format_usage(usage, actions, groups, prefix or "用法：")


def translate_cli_error(message: str) -> str:
    required = re.fullmatch(r"the following arguments are required: (.+)", message)
    if required:
        field = "命令" if required.group(1) == "command" else required.group(1)
        return f"缺少必需参数：{field}"
    patterns = (
        (r"unrecognized arguments: (.+)", r"无法识别的参数：\1"),
        (r"argument (.+): expected one argument", r"参数 \1 需要一个值"),
        (
            r"argument (.+): invalid choice: (.+) \(choose from (.+)\)",
            r"参数 \1 的值 \2 无效（可选值：\3）",
        ),
    )
    for pattern, replacement in patterns:
        if re.fullmatch(pattern, message):
            return re.sub(pattern, replacement, message)
    return "命令行参数无效。请运行 --help 查看用法。"


class ChineseArgumentParser(argparse.ArgumentParser):
    """提供中文帮助与参数错误信息。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["add_help"] = False
        kwargs.setdefault("formatter_class", ChineseHelpFormatter)
        super().__init__(*args, **kwargs)
        self.add_argument("-h", "--help", action="help", help="显示此帮助信息并退出")

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"错误：{translate_cli_error(message)}\n")


def format_runtime_error(exc: BaseException) -> str:
    """把常见运行时异常转换为简洁中文，同时保留必要定位信息。"""
    if isinstance(exc, json.JSONDecodeError):
        return f"JSON 格式无效：第 {exc.lineno} 行，第 {exc.colno} 列"
    if isinstance(exc, FileNotFoundError):
        return f"找不到文件：{exc.filename}"
    if isinstance(exc, PermissionError):
        return f"无权访问文件：{exc.filename}"
    if isinstance(exc, OSError):
        target = exc.filename or "未指定路径"
        return f"文件操作失败：{target}（错误码 {exc.errno}）"
    if isinstance(exc, AssertionError):
        return "内置自测未通过"
    return str(exc)


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
        errors.append("不支持的卡牌结构规范")
    if not deck.get("deck_version"):
        errors.append("缺少 deck_version")
    cards = deck.get("cards")
    if not isinstance(cards, list) or len(cards) != 24:
        errors.append("初始卡组必须恰好包含 24 张卡牌")
        return errors
    ids = [card.get("id") for card in cards]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        errors.append("卡牌 ID 必须存在且唯一")
    families = deck.get("families", {})
    required_modes = {"solo", "friends", "creative"}
    for card in cards:
        family = card.get("family")
        if family not in families:
            errors.append(f"{card.get('id')}：未知卡族")
        prompts = card.get("prompts", {})
        if set(prompts) != required_modes:
            errors.append(f"{card.get('id')}：prompts 必须覆盖所有模式")
        if not card.get("lighter") or not card.get("art_brief"):
            errors.append(f"{card.get('id')}：缺少 lighter 或 art_brief")
    family_counts: dict[str, int] = {}
    for card in cards:
        family_counts[card["family"]] = family_counts.get(card["family"], 0) + 1
    if any(family_counts.get(name) != 4 for name in families):
        errors.append("每个卡族必须恰好包含 4 张卡牌")
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
        raise ValueError("应用排除项后没有剩余卡牌")
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
        raise ValueError("话题排除项使候选卡牌为空")
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
            "以一个可见且不敏感的细节为提示依据。不要推断身份、地点、情绪、"
            "关系、健康或背景故事。"
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
        errors.append("不支持的状态结构规范")
    if state.get("deck_version") != deck.get("deck_version"):
        errors.append("卡组版本不匹配")
    if state.get("mode") not in MODES or state.get("visual") not in VISUALS:
        errors.append("mode 或 visual 无效")
    known = {card["id"] for card in deck["cards"]}
    if any(card_id not in known for card_id in state.get("history", [])):
        errors.append("状态中包含未知卡牌 ID")
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
    print("自测通过")


def build_parser() -> argparse.ArgumentParser:
    parser = ChineseArgumentParser(description=__doc__)
    parser.add_argument(
        "--deck", default=str(DEFAULT_DECK), metavar="卡组路径", help="卡组 JSON 文件路径"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    draw = sub.add_parser("draw", prog=f"{parser.prog} draw", help="开始确定性抽卡序列")
    draw.add_argument("--mode", choices=sorted(MODES), default="solo", help="抽卡模式")
    draw.add_argument("--visual", choices=sorted(VISUALS), default="text", help="视觉形式")
    draw.add_argument("--seed", metavar="种子", help="用于复现抽卡的种子")
    draw.add_argument(
        "--exclude", default="", metavar="标签列表", help="以逗号分隔的排除话题标签"
    )
    draw.add_argument("--output", metavar="输出路径", help="状态 JSON 输出路径")

    nxt = sub.add_parser("next", prog=f"{parser.prog} next", help="消耗当前抽卡并继续")
    nxt.add_argument("--state", required=True, metavar="状态路径", help="现有状态 JSON 路径")
    nxt.add_argument(
        "--action",
        choices=["another", "pass", "lighter"],
        required=True,
        help="推进操作",
    )
    nxt.add_argument("--visual", choices=sorted(VISUALS), help="新的视觉形式")
    nxt.add_argument(
        "--exclude-add", default="", metavar="标签列表", help="新增的排除话题标签"
    )
    nxt.add_argument("--output", metavar="输出路径", help="状态 JSON 输出路径")

    check = sub.add_parser(
        "validate-state", prog=f"{parser.prog} validate-state", help="校验抽卡状态"
    )
    check.add_argument("--state", required=True, metavar="状态路径", help="待校验的状态 JSON 路径")

    sub.add_parser(
        "validate-deck", prog=f"{parser.prog} validate-deck", help="校验卡组结构"
    )
    sub.add_parser("self-test", prog=f"{parser.prog} self-test", help="运行内置黄金自测")
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
        print(f"错误：{format_runtime_error(exc)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
