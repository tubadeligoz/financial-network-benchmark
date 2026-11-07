"""Independent arithmetic oracles on explicitly fictional banks, not BIS risk estimates."""
import copy
import json
import math

import networkx as nx
import pytest

from app.algorithms import AlgorithmEngine
from app.algorithms.engine import fingerprint
from app.benchmark.comparison import compare_rankings
from app.benchmark.manager import run_experiment
from app.datasets.financial import load_synthetic_banks, validate_financial_graph


def bank_graph(edges, equities, period='synthetic-oracle'):
    g=nx.DiGraph(period=period,direction='creditor_to_debtor',exposure_unit='synthetic units',
        creditor_scope='synthetic_banks',debtor_scope='synthetic_banks',coverage='complete fictional network',
        financial_model={'capital_definition':'synthetic book equity','calibration':'none'},
        provenance={'dataset_id':'synthetic-oracle','source_version':'1','data_kind':'synthetic'})
    for n in equities:
        g.add_node(n,entity_type='synthetic_bank',period=period)
    for u,v,w in edges:g.add_edge(u,v,exposure=w,exposure_unit='synthetic units',period=period)
    for n,equity in equities.items():
        outgoing=sum(a['exposure'] for _,_,a in g.out_edges(n,data=True))
        incoming=sum(a['exposure'] for _,_,a in g.in_edges(n,data=True))
        g.nodes[n]['available_financial_features']=dict(equity=equity,external_assets=1000,
            external_liabilities=1000+outgoing-incoming-equity,unit='synthetic units')
    g.graph['graph_sha256']=fingerprint(g)
    return g


def calculate(g,**params):
    r=AlgorithmEngine().run('debtrank',g,params)
    assert r.status=='completed',r.error
    return r


def test_direction_and_exact_two_bank_arithmetic():
    g=bank_graph([('A','B',20)],{'A':100,'B':100})
    r=calculate(g,initial_shocks={'B':.5}).metadata['scenario']
    assert r['final_distress']=={'A':.1,'B':.5}
    assert r['aggregate_initial_distress']==0
    assert r['debtrank_score']==pytest.approx(.1)
    assert r['history'][1]['transmissions'][0]['source']=='B'
    assert r['history'][1]['transmissions'][0]['target']=='A'
    assert calculate(g,initial_shocks={'A':.5}).metadata['scenario']['final_distress']['B']==0


def test_chain_simultaneous_update_and_disconnected_bank():
    g=bank_graph([('A','B',20),('B','C',40)],dict(A=100,B=80,C=60,Z=40))
    s=calculate(g,initial_shocks={'C':.5}).metadata['scenario']
    assert s['history'][1]['distress']['A']==0
    assert s['history'][1]['distress']['B']==.25
    assert s['final_distress']['A']==.05 and s['final_distress']['Z']==0
    assert s['steps']==3 and s['stopping_reason']=='no_distressed_nodes'
    assert s['debtrank_score']==pytest.approx(11/60)


def test_cycle_inactive_receives_but_does_not_retransmit():
    g=bank_graph([('A','B',50),('B','A',50)],dict(A=100,B=100))
    s=calculate(g,initial_shocks={'A':.5}).metadata['scenario']
    assert s['final_distress']=={'A':.625,'B':.25}
    assert s['steps']==2
    assert [h['states']['A'] for h in s['history']]==['D','I','I']
    assert s['debtrank_score']==pytest.approx(.1875)


def test_simultaneous_shocks_clipping_and_no_shock():
    g=bank_graph([('A','B',100),('A','C',100)],dict(A=20,B=100,C=100))
    s=calculate(g,initial_shocks={'B':.8,'C':.8}).metadata['scenario']
    assert s['final_distress']['A']==1 and s['debtrank_score']==1
    zero=calculate(g).metadata['scenario']
    assert zero['steps']==0 and all(v==0 for v in zero['final_distress'].values())
    assert zero['debtrank_score']==0


@pytest.mark.parametrize('magnitude',[0,.01,.1,.5,1])
def test_bounds_repeatability_and_readonly_input(magnitude):
    g=load_synthetic_banks('synthetic-T0');before=copy.deepcopy(g)
    a=calculate(g,initial_shocks={'SYN-BANK-C':magnitude})
    b=calculate(g,initial_shocks={'SYN-BANK-C':magnitude})
    assert a.to_dict()==b.to_dict()
    s=a.metadata['scenario']
    assert 0<=s['debtrank_score']<=1-s['aggregate_initial_distress']+1e-12
    assert all(0<=h<=1 for h in s['final_distress'].values())
    assert s['steps']<=len(g)
    assert nx.utils.graphs_equal(g,before)


