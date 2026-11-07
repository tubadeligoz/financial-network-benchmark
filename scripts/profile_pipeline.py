"""Repeatable diagnostic timings, separate from isolated scientific benchmark trials."""

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from time import perf_counter

import psutil
from fastapi.testclient import TestClient

from app.algorithms import AlgorithmEngine
from app.api.main import create_app
from app.benchmark.manager import environment, summarize
from app.benchmark.source import load_source, identity
from app.datasets.bis import load_bis
from app.graph.builder import build_graph, graph_payload


def measure(function, repeat):
    durations = []
    value = None
    for _ in range(repeat):
        start = perf_counter()
        value = function()
        durations.append(perf_counter() - start)
    return dict(seconds=durations, summary=summarize(durations)), value


def profile(root, repeat):
    sources = [
        ("synthetic-banks", dict(kind="synthetic_financial", period="synthetic-T0")),
        (
            "synthetic-1000",
            dict(kind="synthetic", generator=dict(node_count=1000, edge_count=4000, seed=42)),
        ),
    ]
    folder = root / "data/raw/bis-all-sectors-2025q4"
    if (folder / "observations.csv").exists():
        sources.append(
            (
                "bis-Q4",
                dict(
                    kind="bis",
                    input=str(folder / "observations.csv"),
                    manifest=str(folder / "manifest.json"),
                    period="2025-Q4",
                    missing_policy="exclude",
                ),
            )
        )
    records = []
    engine = AlgorithmEngine()
    for name, source in sources:
        loading, loaded = measure(lambda: load_source(source), repeat)
        graph = loaded[0]
        record = dict(
            case=name, identity=identity(graph), source=source, load_validate_build=loading
        )
        if source["kind"] == "bis":
            validation, data = measure(
                lambda: load_bis(
                    source["input"], source["manifest"], source["period"], missing_policy="exclude"
                ),
                repeat,
            )
            building, _ = measure(lambda: build_graph(data), repeat)
            record.update(load_validation=validation, graph_build=building)
        serialized, payload = measure(
            lambda: json.dumps(graph_payload(graph), allow_nan=False), repeat
        )
        record["graph_serialization"] = dict(serialized, utf8_bytes=len(payload.encode()))
        record["algorithms"] = {}
        for aid, params in [
            ("strength", {}),
            ("pagerank", {}),
            ("betweenness", {"k": 32} if len(graph) > 500 else {}),
        ]:
            kernels = []

            @contextmanager
            def boundary():
                start = perf_counter()
                yield
                kernels.append(perf_counter() - start)

            elapsed, result = measure(
                lambda: engine.run(aid, graph, params, compute_context=boundary), repeat
            )
            if result.status != "completed":
                raise RuntimeError(result.error)
            encoding, text = measure(lambda: json.dumps(result.to_dict(), allow_nan=False), repeat)
            record["algorithms"][aid] = dict(
                engine_total=elapsed,
                compute_seconds=kernels,
                compute_summary=summarize(kernels),
                result_serialization=encoding,
                result_bytes=len(text.encode()),
                scores_sha256=hashlib.sha256(
                    json.dumps(result.scores, sort_keys=True).encode()
                ).hexdigest(),
            )
        records.append(record)
    endpoints = [
        "/health",
        "/datasets",
        "/datasets/synthetic-bank-stress/periods/synthetic-T0/graph?limit_nodes=60",
        "/datasets/synthetic-bank-stress/periods/synthetic-T0/statistics",
        "/experiments",
    ]
    if len(sources) == 3:
        endpoints += [
            "/datasets/bis-lbs/periods/2025-Q4/graph?limit_nodes=60",
            "/datasets/bis-lbs/periods/2025-Q4/analyses",
        ]
    api = []
    with TestClient(create_app(root)) as client:
        for endpoint in endpoints:
            start = perf_counter()
            response = client.get("/api/v1" + endpoint)
            cold = perf_counter() - start
            if response.status_code != 200:
                raise RuntimeError(response.text)
            warm, response = measure(lambda: client.get("/api/v1" + endpoint), repeat)
            api.append(
                dict(
                    endpoint=endpoint,
                    cold_seconds=cold,
                    warm=warm,
                    payload_bytes=len(response.content),
                )
            )
    return dict(
        environment=environment(),
        repeat_count=repeat,
        records=records,
        api=api,
        process_rss_after_bytes=psutil.Process().memory_info().rss,
        limitations=[
            "ASGI TestClient timings include validation/encoding, not TCP/browser latency.",
            "Diagnostic same-process timings are not isolated benchmark runtime/memory trials.",
            "Sequential before/after measurements; machine load/caches are uncontrolled.",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repeat", type=int, default=5, choices=range(3, 21))
    args = parser.parse_args()
    path = Path(args.output)
    if path.exists():
        raise SystemExit("Choose a new output path; previous evidence is preserved.")
    result = profile(Path(__file__).resolve().parents[1], args.repeat)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print("Diagnostic profile saved:", path)
