import networkx as nx

from app.algorithms.base import Algorithm, AlgorithmSpec, Computation, positive_number, boolean


class PageRank(Algorithm):
    spec = AlgorithmSpec('pagerank', 'Directed PageRank', '1.0.0',
        dict(alpha=0.85, tolerance=1e-8, max_iterations=1000, weighted=True),
        'positive exposure normalized per outgoing row, or unit transition weights')

    def resolve(self, parameters):
        p = super().resolve(parameters)
        positive_number(p['alpha'], 'alpha')
        if p['alpha'] >= 1:
            raise ValueError('alpha must satisfy 0 < alpha < 1.')
        positive_number(p['tolerance'], 'tolerance')
        if p['tolerance'] >= 1:
            raise ValueError('tolerance must be less than 1 (global L1 threshold).')
        if type(p['max_iterations']) is not int or p['max_iterations'] < 1:
            raise ValueError('max_iterations must be a positive integer.')
        boolean(p['weighted'], 'weighted')
        return p

    def compute(self, graph, parameters):
        p = parameters
        # NetworkX stops at n * tol; API tolerance denotes the GLOBAL L1 threshold.
        scores = nx.pagerank(graph, alpha=p['alpha'], tol=p['tolerance'] / max(1, len(graph)),
            max_iter=p['max_iterations'], weight='exposure' if p['weighted'] else None)
        return Computation(scores, metadata=dict(personalization='uniform', dangling='uniform',
            tolerance_semantics='global L1 iterate difference',
            networkx_tol=p['tolerance'] / max(1, len(graph)),
            score_unit='dimensionless',
            limitations=['Incoming financial connectivity is not default probability or credit quality.']))
