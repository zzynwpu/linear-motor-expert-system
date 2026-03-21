from __future__ import annotations

import argparse
import json

from .calibration import analyze_csv, save_result_json
from .models import SystemConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="直线电机运动精度估算与校正 CLI")
    parser.add_argument("--input", required=True, help="输入 CSV 文件路径")
    parser.add_argument("--output", help="输出 JSON 报告路径")
    parser.add_argument("--pole-pitch", type=float, default=2.0, help="磁极距，单位 mm")
    parser.add_argument("--harmonics", type=int, default=5, help="拟合谐波阶数")
    parser.add_argument("--lookup-spacing", type=float, default=5.0, help="查表补偿间距，单位 mm")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = SystemConfig(
        pole_pitch_mm=args.pole_pitch,
        harmonic_count=args.harmonics,
        lookup_spacing_mm=args.lookup_spacing,
    )
    result = analyze_csv(args.input, config=config)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if args.output:
        save_result_json(result, args.output)


if __name__ == "__main__":
    main()

