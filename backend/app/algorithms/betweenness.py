import random
import networkx as nx

from app.algorithms.base import Algorithm, AlgorithmSpec, Computation, boolean, positive_number
from app.graph.weights import inverse_exposure_view


class Betweenness(Algorithm):
    spec = AlgorithmSpec('betweenness', 'Directed Betweenness Centrality', '1.0.0',
        dict(mode='unweighted', normalized=True, k=None, seed=42, distance_scale=1.0),
        'unit hop distance, or explicit distance = distance_scale / exposure')

    def resolve(self, parameters):
        p = super().resolve(parameters)
        if p['mode'] not in ('unweighted', 'inverse_exposure'):
            raise ValueError('mode must be unweighted or inverse_exposure.')
        boolean(p['normalized'], 'normalized')
        positive_number(p['distance_scale'], 'distance_scale')
        if p['mode'] == 'unweighted' and p['distance_scale'] != 1:
            raise ValueError('distance_scale is only meaningful for inverse_exposure mode.')
        if p['k'] is not None and (type(p['k']) is not int or p['k'] < 1):
            raise ValueError('k must be a positive integer or null for exact computation.')
        if type(p['seed']) is not int or p['seed'] < 0:
            raise ValueError('seed must be a nonnegative integer.')
        return p

    def validate_graph_parameters(self, graph, parameters):
        if parameters['k'] is not None and parameters['k'] > len(graph):
            raise ValueError('k cannot exceed the number of nodes.')

    def compute(self, graph, parameters):
        p = parameters
        weighted = p['mode'] == 'inverse_exposure'
        working = inverse_exposure_view(graph, p['distance_scale']) if weighted else graph
        pivots = (random.Random(p['seed']).sample(list(graph), p['k'])
                  if p['k'] is not None else None)
        scores = nx.betweenness_centrality(working, weight='distance' if weighted else None,
            normalized=p['normalized'], endpoints=False, k=p['k'], seed=p['seed'])
        return Computation(scores, metadata=dict(
            method='exact' if p['k'] is None else 'approximate_source_sampling',
            sampled_sources=pivots, sample_size=p['k'], seed=p['seed'] if pivots is not None else None,
            endpoints=False, distance_transform='c/exposure' if weighted else 'unit_hops',
            limitations=['Shortest paths are structural, not observed contagion paths.'] +
                (['Floating point distance ties may affect shortest-path counts.'] if weighted else [])))
