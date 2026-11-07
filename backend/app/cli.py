import argparse
import json
import sys
from pathlib import Path

from app.core.models import DataError
from app.datasets.bis import load_bis
from app.datasets.io import write_json
from app.graph.builder import build_graph, graph_payload, validate_references
from app.graph.statistics import statistics


def main(argv=None):
    parser = argparse.ArgumentParser(description='BIS LBS validation and exposure graph CLI (Phase 1).')
    parser.add_argument('command', choices=['validate', 'build', 'stats'])
    parser.add_argument('--dataset', choices=['bis-lbs'], default='bis-lbs')
    parser.add_argument('--input', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--period', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--column-map', help='JSON object mapping source names to BIS canonical names')
    parser.add_argument('--missing-policy', choices=['error', 'exclude'], default='error')
    parser.add_argument('--zero-policy', choices=['error', 'exclude'], default='error')
    parser.add_argument('--self-loop-policy', choices=['error', 'keep'], default='error')
    args = parser.parse_args(argv)
    out = Path(args.output)
    # Never overwrite a source/manifest or old results implicitly.
    artifacts = [out / 'validation-report.json']
    if args.command != 'validate':
        artifacts += [out / 'graph.json', out / 'statistics.json']
    if any(p.exists() for p in artifacts):
        print('Output artifacts already exist; choose a new output directory.', file=sys.stderr)
        return 2
    try:
        mapping = json.loads(Path(args.column_map).read_text(encoding='utf-8')) if args.column_map else None
        if mapping is not None and (not isinstance(mapping, dict) or
                                   not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items())):
            raise DataError('Column map must be a JSON string-to-string object.')
        data = load_bis(args.input, args.manifest, args.period, mapping,
                        args.missing_policy, args.zero_policy, args.self_loop_policy)
        report = validate_references(data)
        write_json(out / 'validation-report.json', report.to_dict())
        if not report.valid:
            print(f'Validation failed: {out / "validation-report.json"}', file=sys.stderr)
            return 2
        if args.command != 'validate':
            graph = build_graph(data)
            write_json(out / 'graph.json', graph_payload(graph))
            write_json(out / 'statistics.json', statistics(graph))
        print(f'{args.command}: successful; output={out}; synthetic={report.provenance["data_kind"] == "synthetic"}')
        return 0
    except (DataError, OSError, ValueError) as exc:
        write_json(out / 'validation-report.json', dict(valid=False, input=args.input,
            issues=[dict(severity='error', code='input_error', message=str(exc))]))
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
