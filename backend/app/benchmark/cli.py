import argparse
import json
import sys
from pathlib import Path

from app.benchmark.manager import run_experiment, temporal_analysis


def main(argv=None):
    parser=argparse.ArgumentParser(description='Reproducible isolated-process financial graph experiments.')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run')
    run.add_argument('--config',required=True)
    run.add_argument('--storage',default='experiments')
    temporal=sub.add_parser('temporal')
    temporal.add_argument('--runs',nargs='+',required=True)
    temporal.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='run':
            config=json.loads(Path(args.config).read_text(encoding='utf-8'))
            path=run_experiment(config,args.storage,progress=lambda x:print(x,flush=True))
            print(f'Results: {path}')
            return 0 if json.loads((path/'summary.json').read_text(encoding='utf-8'))['status']=='completed' else 2
        else:
            temporal_analysis(args.runs,args.output)
            print(f'Temporal results: {args.output}')
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'Experiment error: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__': sys.exit(main())
