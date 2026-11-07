"""Only registered local sources and opaque experiment IDs are exposed to clients."""

import hashlib
from pathlib import Path
import threading
from collections import OrderedDict
import copy

from app.benchmark.source import load_source, identity
from app.graph.statistics import statistics
from app.datasets.financial import DATASET_ID, FIXTURE
from app.datasets.io import read_json_file


def read_json(path):
    try:
        return read_json_file(path)
    except (OSError, ValueError):
        return None


class Repository:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.web = self.root / "data/processed/web"
        self.sources = {}
        self.cache = OrderedDict()
        self._catalog = None
        self._artifact_cache = OrderedDict()
        self._source_signatures = {}
        self._hash_keys = {}
        self.lock = threading.RLock()
        periods = read_json(FIXTURE)["periods"]
        self.sources[DATASET_ID] = {
            period: dict(kind="synthetic_financial", period=period) for period in periods
        }
        for folder in sorted((self.root / "data/raw").glob("bis-all-sectors-*")):
            manifest = read_json(folder / "manifest.json")
            if (
                not manifest
                or manifest.get("dataset_id") != "bis-lbs"
                or not (folder / "observations.csv").exists()
            ):
                continue
            # Period is read from the actual file, never inferred solely from its filename.
            import csv

            with (folder / "observations.csv").open(encoding="utf-8-sig") as stream:
                row = next(csv.DictReader(stream), {})
            period = row.get("TIME_PERIOD")
            if period:
                self.sources.setdefault("bis-lbs", {})[period] = dict(
                    kind="bis",
                    input=str(folder / "observations.csv"),
                    manifest=str(folder / "manifest.json"),
                    period=period,
                    missing_policy="exclude",
                )
        demo = self.root / "data/demo"
        if (demo / "observations.csv").exists() and (demo / "manifest.json").exists():
            self.sources["synthetic-demo"] = {
                "2025-Q4": dict(
                    kind="bis",
                    input=str(demo / "observations.csv"),
                    manifest=str(demo / "manifest.json"),
                    period="2025-Q4",
                )
            }
        seen = set()
        for folder in (
            sorted((self.root / "experiments").iterdir())
            if (self.root / "experiments").exists()
            else []
        ):
            config = read_json(folder / "configuration.json")
            if not config or config.get("source", {}).get("kind") != "synthetic":
                continue
            fingerprint = config.get("expected_graph", {}).get("graph_sha256")
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            self.sources[folder.name] = {"synthetic": config["source"]}

    def source(self, dataset, period):
        try:
            return self.sources[dataset][period]
        except KeyError:
            raise KeyError("Dataset or period is not registered in this local workspace.")

    def check_source(self, dataset, period):
        source = self.source(dataset, period)
        with self.lock:
            paths = (
                [source["input"], source["manifest"]]
                if source["kind"] == "bis"
                else [source["path"]]
                if source["kind"] == "snapshot"
                else [FIXTURE]
                if source["kind"] == "synthetic_financial"
                else []
            )
            try:
                signature = tuple(
                    (str(p), Path(p).stat().st_mtime_ns, Path(p).stat().st_size) for p in paths
                )
            except OSError as exc:
                raise ValueError(
                    "Registered source is unavailable; restore files and restart the API."
                ) from exc
            key = (dataset, period)
            previous = self._source_signatures.setdefault(key, signature)
            if signature != previous:
                raise ValueError(
                    "Registered source changed; restart the API before using this dataset."
                )

    def get(self, dataset, period):
        source = self.source(dataset, period)
        with self.lock:
            self.check_source(dataset, period)
            if (dataset, period) not in self.cache:
                graph, pipeline, validation = load_source(source)
                stats = statistics(graph)
                self.cache[dataset, period] = (graph, stats, validation)
                self._hash_keys[graph.graph["graph_sha256"]] = dataset
                while len(self.cache) > 3:
                    self.cache.popitem(last=False)
            self.cache.move_to_end((dataset, period))
            return self.cache[dataset, period]

    def datasets(self):
        with self.lock:
            return self._datasets()

    def _datasets(self):
        if self._catalog is not None:
            for dataset, periods in self.sources.items():
                # Verify source signatures without materializing evicted graphs.
                for period in periods:
                    self.check_source(dataset, period)
            return copy.deepcopy(self._catalog)
        entries = []
        for dataset, periods in self.sources.items():
            observations = []
            for period in sorted(periods):
                try:
                    g, s, v = self.get(dataset, period)
                    observations.append(
                        dict(
                            period=period,
                            **identity(g),
                            validation_status="warnings" if v.get("issues") else "valid",
                            warning_count=len(v.get("issues", [])),
                        )
                    )
                except (ValueError, OSError) as exc:
                    observations.append(
                        dict(period=period, validation_status="failed", error=str(exc))
                    )
            good = next((o for o in observations if "dataset_id" in o), {})
            entries.append(
                dict(
                    id=dataset,
                    name="BIS Locational Banking Statistics"
                    if dataset == "bis-lbs"
                    else ("Synthetic demo · 3 nodes" if dataset == "synthetic-demo" else dataset),
                    source="BIS"
                    if good.get("data_kind") == "observed_aggregate"
                    else "Explicitly synthetic fixture / generator",
                    data_kind=good.get("data_kind", "unavailable"),
                    periods=observations,
                    version=good.get("dataset_version", "unavailable"),
                )
            )
        self._catalog = entries
        return copy.deepcopy(entries)

    def artifact(self, path):
        """Cache bounded small completed artifacts; stat keys detect new results."""
        path = Path(path)
        try:
            stat = path.stat()
        except OSError:
            return None
        if stat.st_size > 512 * 1024:
            return read_json(path)
        signature = (stat.st_mtime_ns, stat.st_size)
        with self.lock:
            cached = self._artifact_cache.get(path)
            if cached and cached[0] == signature:
                self._artifact_cache.move_to_end(path)
                return cached[1]
            value = read_json(path)
            if value is None: return None
            self._artifact_cache[path] = (signature, value)
            while len(self._artifact_cache) > 64:
                self._artifact_cache.popitem(last=False)
            return value

    def experiments(self):
        records = []
        for path in (self.root / "experiments").glob("*/runs/*/summary.json"):
            summary = self.artifact(path)
            if not summary:
                continue
            opaque = hashlib.sha256(str(path.parent.relative_to(self.root)).encode()).hexdigest()[
                :20
            ]
            records.append(
                dict(id=opaque, path=path.parent, summary=summary, modified=path.stat().st_mtime)
            )
        return sorted(records, key=lambda x: x["modified"], reverse=True)

    def experiment(self, experiment_id):
        item = next((r for r in self.experiments() if r["id"] == experiment_id), None)
        if not item:
            raise KeyError("Experiment not found.")
        return item

    def results(self, experiment_id, limit=20):
        item = self.experiment(experiment_id)
        rankings = {}
        for file in (item["path"] / "rankings").glob("*.json"):
            result = self.artifact(file)
            if not result:
                continue
            rankings[file.stem] = dict(
                result,
                scores=result["scores"][:limit],
                node_count=len(result["scores"]),
                constant_scores=len({row["score"] for row in result["scores"]}) <= 1,
            )
        return dict(
            id=experiment_id,
            summary=item["summary"],
            rankings=rankings,
            comparisons=read_json(item["path"] / "comparisons.json") or [],
            environment=read_json(item["path"] / "environment.json"),
            dataset_key=self.key_for_hash(item["summary"]["graph"]["graph_sha256"]),
        )

    def key_for_hash(self, fingerprint):
        if fingerprint not in self._hash_keys:
            self.datasets()
        return self._hash_keys.get(fingerprint)

    def analyses(self, fingerprint):
        paths = list((self.web / "analyses" / fingerprint).glob("*.json"))
        paths += list((self.root / "data/processed/phase2").glob("*.json"))
        # Actual completed benchmark rankings are also valid computed analyses.
        for item in self.experiments():
            if item["summary"]["graph"]["graph_sha256"] == fingerprint:
                paths += list((item["path"] / "rankings").glob("*.json"))
        found = {}
        for path in sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True):
            result = self.artifact(path)
            if (
                not result
                or result.get("status") != "completed"
                or result.get("graph_sha256") != fingerprint
            ):
                continue
            aid = result["algorithm_id"]
            p = result["parameters"]
            if aid == "strength" and p.get("sort_by") != "total_strength":
                continue
            if aid == "betweenness" and (p.get("mode") != "unweighted" or p.get("k") is not None):
                continue
            if aid == "pagerank" and not p.get("weighted"):
                continue
            if aid == "debtrank":
                continue  # Scenario identity must be selected explicitly, never "latest".
            if aid not in found:
                found[aid] = result
        return found
