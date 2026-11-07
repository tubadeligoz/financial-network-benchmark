export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options, headers: { 'Content-Type': 'application/json', 'X-FNB-Client': 'local-web', ...options.headers },
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null;
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status}). Check the selected data and parameters.`);
  }
  return response.json() as Promise<T>;
}
export const base = (dataset: string, period: string) => `/datasets/${encodeURIComponent(dataset)}/periods/${encodeURIComponent(period)}`;
export const post = <T>(path: string, data: unknown) => api<T>(path, { method: 'POST', body: JSON.stringify(data) });
export const fmt = (value: number | null | undefined, digits = 2) => value == null ? 'Not calculated' : value !== 0 && Math.abs(value) < 10 ** -digits ? value.toExponential(2) : new Intl.NumberFormat('en', { maximumFractionDigits: digits }).format(value);
export const errorText = (error: unknown) => error instanceof Error ? error.message : 'The request could not be completed.';
