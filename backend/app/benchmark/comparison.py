import math
import warnings

from scipy.stats import spearmanr


def score_map(result):
    if result.get('status') != 'completed': raise ValueError('Only completed rankings can be compared.')
    values = {}
    for row in result['scores']:
        if row['node_id'] in values or not math.isfinite(row['score']):
            raise ValueError('Duplicate node or nonfinite score.')
        values[row['node_id']] = row['score']
    return values


def compare_rankings(left, right, top_k=(5,10,20), *, temporal=False):
    reason = comparison_exclusion(left, right)
    if reason: raise ValueError(reason)
    a, b = score_map(left), score_map(right)
    if not temporal and (set(a) != set(b) or left['graph_sha256'] != right['graph_sha256']):
        raise ValueError('Algorithm comparison requires the same graph and node universe.')
    if temporal and (left['algorithm_id'] != right['algorithm_id'] or
                     left['algorithm_version'] != right['algorithm_version'] or left['parameters'] != right['parameters']):
        raise ValueError('Temporal comparison requires the same algorithm/version/parameters.')
    nodes = sorted(set(a) & set(b))
    constant = len(nodes) < 2 or len({a[n] for n in nodes}) <= 1 or len({b[n] for n in nodes}) <= 1
    rho = None
    if not constant:
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            rho = float(spearmanr([a[n] for n in nodes], [b[n] for n in nodes]).statistic)
    rows = []
    for k in top_k:
        if type(k) is not int or k < 1: raise ValueError('K must be a positive integer.')
        entry = dict(k=k, overlap=None, jaccard=None, common_nodes=[])
        if k >= len(nodes) or constant:
            entry['undefined_reason'] = 'constant_scores_or_too_few_nodes' if constant else 'k_not_smaller_than_universe'
        else:
            ordered_a, ordered_b = [sorted(nodes,key=lambda n:(-m[n],n)) for m in (a,b)]
            sa, sb = set(ordered_a[:k]), set(ordered_b[:k])
            entry.update(overlap=len(sa&sb)/k, jaccard=len(sa&sb)/len(sa|sb),
                common_nodes=sorted(sa&sb),
                left_cutoff_tie=a[ordered_a[k-1]] == a[ordered_a[k]],
                right_cutoff_tie=b[ordered_b[k-1]] == b[ordered_b[k]])
        rows.append(entry)
    return dict(universe='intersection' if temporal else 'identical', node_count=len(nodes),
        left_only_nodes=sorted(set(a)-set(b)), right_only_nodes=sorted(set(b)-set(a)),
        spearman=rho, spearman_undefined_reason='constant_scores_or_too_few_nodes' if constant else None,
        top_k=rows, interpretation='ranking agreement, not accuracy; missing nodes never filled with zero')


def comparison_exclusion(left, right):
    """Financial scenario objectives cannot be silently mixed with centrality."""
    if 'debtrank' not in (left.get('algorithm_id'),right.get('algorithm_id')): return None
    if left.get('algorithm_id') != right.get('algorithm_id'):
        return 'Different objectives: financial distress/impact and structural centrality are not comparable.'
    if any(left.get(k)!=right.get(k) for k in ('algorithm_version','parameters')):
        return 'DebtRank comparison requires the same model version and shock configuration.'
    if left.get('metadata',{}).get('model_id') != right.get('metadata',{}).get('model_id'):
        return 'Different financial model definitions.'
    return None
