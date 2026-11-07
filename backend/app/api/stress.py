"""Persisted, explicitly synthetic scenario experiments, independent of BIS."""
import uuid

from app.algorithms import AlgorithmEngine
from app.benchmark.source import load_source
from app.datasets.io import write_json


def run_stress_suite(root, payload, progress):
    eid='stress-'+uuid.uuid4().hex
    suite=dict(id=eid,experiment_id=eid,dataset_key=payload['dataset'],status='running',
        data_kind='synthetic',label='SYNTHETIC — NOT CALIBRATED TO BIS',scenarios=[],impact_rankings=[])
    engine=AlgorithmEngine()
    total=len(payload['sources'])*len(payload['shock_magnitudes'])*2
    completed=0
    for source in payload['sources']:
        graph,_,_=load_source(source['source'])
        if graph.graph['graph_sha256']!=source['graph_sha256']: raise ValueError('Graph changed since stress submission.')
        for magnitude in payload['shock_magnitudes']:
            for mode in ('scenario','impact_ranking'):
                params=dict(mode=mode,initial_shocks={n:magnitude for n in payload['shocked_nodes']}) if mode=='scenario' else dict(mode=mode,shock_magnitude=magnitude)
                result=engine.run('debtrank',graph,params)
                result.experiment_id=eid
                if result.status!='completed': raise ValueError(result.error['message'])
                suite['scenarios' if mode=='scenario' else 'impact_rankings'].append(result.to_dict())
                completed+=1
                progress(f'Synthetic stress {completed}/{total} {graph.graph["period"]} {mode}')
    suite['status']='completed'
    write_json(root/'data/processed/web/stress'/f'{eid}.json',suite)
    return suite
