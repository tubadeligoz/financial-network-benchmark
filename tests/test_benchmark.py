"""Synthetic fixtures only. Reported benchmark artifacts are produced by actual workers."""
import json
from pathlib import Path

import pytest

from app.benchmark.comparison import compare_rankings
from app.benchmark.config import validate_config
from app.benchmark.manager import run_experiment, run_trial, summarize, temporal_analysis
from app.benchmark.source import load_source, identity
from app.benchmark.synthetic import generate_synthetic


def config():
    return dict(experiment_id='test-experiment',
        source=dict(kind='synthetic',generator=dict(node_count=10,edge_count=20,seed=17)),
        algorithms=[dict(case_id='strength',algorithm_id='strength',parameters={})],
        repeat_count=5,warmup_count=0,random_seed=17,
        timeout=dict(trial_seconds=30,algorithm_seconds=10))


def ranking(values, graph_hash='same'):
    return dict(status='completed',scores=[dict(node_id=n,score=s) for n,s in values.items()],
        graph_sha256=graph_hash,algorithm_id='test',algorithm_version='v1',parameters={})


def test_overlap_jaccard_and_spearman_oracles():
    a=ranking(dict(a=4,b=3,c=2,d=1))
    b=ranking(dict(a=1,b=4,c=3,d=2))
    result=compare_rankings(a,b,[2])
    assert result['top_k'][0]['overlap']==.5
    assert result['top_k'][0]['jaccard']==pytest.approx(1/3)
    assert result['spearman']==pytest.approx(-.2)
    reverse=compare_rankings(a,ranking(dict(a=1,b=2,c=3,d=4)),[1])
    assert reverse['spearman']==pytest.approx(-1)


def test_average_ties_and_constant_scores():
    a=ranking(dict(a=3,b=3,c=1,d=0))
    b=ranking(dict(a=3,b=2,c=2,d=0))
    result=compare_rankings(a,b,[1,4])
    assert result['spearman']==pytest.approx(5/6)
    assert result['top_k'][0]['left_cutoff_tie']
    assert result['top_k'][1]['overlap'] is None
    constant=compare_rankings(a,ranking(dict(a=1,b=1,c=1,d=1)),[1])
    assert constant['spearman'] is None and constant['top_k'][0]['overlap'] is None


def test_node_universe_and_temporal_entry_exit():
    a=ranking(dict(a=4,b=3,c=2,d=1))
    b=ranking(dict(a=1,b=4,c=3,e=2),'other')
    with pytest.raises(ValueError): compare_rankings(a,b,[1])
    result=compare_rankings(a,b,[1],temporal=True)
    assert result['node_count']==3
    assert result['left_only_nodes']==['d'] and result['right_only_nodes']==['e']
    assert result['spearman']==pytest.approx(-.5)


@pytest.mark.parametrize('model', ['erdos_renyi','preferential_attachment'])
@pytest.mark.parametrize('directed', [True,False])
@pytest.mark.parametrize('weighted', [True,False])
def test_synthetic_repeatability(model,directed,weighted):
    p=dict(node_count=50,model=model,directed=directed,weighted=weighted,seed=71)
    a,b=generate_synthetic(p),generate_synthetic(p)
    assert a.graph==b.graph
    assert sorted(a.edges(data=True))==sorted(b.edges(data=True))
    assert a.is_directed()==directed and len(a)==50
    assert a.graph['provenance']['data_kind']=='synthetic'
    if not weighted: assert all(d['exposure']==1 for _,_,d in a.edges(data=True))


def test_synthetic_density_and_bounds():
    graph=generate_synthetic(dict(node_count=10,density=.2,seed=42))
    assert graph.number_of_edges()==18
    for p in (dict(node_count=10,edge_count=100),dict(node_count=10000,density=1),
              dict(node_count=10,edge_count=2,density=.1),dict(node_count=10,model='unknown')):
        with pytest.raises(ValueError): generate_synthetic(p)


