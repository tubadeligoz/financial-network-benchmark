import hashlib
import json
import math

import networkx as nx

from app.core.models import DataError, Dataset, Report


def validate_references(dataset: Dataset) -> Report:
    report = dataset.report
    ids = [n['node_id'] for n in dataset.nodes]
    if len(ids) != len(set(ids)):
        report.add('error', 'duplicate_node', 'Node IDs must be unique.')
    known = set(ids)
    seen = set()
    for edge in dataset.edges:
        pair = edge['source'], edge['target']
        if any(node not in known for node in pair):
            report.add('error', 'missing_reference', f'Unknown endpoint: {pair}')
        if pair in seen:
            report.add('error', 'duplicate_edge', f'Duplicate edge: {pair}')
        seen.add(pair)
        if edge['period'] != dataset.period:
            report.add('error', 'period_mismatch', 'Mixed edge periods.')
        weight = edge.get('exposure')
        if not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight <= 0:
            report.add('error', 'invalid_exposure', 'Graph requires finite positive exposures.')
    for node in dataset.nodes:
        if node.get('period') != dataset.period:
            report.add('error', 'period_mismatch', 'Mixed node periods.')
    return report


def graph_payload(graph: nx.DiGraph) -> dict:
    return dict(metadata=dict(graph.graph),
                nodes=[dict(node_id=n, **{k: v for k, v in attrs.items() if k != 'node_id'})
                       for n, attrs in sorted(graph.nodes(data=True))],
                edges=[dict(source=s, target=t, **{k: v for k, v in attrs.items()
                           if k not in ('source', 'target')})
                       for s, t, attrs in sorted(graph.edges(data=True))])


def build_graph(dataset: Dataset) -> nx.DiGraph:
    if not validate_references(dataset).valid:
        raise DataError('Validation failed; inspect validation report. Graph not created.')
    graph = nx.DiGraph(period=dataset.period,
        provenance=dataset.report.provenance, selection=dataset.report.selection,
        direction='creditor_to_debtor', exposure_unit='million USD',
        relationship='cross_border_loans_and_deposits',
        creditor_scope='resident_reporting_banks', debtor_scope='all_sectors',
        node_scope='country_or_territory; asymmetric institutional coverage',
        coverage='partial_observed_network; absent pairs are unknown')
    for node in sorted(dataset.nodes, key=lambda n: n['node_id']):
        graph.add_node(node['node_id'], **node)
    for edge in sorted(dataset.edges, key=lambda e: (e['source'], e['target'])):
        graph.add_edge(edge['source'], edge['target'], **edge)
    # File hash, policies, original source rows and all attributes participate.
    encoded = json.dumps(graph_payload(graph), sort_keys=True, allow_nan=False).encode()
    graph.graph['graph_sha256'] = hashlib.sha256(encoded).hexdigest()
    return graph
