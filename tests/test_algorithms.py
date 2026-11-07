"""Independent mathematical oracles on SYNTHETIC graphs, never real bank claims."""
import copy
import json
import math

import networkx as nx
import pytest

from app.algorithms import AlgorithmEngine
from app.algorithms.base import Algorithm, AlgorithmSpec, Computation
from app.algorithms.cli import main, read_snapshot
from app.algorithms.engine import fingerprint
from app.core.models import Dataset, Report
from app.graph.builder import build_graph, graph_payload
from app.graph.weights import inverse_exposure_view


def fixture(edges=(), nodes=()):
    ids = sorted(set(nodes) | {n for s, t, _ in edges for n in (s, t)})
    report = Report(dict(dataset_id='synthetic-oracle', source_version='v1', data_kind='synthetic'))
    return build_graph(Dataset([dict(node_id=n, period='2025-Q4') for n in ids],
        [dict(source=s, target=t, exposure=w, period='2025-Q4') for s, t, w in edges], report, '2025-Q4'))


def result(algorithm, graph, **parameters):
    value = AlgorithmEngine().run(algorithm, graph, parameters)
    assert value.status == 'completed', value.error
    return value


def scores(value):
    return {row['node_id']: row['score'] for row in value.scores}


@pytest.mark.parametrize('algorithm', ['strength', 'betweenness', 'pagerank'])
def test_empty(algorithm):
    value = result(algorithm, fixture())
    assert value.scores == [] and value.top(20) == []


@pytest.mark.parametrize('algorithm,expected', [('strength', 0), ('betweenness', 0), ('pagerank', 1)])
def test_single_node(algorithm, expected):
    assert scores(result(algorithm, fixture(nodes=['only']))) == {'only': expected}


def test_strength_independent_sums():
    graph = fixture([('a', 'b', 10), ('b', 'a', 4), ('b', 'c', 6)], ['isolate'])
    value = result('strength', graph)
    rows = {r['node_id']: r for r in value.scores}
    assert rows['b']['metrics'] == dict(in_degree=1, out_degree=2, in_strength=10,
                                       out_strength=10, total_strength=20)
    assert rows['a']['score'] == 14 and rows['c']['score'] == 6
    assert rows['isolate']['score'] == 0
    assert scores(result('strength', graph, sort_by='out_strength'))['a'] == 10
    assert scores(result('strength', graph, sort_by='in_degree'))['c'] == 1


def test_directed_chain_betweenness_and_components():
    graph = fixture([('a', 'b', 1), ('b', 'c', 1), ('d', 'e', 1)], ['z'])
    assert scores(result('betweenness', graph, normalized=False)) == dict(a=0, b=1, c=0, d=0, e=0, z=0)
    # 6 nodes: directed normalization denominator (6-1)*(6-2)=20.
    assert scores(result('betweenness', graph))['b'] == pytest.approx(1/20)
    reversed_graph = fixture([('b', 'a', 1), ('b', 'c', 1)])
    assert all(v == 0 for v in scores(result('betweenness', reversed_graph)).values())


def test_inverse_exposure_changes_paths_not_source():
    # Direct a->c: distance 1, a->b->c: 1/4+1/4=1/2.
    graph = fixture([('a', 'b', 4), ('b', 'c', 4), ('a', 'c', 1)])
    original = copy.deepcopy(graph_payload(graph))
    assert scores(result('betweenness', graph, normalized=False))['b'] == 0
    weighted = result('betweenness', graph, mode='inverse_exposure', normalized=False)
    assert scores(weighted)['b'] == 1
    assert graph_payload(graph) == original
    assert 'distance' not in graph['a']['b']
    assert inverse_exposure_view(graph)['a']['b']['distance'] == .25


def test_multiple_equal_shortest_paths():
    graph = fixture([('a', 'b', 1), ('a', 'c', 1), ('b', 'd', 1), ('c', 'd', 1)])
    for mode in ('unweighted', 'inverse_exposure'):
        value = scores(result('betweenness', graph, mode=mode, normalized=False))
        assert value['b'] == .5 and value['c'] == .5


def test_pagerank_two_node_cycle_and_disconnected():
    assert scores(result('pagerank', fixture([('a', 'b', 7), ('b', 'a', 2)]))) == pytest.approx({'a': .5, 'b': .5})
    graph = fixture(nodes=['b', 'a', 'c'])
    assert scores(result('pagerank', graph)) == pytest.approx(dict(a=1/3, b=1/3, c=1/3))