def test_config_and_summary_validation():
    c=validate_config(config())
    assert c['measurement']['memory_repeats']==5
    for key,value in [('repeat_count',4),('random_seed',True),('warmup_count',-1),('experiment_id','../escape')]:
        bad=config();bad[key]=value
        with pytest.raises(ValueError): validate_config(bad)
    bad=config();bad['measurement']=dict(memory_repeats=4)
    with pytest.raises(ValueError): validate_config(bad)
    assert summarize([1,2,3,None])==dict(count=3,mean=2,median=2,standard_deviation=1,min=1,max=3)
    assert summarize([])['mean'] is None


def job(profile='timing'):
    c=validate_config(config());g,_,_=load_source(c['source'])
    return dict(config=c,identity=identity(g),case=c['algorithms'][0],profile=profile,repeat_index=0)


def test_actual_trial_separates_measurements_and_handles_failure(tmp_path):
    value=run_trial(job(),tmp_path/'actual')
    assert value['status']=='completed',value.get('error')
    assert value['runtime_seconds']>0
    assert value['engine_elapsed_seconds']>=value['runtime_seconds']
    assert value['pipeline']['synthetic_generation_seconds']>0
    assert value['memory']['baseline_rss_bytes']>0
    assert value['memory']['sampled_peak_rss_bytes'] is None
    bad=job();bad['case']=dict(case_id='failure',algorithm_id='unknown',parameters={})
    value=run_trial(bad,tmp_path/'failure')
    assert value['status']=='invalid_parameters' and value['runtime_seconds'] is None
    bad=job();bad['case']=dict(case_id='nonconverged',algorithm_id='pagerank',
                             parameters=dict(max_iterations=1,tolerance=1e-15))
    value=run_trial(bad,tmp_path/'nonconverged')
    assert value['status']=='nonconverged' and value['runtime_seconds'] is None


def test_actual_timeout_and_resource_limit(tmp_path):
    j=job();j['config']['timeout']['trial_seconds']=.001
    value=run_trial(j,tmp_path/'timeout')
    assert value['status']=='timeout' and value['runtime_seconds'] is None
    assert value['trial_wall_seconds']>0
    j=job();j['config']['measurement']['rss_limit_mb']=.00001
    value=run_trial(j,tmp_path/'limit')
    assert value['status']=='resource_limit' and value['runtime_seconds'] is None


def test_real_worker_memory_measurement(tmp_path):
    value=run_trial(job('memory'),tmp_path/'memory')
    assert value['status']=='completed',value.get('error')
    m=value['memory']
    assert m['sampled_peak_rss_bytes']>=m['baseline_rss_bytes']>0
    assert m['sample_count']>=2
    assert m['process_peak_rss_bytes'] is None or m['process_peak_rss_bytes']>0


def test_experiment_rerun_counts_storage_and_identity(tmp_path):
    first=run_experiment(config(),tmp_path)
    second=run_experiment(config(),tmp_path)
    assert first!=second
    for run in (first,second):
        summary=json.loads((run/'summary.json').read_text())
        assert summary['status']=='completed'
        assert summary['raw_trial_count']==10
        aggregate=summary['aggregated']['strength']
        assert aggregate['timing_successes']==5 and aggregate['memory_successes']==5
        assert aggregate['runtime_seconds']['count']==5
        raw=json.loads((run/'raw-measurements.json').read_text())
        assert len(raw)==10 and all(r['ranking_matches_reference'] for r in raw)
        assert all((run/r['result_path']).exists() for r in raw)
        assert all(not Path(r['result_path']).is_absolute() for r in raw)
        env=json.loads((run/'environment.json').read_text())
        assert env['application_source_sha256'] and env['packages']['psutil']
        assert env['dependency_versions']['fastapi']
        import zipfile
        with zipfile.ZipFile(run/env['source_archive']['path']) as archive:
            assert 'backend/app/datasets/synthetic_banks.json' in archive.namelist()
            assert all('data/raw/' not in name and '.env' not in name for name in archive.namelist())
        assert summary['graph']['data_kind']=='synthetic'
    a=json.loads((first/'rankings/strength.json').read_text())
    b=json.loads((second/'rankings/strength.json').read_text())
    assert a['scores']==b['scores'] and a['graph_sha256']==b['graph_sha256']
    bad=config();bad['source']['generator']['seed']=18
    with pytest.raises(ValueError): run_experiment(bad,tmp_path)
    with pytest.raises(ValueError): temporal_analysis([first,second],tmp_path/'temporal.json')
