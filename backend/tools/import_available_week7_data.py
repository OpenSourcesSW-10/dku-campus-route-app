import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.seed.week4_excel import import_week4_excel
from app.seed.week5_positions import import_room_positions
from app.seed.week6_indoor_graph import import_week6_indoor_graph
from app.seed.week7_outdoor_graph import import_week7_outdoor_graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Import all currently available week 4~7 backend data.")
    parser.add_argument("db_root", type=Path, help="Directory containing DB files and design folders.")
    parser.add_argument("--replace", action="store_true", help="Replace imported tables before importing.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()

    db_root = args.db_root
    indoor_dir = db_root / "내부 구조 설계"
    outdoor_dir = _first_existing_dir(db_root / "외부 구조 설계_최종", db_root / "외부 구조 설계")

    db = SessionLocal()
    try:
        _print_report("week4", import_week4_excel(db, db_root, replace=args.replace))
        _print_report("week5_positions", import_room_positions(db, indoor_dir, replace=True))
        _print_report("week6_indoor_graph", import_week6_indoor_graph(db, indoor_dir, replace=True))
        _print_report("week7_outdoor_graph", import_week7_outdoor_graph(db, outdoor_dir, replace=True))
    finally:
        db.close()


def _first_existing_dir(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[-1]


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