def test_pagerank_directed_dangling_closed_form():
    # a->b, b dangling: p_b=(1+alpha)*p_a, p_a=1/(2+alpha).
    alpha = .8
    value = scores(result('pagerank', fixture([('a', 'b', 2)]), alpha=alpha, tolerance=1e-12))
    assert value == pytest.approx({'a': 1/2.8, 'b': 1.8/2.8}, abs=1e-11)


def test_weighted_pagerank_independent_stationary_solution():
    # a->b:3, a->c:1; b->a and c->a. With alpha=.5:
    # p_a=4/9; p_b=1/6 + (.5*.75*4/9)=1/3; p_c=2/9.
    graph = fixture([('a', 'b', 3), ('a', 'c', 1), ('b', 'a', 1), ('c', 'a', 1)])
    weighted = scores(result('pagerank', graph, alpha=.5, tolerance=1e-12))
    assert weighted == pytest.approx(dict(a=4/9, b=1/3, c=2/9), abs=1e-11)
    unweighted = scores(result('pagerank', graph, alpha=.5, weighted=False, tolerance=1e-12))
    assert unweighted == pytest.approx(dict(a=4/9, b=5/18, c=5/18), abs=1e-11)


@pytest.mark.parametrize('algorithm', ['strength', 'betweenness', 'pagerank'])
def test_ties_and_top_n_are_deterministic(algorithm):
    value = result(algorithm, fixture(nodes=[f'{i:02}' for i in range(25)]))
    assert [r['node_id'] for r in value.scores] == [f'{i:02}' for i in range(25)]
    assert [r['rank'] for r in value.scores] == list(range(1, 26))
    assert [len(value.top(n)) for n in (5, 10, 20)] == [5, 10, 20]
    assert [len(value.to_dict()['top_nodes'][str(n)]) for n in (5, 10, 20)] == [5, 10, 20]
    with pytest.raises(ValueError): value.top(0)


@pytest.mark.parametrize('weight', [0, -1, math.nan, math.inf, '10', None, True])
@pytest.mark.parametrize('algorithm', ['strength', 'betweenness', 'pagerank'])
def test_invalid_weights(algorithm, weight):
    graph = fixture([('a', 'b', 1)])
    graph['a']['b']['exposure'] = weight
    value = AlgorithmEngine().run(algorithm, graph)
    assert value.status == 'invalid_graph' and value.scores == []


def test_tampered_fingerprint_rejected():
    graph = fixture([('a', 'b', 1)])
    graph['a']['b']['exposure'] = 2
    assert AlgorithmEngine().run('strength', graph).status == 'invalid_graph'


def test_convergence_failure_has_no_scores():
    value = AlgorithmEngine().run('pagerank', fixture([('a', 'b', 1)]),
                                 dict(max_iterations=1, tolerance=1e-15))
    assert value.status == 'nonconverged'
    assert value.error['code'] == 'pagerank_nonconvergence' and value.scores == []


def test_approximate_records_actual_pivots_and_repeats():
    graph = fixture([(str(i), str(i+1), 1) for i in range(8)])
    a = result('betweenness', graph, k=4, seed=17)
    b = result('betweenness', graph, k=4, seed=17)
    assert a.to_dict() == b.to_dict()
    assert a.metadata['method'] == 'approximate_source_sampling'
    assert len(a.metadata['sampled_sources']) == 4 and a.metadata['seed'] == 17
    full_sample = result('betweenness', graph, k=len(graph), seed=17)
    assert scores(full_sample) == pytest.approx(scores(result('betweenness', graph)))
    assert full_sample.metadata['method'] != 'exact'


@pytest.mark.parametrize('algorithm,parameters', [
    ('strength', {'sort_by': 'bad'}), ('pagerank', {'alpha': 1}),
    ('pagerank', {'tolerance': 0}), ('pagerank', {'weighted': 'yes'}),
    ('pagerank', {'max_iterations': True}), ('betweenness', {'k': 20}),
    ('betweenness', {'k': 0}), ('betweenness', {'mode': 'exposure'}),
    ('betweenness', {'seed': None}), ('strength', {'unexpected': 1})])
def test_invalid_parameters(algorithm, parameters):
    assert AlgorithmEngine().run(algorithm, fixture([('a', 'b', 1)]), parameters).status == 'invalid_parameters'


