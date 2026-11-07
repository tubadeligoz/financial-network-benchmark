from time import perf_counter_ns

import networkx as nx

from app.algorithms.cli import read_snapshot
from app.algorithms.engine import fingerprint
from app.datasets.bis import load_bis
from app.graph.builder import build_graph
from app.benchmark.synthetic import generate_synthetic
from app.datasets.financial import load_synthetic_banks


def load_source(source):
    times = dict(dataset_load_validation_seconds=None, graph_build_seconds=None,
                 snapshot_read_seconds=None, synthetic_generation_seconds=None)
    start = perf_counter_ns()
    if source['kind'] == 'bis':
        data = load_bis(source['input'], source['manifest'], source['period'],
            missing_policy=source.get('missing_policy', 'error'),
            zero_policy=source.get('zero_policy', 'error'),
            self_loop_policy=source.get('self_loop_policy', 'error'))
        times['dataset_load_validation_seconds'] = (perf_counter_ns()-start)/1e9
        start = perf_counter_ns()
        graph = build_graph(data)
        times['graph_build_seconds'] = (perf_counter_ns()-start)/1e9
        warnings = data.report.to_dict()
    elif source['kind'] == 'snapshot':
        graph = read_snapshot(source['path'])
        times['snapshot_read_seconds'] = (perf_counter_ns()-start)/1e9
        warnings = {'note': 'Snapshot input: original table loading/build costs were not measured.'}
    elif source['kind'] == 'synthetic':
        graph = generate_synthetic(source['generator'])
        times['synthetic_generation_seconds'] = (perf_counter_ns()-start)/1e9
        warnings = {'note': 'Synthetic observations; no actual banks or financial amounts.'}
    elif source['kind'] == 'synthetic_financial':
        graph = load_synthetic_banks(source['period'])
        times['synthetic_generation_seconds'] = (perf_counter_ns()-start)/1e9
        warnings = {'note':'SYNTHETIC — NOT CALIBRATED TO BIS; explicit book-equity balance sheets validated.'}
    else:
        raise ValueError('Source kind must be bis, snapshot, synthetic or synthetic_financial.')
    if fingerprint(graph) != graph.graph.get('graph_sha256'):
        raise ValueError('Input graph fingerprint mismatch.')
    return graph, times, warnings


def identity(graph):
    provenance = graph.graph['provenance']
    return dict(dataset_id=provenance['dataset_id'], dataset_version=provenance['source_version'],
        selected_period=graph.graph['period'], graph_sha256=graph.graph['graph_sha256'],
        data_kind=provenance['data_kind'], node_count=len(graph),
        edge_count=graph.number_of_edges(), density=nx.density(graph),
        direction=graph.graph['direction'], exposure_unit=graph.graph['exposure_unit'],
        creditor_scope=graph.graph.get('creditor_scope'), debtor_scope=graph.graph.get('debtor_scope'))
