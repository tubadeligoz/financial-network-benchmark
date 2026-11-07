import argparse
import json
from pathlib import Path
import sys

import networkx as nx

from app.algorithms.engine import AlgorithmEngine
from app.datasets.io import write_json


def read_snapshot(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    graph = nx.DiGraph(**data['metadata'])
    for node in data['nodes']:
        if not isinstance(node.get('node_id'), str) or node['node_id'] in graph:
            raise ValueError('Node IDs must be unique strings.')
        graph.add_node(node['node_id'], **node)
    for edge in data['edges']:
        source, target = edge['source'], edge['target']
        if source not in graph or target not in graph or graph.has_edge(source, target):
            raise ValueError('Unknown edge endpoints or duplicate edge in snapshot.')
        graph.add_edge(source, target, **edge)
    return graph


def main(argv=None):
    parser = argparse.ArgumentParser(description='Score a validated Phase 1 graph snapshot; no benchmarking.')
    parser.add_argument('--graph', required=True)
    parser.add_argument('--algorithm', required=True, help='Algorithm ID: strength, betweenness, pagerank')
    parser.add_argument('--parameters-file', help='JSON parameter object; otherwise documented defaults')
    parser.add_argument('--output', required=True, help='New result JSON file')
    parser.add_argument('--top', type=int, default=5)
    args = parser.parse_args(argv)
    output = Path(args.output)
    if output.exists():
        print('Output exists; choose a new result filename.', file=sys.stderr)
        return 2
    try:
        if args.top < 1:
            raise ValueError('top must be positive.')
        graph = read_snapshot(args.graph)
        parameters = (json.loads(Path(args.parameters_file).read_text(encoding='utf-8'))
                      if args.parameters_file else {})
        result = AlgorithmEngine().run(args.algorithm, graph, parameters)
        write_json(output, result.to_dict())
        print(json.dumps(dict(status=result.status, algorithm=result.algorithm_id,
            graph_sha256=result.graph_sha256, top=result.top(args.top), error=result.error), ensure_ascii=False))
        return 0 if result.status == 'completed' else 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Cannot score snapshot: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
