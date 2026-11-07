"""Compare full and summary statistics responses without changing graph semantics."""
import argparse
import json
from pathlib import Path
from time import perf_counter

from fastapi.testclient import TestClient
from app.api.main import create_app
from app.benchmark.manager import summarize


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Choose a new evidence path.')
    root=Path(__file__).resolve().parents[1]
    records=[]
    with TestClient(create_app(root)) as client:
        datasets=client.get('/api/v1/datasets').json()
        for dataset in datasets:
            if dataset['id'] not in ('bis-lbs','synthetic-er-1000-v1'):continue
            period=dataset['periods'][-1]['period']
            prefix=f'/api/v1/datasets/{dataset["id"]}/periods/{period}/statistics'
            item={'dataset':dataset['id'],'period':period}
            for mode,suffix in [('full',''),('summary','?summary=true')]:
                samples=[]
                for _ in range(5):
                    start=perf_counter();response=client.get(prefix+suffix);samples.append(perf_counter()-start)
                    response.raise_for_status()
                item[mode]={'bytes':len(response.content),'seconds':samples,'summary':summarize(samples)}
                if mode=='full':full=response.json()
                else:
                    reduced=response.json()
                    assert all(full[k]==reduced[k] for k in ('graph_sha256','density','node_count','edge_count'))
            records.append(item)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'records':records,'scope':'ASGI TestClient; five serial requests; full/summary same graph'},indent=2),encoding='utf-8')
    print('Payload measurements:',records)
