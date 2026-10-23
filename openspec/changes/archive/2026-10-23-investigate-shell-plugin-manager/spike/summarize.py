#!/usr/bin/env python3
"""Turn zsh-bench --raw output (+ install_ms from setup) into median/p90 JSON or a table."""
import json
import re
import statistics
import sys
from pathlib import Path

WARMUP = 3
METRICS = (
    "warm_prompt_ms",
    "warm_loaded_ms",
    "first_prompt_lag_ms",
    "first_command_lag_ms",
    "command_lag_ms",
    "input_lag_ms",
    "exit_time_ms",
)
FLAGS = (
    "has_compsys",
    "has_syntax_highlighting",
    "has_autosuggestions",
    "has_git_prompt",
)


def parse(path: Path) -> dict:
    text = path.read_text()
    data: dict = {"name": path.name.rsplit(".", 2)[0]}
    m = re.search(r"install_ms=([\d.]+)", text)
    data["install_ms"] = round(float(m.group(1)), 1) if m else None
    rc = re.search(r"install_rc=(\d+)", text)
    data["install_rc"] = int(rc.group(1)) if rc else None
    warm = re.findall(r"^warm: (prompt_ms|loaded_ms)=([\d.]+)(.*)$", text, re.M)
    for key in ("prompt_ms", "loaded_ms"):
        vals = " ".join(v for k, v, _ in warm if k == key)
        text += f"\nwarm_{key}=( {vals} )"
    feats = [rest.split() for k, _, rest in warm if k == "loaded_ms"]
    data["features"] = dict(kv.split("=", 1) for kv in feats[-1]) if feats else {}
    for name, values in re.findall(r"^(\w+)=\(\s*([^)]*)\)", text, re.M):
        nums = [float(v) for v in values.split()]
        if name in METRICS:
            measured = nums[WARMUP:] if len(nums) > WARMUP + 2 else nums
            measured.sort()
            p90 = measured[
                min(len(measured) - 1, int(round(0.9 * (len(measured) - 1))))
            ]
            data[name] = {
                "median": round(statistics.median(measured), 2),
                "p90": round(p90, 2),
                "n": len(measured),
            }
        elif name in FLAGS:
            data[name] = int(nums[-1]) if nums else None
    return data


def line(d: dict) -> str:
    def m(k):
        v = d.get(k)
        return f"{v['median']:.1f}/{v['p90']:.1f}" if v else "-"

    inst = f"{d['install_ms']:.0f}" if d.get("install_ms") is not None else "-"
    if d.get("install_rc") == 124:
        inst = "TIMEOUT"
    missing = [k for k, v in d.get("features", {}).items() if v != "1"]
    flags = (
        "ok" if d.get("features") and not missing else "missing:" + ",".join(missing)
    )
    return (
        f"{d['name']:<24} zb-prompt {m('first_prompt_lag_ms'):>11}  prompt {m('warm_prompt_ms'):>11}  "
        f"loaded {m('warm_loaded_ms'):>11}  cmd {m('command_lag_ms'):>10}  input {m('input_lag_ms'):>9}  "
        f"install {inst:>7}  {flags}"
    )


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--line":
        for p in args[1:]:
            print(line(parse(Path(p))))
    else:
        print(json.dumps(parse(Path(args[0])), indent=2))
