#!/usr/bin/env python3
"""城市平行人生冒险的确定性状态管理器。"""

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


def translate_argparse_error(message: str) -> str:
    """把 argparse 的常见参数错误转换为中文。"""
    if message == "the following arguments are required: command":
        return "缺少必填参数：命令"
    replacements = (
        ("the following arguments are required:", "缺少必填参数："),
        ("unrecognized arguments:", "无法识别的参数："),
        ("invalid int value:", "无效的整数值："),
        ("invalid choice:", "无效选项："),
        ("choose from", "可选值为"),
        ("expected one argument", "应提供一个参数"),
        ("expected at least one argument", "应至少提供一个参数"),
        ("argument ", "参数 "),
    )
    for source, target in replacements:
        message = message.replace(source, target)
    return message


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
    return str(exc)


class ChineseArgumentParser(argparse.ArgumentParser):
    """使用中文帮助标题和参数错误的命令行解析器。"""

    def format_usage(self) -> str:
        return super().format_usage().replace("usage: ", "用法：", 1)

    def format_help(self) -> str:
        return (
            super().format_help()
            .replace("usage: ", "用法：", 1)
            .replace("positional arguments:", "位置参数：")
            .replace("options:", "选项：")
            .replace("show this help message and exit", "显示帮助信息并退出")
        )

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: 参数错误：{translate_argparse_error(message)}\n")


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
        errors.append(f"缺少字段：{sorted(missing)}")
        return errors
    if state["schema_version"] != SCHEMA_VERSION:
        errors.append("不支持的 schema_version")
    prefs = state["verification_preferences"]
    if not isinstance(prefs, list) or not prefs or any(v not in VERIFICATION for v in prefs):
        errors.append("verification_preferences 无效")
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
            errors.append(f"指标 {key} 必须是 [{lower}, {upper}] 范围内的整数")
    if len(state["visited"]) != len(set(state["visited"])):
        errors.append("visited 中的关卡 ID 必须唯一")
    if len(state["flags"]) != len(set(state["flags"])):
        errors.append("flags 必须唯一")
    return errors


def new_state(args: argparse.Namespace) -> dict[str, Any]:
    prefs = parse_csv(args.verification)
    invalid = sorted(set(prefs) - VERIFICATION)
    if invalid or not prefs:
        raise ValueError(f"验证方式无效：{invalid or prefs}")
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
        raise ValueError(f"关卡已经访问：{args.checkpoint}")
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
        key, reason = "keeper-of-the-map", "收集了三条线索，并获得正声望"
    elif metrics["relationship"] >= 2:
        key, reason = "trusted-companion", "在路线中建立了稳固关系"
    elif metrics["time_remaining"] == 0 or metrics["energy"] <= 10:
        key, reason = "last-minute-return", "结束时已无剩余时间或精力很低"
    else:
        key, reason = "unfinished-thread", "留下了一条可供重玩的有效未解支线"
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
            assert "已经访问" in str(exc)
        else:
            raise AssertionError("错误地接受了重复关卡")
    print("SELF_TEST_OK")


def build_parser() -> argparse.ArgumentParser:
    parser = ChineseArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="创建新状态")
    new.add_argument("--identity", required=True, metavar="身份", help="虚构身份")
    new.add_argument("--minutes", type=int, default=75, metavar="分钟", help="初始时长，默认 75 分钟")
    new.add_argument("--budget", type=int, default=0, metavar="预算", help="初始预算，默认 0")
    new.add_argument(
        "--verification", default="observation,self-report", metavar="验证方式列表",
        help="以逗号分隔的验证方式，默认 observation,self-report",
    )
    new.add_argument("--seed", type=int, metavar="种子", help="可选的确定性随机种子")
    new.add_argument("--output", metavar="输出文件", help="同时写入指定文件")

    update = sub.add_parser("update", help="应用一次关卡选择")
    update.add_argument("--state", required=True, metavar="状态文件", help="现有状态文件")
    update.add_argument("--checkpoint", required=True, metavar="关卡ID", help="唯一关卡 ID")
    update.add_argument("--choice", required=True, metavar="选择", help="玩家作出的选择")
    update.add_argument(
        "--verification", required=True, choices=sorted(VERIFICATION), help="本关使用的验证方式",
    )
    update.add_argument("--time", type=int, default=0, metavar="时间变化", help="剩余分钟数的变化量")
    update.add_argument("--energy", type=int, default=0, metavar="精力变化", help="精力的变化量")
    update.add_argument("--budget", type=int, default=0, metavar="预算变化", help="剩余预算的变化量")
    update.add_argument("--clues", type=int, default=0, metavar="线索变化", help="线索数量的变化量")
    update.add_argument(
        "--relationship", type=int, default=0, metavar="关系变化", help="关系值的变化量",
    )
    update.add_argument("--reputation", type=int, default=0, metavar="声望变化", help="声望值的变化量")
    update.add_argument("--flags", default="", metavar="标记列表", help="以逗号分隔的新增剧情标记")
    update.add_argument("--output", metavar="输出文件", help="同时写入指定文件")

    validate = sub.add_parser("validate", help="验证状态文件")
    validate.add_argument("--state", required=True, metavar="状态文件", help="要验证的状态文件")

    ending = sub.add_parser("ending", help="为有效状态判定结局")
    ending.add_argument("--state", required=True, metavar="状态文件", help="要判定结局的状态文件")

    sub.add_parser("self-test", help="运行内置确定性检查")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "new":
            if args.minutes <= 0 or args.budget < 0:
                raise ValueError("minutes 必须为正数，budget 不得为负数")
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
        print(f"错误：{format_runtime_error(exc)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
