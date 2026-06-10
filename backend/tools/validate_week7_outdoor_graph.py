import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.seed.week7_outdoor_graph import validate_week7_outdoor_graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate week 7 outdoor graph and entrance link data files.")
    parser.add_argument("data_dir", type=Path)
    args = parser.parse_args()
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()
    db = SessionLocal()
    try:
        report = validate_week7_outdoor_graph(db, args.data_dir)
    finally:
        db.close()
    print("stats")
    for key, value in report.stats.items():
        print(f"- {key}: {value}")
    for warning in report.warnings:
        print(f"warning: {warning}")
    for error in report.errors:
        print(f"error: {error}")
    if report.errors:
        raise SystemExit(1)
    print("validation ok")


if __name__ == "__main__":
    main()
