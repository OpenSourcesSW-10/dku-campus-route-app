import csv
from pathlib import Path

from app.seed.xlsx_reader import read_first_sheet


def find_existing_file(data_dir: Path, filenames: tuple[str, ...]) -> Path | None:
    for filename in filenames:
        path = data_dir / filename
        if path.exists():
            return path
    return None


def read_table(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            return [
                {normalize_header(key): (value or "").strip() for key, value in row.items() if key}
                for row in csv.DictReader(csv_file)
                if any((value or "").strip() for value in row.values())
            ]
    return read_first_sheet(path)


def normalize_header(value: str) -> str:
    return value.strip().lower()


def bool_value(value: str | None, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


def int_value(value: str | None, default: int = 0) -> int:
    if value in (None, ""):
        return default
    return int(float(value))


def float_value(value: str | None, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def optional_str(value: str | None) -> str | None:
    return value if value not in (None, "") else None
