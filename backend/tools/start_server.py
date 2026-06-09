import os
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    _ensure_backend_import_path(backend_root)
    data_root = Path(os.getenv("DEPLOYMENT_DATA_ROOT", "data/week7"))
    if not data_root.is_absolute():
        data_root = backend_root / data_root

    if os.getenv("IMPORT_DATA_ON_START", "true").lower() in {"1", "true", "yes", "y"}:
        _validate_data_root(data_root)

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, app_dir=str(backend_root))


def _ensure_backend_import_path(backend_root: Path) -> None:
    backend_path = str(backend_root)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


def _validate_data_root(data_root: Path) -> None:
    if not data_root.exists():
        raise FileNotFoundError(f"Deployment data root does not exist: {data_root}")


if __name__ == "__main__":
    main()
