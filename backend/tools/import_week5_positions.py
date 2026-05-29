import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.seed.week5_positions import import_room_positions


def main() -> None:
    parser = argparse.ArgumentParser(description="Import week 5 room position data into the backend DB.")
    parser.add_argument("data_dir", type=Path, help="Directory containing room_positions.csv or room_positions.xlsx.")
    parser.add_argument("--replace", action="store_true", help="Clear existing room_positions before importing.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()
    db = SessionLocal()
    try:
        report = import_room_positions(db, args.data_dir, replace=args.replace)
    finally:
        db.close()

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

    print("import ok")


if __name__ == "__main__":
    main()
