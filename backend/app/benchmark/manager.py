import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version, distributions
from itertools import combinations
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
import uuid

import psutil

from app.benchmark.config import validate_config
from app.benchmark.comparison import compare_rankings, comparison_exclusion
from app.benchmark.source import load_source, identity
from app.datasets.io import write_json
from app.benchmark.storage import archive_source

THREAD_LIMITS = {k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
                                'VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')}


def environment():
    code = hashlib.sha256()
    app = Path(__file__).resolve().parents[1]
    for path in sorted(p for p in app.rglob('*') if p.suffix in ('.py','.json')):
        code.update(str(path.relative_to(app)).replace('\\','/').encode())
        code.update(path.read_bytes())
    return dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
        processor=platform.processor(), machine=platform.machine(),
        logical_cpus=psutil.cpu_count(), physical_cpus=psutil.cpu_count(logical=False),
        total_ram_bytes=psutil.virtual_memory().total,
        packages={p:version(p) for p in ('networkx','numpy','pandas','scipy','psutil','pyarrow')},
        application_source_sha256=code.hexdigest(), benchmark_version='1.1.0',
        dependency_versions={d.metadata['Name']:d.version for d in distributions() if d.metadata['Name']},
        clock=time.get_clock_info('perf_counter').__dict__, worker_thread_limits=THREAD_LIMITS,
        measurement_notes=['One trial per fresh process; serial scheduling.',
            'Timing and memory series are separate; OS caches and other system load are not controlled.',
            'CPU frequency/power policy/thermal state are not locked. No hardware affinity is forced.'])


def summarize(values):
    values = [v for v in values if v is not None]
    return dict(count=len(values), mean=statistics.mean(values) if values else None,
        median=statistics.median(values) if values else None,
        standard_deviation=statistics.stdev(values) if len(values)>1 else None,
        min=min(values) if values else None, max=max(values) if values else None)


def stop_process_tree(process):
    try:
        root = psutil.Process(process.pid)
        children = root.children(recursive=True)
        for child in children:
            try: child.kill()
            except psutil.NoSuchProcess: pass
        root.kill()
        psutil.wait_procs(children, timeout=3)
    except psutil.NoSuchProcess: pass
    process.wait(timeout=5)


