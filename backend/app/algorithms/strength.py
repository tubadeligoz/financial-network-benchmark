import math

from app.algorithms.base import Algorithm, AlgorithmSpec, Computation


class Strength(Algorithm):
    spec = AlgorithmSpec('strength', 'Weighted Degree / Strength', '1.0.0',
        {'sort_by': 'total_strength'}, 'positive exposure in a common financial unit')
    fields = ('in_degree', 'out_degree', 'in_strength', 'out_strength', 'total_strength')

    def resolve(self, parameters):
        result = super().resolve(parameters)
        if result['sort_by'] not in self.fields:
            raise ValueError(f'sort_by must be one of {self.fields}.')
        return result

    def compute(self, graph, parameters):
        metrics = {}
        for node in graph:
            incoming = math.fsum(a['exposure'] for _, _, a in graph.in_edges(node, data=True))
            outgoing = math.fsum(a['exposure'] for _, _, a in graph.out_edges(node, data=True))
            metrics[node] = dict(in_degree=graph.in_degree(node), out_degree=graph.out_degree(node),
                in_strength=incoming, out_strength=outgoing, total_strength=incoming + outgoing)
        return Computation({n: m[parameters['sort_by']] for n, m in metrics.items()}, metrics,
            dict(score_metric=parameters['sort_by'], exposure_unit=graph.graph['exposure_unit'],
                 score_unit='count' if parameters['sort_by'].endswith('degree') else graph.graph['exposure_unit']))
