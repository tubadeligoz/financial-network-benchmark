"""One trial per OS process. Invoked only by manager's bounded subprocess runner."""
import gc
import json
from pathlib import Path
import sys
import time

from app.algorithms import AlgorithmEngine
from app.benchmark.measurement import KernelMeasurement, process_peak
from app.benchmark.source import load_source, identity
from app.datasets.io import write_json


def execute(job):
    phase_path = Path(job['phase_path'])
    def phase(name):
        tmp = phase_path.with_suffix('.tmp')
        write_json(tmp, dict(stage=name, monotonic=time.monotonic()))
        for attempt in range(20):
            try:
                tmp.replace(phase_path)
                break
            except PermissionError:
                if attempt==19: raise
                time.sleep(.001)
    phase('loading')
    graph, pipeline, warnings = load_source(job['config']['source'])
    actual = identity(graph)
    if actual != job['identity']: raise ValueError('Worker graph differs from preflight identity.')
    engine = AlgorithmEngine()
    case = job['case']
    for _ in range(job['config']['warmup_count']):
        phase('warmup')
        warm = engine.run(case['algorithm_id'], graph, case['parameters'])
        if warm.status != 'completed':
            return dict(status=warm.status, runtime_seconds=None, pipeline=pipeline,
                        result=warm.to_dict(), identity=actual, error=warm.error)
        del warm
    gc.collect()
    phase('preparing')
    measurement = KernelMeasurement(job['profile'], job['config']['measurement']['sample_interval_ms'], phase)
    start = time.perf_counter_ns()
    result = engine.run(case['algorithm_id'], graph, case['parameters'], compute_context=lambda: measurement)
    engine_elapsed = (time.perf_counter_ns()-start)/1e9
    result.experiment_id = job['config']['experiment_id']
    measured = dict(measurement.values)
    measured.update(process_peak())
    phase('finished')
    return dict(status=result.status, runtime_seconds=(measured.get('attempt_compute_seconds')
        if result.status=='completed' else None), engine_elapsed_seconds=engine_elapsed,
        pipeline=pipeline, memory=measured, result=result.to_dict(), identity=actual, error=result.error)


def main():
    job = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    try:
        result = execute(job)
    except Exception as exc:
        result = dict(status='worker_error', runtime_seconds=None,
                      error=dict(code='worker_error',message=str(exc)))
    write_json(job['output_path'], result)


if __name__ == '__main__': main()
