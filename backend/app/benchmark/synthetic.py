import hashlib
import json
import math
import random

import networkx as nx

from app.algorithms.engine import fingerprint


def generate_synthetic(parameters):
    defaults = dict(node_count=100, model='erdos_renyi', seed=42, directed=True, weighted=True)
    p = dict(defaults, **parameters)
    if set(p) - set(defaults) - {'edge_count', 'density', 'attachment_m'}:
        raise ValueError('Unknown synthetic generator parameter.')
    n = p['node_count']
    if type(n) is not int or not 1 <= n <= 100000 or type(p['seed']) is not int or p['seed'] < 0:
        raise ValueError('node_count must be 1..100000 and seed a nonnegative integer.')
    if type(p['directed']) is not bool or type(p['weighted']) is not bool:
        raise ValueError('directed and weighted must be boolean.')
    rng = random.Random(p['seed'] + 1)
    if p['model'] == 'erdos_renyi':
        if 'attachment_m' in p or ('edge_count' in p and 'density' in p):
            raise ValueError('G(n,m) takes edge_count OR density, not attachment_m.')
        maximum = n * (n-1) if p['directed'] else n * (n-1) // 2
        if 'density' in p:
            density = p['density']
            if isinstance(density, bool) or not isinstance(density, (int, float)) or not math.isfinite(density) or not 0 <= density <= 1:
                raise ValueError('density must be between 0 and 1.')
            m = round(maximum * density)
        else:
            m = p.get('edge_count', min(4*n, maximum))
        if type(m) is not int or not 0 <= m <= maximum:
            raise ValueError('Invalid edge_count.')
        if m>250000: raise ValueError('Phase 3 generator safety cap: 250000 edges.')
        graph = nx.gnm_random_graph(n, m, seed=p['seed'], directed=p['directed'])
    elif p['model'] == 'preferential_attachment':
        if 'edge_count' in p or 'density' in p:
            raise ValueError('Preferential attachment uses attachment_m, not edge_count/density.')
        m = p.get('attachment_m', 2)
        if type(m) is not int or not 1 <= m < n:
            raise ValueError('Require 1 <= attachment_m < node_count.')
        if m*(n-m)>250000: raise ValueError('Phase 3 generator safety cap: 250000 edges.')
        base = nx.barabasi_albert_graph(n, m, seed=p['seed'])
        graph = nx.DiGraph() if p['directed'] else nx.Graph()
        graph.add_nodes_from(base)
        for s, t in sorted(base.edges()):
            graph.add_edge(*((t, s) if p['directed'] and rng.random() < .5 else (s, t)))
    else:
        raise ValueError('model must be erdos_renyi or preferential_attachment.')
    graph = nx.relabel_nodes(graph, {i: f'syn-{i:08}' for i in graph})
    for s, t in sorted(graph.edges()):
        graph[s][t].update(exposure=rng.uniform(1, 100) if p['weighted'] else 1.0,
            exposure_unit='synthetic units', period='synthetic',
            source_metadata=dict(data_kind='synthetic'))
    config_hash = hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()
    graph.graph.update(period='synthetic', direction='creditor_to_debtor',
        exposure_unit='synthetic units', coverage='synthetic; no real financial observations',
        creditor_scope='synthetic_entities', debtor_scope='synthetic_entities',
        provenance=dict(dataset_id='synthetic-'+p['model'], source_version='generator-v1',
                        input_sha256=config_hash, data_kind='synthetic'),
        generator=p, directed=p['directed'], weighted=p['weighted'])
    graph.graph['graph_sha256'] = fingerprint(graph)
    return graph
