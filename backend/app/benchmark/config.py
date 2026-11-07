import copy
import json
import math
from pathlib import Path
import re

from app.algorithms import AlgorithmEngine


def positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and positive.')


def validate_config(config):
    c = copy.deepcopy(config)
    json.dumps(c, allow_nan=False)
    allowed = {'experiment_id', 'source', 'algorithms', 'repeat_count', 'random_seed',
               'warmup_count', 'timeout', 'measurement', 'top_k', 'expected_graph'}
    if set(c)-allowed:
        raise ValueError(f'Unknown config fields: {sorted(set(c)-allowed)}')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', c.get('experiment_id', '')):
        raise ValueError('experiment_id must be a safe 1..80 character identifier.')
    c.setdefault('repeat_count', 5)
    c.setdefault('random_seed', 42)
    c.setdefault('warmup_count', 1)
    if type(c['repeat_count']) is not int or c['repeat_count'] < 5:
        raise ValueError('repeat_count must be at least 5.')
    if type(c['random_seed']) is not int or not 0 <= c['random_seed'] < 2**32:
        raise ValueError('random_seed must be an integer in 0..2**32-1 (PYTHONHASHSEED).')
    if type(c['warmup_count']) is not int or not 0 <= c['warmup_count'] <= 10:
        raise ValueError('warmup_count must be 0..10.')
    c['timeout'] = dict({'trial_seconds':60, 'algorithm_seconds':20}, **c.get('timeout', {}))
    if set(c['timeout']) != {'trial_seconds', 'algorithm_seconds'}:
        raise ValueError('Unknown timeout settings.')
    for key, value in c['timeout'].items(): positive(value, key)
    c['measurement'] = dict({'memory_repeats':5, 'sample_interval_ms':5, 'rss_limit_mb':2048},
                            **c.get('measurement', {}))
    if set(c['measurement']) != {'memory_repeats', 'sample_interval_ms', 'rss_limit_mb'}:
        raise ValueError('Unknown measurement settings.')
    if type(c['measurement']['memory_repeats']) is not int or c['measurement']['memory_repeats'] < 5:
        raise ValueError('memory_repeats must be >=5, separate from timing repeats.')
    for key in ('sample_interval_ms', 'rss_limit_mb'): positive(c['measurement'][key], key)
    c.setdefault('top_k', [5, 10, 20])
    if not isinstance(c['top_k'], list) or any(type(k) is not int or k < 1 for k in c['top_k']):
        raise ValueError('top_k must contain positive integers.')
    if len(c['top_k']) != len(set(c['top_k'])): raise ValueError('Duplicate top_k.')
    source = c['source']
    kinds = {'bis': {'kind','input','manifest','period','missing_policy','zero_policy','self_loop_policy'},
             'snapshot': {'kind','path'}, 'synthetic': {'kind','generator'},
             'synthetic_financial': {'kind','period'}}
    if source.get('kind') not in kinds or set(source)-kinds[source['kind']]:
        raise ValueError('Unknown source kind/fields.')
    for key in ('input','manifest','path'):
        if key in source: source[key] = str(Path(source[key]).resolve())
    algorithms = c['algorithms']
    if not isinstance(algorithms, list) or not algorithms:
        raise ValueError('At least one algorithm case is required.')
    engine = AlgorithmEngine()
    catalog = {x['algorithm_id']: x for x in engine.catalog()}
    seen = set()
    for case in algorithms:
        if set(case)-{'case_id','algorithm_id','parameters'}: raise ValueError('Unknown algorithm case fields.')
        case.setdefault('case_id', case['algorithm_id'])
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', case['case_id']) or case['case_id'] in seen:
            raise ValueError('Algorithm case IDs must be unique safe identifiers.')
        seen.add(case['case_id'])
        if case['algorithm_id'] not in catalog: raise ValueError('Unknown algorithm ID.')
        params = case.setdefault('parameters', {})
        if not isinstance(params, dict): raise ValueError('Algorithm parameters must be an object.')
        if case['algorithm_id'] == 'betweenness': params.setdefault('seed', c['random_seed'])
        # Use algorithm-owned validation; no duplicate benchmark parameter semantics.
        engine.resolve_parameters(case['algorithm_id'],params)
    return c
