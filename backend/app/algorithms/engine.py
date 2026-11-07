import copy
import hashlib
import json
import math
from importlib.metadata import version
from dataclasses import asdict
from types import MappingProxyType
from contextlib import nullcontext

import networkx as nx

from app.algorithms.base import AlgorithmResult
from app.algorithms.strength import Strength
from app.algorithms.betweenness import Betweenness
from app.algorithms.pagerank import PageRank
from app.algorithms.debtrank import DebtRank
from app.graph.builder import graph_payload


def fingerprint(graph: nx.DiGraph) -> str:
    payload = graph_payload(graph)
    payload['metadata'].pop('graph_sha256', None)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _immutable(value):
    if isinstance(value, dict):
        return MappingProxyType({k: _immutable(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_immutable(x) for x in value)
    return value


def readonly_snapshot(graph: nx.DiGraph) -> nx.DiGraph:
    # Canonical traversal order: hashes intentionally ignore insertion order.
    snapshot = nx.DiGraph(**copy.deepcopy(graph.graph))
    for node, attrs in sorted(graph.nodes(data=True)):
        snapshot.add_node(node, **copy.deepcopy(attrs))
    for source, target, attrs in sorted(graph.edges(data=True)):
        snapshot.add_edge(source, target, **copy.deepcopy(attrs))
    snapshot.graph = _immutable(snapshot.graph)
    for node in snapshot:
        snapshot._node[node] = _immutable(snapshot._node[node])
    for source, target in snapshot.edges:
        attrs = _immutable(snapshot._succ[source][target])
        snapshot._succ[source][target] = attrs
        snapshot._pred[target][source] = attrs
    return nx.freeze(snapshot)


class AlgorithmEngine:
    def __init__(self):
        self._algorithms = {}
        for algorithm in (Strength(), Betweenness(), PageRank(), DebtRank()):
            self.register(algorithm)

    def register(self, algorithm):
        if algorithm.spec.algorithm_id in self._algorithms:
            raise ValueError(f'Algorithm already registered: {algorithm.spec.algorithm_id}')
        self._algorithms[algorithm.spec.algorithm_id] = algorithm

    def catalog(self):
        return [asdict(a.spec) for _, a in sorted(self._algorithms.items())]

    def resolve_parameters(self, algorithm_id, parameters):
        if algorithm_id not in self._algorithms:
            raise ValueError(f'Unknown algorithm: {algorithm_id}')
        return self._algorithms[algorithm_id].resolve(parameters)

    def run(self, algorithm_id: str, graph: nx.DiGraph, parameters: dict | None = None, *, compute_context=None) -> AlgorithmResult:
        algorithm = self._algorithms.get(algorithm_id)
        provenance = graph.graph.get('provenance', {})
        result = AlgorithmResult(algorithm_id=algorithm_id,
            algorithm_name=algorithm.spec.name if algorithm else algorithm_id,
            algorithm_version=algorithm.spec.version if algorithm else 'unknown',
            dataset_id=provenance.get('dataset_id'), dataset_version=provenance.get('source_version'),
            period=graph.graph.get('period'), graph_sha256=graph.graph.get('graph_sha256'),
            parameters=parameters if isinstance(parameters, dict) else {}, status='pending', metadata=dict(
                implementation='networkx', networkx_version=nx.__version__,
                direction=graph.graph.get('direction'), coverage=graph.graph.get('coverage'),
                creditor_scope=graph.graph.get('creditor_scope'), debtor_scope=graph.graph.get('debtor_scope'),
                source_file_sha256=provenance.get('input_sha256'), data_kind=provenance.get('data_kind'),
                tie_policy='score descending, node_id ascending (lexicographic); ordinal rank',
                score_scales_comparable_across_algorithms=False))
        result.metadata['scipy_version'] = version('scipy')
        stage = 'parameters'
        try:
            if algorithm is None:
                raise ValueError(f'Unknown algorithm: {algorithm_id}')
            if parameters is not None and not isinstance(parameters, dict):
                raise ValueError('parameters must be an object.')
            json.dumps(parameters, allow_nan=False)
            p = algorithm.resolve(parameters or {})
            result.parameters = p
            stage = 'graph'
            if not graph.is_directed() or graph.is_multigraph():
                raise ValueError('Only simple directed DiGraph snapshots are supported.')
            if any(not isinstance(n, str) or not n for n in graph):
                raise ValueError('Node IDs must be nonempty strings.')
            if not result.dataset_id or not result.dataset_version or not result.period:
                raise ValueError('Validated dataset provenance and period are required.')
            if graph.graph.get('direction') != 'creditor_to_debtor' or not graph.graph.get('exposure_unit'):
                raise ValueError('Exposure unit and creditor_to_debtor direction are required.')
            for _, _, attrs in graph.edges(data=True):
                w = attrs.get('exposure')
                if isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or w <= 0:
                    raise ValueError('Every edge requires a finite positive exposure, including unweighted modes.')
            if fingerprint(graph) != result.graph_sha256:
                raise ValueError('Graph fingerprint mismatch: rebuild the validated snapshot.')
            stage = 'parameters'
            algorithm.validate_graph_parameters(graph, p)
            stage = 'execution'
            snapshot = readonly_snapshot(graph)
            # Optional observation boundary excludes validation, copying and ranking.
            with compute_context() if compute_context else nullcontext():
                computation = algorithm.compute(snapshot, p)
            if set(computation.scores) != set(graph):
                raise ValueError('Algorithm must return a score for every node.')
            if any(not math.isfinite(v) for v in computation.scores.values()) or any(
                    not math.isfinite(v) for metrics in computation.metrics.values() for v in metrics.values()):
                raise ValueError('Algorithm returned nonfinite scores.')
            ordered = sorted(computation.scores, key=lambda n: (-computation.scores[n], n))
            result.scores = [dict(node_id=n, score=float(computation.scores[n]), rank=i,
                                  metrics=computation.metrics.get(n, {}))
                             for i, n in enumerate(ordered, 1)]
            result.metadata.update(computation.metadata)
            result.status = 'completed'
        except nx.PowerIterationFailedConvergence:
            result.status = 'nonconverged'
            result.error = dict(code='pagerank_nonconvergence',
                message='Power iteration did not reach tolerance within max_iterations; no scores published.')
        except Exception as exc:
            result.status = {'parameters': 'invalid_parameters', 'graph': 'invalid_graph'}.get(stage, 'failed')
            result.error = dict(code=result.status, message=str(exc))
        return result