def test_registration_and_readonly_enforcement():
    class NewAlgorithm(Algorithm):
        spec = AlgorithmSpec('custom', 'Custom test', 'test-v1', {}, 'none')
        def compute(self, graph, parameters):
            return Computation({n: 1 for n in graph})
    class MutatingAlgorithm(NewAlgorithm):
        spec = AlgorithmSpec('mutation', 'Forbidden mutation', 'test-v1', {}, 'none')
        def compute(self, graph, parameters):
            graph['a']['b']['exposure'] = 999
    engine = AlgorithmEngine()
    engine.register(NewAlgorithm())
    engine.register(MutatingAlgorithm())
    graph = fixture([('a', 'b', 1)])
    original = copy.deepcopy(graph_payload(graph))
    assert engine.run('custom', graph).status == 'completed'
    assert engine.run('mutation', graph).status == 'failed'
    assert graph_payload(graph) == original
    with pytest.raises(ValueError): engine.register(NewAlgorithm())
    assert any(s['algorithm_id'] == 'custom' for s in engine.catalog())


def test_unsupported_graph_types():
    for graph in (nx.Graph(), nx.MultiDiGraph()):
        assert AlgorithmEngine().run('strength', graph).status == 'invalid_graph'


def test_all_algorithms_preserve_source_and_schema():
    graph = fixture([('a', 'b', 3), ('b', 'c', 1)])
    original = copy.deepcopy(graph_payload(graph))
    engine = AlgorithmEngine()
    for algorithm in ('strength', 'betweenness', 'pagerank'):
        first = engine.run(algorithm, graph).to_dict()
        assert first['status'] == 'completed'
        assert first == engine.run(algorithm, graph).to_dict()
        assert first['graph_sha256'] == graph.graph['graph_sha256']
        assert first['dataset_version'] == 'v1'
        json.dumps(first, allow_nan=False)
    assert graph_payload(graph) == original


def test_snapshot_cli(tmp_path):
    path, output = tmp_path/'graph.json', tmp_path/'result.json'
    path.write_text(json.dumps(graph_payload(fixture([('a', 'b', 1)]))))
    assert fingerprint(read_snapshot(path)) == read_snapshot(path).graph['graph_sha256']
    assert main(['--graph', str(path), '--algorithm', 'strength', '--output', str(output)]) == 0
    assert json.loads(output.read_text())['scores'][0]['node_id'] == 'a'
    assert main(['--graph', str(path), '--algorithm', 'strength', '--output', str(output)]) == 2


def test_nonfinite_parameter_error_is_json_serializable():
    value = AlgorithmEngine().run('pagerank', fixture(nodes=['a']), {'alpha': math.nan})
    assert value.status == 'invalid_parameters'
    json.dumps(value.to_dict(), allow_nan=False)
    assert AlgorithmEngine().run('strength', fixture(), ['invalid']).status == 'invalid_parameters'


def test_insertion_order_does_not_change_approximation():
    graph = fixture([(str(i), str(i+1), 1) for i in range(8)])
    other = nx.DiGraph(**copy.deepcopy(graph.graph))
    other.add_nodes_from(reversed(list(graph.nodes(data=True))))
    other.add_edges_from(reversed(list(graph.edges(data=True))))
    assert fingerprint(graph) == fingerprint(other)
    a = result('betweenness', graph, k=3, seed=17)
    b = result('betweenness', other, k=3, seed=17)
    assert a.to_dict() == b.to_dict()


def test_cli_convergence_error_and_tampered_snapshot(tmp_path):
    path = tmp_path/'graph.json'
    path.write_text(json.dumps(graph_payload(fixture([('a', 'b', 1)]))))
    params = tmp_path/'parameters.json'
    params.write_text(json.dumps(dict(max_iterations=1, tolerance=1e-15)))
    output = tmp_path/'failed.json'
    assert main(['--graph', str(path), '--algorithm', 'pagerank', '--parameters-file', str(params),
                 '--output', str(output)]) == 2
    assert json.loads(output.read_text())['status'] == 'nonconverged'
    payload = json.loads(path.read_text())
    payload['edges'][0]['exposure'] = 2
    path.write_text(json.dumps(payload))
    output = tmp_path/'tampered.json'
    assert main(['--graph', str(path), '--algorithm', 'strength', '--output', str(output)]) == 2
    assert json.loads(output.read_text())['status'] == 'invalid_graph'
