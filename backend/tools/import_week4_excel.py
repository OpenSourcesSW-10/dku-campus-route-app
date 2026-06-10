import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.seed.week4_excel import import_week4_excel


def main() -> None:
    parser = argparse.ArgumentParser(description="Import week 4 Excel/CSV data into the backend DB.")
    parser.add_argument("data_dir", type=Path, help="Directory containing the W3/W4 xlsx or csv files.")
    parser.add_argument("--replace", action="store_true", help="Clear imported core data before importing.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()
    db = SessionLocal()
    try:
        report = import_week4_excel(db, args.data_dir, replace=args.replace)
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
