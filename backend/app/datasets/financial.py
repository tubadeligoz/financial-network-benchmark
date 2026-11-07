"""Independent fictional bank balance sheets. Never impute BIS financial fields."""
import hashlib
import json
import math
from pathlib import Path

import networkx as nx

from app.graph.builder import graph_payload

FIXTURE = Path(__file__).with_name('synthetic_banks.json')
DATASET_ID = 'synthetic-bank-stress'


def finite_number(value, name, *, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(value) or (value <= 0 if positive else value < 0)):
        raise ValueError(f'{name} must be finite and {"positive" if positive else "nonnegative"}.')
    return float(value)


def validate_financial_graph(graph):
    if (graph.graph.get('provenance', {}).get('data_kind') != 'synthetic' or
            any(a.get('entity_type') != 'synthetic_bank' for _, a in graph.nodes(data=True)) or
            graph.graph.get('creditor_scope') != 'synthetic_banks' or
            graph.graph.get('debtor_scope') != 'synthetic_banks'):
        raise ValueError('incompatible_entity_scope: DebtRank is restricted to explicitly synthetic bank networks; BIS countries/all sectors are not banks.')
    if not graph or not graph.is_directed() or graph.is_multigraph():
        raise ValueError('A nonempty simple directed synthetic bank graph is required.')
    if graph.graph.get('direction') != 'creditor_to_debtor':
        raise ValueError('Financial exposure direction must be creditor_to_debtor.')
    model = graph.graph.get('financial_model', {})
    if not model.get('capital_definition') or not model.get('calibration'):
        raise ValueError('missing_financial_inputs: explicit capital definition and model assumptions required.')
    unit = graph.graph.get('exposure_unit')
    for u, v, edge in graph.edges(data=True):
        finite_number(edge.get('exposure'), 'exposure', positive=True)
        if u == v or edge.get('exposure_unit') != unit or edge.get('period') != graph.graph['period']:
            raise ValueError('Self-loops, mixed periods or inconsistent exposure units are not supported.')
    for node, attrs in graph.nodes(data=True):
        f = attrs.get('available_financial_features', {})
        equity = finite_number(f.get('equity'), f'{node}.equity', positive=True)
        assets = finite_number(f.get('external_assets'), f'{node}.external_assets')
        liabilities = finite_number(f.get('external_liabilities'), f'{node}.external_liabilities')
        if f.get('unit') != unit or attrs.get('period') != graph.graph['period']:
            raise ValueError('Financial units and periods must match the exposure snapshot.')
        total_assets = assets + math.fsum(a['exposure'] for _, _, a in graph.out_edges(node, data=True))
        total_liabilities = liabilities + math.fsum(a['exposure'] for _, _, a in graph.in_edges(node, data=True))
        if not math.isclose(total_assets-total_liabilities, equity, rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError(f'{node}: inconsistent balance sheet; assets - liabilities must equal book equity.')
    if math.fsum(a['exposure'] for _, _, a in graph.edges(data=True)) <= 0:
        raise ValueError('Economic-value denominator is zero; no uniform weights are imputed.')


def load_synthetic_banks(period):
    raw = FIXTURE.read_bytes()
    source = json.loads(raw)
    if period not in source['periods']:
        raise ValueError('Unknown synthetic bank period.')
    record = source['periods'][period]
    g = nx.DiGraph(period=period, direction='creditor_to_debtor',
        exposure_unit=source['unit'], creditor_scope='synthetic_banks', debtor_scope='synthetic_banks',
        coverage=source['assumptions']['coverage'], financial_model=source['assumptions'],
        provenance=dict(dataset_id=source['dataset_id'], source_version=source['version'],
            data_kind='synthetic', input_sha256=hashlib.sha256(raw).hexdigest(), source_url='urn:fnb:synthetic-bank-stress'))
    for bank in record['banks']:
        node = bank['id']
        if node in g: raise ValueError('Duplicate bank identifier.')
        g.add_node(node, node_id=node, source_identifier=node, entity_type='synthetic_bank',
            dataset_id=source['dataset_id'], period=period,
            available_financial_features={k:v for k,v in bank.items() if k != 'id'} | {'unit':source['unit']},
            source_metadata={'label':source['label']})
    for u,v,amount in record['exposures']:
        if u not in g or v not in g or g.has_edge(u,v): raise ValueError('Invalid or duplicate exposure reference.')
        g.add_edge(u,v, exposure=amount, exposure_unit=source['unit'], period=period,
            source_metadata={'data_kind':'synthetic', 'label':source['label']})
    validate_financial_graph(g)
    g.graph['graph_sha256'] = hashlib.sha256(json.dumps(graph_payload(g),sort_keys=True,allow_nan=False).encode()).hexdigest()
    return g
