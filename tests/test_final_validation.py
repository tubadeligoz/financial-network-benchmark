"""Regressions found by the Phase 6 quality audit. All fixtures are synthetic."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil

import pytest

from app.api.repository import Repository
from app.core.models import DataError
from app.datasets.io import read_manifest, write_json, read_json_file


def test_atomic_json_never_publishes_partial_or_invalid_document(tmp_path):
    path = tmp_path / "result.json"
    write_json(path, {"sequence": 0, "values": list(range(512))})

    def reader():
        for _ in range(150):
            value = read_json_file(path)
            assert value["values"] == list(range(512))

    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(reader)
        for index in range(20):
            write_json(path, {"sequence": index, "values": list(range(512))})
        future.result()
    saved = path.read_bytes()
    with pytest.raises(ValueError):
        write_json(path, {"invalid": float("nan")})
    assert path.read_bytes() == saved
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.parametrize("value", [[], None, 42, "manifest"])
def test_manifest_root_must_be_object(tmp_path, value):
    path = tmp_path / "manifest.json"
    write_json(path, value)
    with pytest.raises(DataError, match="JSON object"):
        read_manifest(path)


def test_catalog_cache_graph_eviction_and_source_mutation(tmp_path):
    demo = tmp_path / "data/demo"
    demo.mkdir(parents=True)
    original = Path(__file__).resolve().parents[1] / "data/demo"
    for name in ("manifest.json", "observations.csv"):
        shutil.copy(original / name, demo / name)
    repo = Repository(tmp_path)
    for seed in range(4):
        repo.sources[f"synthetic-{seed}"] = {
            "synthetic": dict(
                kind="synthetic", generator=dict(node_count=10, edge_count=20, seed=seed)
            )
        }
    first = repo.datasets()
    assert len(repo.cache) <= 3
    assert repo.datasets() == first
    first.clear()
    assert repo.datasets()  # Clients cannot mutate the catalog cache.
    graph = repo.get("synthetic-bank-stress", "synthetic-T0")[0]
    assert repo.key_for_hash(graph.graph["graph_sha256"]) == "synthetic-bank-stress"
    (demo / "observations.csv").write_text((demo / "observations.csv").read_text() + "\n")
    with pytest.raises(ValueError, match="restart"):
        repo.get("synthetic-demo", "2025-Q4")
    with pytest.raises(ValueError, match="restart"):
        repo.datasets()


def test_artifact_cache_reloads_changed_files(tmp_path):
    repo = Repository(tmp_path)
    path = tmp_path / "summary.json"
    write_json(path, {"value": 1})
    assert repo.artifact(path) == {"value": 1}
    write_json(path, {"value": 22})
    assert repo.artifact(path) == {"value": 22}
