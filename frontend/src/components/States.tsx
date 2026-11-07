import { AlertCircle, CheckCircle2, LoaderCircle } from 'lucide-react';
import type { Job } from '../api/types';
import { post } from '../api/client';
import { useState } from 'react';

export function Status({ loading, error, empty, children }: { loading?: boolean; error?: string | null; empty?: string; children?: React.ReactNode }) {
  if (loading) return <div className="state" role="status"><LoaderCircle className="spin" size={22} /> Loading research data…</div>;
  if (error) return <div className="state error" role="alert"><AlertCircle size={22} /><div><strong>Unable to load data</strong><p>{error}</p></div></div>;
  if (empty) return <div className="state empty"><span className="empty-mark">∅</span><div><strong>No results yet</strong><p>{empty}</p></div></div>;
  return <>{children}</>;
}
export function JobStatus({ job, error, onResults }: { job: Job | null; error?: string | null; onResults?: (id: string) => void }) {
  const [cancelError,setCancelError]=useState<string|null>(null);
  if (error) return <div className="notice error" role="alert">{error}</div>;
  if (!job) return null;
  const active = job.status === 'queued' || job.status === 'running';
  return <div className={`job-status ${job.status}`} role="status" aria-live="polite">
    {active ? <LoaderCircle size={20} className="spin" /> : <CheckCircle2 size={20} />}
    <div className="grow"><strong>Job {job.status}</strong><p>{job.progress?.message || 'Local calculation job'}</p>
      {job.progress?.total != null && <progress aria-label="Completed benchmark trials" value={job.progress.completed ?? 0} max={job.progress.total} />}
      {job.error && <p className="error-text">{typeof job.error === 'string' ? job.error : job.error.message}</p>}
      {cancelError && <p role="alert" className="error-text">{cancelError}</p>}
    </div>
    {active && <button className="button secondary" disabled={job.cancel_requested} onClick={() => { setCancelError(null); void post(`/jobs/${job.id}/cancel`, {}).catch(e=>setCancelError(e instanceof Error?e.message:'Cancellation failed.')); }}>{job.cancel_requested ? 'Cancelling…' : 'Cancel'}</button>}
    {job.result?.experiment_id && onResults && <button className="button secondary" onClick={() => onResults(job.result!.experiment_id!)}>View results</button>}
  </div>;
}
