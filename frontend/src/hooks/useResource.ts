import { useEffect, useState } from 'react';
import { api, errorText } from '../api/client';

export function useResource<T>(path: string | null, revision = 0) {
  const key=`${path ?? ''}#${revision}`;
  const [state, setState] = useState<{key:string; data: T | null; loading: boolean; error: string | null }>({key, data: null, loading: !!path, error: null });
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    setState({key, data: null, loading: true, error: null });
    api<T>(path, { signal: controller.signal }).then(data => {
      if (!controller.signal.aborted) setState({key, data, loading: false, error: null });
    }).catch(error => {
      if (!controller.signal.aborted) setState({key, data: null, loading: false, error: errorText(error) });
    });
    return () => controller.abort();
  }, [path, revision,key]);
  return path && state.key===key ? state : { data: null, loading: !!path, error: null };
}
