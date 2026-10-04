import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
export type { Organization, Profile as User, Tokens } from '../../packages/api-client/src';
export const apiBase = (process.env.EXPO_PUBLIC_API_BASE_URL ?? (Platform.OS === 'android' ? 'http://10.0.2.2:8000/api/v1' : 'http://localhost:8000/api/v1')).replace(/\/$/, '');
const refreshKey = 'ticket.refresh'; let browserRefresh: string | null = null;
export async function saveRefresh(value: string | null) {
  if (Platform.OS === 'web') { browserRefresh = value; return; }
  if (value) await SecureStore.setItemAsync(refreshKey, value, { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY });
  else await SecureStore.deleteItemAsync(refreshKey);
}
export function getRefresh() { return Platform.OS === 'web' ? Promise.resolve(browserRefresh) : SecureStore.getItemAsync(refreshKey); }
export class ApiError extends Error { constructor(message: string, public status: number, public data?: unknown) { super(message); } }
export async function request<T>(path: string, options: RequestInit = {}, access?: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, { ...options,
    headers: { 'Content-Type': 'application/json', ...(access ? { Authorization: `Bearer ${access}` } : {}), ...options.headers } });
  if (!response.ok) {
    const data = await response.json().catch(() => null) as { message?: string; details?: Record<string, unknown> } | null;
    throw new ApiError(data?.details ? Object.values(data.details).flat().join(' ') : data?.message ?? `Request failed (${response.status}).`, response.status, data);
  }
  if (response.status === 204) return undefined as T;
  return response.headers.get('Content-Type')?.includes('application/json') ? response.json() as Promise<T> : response.blob() as Promise<T>;
}
