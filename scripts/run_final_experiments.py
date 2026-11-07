"""Rerun existing methods for final validation; retain earlier phase evidence."""
import argparse
import json
from pathlib import Path

from app.benchmark.manager import run_experiment
from app.datasets.io import write_json


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-bis',action='store_true',help='Requires the original local Q4 CSV and manifest.')
    parser.add_argument('--output',type=Path,default=Path('data/processed/phase6/experiment-index.json'))
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Choose a new evidence path.')
    cases=[('synthetic-debtrank.json','final-synthetic-debtrank-v1')]
    if args.include_bis:cases.append(('bis-2025q4.json','final-bis-2025q4-v1'))
    runs=[]
    for filename,eid in cases:
        config=json.loads((Path('configs/benchmarks')/filename).read_text(encoding='utf-8'))
        config['experiment_id']=eid
        runs.append(str(run_experiment(config,progress=lambda msg:print(msg,flush=True)).relative_to(Path.cwd())))
    write_json(args.output,{'run_paths':runs,'note':'Actual final reruns; historical Phase 3/5 measurements remain separate.'})
