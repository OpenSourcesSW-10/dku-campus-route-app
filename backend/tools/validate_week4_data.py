import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.seed.week4_excel import validate_week4_excel


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate week 4 Excel/CSV data files.")
    parser.add_argument("data_dir", type=Path, help="Directory containing the W3/W4 xlsx or csv files.")
    args = parser.parse_args()

    report = validate_week4_excel(args.data_dir)
    print("stats")
    for key, value in report.stats.items():
        print(f"- {key}: {value}")

    if report.warnings:
        print("warnings")
        for warning in report.warnings:
            print(f"- {warning}")

    if report.errors:
        print("errors")
        for error in report.errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("validation ok")


if __name__ == "__main__":
    main()
