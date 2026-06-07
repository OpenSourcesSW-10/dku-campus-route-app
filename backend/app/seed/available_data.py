from pathlib import Path
from typing import Any

from app.seed.reference_data import import_reference_data
from app.seed.week4_excel import import_week4_excel
from app.seed.week5_positions import import_room_positions
from app.seed.week6_indoor_graph import import_week6_indoor_graph
from app.seed.week7_outdoor_graph import import_week7_outdoor_graph


def import_available_week8_data(db: Any, db_root: Path, replace: bool = False) -> dict[str, Any]:
    # week4~8 제출용 자료를 정해진 순서로 import. 앞 단계 PK가 뒤 단계 FK 기준이 됨.
    indoor_dir = db_root / "내부 구조 설계"
    outdoor_dir = _first_existing_dir(db_root / "외부 구조 설계_최종", db_root / "외부 구조 설계")

    reports: dict[str, Any] = {}
    reports["week4"] = import_week4_excel(db, db_root, replace=replace)
    if _has_errors(reports["week4"]):
        return reports

    reports["reference_data"] = import_reference_data(db, db_root, replace=replace)
    if _has_errors(reports["reference_data"]):
        return reports

    reports["week5_positions"] = import_room_positions(db, indoor_dir, replace=replace)
    if _has_errors(reports["week5_positions"]):
        return reports

    reports["week6_indoor_graph"] = import_week6_indoor_graph(db, indoor_dir, replace=replace)
    if _has_errors(reports["week6_indoor_graph"]):
        return reports

    reports["week7_outdoor_graph"] = import_week7_outdoor_graph(db, outdoor_dir, replace=replace)
    return reports


def raise_for_failed_reports(reports: dict[str, Any]) -> None:
    failed = []
    for label, report in reports.items():
        errors = getattr(report, "errors", [])
        if errors:
            failed.append(f"{label}: {'; '.join(errors)}")
    if failed:
        raise ValueError(" / ".join(failed))


def _has_errors(report: Any) -> bool:
    return bool(getattr(report, "errors", []))


def _first_existing_dir(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[-1]