def run_trial(job, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    job = dict(job, phase_path=str(folder/'phase.json'), output_path=str(folder/'worker-result.json'))
    write_json(folder/'job.json', job)
    env = dict(os.environ, **THREAD_LIMITS, PYTHONHASHSEED=str(job['config']['random_seed']), PYTHONIOENCODING='utf-8')
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    start = time.perf_counter()
    peak, last_phase, status, reason = 0, {'stage':'starting'}, None, None
    with (folder/'stdout.log').open('w',encoding='utf-8') as out, (folder/'stderr.log').open('w',encoding='utf-8') as err:
        process = subprocess.Popen([sys.executable,'-m','app.benchmark.worker',str(folder/'job.json')],
            stdout=out, stderr=err, env=env, creationflags=creationflags)
        try:
            monitor = psutil.Process(process.pid)
            while process.poll() is None:
                try: peak = max(peak,monitor.memory_info().rss)
                except psutil.NoSuchProcess: pass
                try: last_phase = json.loads((folder/'phase.json').read_text(encoding='utf-8'))
                except (OSError,ValueError): pass
                elapsed = time.perf_counter()-start
                timeout = job['config']['timeout']
                phase_elapsed = time.monotonic()-last_phase.get('monotonic', time.monotonic())
                if peak > job['config']['measurement']['rss_limit_mb']*1024**2:
                    status,reason = 'resource_limit','Sampled worker RSS exceeded configured limit.'
                elif elapsed > timeout['trial_seconds']:
                    status,reason = 'timeout','Whole-trial wall-clock budget exceeded.'
                elif last_phase['stage'] in ('computing','warmup') and phase_elapsed > timeout['algorithm_seconds']:
                    status,reason = 'timeout','Compute/warmup wall-clock budget exceeded.'
                if status:
                    stop_process_tree(process)
                    break
                time.sleep(.005)
        finally:
            if process.poll() is None: stop_process_tree(process)
    wall = time.perf_counter()-start
    if status:
        result = dict(status=status, runtime_seconds=None,
                      error=dict(code=status,message=reason), stopped_stage=last_phase['stage'])
    else:
        try: result=json.loads((folder/'worker-result.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):
            result=dict(status='worker_error',runtime_seconds=None,
                        error=dict(code='worker_error',message=f'Worker exited {process.returncode} without valid result.'))
        if result.get('runtime_seconds') is not None and result['runtime_seconds']>job['config']['timeout']['algorithm_seconds']:
            result.update(status='timeout',runtime_seconds=None,
                error=dict(code='timeout',message='Completed compute exceeded budget between supervisor polls.'))
    result.update(trial_wall_seconds=wall, parent_sampled_peak_worker_rss_bytes=peak,
                  case_id=job['case']['case_id'], profile=job['profile'], repeat_index=job['repeat_index'],
                  worker_exit_code=process.returncode)
    write_json(folder/'trial.json',result)
    return result


def write_raw(path, rows):
    write_json(path/'raw-measurements.json', rows)
    columns = ['case_id','profile','repeat_index','status','runtime_seconds','trial_wall_seconds',
               'baseline_rss_bytes','sampled_peak_rss_bytes','process_peak_rss_bytes','result_path','error']
    with (path/'raw-measurements.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k:(json.dumps(row[k]) if k=='error' else row[k]) for k in columns})


def run_experiment(config, storage_root='experiments', progress=None):
    config=validate_config(config)
    graph,pipeline,warnings=load_source(config['source'])
    graph_identity=identity(graph)
    for key,value in config.get('expected_graph',{}).items():
        if graph_identity.get(key)!=value: raise ValueError(f'Expected graph {key} does not match source.')
    root=Path(storage_root).resolve()/config['experiment_id']
    root.mkdir(parents=True,exist_ok=True)
    saved=root/'configuration.json'
    effective=dict(config,expected_graph=graph_identity)
    if saved.exists():
        if json.loads(saved.read_text(encoding='utf-8'))!=effective:
            raise ValueError('Experiment ID already belongs to different configuration/source hash; use a new ID.')
    else: write_json(saved,effective)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
    run=root/'runs'/run_id
    run.mkdir(parents=True,exist_ok=False)
    write_json(run/'configuration.json',effective)
    write_json(run/'environment.json',dict(environment(),source_archive=archive_source(run)))
    write_json(run/'source-report.json',dict(identity=graph_identity,preflight_pipeline=pipeline,validation=warnings))
    write_json(run/'status.json',dict(status='running',run_id=run_id))
    rows,rankings,schedule=[],{},[]
    rng=random.Random(config['random_seed'])
    for profile,count in [('timing',config['repeat_count']),('memory',config['measurement']['memory_repeats'])]:
        for repeat in range(count):
            cases=list(config['algorithms']);rng.shuffle(cases)
            schedule.extend(dict(profile=profile,repeat_index=repeat,case=case) for case in cases)
    write_json(run/'schedule.json',schedule)
    try:
        for order,entry in enumerate(schedule):
            job=dict(config=config,identity=graph_identity,**entry)
            trial_folder=run/'trials'/f'{order:04}'
            trial=run_trial(job,trial_folder)
            ranking=trial.get('result')
            case_id=entry['case']['case_id']
            if trial['status']=='completed' and ranking:
                digest=hashlib.sha256(json.dumps(ranking['scores'],sort_keys=True).encode()).hexdigest()
                if case_id not in rankings:
                    rankings[case_id]=ranking
                    write_json(run/'rankings'/f'{case_id}.json',ranking)
                reference=hashlib.sha256(json.dumps(rankings[case_id]['scores'],sort_keys=True).encode()).hexdigest()
                consistent=digest==reference
            else: digest,consistent=None,None
            memory=trial.get('memory',{})
            rows.append(dict(case_id=case_id,profile=entry['profile'],repeat_index=entry['repeat_index'],
                status=trial['status'],runtime_seconds=trial.get('runtime_seconds'),
                trial_wall_seconds=trial['trial_wall_seconds'],pipeline=trial.get('pipeline'),
                baseline_rss_bytes=memory.get('baseline_rss_bytes'),
                sampled_peak_rss_bytes=memory.get('sampled_peak_rss_bytes'),
                process_peak_rss_bytes=memory.get('process_peak_rss_bytes'),
                sampled_peak_delta_bytes=memory.get('sampled_peak_delta_bytes'),
                ranking_sha256=digest,ranking_matches_reference=consistent,
                result_path=(trial_folder/'trial.json').relative_to(run).as_posix(),error=trial.get('error')))
            write_raw(run,rows)
            if progress: progress(f'{config["experiment_id"]} {order+1}/{len(schedule)} {case_id}: {trial["status"]}')
        aggregate={}
        for case in config['algorithms']:
            relevant=[r for r in rows if r['case_id']==case['case_id']]
            timing=[r for r in relevant if r['profile']=='timing' and r['status']=='completed']
            memory=[r for r in relevant if r['profile']=='memory' and r['status']=='completed']
            aggregate[case['case_id']]=dict(runtime_seconds=summarize([r['runtime_seconds'] for r in timing]),
                sampled_peak_rss_bytes=summarize([r['sampled_peak_rss_bytes'] for r in memory]),
                process_peak_rss_bytes=summarize([r['process_peak_rss_bytes'] for r in memory]),
                sampled_peak_delta_bytes=summarize([r['sampled_peak_delta_bytes'] for r in memory]),
                pipeline_seconds={k:summarize([(r['pipeline'] or {}).get(k) for r in timing]) for k in
                    ('dataset_load_validation_seconds','graph_build_seconds','snapshot_read_seconds','synthetic_generation_seconds')},
                status_counts={status:sum(r['status']==status for r in relevant) for status in sorted({r['status'] for r in relevant})},
                timing_successes=len(timing),memory_successes=len(memory),
                ranking_repeatable=all(r['ranking_matches_reference'] is not False for r in relevant) if timing else None,
                timing_complete=len(timing)==config['repeat_count'],
                memory_complete=len(memory)==config['measurement']['memory_repeats'])
        comparisons=[]
        exclusions=[]
        for a,b in combinations(sorted(rankings),2):
            reason=comparison_exclusion(rankings[a],rankings[b])
            if reason:
                exclusions.append(dict(left_case=a,right_case=b,reason=reason))
                continue
            comparisons.append(dict(left_case=a,right_case=b,**compare_rankings(rankings[a],rankings[b],config['top_k'])))
        write_json(run/'comparisons.json',comparisons)
        status='completed' if all(r['status']=='completed' for r in rows) else 'completed_with_failures'
        summary=dict(experiment_id=config['experiment_id'],run_id=run_id,status=status,
            graph=graph_identity,algorithm_cases=config['algorithms'],aggregated=aggregate,
            raw_trial_count=len(rows),rankings_available=sorted(rankings),comparison_exclusions=exclusions)
        write_json(run/'summary.json',summary)
        write_json(run/'status.json',dict(status=status,run_id=run_id))
    except BaseException as exc:
        write_json(run/'status.json',dict(status='interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',message=str(exc)))
        raise
    return run


def temporal_analysis(run_paths, output):
    records=[]
    for path in run_paths:
        path=Path(path)
        summary=json.loads((path/'summary.json').read_text(encoding='utf-8'))
        env=json.loads((path/'environment.json').read_text(encoding='utf-8'))
        records.append((summary['graph']['selected_period'],path,summary,env))
    records.sort(key=lambda x:x[0])
    if len(records)<2 or len({r[0] for r in records})!=len(records):
        raise ValueError('Temporal analysis needs >=2 distinct observed periods.')
    for _,_,summary,_ in records:
        if summary['graph']['data_kind']=='synthetic': raise ValueError('Synthetic labels are not real historical dates.')
    pairs=[]
    for left,right in zip(records,records[1:]):
        lp,lpath,ls,le=left;rp,rpath,rs,re=right
        if any(ls['graph'][k]!=rs['graph'][k] for k in ('dataset_id','dataset_version','direction','creditor_scope','debtor_scope')):
            raise ValueError('Temporal graph sources/scopes differ.')
        same_environment=le==re
        cases=[]
        for case in sorted(set(ls['rankings_available'])&set(rs['rankings_available'])):
            a=json.loads((lpath/'rankings'/f'{case}.json').read_text(encoding='utf-8'))
            b=json.loads((rpath/'rankings'/f'{case}.json').read_text(encoding='utf-8'))
            comparison=compare_rankings(a,b,temporal=True)
            cases.append(dict(case_id=case,comparison=comparison,
                left_median_seconds=ls['aggregated'][case]['runtime_seconds']['median'],
                right_median_seconds=rs['aggregated'][case]['runtime_seconds']['median']))
        pairs.append(dict(left_period=lp,right_period=rp,left_density=ls['graph']['density'],
            right_density=rs['graph']['density'],same_recorded_environment=same_environment,cases=cases))
    result=dict(pairs=pairs,interpretation='Common-node ranking stability, not predictive accuracy; entry/exit nodes explicitly listed.')
    if Path(output).exists(): raise ValueError('Temporal output exists; choose new path.')
    write_json(output,result)
    return result
