import { useEffect, useState } from 'react';
import { api, errorText } from '../api/client';
import type { Job } from '../api/types';

export function useJob(id: string | null) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!id) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    setJob(null); setError(null);
    const poll = async () => {
      try {
        const value = await api<Job>(`/jobs/${id}`);
        if (stopped) return;
        setJob(value);
        if (value.status === 'queued' || value.status === 'running') timer = setTimeout(poll, 1000);
      } catch (err) { if (!stopped) setError(errorText(err)); }
    };
    void poll();
    return () => { stopped = true; clearTimeout(timer); };
  }, [id]);
  return { job: id ? job : null, error: id ? error : null };
}
