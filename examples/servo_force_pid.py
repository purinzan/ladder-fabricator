"""Generate a MELSEC iQ-F force-controlled servo ladder design as SVG.

The servo command register (D310) is an integration boundary. Map it to the
actual motion module or servo network only after choosing that hardware.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from gx3_ladder_export import parse_circuit, render_circuit


def circuit_ast():
    enabled = {"and": ["M100", "X2", {"not": "X3"}, {"not": "M101"}, {"not": "M110"}]}
    return parse_circuit({
        "schema_version": 2,
        "target": {"vendor": "melsec", "series": "iq-f"},
        "title": "ロードセルPID押圧位置制御（設計回路）",
        "comments": {
            "X0": "押圧開始", "X1": "停止要求", "X2": "サーボ準備完了",
            "X3": "非常停止作動", "X4": "異常リセット", "X5": "サーボ異常",
            "X6": "前進限界", "M100": "押圧制御実行中", "M101": "押圧異常",
            "M110": "目標圧到達", "D100": "目標圧力", "D101": "ロードセル実圧力",
            "D102": "過圧上限", "D200": "PIDパラメータ先頭（25点占有）",
            "D300": "PID位置補正量", "D310": "サーボ位置指令（機種別割付）",
            "Y0": "位置指令更新許可",
        },
        "rungs": [
            {
                "id": "pressure_fault",
                "title": "過圧・サーボ異常・前進限界を異常保持",
                "logic": {"or": [
                    "X5", "X6",
                    {"and": ["M100", {"compare": {"operator": ">=", "left": "D101", "right": "D102"}}]},
                ]},
                "output": {"type": "set", "device": "M101"},
            },
            {
                "id": "pressure_reached",
                "title": "ロードセル実圧力が目標圧力へ到達",
                "logic": {"and": [
                    "M100", {"compare": {"operator": ">=", "left": "D101", "right": "D100"}},
                ]},
                "output": {"type": "set", "device": "M110"},
            },
            {
                "id": "stop_control",
                "title": "停止・非常停止・目標到達・異常でPID制御を停止",
                "logic": {"or": ["X1", "X3", "M101", "M110"]},
                "output": {"type": "rst", "device": "M100"},
            },
            {
                "id": "reset_fault",
                "title": "圧力が上限未満かつ非常停止解除後に異常をリセット",
                "logic": {"and": [
                    "X4", {"not": "X3"},
                    {"compare": {"operator": "<", "left": "D101", "right": "D102"}},
                ]},
                "output": {"type": "rst", "device": "M101"},
            },
            {
                "id": "reset_reached",
                "title": "再始動前に目標圧到達を解除",
                "logic": {"and": [
                    "X4", {"compare": {"operator": "<", "left": "D101", "right": "D100"}},
                ]},
                "output": {"type": "rst", "device": "M110"},
            },
            {
                "id": "start_control",
                "title": "安全条件成立時の立ち上がりで押圧制御を開始",
                "logic": {"and": [
                    {"device": "X0", "contact": "rising"}, "X2", {"not": "X3"},
                    {"not": "M101"}, {"not": "M110"},
                ]},
                "output": {"type": "set", "device": "M100"},
            },
            {
                "id": "force_pid",
                "title": "目標圧力とロードセル実圧力から位置補正量を演算",
                "logic": enabled,
                "output": {
                    "type": "pid", "setpoint": "D100", "process_value": "D101",
                    "parameters": "D200", "destination": "D300",
                },
            },
            {
                "id": "apply_position",
                "title": "PID位置補正量をサーボ位置指令へ渡す（実機別に置換）",
                "logic": enabled,
                "output": {"type": "mov", "source": "D300", "destination": "D310"},
            },
            {
                "id": "servo_command_enable",
                "title": "PID演算中だけ位置指令を更新し、目標圧到達位置で停止",
                "logic": enabled,
                "output": {"type": "coil", "device": "Y0"},
            },
        ],
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=Path,
                        default=Path("outputs/servo-force-pid-melsec.svg"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_circuit(circuit_ast()) + "\n", encoding="utf-8")
    print(f"written: {args.output}")


if __name__ == "__main__":
    main()
