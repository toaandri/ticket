export interface User {
  id: string;
  email: string;
  display_name: string;
  email_verified_at: string | null;
}
export interface Organization {
  id: string;
  name: string;
  slug: string;
  owner: string;
}
export interface Tokens {
  access: string;
  refresh: string;
}
export async function request<T>(path: string, options: RequestInit = {}, access?: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(access ? { Authorization: `Bearer ${access}` } : {}), ...options.headers },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null) as { message?: string; details?: Record<string, unknown> } | null;
    const details = data?.details ? Object.values(data.details).flat().join(' ') : '';
    throw new Error(details || data?.message || `Request failed (${response.status}).`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
