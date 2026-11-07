import hashlib
import json
from pathlib import Path
import re
import sys

from app.algorithms import AlgorithmEngine
from app.benchmark.manager import run_experiment
from app.benchmark.source import load_source
from app.datasets.io import write_json
from app.api.stress import run_stress_suite


def main():
    request=Path(sys.argv[1]);job=json.loads(request.read_text(encoding='utf-8'))
    folder=request.parent;root=Path(job['root']);p=job['payload']
    def progress(message):
        match=re.search(r' (\d+)/(\d+) ',message)
        write_json(folder/'progress.json',dict(message=message,
            completed=int(match[1]) if match else None,total=int(match[2]) if match else None))
    try:
        if job['kind']=='algorithm':
            progress('Loading and validating selected graph')
            graph,_,_=load_source(p['source'])
            if graph.graph['graph_sha256']!=p['expected_graph_sha256']:
                raise ValueError('Source changed since submission. Restart the API and select the validated graph again.')
            progress('Computing '+p['algorithm_id'])
            result=AlgorithmEngine().run(p['algorithm_id'],graph,p['parameters']).to_dict()
            result['experiment_id']='analysis-'+folder.name
            if result['status']=='completed':
                key=hashlib.sha256(json.dumps(result['parameters'],sort_keys=True).encode()).hexdigest()[:12]
                write_json(root/'data/processed/web/analyses'/result['graph_sha256']/(p['algorithm_id']+'-'+key+'.json'),result)
            output=dict(status='completed' if result['status']=='completed' else 'failed',analysis=result,error=result['error'])
        elif job['kind']=='stress':
            suite=run_stress_suite(root,p,progress)
            output=dict(status='completed',stress_experiment_id=suite['id'],error=None)
        else:
            progress('Preparing benchmark experiment')
            run=run_experiment(p['config'],root/'experiments',progress=progress)
            summary=json.loads((run/'summary.json').read_text(encoding='utf-8'))
            opaque=hashlib.sha256(str(run.relative_to(root)).encode()).hexdigest()[:20]
            output=dict(status='completed' if summary['status']=='completed' else 'failed',
                        experiment_id=opaque,run_id=summary['run_id'],summary=summary,
                        error=None if summary['status']=='completed' else 'Experiment finished with failed trials; inspect results.')
    except Exception as exc: output=dict(status='failed',error=str(exc))
    write_json(folder/'result.json',output)
    return 0 if output['status']=='completed' else 2


if __name__=='__main__':sys.exit(main())
