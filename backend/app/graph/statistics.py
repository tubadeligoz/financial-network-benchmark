import math
from collections import Counter
import networkx as nx


def statistics(graph: nx.DiGraph) -> dict:
    values = sorted(d['exposure'] for _, _, d in graph.edges(data=True))
    n = len(values)
    weights = dict(count=n, min=min(values) if n else None, max=max(values) if n else None,
                   mean=math.fsum(values) / n if n else None,
                   median=(values[n // 2] if n % 2 else
                           (values[n // 2 - 1] + values[n // 2]) / 2) if n else None,
                   sorted_values=values)
    weak = sorted([sorted(c) for c in nx.weakly_connected_components(graph)], key=lambda c: (-len(c), c))
    strong = sorted([sorted(c) for c in nx.strongly_connected_components(graph)], key=lambda c: (-len(c), c))
    per_node = {node: dict(in_degree=graph.in_degree(node), out_degree=graph.out_degree(node),
         in_strength=math.fsum(d['exposure'] for _, _, d in graph.in_edges(node, data=True)),
         out_strength=math.fsum(d['exposure'] for _, _, d in graph.out_edges(node, data=True)))
         for node in sorted(graph)}
    return dict(node_count=graph.number_of_nodes(), edge_count=graph.number_of_edges(),
        density=nx.density(graph), self_loop_count=nx.number_of_selfloops(graph),
        in_degree_distribution=dict(sorted(Counter(x['in_degree'] for x in per_node.values()).items())),
        out_degree_distribution=dict(sorted(Counter(x['out_degree'] for x in per_node.values()).items())),
        weakly_connected_components=dict(count=len(weak), members=weak),
        strongly_connected_components=dict(count=len(strong), members=strong),
        nodes=per_node, weight_distribution=weights, period=graph.graph['period'],
        exposure_unit=graph.graph['exposure_unit'], graph_sha256=graph.graph['graph_sha256'],
        coverage=graph.graph['coverage'])
