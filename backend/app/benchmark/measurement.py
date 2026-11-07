import threading
import time

import psutil


class KernelMeasurement:
    """Compute boundary only; sampler is enabled only in separate memory trials."""
    def __init__(self, profile, interval_ms, phase):
        self.profile, self.interval, self.phase = profile, interval_ms/1000, phase
        self.values = {}
        self.samples = []
        self.stop = threading.Event()
        self.proc = psutil.Process()

    def sample(self):
        self.samples.append((time.perf_counter_ns(), self.proc.memory_info().rss))

    def monitor(self):
        while not self.stop.wait(self.interval): self.sample()

    def __enter__(self):
        self.values['baseline_rss_bytes'] = self.proc.memory_info().rss
        if self.profile == 'memory':
            self.sample()
            self.thread = threading.Thread(target=self.monitor, daemon=True)
            self.thread.start()
        self.phase('computing')
        self.start_cpu = time.process_time_ns()
        self.start = time.perf_counter_ns()
        return self

    def __exit__(self, *exc):
        elapsed = (time.perf_counter_ns()-self.start)/1e9
        cpu = (time.process_time_ns()-self.start_cpu)/1e9
        self.values.update(attempt_compute_seconds=elapsed, cpu_seconds=cpu,
                           effective_cpu_percent=100*cpu/elapsed if elapsed else None)
        self.phase('postprocessing')
        if self.profile == 'memory':
            self.sample()
            self.stop.set()
            self.thread.join()
            peak = max(x[1] for x in self.samples)
            self.values.update(sampled_peak_rss_bytes=peak,
                sampled_peak_delta_bytes=max(0,peak-self.values['baseline_rss_bytes']),
                sample_count=len(self.samples),
                maximum_sample_gap_ms=max((b[0]-a[0])/1e6 for a,b in zip(self.samples,self.samples[1:])),
                sample_interval_ms=self.interval*1000)
        else:
            self.values.update(sampled_peak_rss_bytes=None, sampled_peak_delta_bytes=None)


def process_peak():
    info = psutil.Process().memory_info()
    if hasattr(info, 'peak_wset'):
        return dict(process_peak_rss_bytes=info.peak_wset, process_peak_method='Windows peak working set through result assembly')
    try:
        import resource, sys
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return dict(process_peak_rss_bytes=int(peak if sys.platform=='darwin' else peak*1024),
                    process_peak_method='OS process lifetime high-water mark through result assembly')
    except ImportError:
        return dict(process_peak_rss_bytes=None, process_peak_method='unavailable')
