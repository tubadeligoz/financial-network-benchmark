"""API contracts use explicitly synthetic source files, never fabricated observed results."""
import json
from pathlib import Path
import shutil
import time

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.api.jobs import Jobs

ROOT=Path(__file__).resolve().parents[1]
HEADERS={'X-FNB-Client':'local-web'}


@pytest.fixture
def client(tmp_path):
    demo=tmp_path/'data/demo'
    demo.mkdir(parents=True)
    for name in ('manifest.json','observations.csv'):
        shutil.copy(ROOT/'data/demo'/name,demo/name)
    with TestClient(create_app(tmp_path)) as session:
        yield session


def test_catalog_graph_and_node_contract(client):
    source=next(d for d in client.get('/api/v1/datasets').json() if d['id']=='synthetic-demo')
    assert source['data_kind']=='synthetic'
    period=source['periods'][0]
    assert period['node_count']==3
    prefix='/api/v1/datasets/synthetic-demo/periods/2025-Q4'
    view=client.get(prefix+'/graph?limit_nodes=2').json()
    assert view['visible_nodes']==2 and view['total_nodes']==3 and view['filtered']
    assert view['analysis_scope']=='full_validated_graph'
    assert view['graph_sha256']==period['graph_sha256']
    assert all(e['exposure']>0 for e in view['edges'])
    node=client.get(prefix+'/nodes/US').json()
    assert node['node_id']=='US' and node['scores']=={}
    assert node['statistics']['out_strength']>0
    assert client.get(prefix+'/validation').status_code==200
    assert client.get(prefix+'/statistics').json()['node_count']==3
    full=client.get(prefix+'/statistics').json()
    small=client.get(prefix+'/statistics?summary=true').json()
    assert small['graph_sha256']==full['graph_sha256'] and small['node_count']==full['node_count']
    assert 'nodes' not in small and 'sorted_values' not in small['weight_distribution']
    assert small['weight_distribution']['mean']==full['weight_distribution']['mean']
    assert small['statistics_scope']=='summary'
    assert client.get(prefix+'/search?q=US').json()[0]['node_id']=='US'
    assert client.get(prefix+'/graph?limit_nodes=251').status_code==422
    assert client.get(prefix+'/graph?min_exposure=-1').status_code==422
    assert client.get(prefix+'/nodes/missing').status_code==404
    assert client.get('/api/v1/datasets/missing').status_code==404


def test_mutation_guards_and_parameter_validation(client):
    body=dict(dataset='synthetic-demo',period='2025-Q4',algorithm_id='pagerank',parameters={})
    assert client.post('/api/v1/analyses',json=body).status_code==403
    assert client.post('/api/v1/analyses',headers={**HEADERS,'Origin':'https://untrusted.example'},json=body).status_code==403
    body['parameters']={'alpha':2}
    assert client.post('/api/v1/analyses',headers=HEADERS,json=body).status_code==422
    assert client.get('/api/v1/health').json()['uploads_enabled'] is False
    assert client.post('/api/v1/uploads',headers=HEADERS,content=b'x'*65537).status_code==413
    assert client.get('/api/v1/experiments').json()==[]
    assert client.get('/api/v1/experiments/unknown/export').status_code==404
    assert client.post('/api/v1/analyses',headers={**HEADERS,'Content-Length':'invalid'},json=body).status_code==400
    chunks=(chunk for chunk in (b'a'*40000,b'b'*40000))
    assert client.post('/api/v1/analyses',headers=HEADERS,content=chunks).status_code==413


def test_actual_algorithm_job_and_saved_result(client):
    response=client.post('/api/v1/analyses',headers=HEADERS,json=dict(dataset='synthetic-demo',period='2025-Q4',algorithm_id='pagerank',parameters={}))
    assert response.status_code==202
    job=response.json()
    assert job['status']=='queued'
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        job=client.get('/api/v1/jobs/'+job['id']).json()
        if job['status'] not in ('queued','running'): break
        time.sleep(.1)
    assert job['status']=='completed',job
    result=job['result']['analysis']
    assert result['status']=='completed' and len(result['scores'])==3
    assert sum(s['score'] for s in result['scores'])==pytest.approx(1)
    stored=client.get('/api/v1/datasets/synthetic-demo/periods/2025-Q4/analyses').json()
    assert stored['pagerank']['graph_sha256']==result['graph_sha256']


def test_queue_cancel_and_restart(tmp_path):
    jobs=Jobs(tmp_path)
    job=jobs.submit('algorithm',{'synthetic_test':True})
    assert jobs.cancel(job['id'])['status']=='cancelled'
    job=jobs.submit('algorithm',{'synthetic_test':True})
    jobs=Jobs(tmp_path)  # A new process has a new in-memory queue.
    jobs.start()
    try:
        assert jobs.get(job['id'])['status']=='failed'
        assert 'restarted' in jobs.get(job['id'])['error']
    finally: jobs.close()
    saved=json.loads((jobs.folder/job['id']/'status.json').read_text())
    assert saved['status']=='failed'


def test_synthetic_stress_api_and_exports(client):
    prefix='/api/v1/datasets/synthetic-bank-stress/periods/synthetic-T0'
    eligible=client.get(prefix+'/financial-eligibility').json()
    assert eligible['eligible'] and len(eligible['banks'])==5
    assert client.get('/api/v1/datasets/synthetic-demo/periods/2025-Q4/financial-eligibility').json()['eligible'] is False
    body=dict(dataset='synthetic-bank-stress',periods=['synthetic-T0','synthetic-T1'],
        shocked_nodes=['SYN-BANK-B','SYN-BANK-C'],shock_magnitudes=[.1,.5])
    response=client.post('/api/v1/stress-tests',headers=HEADERS,json=body)
    assert response.status_code==202
    jid=response.json()['id'];deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        job=client.get('/api/v1/jobs/'+jid).json()
        if job['status'] not in ('queued','running'):break
        time.sleep(.1)
    assert job['status']=='completed',job
    suite=client.get('/api/v1/stress-experiments?dataset=synthetic-bank-stress').json()[0]
    assert len(suite['scenarios'])==4 and len(suite['impact_rankings'])==4
    assert all(r['experiment_id']==suite['id'] for r in suite['scenarios'])
    assert {r['period'] for r in suite['scenarios']}=={'synthetic-T0','synthetic-T1'}
    assert all(r['metadata']['scenario']['initial_shocks'].keys()=={'SYN-BANK-B','SYN-BANK-C'} for r in suite['scenarios'])
    exported=client.get('/api/v1/stress-experiments/'+suite['id']+'/export?format=json')
    assert exported.json()==suite
    csv=client.get('/api/v1/stress-experiments/'+suite['id']+'/export?format=csv')
    assert 'model_assumptions' in csv.text and 'synthetic-T0' in csv.text
    assert client.get('/api/v1/stress-experiments/missing/export').status_code==404
    body['shock_magnitudes']=[2]
    assert client.post('/api/v1/stress-tests',headers=HEADERS,json=body).status_code==422
    body['shock_magnitudes']=[.5,.5]
    assert client.post('/api/v1/stress-tests',headers=HEADERS,json=body).status_code==422
    invalid=dict(dataset='synthetic-demo',period='2025-Q4',algorithm_id='debtrank',parameters={})
    response=client.post('/api/v1/analyses',headers=HEADERS,json=invalid)
    assert response.status_code==422 and 'incompatible_entity_scope' in response.json()['detail']
