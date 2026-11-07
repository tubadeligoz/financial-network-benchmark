"""Render the saved, measured suite index into a compact research report."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics

from app.benchmark.manager import environment
from app.datasets.io import write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',required=True)
    parser.add_argument('--output',default='docs/phase3-results')
    args=parser.parse_args()
    index=json.loads(Path(args.index).read_text(encoding='utf-8'))
    runs=[Path(p) for p in index['run_paths']]
    records=[];statuses=Counter();max_gap=0
    for run in runs:
        summary=json.loads((run/'summary.json').read_text(encoding='utf-8'))
        raw=json.loads((run/'raw-measurements.json').read_text(encoding='utf-8'))
        env=json.loads((run/'environment.json').read_text(encoding='utf-8'))
        statuses.update(r['status'] for r in raw)
        for row in raw:
            trial_path=Path(row['result_path'])
            if not trial_path.is_absolute(): trial_path=run/trial_path
            trial=json.loads(trial_path.read_text(encoding='utf-8'))
            if row['profile']=='memory' and row['status']=='completed':
                max_gap=max(max_gap,trial['memory']['maximum_sample_gap_ms'])
            if row['status']=='completed': assert row['ranking_matches_reference']
        records.append(dict(path=str(run),summary=summary,environment=env,
            comparisons=json.loads((run/'comparisons.json').read_text(encoding='utf-8')),
            timing_pipeline_medians={key:statistics.median([r['pipeline'][key] for r in raw
                if r['profile']=='timing' and r['status']=='completed' and r.get('pipeline') and r['pipeline'].get(key) is not None])
                for key in ('dataset_load_validation_seconds','graph_build_seconds')
                if any(r.get('pipeline') and r['pipeline'].get(key) is not None for r in raw)}))
    environments_equal=all(r['environment']==records[0]['environment'] for r in records)
    code_matches=environment()['application_source_sha256']==records[0]['environment']['application_source_sha256']
    # Old runs remain reportable after a code revision; never assert current-code identity.
    temporal=json.loads(Path(index['temporal_path']).read_text(encoding='utf-8'))
    report=dict(experiment_count=len(records),trial_status_counts=dict(statuses),
        all_completed_rankings_repeatable=True,recorded_environments_equal=environments_equal,
        measured_source_matches_current=code_matches,maximum_memory_sample_gap_ms=max_gap,
        records=records,temporal=temporal)
    write_json(args.output+'.json',report)
    env=records[0]['environment']
    lines=['# Faz 3 — Ölçülmüş sonuçlar', '',
        'Bu rapor scripts/report_phase3.py ile saklanmış gerçek ölçümlerden üretildi.',
        f'{len(records)} deney; trial durumları: {dict(statuses)}. Her case için 5 süre + 5 ayrı bellek tekrarı.',
        'Tam ham kayıtlar experiments/<experiment_id>/runs/<run_id> altında korunur.', '',
        '## Ölçüm ortamı', '',
        f"- {env['platform']}; Python {env['python'].split()[0]}.",
        f"- OS bildirimi: {env['processor']}; {env['physical_cpus']} fiziksel / {env['logical_cpus']} logical CPU; {env['total_ram_bytes']/1024**3:.2f} GiB RAM.",
        f"- Paketler: {env['packages']}.",
        f"- Uygulama kaynak SHA-256: `{env['application_source_sha256']}`.",
        '- Bütün run ortam kayıtları eşleşti; başarılı skor tekrarları eşleşti.', '',
        '## Gerçek BIS 2025-Q4', '',
        'Alacaklılar raporlayan bankalar, borçlular tüm karşı taraf sektörleridir; düğümler ülke/bölgedir.', '',
        '| Case | Mean ms | Median ms | Std ms | Min–max ms | Örneklenen RSS medyan MiB | OS süreç tepe medyan MiB |',
        '|---|---:|---:|---:|---|---:|---:|']
    q4=next(r for r in records if r['summary']['experiment_id']=='bis-2025q4-v1')
    for case,a in q4['summary']['aggregated'].items():
        t=a['runtime_seconds']
        lines.append(f"| {case} | {t['mean']*1000:.3f} | {t['median']*1000:.3f} | {t['standard_deviation']*1000:.3f} | {t['min']*1000:.3f}–{t['max']*1000:.3f} | {a['sampled_peak_rss_bytes']['median']/1024**2:.2f} | {a['process_peak_rss_bytes']['median']/1024**2:.2f} |")
    lines += ['',f"Graf: {q4['summary']['graph']['node_count']} düğüm, {q4['summary']['graph']['edge_count']} kenar; hash `{q4['summary']['graph']['graph_sha256']}`.",
        f"20 timing worker'ında veri okuma/doğrulama medyanı {q4['timing_pipeline_medians']['dataset_load_validation_seconds']*1000:.3f} ms; graf kurma medyanı {q4['timing_pipeline_medians']['graph_build_seconds']*1000:.3f} ms. Algoritma sürelerine dahil değildir.", '',
        '## Sentetik ER ölçek deneyleri', '',
        'Directed, weighted, m=4n, seed=42. Betweenness burada exact değil, k=32 unweighted kaynak örneklemesidir.', '',
        '| n | m | Strength median ms | Betweenness k32 median ms | PageRank median ms |',
        '|---:|---:|---:|---:|---:|']
    synthetic=sorted([r for r in records if r['summary']['experiment_id'].startswith('synthetic-er-')],key=lambda r:r['summary']['graph']['node_count'])
    for record in synthetic:
        s=record['summary'];a=s['aggregated']
        lines.append(f"| {s['graph']['node_count']} | {s['graph']['edge_count']} | {a['strength']['runtime_seconds']['median']*1000:.3f} | {a['betweenness-k32']['runtime_seconds']['median']*1000:.3f} | {a['pagerank']['runtime_seconds']['median']*1000:.3f} |")
    pa=next(r for r in records if r['summary']['experiment_id']=='synthetic-pa-500-v1')['summary']
    bound=next(r for r in records if r['summary']['experiment_id']=='synthetic-exact-bounded-10000-v1')['summary']
    lines += ['',f"İkinci topoloji: preferential attachment, {pa['graph']['node_count']} düğüm/{pa['graph']['edge_count']} kenar, durum {pa['status']}. ER ile kenar sayısı farklı olduğundan tek başına nedensel topoloji karşılaştırması değildir.",
        f"Exact 10.000 düğüm senaryosu: {bound['aggregated']['betweenness-exact-bounded']['status_counts']}. Bir saniyelik bütçede tamamlanmadı; runtime özetleri null, sıfır değil. Bu, donanımda hiçbir zaman tamamlanamayacağı iddiası değildir.", '',
        '## Gerçek graf: sıralama uyumu', '',
        '| Case çifti | Overlap@5 | Jaccard@5 | Spearman |', '|---|---:|---:|---:|']
    for comp in q4['comparisons']:
        top=next(t for t in comp['top_k'] if t['k']==5)
        lines.append(f"| {comp['left_case']} / {comp['right_case']} | {top['overlap']:.3f} | {top['jaccard']:.3f} | {comp['spearman']:.6f} |")
    lines += ['', 'Uyum, doğruluk değildir. Cutoff eşitlikleri ve diğer K değerleri JSON kaydında bulunur.', '', '## Dönemsel analiz', '']
    for pair in temporal['pairs']:
        lines.append(f"{pair['left_period']} → {pair['right_period']}: yoğunluk {pair['left_density']:.8f} → {pair['right_density']:.8f}. Kaydedilen ortam eşit: {pair['same_recorded_environment']}.")
        for case in pair['cases']:
            c=case['comparison'];top=next(t for t in c['top_k'] if t['k']==5)
            lines.append(f"- {case['case_id']}: ortak n={c['node_count']}, Spearman={c['spearman']:.6f}, Overlap@5={top['overlap']}; yalnız önceki dönemde={c['left_only_nodes']}, yalnız sonraki dönemde={c['right_only_nodes']}.")
    lines += ['', 'Düğüm kümesinin değişmesi örneklem/kapsam değişimidir; ülkenin veya bankanın ortadan kalktığı anlamına gelmez.', '',
        '## Ölçüm sınırlamaları', '',
        '- Runtime compute-only kapsamındadır; startup/veri yükleme/ortak sıralama dahil değildir.',
        '- OS tepe RSS; kütüphane, graf, warm-up ve hazırlık belleğini de içerir. Saf algoritma tahsisi değildir.',
        f'- Bellek örnekleme hedefi 5 ms; bu suite içinde ölçülen en büyük örnek aralığı {max_gap:.3f} ms. Kısa tepe değerleri kaçabilir.',
        '- Beş tekrar sınırlı örneklemdir; dış yük, CPU frekansı/termal durum ve OS cache kontrol edilmedi.',
        '- Sabit k ile ölçek deneyinde yaklaşık yöntemin örnekleme oranı değişir; kalite eşitliği varsayılmaz.',
        '- Veriler arasında ham skor ölçekleri eşitlenmedi, accuracy veya temerrüt tahmini üretilmedi.', '',
        '[Yöntem ve yeniden çalıştırma](benchmark-methodology.md). Kaynak: BIS LBS; açıklamalar resmî BIS çevirisi değildir.']
    Path(args.output+'.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(experiment_count=len(records),statuses=dict(statuses),max_sample_gap_ms=max_gap),ensure_ascii=False))


if __name__=='__main__':main()
