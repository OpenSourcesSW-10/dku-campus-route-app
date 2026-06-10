import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.seed.available_data import import_available_week8_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Import all currently available week 4~8 backend data.")
    parser.add_argument("db_root", type=Path, help="Directory containing DB files and design folders.")
    parser.add_argument("--replace", action="store_true", help="Replace imported tables before importing.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()

    db_root = args.db_root
    db = SessionLocal()
    try:
        reports = import_available_week8_data(db, db_root, replace=args.replace)
    finally:
        db.close()

    for label, report in reports.items():
        _print_report(label, report)


def _print_report(label: str, report) -> None:
    print(label)
    for key, value in report.stats.items():
        print(f"- {key}: {value}")
    for warning in report.warnings:
        print(f"warning: {warning}")
    for error in report.errors:
        print(f"error: {error}")
    if report.errors:
        raise SystemExit(1)
    print(f"{label} import ok")


if __name__ == "__main__":
    main()
