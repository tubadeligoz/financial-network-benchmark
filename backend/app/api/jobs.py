import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import uuid
import logging

from app.api.repository import read_json
from app.benchmark.manager import stop_process_tree, THREAD_LIMITS
from app.datasets.io import write_json

logger=logging.getLogger(__name__)


class Jobs:
    def __init__(self, root):
        self.root=Path(root)
        self.folder=self.root/'data/processed/web/jobs'
        self.queue=queue.Queue()
        self.jobs={}
        self.lock=threading.RLock()
        self.stop=threading.Event()
        self.thread=None

    def start(self):
        for path in self.folder.glob('*/status.json'):
            job=read_json(path)
            if not job: continue
            if job['status'] in ('queued','running'):
                job.update(status='failed',error='API restarted before completion; job was not resumed.')
                write_json(path,job)
            self.jobs[job['id']]=job
        self.thread=threading.Thread(target=self.loop,daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()
        with self.lock:
            for job in self.jobs.values():
                if job['status'] in ('queued','running'):
                    job['cancel_requested']=True
                    if job['status']=='queued': job['status']='cancelled'
                    self.save(job)
        if self.thread: self.thread.join(timeout=8)

    def save(self, job):
        write_json(self.folder/job['id']/'status.json',job)

    def submit(self, kind, payload):
        with self.lock:
            if sum(j['status'] in ('queued','running') for j in self.jobs.values())>=8:
                raise ValueError('The local queue is full. Wait for an active job to finish.')
            jid=uuid.uuid4().hex
            job=dict(id=jid,kind=kind,status='queued',created_at=time.time(),cancel_requested=False,
                     error=None,result=None)
            self.jobs[jid]=job
            write_json(self.folder/jid/'request.json',dict(kind=kind,root=str(self.root),payload=payload))
            self.save(job)
            self.queue.put(jid)
            logger.info('Job queued id=%s kind=%s',jid,kind)
            return dict(job)

    def get(self, jid):
        with self.lock:
            if jid not in self.jobs: raise KeyError('Job not found.')
            job=dict(self.jobs[jid])
        job['progress']=read_json(self.folder/jid/'progress.json')
        return job

    def cancel(self, jid):
        with self.lock:
            job=self.jobs[jid]
            if job['status'] in ('queued','running'):
                job['cancel_requested']=True
                if job['status']=='queued': job['status']='cancelled'
                self.save(job)
        return self.get(jid)

    def loop(self):
        while not self.stop.is_set():
            try: jid=self.queue.get(timeout=.1)
            except queue.Empty: continue
            with self.lock:
                job=self.jobs[jid]
                if job['cancel_requested']: continue
                job['status']='running';job['started_at']=time.time();self.save(job)
                logger.info('Job started id=%s kind=%s',jid,job['kind'])
            folder=self.folder/jid
            process=None
            try:
                env=dict(os.environ,**THREAD_LIMITS,PYTHONIOENCODING='utf-8')
                with (folder/'worker.log').open('w',encoding='utf-8') as log:
                    process=subprocess.Popen([sys.executable,'-m','app.api.worker',str(folder/'request.json')],
                        stdout=log,stderr=log,env=env,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                    while process.poll() is None:
                        if self.stop.is_set() or job['cancel_requested'] or time.time()-job['started_at']>1800:
                            stop_process_tree(process)
                            break
                        time.sleep(.1)
                result=read_json(folder/'result.json')
                with self.lock:
                    job['result']=result
                    if job['cancel_requested'] or self.stop.is_set(): job['status']='cancelled'
                    elif process.returncode==0 and result and result.get('status')=='completed': job['status']='completed'
                    else:
                        job['status']='failed'
                        job['error']=(result or {}).get('error') or 'Worker failed or exceeded the 30-minute local job budget. See local worker log.'
                    job['finished_at']=time.time();self.save(job)
                    logger.info('Job finished id=%s status=%s',jid,job['status'])
            except Exception as exc:
                logger.exception('Job failed id=%s',jid)
                if process is not None and process.poll() is None: stop_process_tree(process)
                with self.lock:
                    job.update(status='failed',error=str(exc),finished_at=time.time());self.save(job)
