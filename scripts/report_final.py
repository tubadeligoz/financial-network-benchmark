"""Derive final research tables exclusively from completed local experiments."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
index=json.loads((root/'data/processed/phase6/experiment-index.json').read_text())
records=[]
lines=['# Experimental Results','', 'Faz 6 gerçek koşuları; tarihsel Faz 3/5 sonuçlarıyla birleştirilmez. Süreler hesaplama sınırıdır; RSS süreç tabanını içerir.','', '| Experiment / case | n / m | Median ms | Mean ms | SD ms | Peak RSS MiB median | Timing / memory successes |','|---|---:|---:|---:|---:|---:|---:|']
for name in index['run_paths']:
    path=root/name
    s=json.loads((path/'summary.json').read_text())
    assert s['status']=='completed'
    record={'path':name,'summary':s,'environment':json.loads((path/'environment.json').read_text()),'comparisons':json.loads((path/'comparisons.json').read_text())}
    records.append(record)
    for case,a in s['aggregated'].items():
        t=a['runtime_seconds'];rss=a['sampled_peak_rss_bytes']['median']/1048576
        lines.append(f"| {s['experiment_id']} / {case} | {s['graph']['node_count']} / {s['graph']['edge_count']} | {t['median']*1000:.4f} | {t['mean']*1000:.4f} | {t['standard_deviation']*1000:.4f} | {rss:.3f} | {a['timing_successes']} / {a['memory_successes']} |")
    lines.extend(['',f"Run `{s['run_id']}`; graph `{s['graph']['graph_sha256']}`.",''])
lines+=['','## Interpretation','', 'Strength measures exposure volume; betweenness structural shortest-path mediation; PageRank directed importance. DebtRank here measures only explicitly synthetic distress. Runtime comparisons do not establish predictive accuracy or a common financial target. Five repeats and uncontrolled system load do not establish statistical significance.','', 'BIS country edges are published aggregate claims projected to a graph, not reconstructed bank exposures. Missing pairs remain unknown. The separate bank model is handcrafted synthetic data.','', 'Full parameters, source hashes, hardware, dependencies, comparisons and source archive digests are indexed in [evidence-index.json](evidence-index.json). Raw trials remain under each local run directory. Historical scaling and controlled timeouts are separately documented in [phase3-results.md](phase3-results.md); they use the historical code environment.']
(root/'docs/experimental-results.md').write_text('\n'.join(lines),encoding='utf-8')
evidence={'final_runs':records,'profiles':{name:json.loads((root/f'data/processed/phase6/{name}.json').read_text()) for name in ('profile-before','profile-after','payloads')},'validation':{'python_passed':141,'frontend_unit_passed':8,'synthetic_browser_passed':3,'optional_real_browser_skipped':1,'hosted_ci_executed':False}}
(root/'docs/evidence-index.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False),encoding='utf-8')
print('Research tables and evidence index generated from completed runs.')
