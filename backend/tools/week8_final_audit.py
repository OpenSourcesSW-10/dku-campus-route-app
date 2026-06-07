import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.services.readiness import build_week8_readiness_report


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()
    db = SessionLocal()
    try:
        report = build_week8_readiness_report(db)
    finally:
        db.close()

    print(f"overallStatus: {report['overallStatus']}")
    for check in report["checks"]:
        print(f"- [{check['status']}] {check['name']}: {check['message']}")
        if check.get("requiredAction"):
            print(f"  requiredAction: {check['requiredAction']}")
        if check.get("details"):
            print(f"  details: {check['details']}")
    if report["overallStatus"] == "BLOCKED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
