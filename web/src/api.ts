export type { Tokens, Organization, Profile as User } from '../../packages/api-client/src';
export class ApiError extends Error {
  constructor(message: string, public status: number, public data?: unknown) { super(message); }
}
export async function request<T>(path: string, options: RequestInit = {}, access?: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options, headers: { 'Content-Type': 'application/json', ...(access ? { Authorization: `Bearer ${access}` } : {}), ...options.headers },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null) as { message?: string; details?: Record<string, unknown> } | null;
    throw new ApiError(data?.details ? Object.values(data.details).flat().join(' ') : data?.message || `Request failed (${response.status}).`, response.status, data);
  }
  if (response.status === 204) return undefined as T;
  return response.headers.get('Content-Type')?.includes('application/json') ? response.json() as Promise<T> : response.blob() as Promise<T>;
}
