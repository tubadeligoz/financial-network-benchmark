"""Execute the documented real, temporal and synthetic suite (serial, bounded)."""
import argparse
import copy
import json
from pathlib import Path

from app.benchmark.manager import run_experiment, temporal_analysis
from app.datasets.io import write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--storage',default='experiments')
    parser.add_argument('--sizes',nargs='+',type=int,default=[100,500,1000,5000,10000])
    args=parser.parse_args()
    runs=[]
    base=json.loads(Path('configs/benchmarks/bis-2025q4.json').read_text())
    for quarter in ('2025q3','2025q4'):
        config=copy.deepcopy(base)
        config['experiment_id']=f'bis-{quarter}-v1'
        config['source']['input']=f'data/raw/bis-all-sectors-{quarter}/observations.csv'
        config['source']['manifest']=f'data/raw/bis-all-sectors-{quarter}/manifest.json'
        config['source']['period']='2025-Q'+quarter[-1]
        if quarter=='2025q3': config.pop('expected_graph')
        path=run_experiment(config,args.storage,progress=lambda x:print(x,flush=True))
        runs.append(path)
    temporal=Path(args.storage)/'temporal'/f'{runs[0].name}-{runs[1].name}.json'
    temporal_analysis(runs,temporal)
    synthetic=json.loads(Path('configs/benchmarks/synthetic-100.json').read_text())
    for size in args.sizes:
        config=copy.deepcopy(synthetic)
        config['experiment_id']=f'synthetic-er-{size}-v1'
        config['source']['generator'].update(node_count=size,edge_count=4*size)
        runs.append(run_experiment(config,args.storage,progress=lambda x:print(x,flush=True)))
    config=copy.deepcopy(synthetic)
    config['experiment_id']='synthetic-pa-500-v1'
    config['source']['generator']=dict(node_count=500,attachment_m=2,model='preferential_attachment',seed=42,directed=True,weighted=True)
    runs.append(run_experiment(config,args.storage,progress=lambda x:print(x,flush=True)))
    config=copy.deepcopy(synthetic)
    config['experiment_id']='synthetic-exact-bounded-10000-v1'
    config['source']['generator'].update(node_count=10000,edge_count=40000)
    config['algorithms']=[dict(case_id='betweenness-exact-bounded',algorithm_id='betweenness',parameters={})]
    config['warmup_count']=0
    config['timeout']['algorithm_seconds']=1
    runs.append(run_experiment(config,args.storage,progress=lambda x:print(x,flush=True)))
    # A compact index, not hand-entered measurements.
    index=dict(run_paths=[str(p) for p in runs],temporal_path=str(temporal.resolve()),
        summaries=[json.loads((p/'summary.json').read_text()) for p in runs])
    write_json(Path(args.storage)/f'suite-index-{runs[0].name}.json',index)
    print('Suite complete.',flush=True)


if __name__=='__main__': main()
