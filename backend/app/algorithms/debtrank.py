"""2012 single-pass dynamics with an explicitly synthetic book-equity buffer."""
import hashlib
import json
import math

from app.algorithms.base import Algorithm, AlgorithmSpec, Computation
from app.datasets.financial import finite_number, validate_financial_graph

MODEL_ID = 'debtrank-single-pass-book-equity'
MODEL_VERSION = '1.0.0'


def propagate(graph, shocks, *, keep_history=True):
    """Synchronous U→D→I; inactive nodes can receive but never retransmit distress."""
    nodes = sorted(graph)
    h = {n:float(shocks.get(n,0)) for n in nodes}
    initial = dict(h)
    states = {n:'D' if h[n]>0 else 'U' for n in nodes}
    total = math.fsum(a['exposure'] for _,_,a in graph.edges(data=True))
    values = {n:math.fsum(a['exposure'] for _,_,a in graph.out_edges(n,data=True))/total for n in nodes}
    history = [dict(step=0, distress=dict(h), states=dict(states), transmissions=[])] if keep_history else []
    steps = 0
    while any(s=='D' for s in states.values()):
        transmitting = {n for n in nodes if states[n]=='D'}
        contributions = {n:[] for n in nodes}
        transmissions = []
        for creditor, debtor, edge in sorted(graph.edges(data=True)):
            if debtor not in transmitting: continue
            equity = graph.nodes[creditor]['available_financial_features']['equity']
            impact = min(1.0, edge['exposure']/equity)
            amount = impact*h[debtor]
            if amount>0:
                contributions[creditor].append(amount)
                if keep_history: transmissions.append(dict(source=debtor,target=creditor,
                    exposure_source=creditor,exposure_target=debtor,potential_distress_increment=amount))
        following = {n:min(1.0,h[n]+math.fsum(contributions[n])) for n in nodes}
        states = {n:('I' if states[n] in ('D','I') else 'D' if following[n]>0 else 'U') for n in nodes}
        h = following
        steps += 1
        if keep_history: history.append(dict(step=steps,distress=dict(h),states=dict(states),transmissions=transmissions))
        if steps>len(nodes): raise RuntimeError('Single-pass stopping invariant violated.')
    h0 = math.fsum(values[n]*initial[n] for n in nodes)
    final = math.fsum(values[n]*h[n] for n in nodes)
    return dict(initial_shocks={n:v for n,v in initial.items() if v>0},
        affected_nodes=[n for n in nodes if h[n]>initial[n]], final_distress=h,
        economic_value_weights=values, aggregate_initial_distress=h0, aggregate_distress=final,
        debtrank_score=max(0.0,final-h0), steps=steps, stopping_reason='no_distressed_nodes', history=history)


class DebtRank(Algorithm):
    spec = AlgorithmSpec('debtrank','DebtRank · synthetic single-pass','1.0.0',
        {'mode':'scenario','initial_shocks':{},'shock_magnitude':1.0},
        'bilateral synthetic bank claims and consistent book-equity balance sheets')

    def resolve(self, parameters):
        p = super().resolve(parameters)
        if p['mode'] not in ('scenario','impact_ranking'): raise ValueError('DebtRank mode must be scenario or impact_ranking.')
        if not isinstance(p['initial_shocks'],dict): raise ValueError('initial_shocks must map bank IDs to relative equity distress.')
        for n,v in p['initial_shocks'].items():
            if not isinstance(n,str) or not n: raise ValueError('Shock IDs must be nonempty strings.')
            if finite_number(v,'shock magnitude')>1: raise ValueError('Shock magnitude must be in [0,1].')
        if finite_number(p['shock_magnitude'],'shock_magnitude')>1: raise ValueError('shock_magnitude must be in [0,1].')
        if p['mode']=='impact_ranking' and p['initial_shocks']:
            raise ValueError('impact_ranking uses one seed at a time; initial_shocks must be empty.')
        if p['mode']=='scenario' and p['shock_magnitude']!=1:
            raise ValueError('Scenario magnitudes belong in initial_shocks; shock_magnitude is reserved for impact_ranking.')
        return p

    def validate_graph_parameters(self, graph, parameters):
        validate_financial_graph(graph)
        if set(parameters['initial_shocks'])-set(graph): raise ValueError('Shock node not found in graph.')
        if len(graph)>500: raise ValueError('Synthetic DebtRank v1 is limited to 500 banks.')

    def compute(self, graph, parameters):
        scenario_hash = hashlib.sha256(json.dumps(dict(model_id=MODEL_ID,model_version=MODEL_VERSION,
            graph_sha256=graph.graph['graph_sha256'],parameters=parameters),sort_keys=True).encode()).hexdigest()
        metadata = dict(model_id=MODEL_ID,model_version=MODEL_VERSION,scenario_id=scenario_hash[:16],
            implementation='python synchronous single-pass',
            scenario_sha256=scenario_hash,model_assumptions=dict(graph.graph['financial_model']),
            financial_interpretation='synthetic distress propagation; not default probability or payment clearing',
            loss_direction='debtor_to_creditor',value_weight_definition='share of fictional interbank assets',
            risk_score_interpretation='final node distress' if parameters['mode']=='scenario' else 'single-seed additional aggregate distress',
            analysis_objective='scenario_distress' if parameters['mode']=='scenario' else 'seed_systemic_impact',
            score_scales_comparable_across_algorithms=False)
        if parameters['mode']=='scenario':
            scenario = propagate(graph,parameters['initial_shocks'])
            metadata['scenario'] = scenario
            metrics = {n:dict(initial_distress=parameters['initial_shocks'].get(n,0),
                additional_distress=scenario['final_distress'][n]-parameters['initial_shocks'].get(n,0)) for n in graph}
            return Computation(scenario['final_distress'],metrics,metadata)
        scenarios = {n:propagate(graph,{n:parameters['shock_magnitude']},keep_history=False) for n in sorted(graph)}
        metadata['seed_scenarios'] = scenarios
        return Computation({n:s['debtrank_score'] for n,s in scenarios.items()},
            {n:dict(aggregate_distress=s['aggregate_distress'],initial_aggregate_distress=s['aggregate_initial_distress']) for n,s in scenarios.items()},metadata)