@pytest.mark.parametrize('invalid',[None,0,-1,float('nan'),True])
def test_invalid_capital(invalid):
    g=load_synthetic_banks('synthetic-T0');g.nodes['SYN-BANK-A']['available_financial_features']['equity']=invalid
    g.graph['graph_sha256']=fingerprint(g) if not isinstance(invalid,float) or math.isfinite(invalid) else 'invalid'
    with pytest.raises(ValueError):validate_financial_graph(g)


def test_missing_scope_units_balance_sheet_and_empty():
    g=load_synthetic_banks('synthetic-T0');g.graph['debtor_scope']='all_sectors'
    assert 'incompatible_entity_scope' in AlgorithmEngine().run('debtrank',g).error['message'] or AlgorithmEngine().run('debtrank',g).status=='invalid_graph'
    for change in ('missing','unit','balance'):
        g=load_synthetic_banks('synthetic-T0');f=g.nodes['SYN-BANK-A']['available_financial_features']
        if change=='missing': f.pop('equity')
        elif change=='unit': f['unit']='USD'
        else: f['external_assets']+=1
        with pytest.raises(ValueError):validate_financial_graph(g)
    with pytest.raises(ValueError):validate_financial_graph(nx.DiGraph())
    with pytest.raises(ValueError):validate_financial_graph(bank_graph([],{'A':100}))


@pytest.mark.parametrize('params',[{'initial_shocks':{'missing':.5}},{'initial_shocks':{'SYN-BANK-A':-1}},
    {'initial_shocks':{'SYN-BANK-A':True}},{'initial_shocks':{'SYN-BANK-A':1.1}},
    {'mode':'impact_ranking','initial_shocks':{'SYN-BANK-A':.1}}, {'shock_magnitude':.5}])
def test_invalid_shocks(params):
    assert AlgorithmEngine().run('debtrank',load_synthetic_banks('synthetic-T0'),params).status=='invalid_parameters'


def test_ranking_separates_seed_impact_and_received_distress_and_periods():
    g=load_synthetic_banks('synthetic-T0')
    rank=calculate(g,mode='impact_ranking',shock_magnitude=.5)
    for row in rank.scores:
        oracle=calculate(g,initial_shocks={row['node_id']:.5}).metadata['scenario']
        assert row['score']==oracle['debtrank_score']
    other=calculate(load_synthetic_banks('synthetic-T1'),initial_shocks={'SYN-BANK-C':.5})
    assert other.metadata['scenario']['debtrank_score']!=rank.metadata['seed_scenarios']['SYN-BANK-C']['debtrank_score']
    with pytest.raises(ValueError,match='Different objectives'):
        compare_rankings(rank.to_dict(),AlgorithmEngine().run('pagerank',g).to_dict())
    with pytest.raises(ValueError,match='same model version'):
        compare_rankings(rank.to_dict(),calculate(g).to_dict())


def test_actual_risk_benchmark_excludes_centrality_comparison(tmp_path):
    config=dict(experiment_id='synthetic-risk-benchmark',source=dict(kind='synthetic_financial',period='synthetic-T0'),
        algorithms=[dict(case_id='risk',algorithm_id='debtrank',parameters={'mode':'impact_ranking'}),
                    dict(case_id='centrality',algorithm_id='strength',parameters={})],
        repeat_count=5,warmup_count=0,measurement={'memory_repeats':5})
    run=run_experiment(config,tmp_path)
    summary=json.loads((run/'summary.json').read_text())
    assert summary['status']=='completed'
    assert len(summary['comparison_exclusions'])==1
    assert json.loads((run/'comparisons.json').read_text())==[]
    risk=json.loads((run/'rankings/risk.json').read_text())
    assert risk['experiment_id']==config['experiment_id']
    assert risk['metadata']['analysis_objective']=='seed_systemic_impact'
    assert summary['aggregated']['risk']['timing_successes']==5
    assert summary['aggregated']['risk']['memory_successes']==5
