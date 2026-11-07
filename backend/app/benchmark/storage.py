"""Portable source evidence for new benchmark runs; no raw or secret files."""

import hashlib
from pathlib import Path
import zipfile

from app.datasets.io import write_json


def archive_source(run: Path) -> dict[str, str]:
    backend = Path(__file__).resolve().parents[2]
    project = backend.parent
    files = sorted(p for p in (backend / "app").rglob("*") if p.suffix in (".py", ".json"))
    files += [backend / "pyproject.toml", backend / "requirements-lock.txt"]
    files += [
        p
        for p in (project / "frontend/package.json", project / "frontend/package-lock.json")
        if p.exists()
    ]
    manifest = {}
    target = run / "source-code.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            name = path.relative_to(project).as_posix()
            content = path.read_bytes()
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, content)
            manifest[name] = hashlib.sha256(content).hexdigest()
    write_json(run / "source-manifest.json", manifest)
    return dict(
        path="source-code.zip",
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        manifest="source-manifest.json",
    )
