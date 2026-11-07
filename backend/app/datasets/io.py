import hashlib
import csv
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any

import pandas as pd

from app.core.models import DataError


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    try:
        if path.suffix.lower() == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as stream:
                header = next(csv.reader(stream), [])
            if len(header) != len(set(header)):
                raise DataError("Duplicate CSV column names are forbidden.")
            # Keep NA (Namibia), leading zeros, and source missing tokens intact.
            return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        if path.suffix.lower() == ".parquet":
            frame = pd.read_parquet(path)
            return frame.astype(object).where(frame.notna(), "").astype(str)
        raise DataError("Supported formats: .csv and .parquet (BIS flat/SDMX CSV).")
    except (OSError, ValueError, ImportError) as exc:
        raise DataError(f"Cannot read {path}: {exc}") from exc


def read_json_file(path: str | Path) -> Any:
    """Read complete JSON; retry transient Windows replacement sharing violations."""
    for attempt in range(20):
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.005)
    raise RuntimeError("Unreachable JSON read retry state")


def read_manifest(path: str | Path) -> dict[str, Any]:
    try:
        data = read_json_file(path)
    except (OSError, ValueError) as exc:
        raise DataError(f"Cannot read manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise DataError("Manifest must be a JSON object.")
    for key in ("dataset_id", "source_url", "source_version", "accessed_at", "data_kind"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise DataError(f"Manifest requires nonempty string: {key}")
    if data["data_kind"] not in ("observed_aggregate", "synthetic"):
        raise DataError("data_kind must be observed_aggregate or synthetic.")
    return data


def write_json(path: str | Path, data: Any) -> None:
    """Replace a complete JSON document atomically, including concurrent job readers."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
        for attempt in range(20):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.005)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
